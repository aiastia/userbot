"""关键词转发处理器 - 监控关键词并转发到指定目标"""
import re
import logging
from telethon import events
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class KeywordHandler:
    """
    监控指定聊天中的消息
    当消息包含指定关键词时，转发到目标机器人
    内置限速机制防止被封
    """

    def __init__(self, client, config):
        self.client = client
        self.config = config
        self.keywords = [kw.lower() for kw in config.get("keywords", [])]
        self.forward_to = config.get("forward_to")
        self.forward_media = config.get("forward_media", True)
        self.include_source_info = config.get("include_source_info", True)
        self.watch_chats = config.get("watch_chats", ["all"])
        self.exclude_chats = config.get("exclude_chats", [])

        # 初始化限速器
        rate_config = config.get("rate_limit", {})
        self.rate_limiter = RateLimiter(
            max_per_minute=rate_config.get("max_per_minute", 5),
            max_per_hour=rate_config.get("max_per_hour", 30),
            min_interval=rate_config.get("min_interval", 3),
        )

        # 统计信息
        self.stats = {
            "total_matched": 0,
            "total_forwarded": 0,
            "total_rate_limited": 0,
        }

        if not self.forward_to:
            logger.warning("⚠️ 未设置转发目标 (forward_to)，关键词转发功能将无法工作")

    def register(self):
        """注册事件处理器"""
        if not self.forward_to:
            logger.error("无法注册关键词转发处理器: 未设置 forward_to")
            return

        @self.client.on(events.NewMessage(func=self._should_process))
        async def handle_keyword(event):
            await self._process_keyword(event)

        logger.info(
            f"关键词监控已注册 - 关键词: {self.keywords}, "
            f"转发目标: {self.forward_to}"
        )

    def _should_process(self, event):
        """判断是否需要处理该消息"""
        message = event.message
        if not message or not message.text:
            return False

        # 检查排除列表
        chat_id = event.chat_id
        if chat_id in self.exclude_chats:
            return False

        return True

    def _match_keywords(self, text):
        """检查文本是否包含关键词，返回匹配到的关键词列表"""
        text_lower = text.lower()
        matched = [kw for kw in self.keywords if kw in text_lower]
        return matched

    async def _process_keyword(self, event):
        """处理关键词匹配"""
        try:
            message = event.message
            text = message.text or ""
            matched_keywords = self._match_keywords(text)

            if not matched_keywords:
                return

            self.stats["total_matched"] += 1
            chat_title = await self._get_chat_title(event)

            logger.info(
                f"🔍 关键词匹配! 来源: {chat_title} | "
                f"匹配词: {matched_keywords} | "
                f"消息: {text[:50]}..."
            )

            # 通过限速器
            await self.rate_limiter.acquire()

            # 构建转发内容
            forward_text = await self._build_forward_text(message, event, matched_keywords)

            try:
                # 尝试直接转发消息
                if self.forward_media and message.media:
                    await self.client.send_message(
                        self.forward_to,
                        forward_text,
                        file=message.media,
                        link_preview=False,
                    )
                else:
                    await self.client.send_message(
                        self.forward_to,
                        forward_text,
                        link_preview=False,
                    )

                self.stats["total_forwarded"] += 1
                logger.info(f"✅ 已转发到 {self.forward_to}")

            except Exception as send_err:
                # 如果发送失败，尝试只发文字
                logger.warning(f"转发失败（尝试仅文字）: {send_err}")
                try:
                    await self.client.send_message(
                        self.forward_to,
                        forward_text,
                        link_preview=False,
                    )
                    self.stats["total_forwarded"] += 1
                    logger.info(f"✅ 已转发文字到 {self.forward_to}")
                except Exception as e2:
                    logger.error(f"转发文字也失败: {e2}")

        except Exception as e:
            logger.error(f"处理关键词转发时出错: {e}", exc_info=True)

    async def _build_forward_text(self, message, event, matched_keywords):
        """构建转发的消息文本"""
        parts = []

        # 添加来源信息
        if self.include_source_info:
            chat_title = await self._get_chat_title(event)
            sender = await self._get_sender_name(event)
            date_str = message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else "未知时间"

            parts.append("📢 **关键词告警**")
            parts.append(f"📌 匹配词: {', '.join(matched_keywords)}")
            parts.append(f"👤 来源: {sender}")
            parts.append(f"💬 群组: {chat_title}")
            parts.append(f"🕐 时间: {date_str}")
            parts.append(f"🔗 消息ID: `{message.id}`")
            parts.append("")
            parts.append("📝 **原文内容:**")
            parts.append("─" * 30)

        # 添加原文
        if message.text:
            parts.append(message.text)

        return "\n".join(parts)

    async def _get_chat_title(self, event):
        """获取聊天标题"""
        try:
            chat = await event.get_chat()
            if hasattr(chat, "title"):
                return chat.title
            elif hasattr(chat, "first_name"):
                return chat.first_name
            return str(event.chat_id)
        except Exception:
            return str(event.chat_id)

    async def _get_sender_name(self, event):
        """获取发送者名称"""
        try:
            sender = await event.get_sender()
            if sender:
                if hasattr(sender, "first_name"):
                    name = sender.first_name
                    if hasattr(sender, "last_name") and sender.last_name:
                        name += f" {sender.last_name}"
                    return name
                elif hasattr(sender, "title"):
                    return sender.title
            return "未知用户"
        except Exception:
            return "未知用户"

    def get_stats(self):
        """获取统计信息"""
        stats = self.stats.copy()
        stats["rate_limiter"] = self.rate_limiter.status
        return stats