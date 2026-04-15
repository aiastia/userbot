"""视频监控处理器 - 监控聊天中的视频并转发到指定聊天（可选下载）"""
import os
import logging
from telethon import events
from telethon.tl.types import (
    MessageMediaDocument,
    DocumentAttributeVideo,
    DocumentAttributeFilename,
)

logger = logging.getLogger(__name__)


class VideoHandler:
    """
    监控指定聊天中的视频消息
    根据视频时长和大小条件，自动转发到目标聊天
    """

    def __init__(self, client, config):
        self.client = client
        self.config = config
        self.min_duration = config.get("min_duration", 60)  # 秒
        self.min_size_mb = config.get("min_size_mb", 10)  # MB
        self.forward_to = config.get("forward_to")  # 转发目标聊天
        self.include_documents = config.get("include_documents", True)
        self.watch_chats = config.get("watch_chats", ["all"])
        self.exclude_chats = config.get("exclude_chats", [])

        # 是否同时下载到本地（默认否）
        self.download_enabled = config.get("download_enabled", False)
        self.download_dir = config.get("download_dir", "./downloads")

        # 统计
        self.stats = {
            "total_checked": 0,
            "total_forwarded": 0,
            "total_downloaded": 0,
            "total_skipped": 0,
        }

        # 确保下载目录存在（如果启用了下载）
        if self.download_enabled:
            os.makedirs(self.download_dir, exist_ok=True)

        if not self.forward_to:
            logger.warning("⚠️ 未设置视频转发目标 (forward_to)，视频转发功能将无法工作")

    def register(self):
        """注册事件处理器"""
        if not self.forward_to:
            logger.error("无法注册视频监控处理器: 未设置 forward_to")
            return

        @self.client.on(events.NewMessage(func=self._should_process))
        async def handle_video(event):
            await self._process_video(event)

        logger.info(
            f"视频监控已注册 - 最小时长: {self.min_duration}s, "
            f"最小大小: {self.min_size_mb}MB, "
            f"转发到: {self.forward_to}, "
            f"下载到本地: {'是' if self.download_enabled else '否'}"
        )

    def _should_process(self, event):
        """判断是否需要处理该消息"""
        message = event.message
        if not message or not message.media:
            return False

        # 检查是否是视频类型的文档
        is_video = isinstance(message.media, MessageMediaDocument)
        if not is_video:
            return False

        # 检查排除列表
        chat_id = event.chat_id
        if chat_id in self.exclude_chats:
            return False

        return True

    async def _process_video(self, event):
        """处理视频消息 - 检查条件并转发"""
        try:
            message = event.message
            document = message.media.document

            self.stats["total_checked"] += 1

            # 获取视频属性
            video_attr = None
            filename = None
            for attr in document.attributes:
                if isinstance(attr, DocumentAttributeVideo):
                    video_attr = attr
                if isinstance(attr, DocumentAttributeFilename):
                    filename = attr.file_name

            if not video_attr:
                # 没有视频属性，检查是否是文档类视频
                if not self.include_documents:
                    return
                if document.mime_type and "video" in document.mime_type:
                    duration = 0
                    file_size_mb = document.size / (1024 * 1024)
                else:
                    return
            else:
                duration = video_attr.duration
                file_size_mb = document.size / (1024 * 1024)

            # 判断是否满足条件（时长 OR 大小，满足其一即可）
            meets_duration = duration >= self.min_duration
            meets_size = file_size_mb >= self.min_size_mb

            if not meets_duration and not meets_size:
                self.stats["total_skipped"] += 1
                logger.debug(
                    f"视频不满足条件 - 时长: {duration}s (需要>={self.min_duration}s), "
                    f"大小: {file_size_mb:.1f}MB (需要>={self.min_size_mb}MB)"
                )
                return

            # 满足条件，准备转发
            chat_title = await self._get_chat_title(event)
            reason = []
            if meets_duration:
                reason.append(f"时长{duration}s")
            if meets_size:
                reason.append(f"大小{file_size_mb:.1f}MB")

            logger.info(
                f"🎬 发现符合条件的视频! 来源: {chat_title} | "
                f"原因: {', '.join(reason)}"
            )

            # 构建转发说明
            caption = (
                f"📹 视频转发\n"
                f"📌 来源: {chat_title}\n"
                f"⏱ 时长: {duration}s\n"
                f"📦 大小: {file_size_mb:.1f}MB\n"
            )
            if filename:
                caption += f"📄 文件名: {filename}"
            if message.text:
                caption += f"\n💬 原文: {message.text}"

            # 转发消息到目标聊天
            try:
                # 方式1: 直接转发（保留原始信息）
                await self.client.forward_messages(
                    self.forward_to,
                    message,
                )
                self.stats["total_forwarded"] += 1
                logger.info(f"✅ 视频已转发到 {self.forward_to}")
            except Exception as fwd_err:
                # 转发失败时，尝试重新发送
                logger.warning(f"直接转发失败，尝试重新发送: {fwd_err}")
                try:
                    await self.client.send_message(
                        self.forward_to,
                        caption,
                        file=message.media,
                    )
                    self.stats["total_forwarded"] += 1
                    logger.info(f"✅ 视频已重新发送到 {self.forward_to}")
                except Exception as send_err:
                    logger.error(f"❌ 视频转发/发送均失败: {send_err}")

            # 如果启用了下载，同时保存到本地
            if self.download_enabled:
                try:
                    dl_filename = filename or f"video_{message.id}.mp4"
                    dl_filename = self._sanitize_filename(dl_filename)
                    dl_path = os.path.join(self.download_dir, dl_filename)
                    logger.info(f"📥 开始下载到本地: {dl_filename}")
                    result = await self.client.download_media(
                        message,
                        file=dl_path,
                        progress_callback=self._progress_callback,
                    )
                    if result:
                        self.stats["total_downloaded"] += 1
                        logger.info(f"✅ 已下载到: {result}")
                    else:
                        logger.warning(f"❌ 下载失败: {dl_filename}")
                except Exception as dl_err:
                    logger.error(f"下载出错: {dl_err}")

        except Exception as e:
            logger.error(f"处理视频时出错: {e}", exc_info=True)

    async def _get_chat_title(self, event):
        """获取聊天标题"""
        try:
            chat = await event.get_chat()
            if hasattr(chat, "title"):
                return chat.title
            elif hasattr(chat, "first_name"):
                return chat.first_name
            else:
                return str(event.chat_id)
        except Exception:
            return str(event.chat_id)

    def _progress_callback(self, received, total):
        """下载进度回调"""
        percentage = received / total * 100
        received_mb = received / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        if int(percentage) % 25 == 0:
            logger.info(f"  下载进度: {percentage:.0f}% ({received_mb:.1f}/{total_mb:.1f} MB)")

    @staticmethod
    def _sanitize_filename(filename):
        """清理文件名中的非法字符"""
        illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200] + ext
        return filename

    def get_stats(self):
        """获取统计信息"""
        return self.stats.copy()
