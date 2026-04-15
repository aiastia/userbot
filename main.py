#!/usr/bin/env python3
"""
Telegram Userbot - 视频监控 + 关键词转发
功能:
  1. 监控聊天中的视频，按时长/大小条件自动下载
  2. 监控关键词，自动转发匹配消息到指定机器人（含限速）
"""
import os
import sys
import logging
import asyncio
from datetime import datetime

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from utils.config_loader import ConfigLoader
from handlers.video_handler import VideoHandler
from handlers.keyword_handler import KeywordHandler


def setup_logging(config):
    """配置日志"""
    log_config = config.logging_config
    level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    log_file = log_config.get("log_file", "./logs/userbot.log")

    # 确保日志目录存在
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # 配置日志格式
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 同时输出到文件和控制台
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    return logging.getLogger("Userbot")


async def main():
    """主函数"""
    # 加载配置
    try:
        config = ConfigLoader("config.yaml")
    except FileNotFoundError:
        print("❌ 找不到 config.yaml 配置文件！")
        print("请复制 config.yaml 并填写你的 Telegram API 信息。")
        sys.exit(1)

    # 配置日志
    logger = setup_logging(config)
    logger.info("=" * 50)
    logger.info("Telegram Userbot 启动中...")
    logger.info("=" * 50)

    # 获取 Telegram 配置
    tg_config = config.telegram
    api_id = tg_config.get("api_id")
    api_hash = tg_config.get("api_hash")
    phone_number = tg_config.get("phone_number")
    session_name = tg_config.get("session_name", "userbot_session")

    if not api_id or api_id == 12345678:
        logger.error("❌ 请在 config.yaml 中设置正确的 api_id")
        sys.exit(1)
    if not api_hash or api_hash == "your_api_hash_here":
        logger.error("❌ 请在 config.yaml 中设置正确的 api_hash")
        sys.exit(1)
    if not phone_number:
        logger.error("❌ 请在 config.yaml 中设置 phone_number")
        sys.exit(1)

    # 创建 Telegram 客户端
    client = TelegramClient(session_name, api_id, api_hash)

    # 连接并登录
    await client.connect()
    logger.info("已连接到 Telegram 服务器")

    if not await client.is_user_authorized():
        logger.info("需要登录验证...")
        await client.send_code_request(phone_number)
        code = input("请输入收到的验证码: ")
        try:
            await client.sign_in(phone_number, code)
        except SessionPasswordNeededError:
            password = input("请输入两步验证密码: ")
            await client.sign_in(password=password)
        logger.info("✅ 登录成功!")
    else:
        logger.info("✅ 已使用现有会话登录")

    # 获取当前用户信息
    me = await client.get_me()
    logger.info(f"👤 已登录为: {me.first_name} (ID: {me.id})")

    # ========== 注册处理器 ==========

    # 功能1: 视频监控
    video_handler = None
    if config.video_monitor.get("enabled", False):
        video_handler = VideoHandler(client, config.video_monitor)
        video_handler.register()
        logger.info("📹 视频监控功能已启用")
    else:
        logger.info("📹 视频监控功能未启用")

    # 功能2: 关键词转发
    keyword_handler = None
    if config.keyword_forward.get("enabled", False):
        keyword_handler = KeywordHandler(client, config.keyword_forward)
        keyword_handler.register()
        logger.info("🔑 关键词转发功能已启用")
    else:
        logger.info("🔑 关键词转发功能未启用")

    # 注册管理命令（通过 Telegram 私聊自己发送命令）
    @client.on(events.NewMessage(outgoing=True, func=lambda e: e.is_private and e.chat_id == me.id))
    async def handle_commands(event):
        """处理管理命令（给自己发消息来控制）"""
        text = event.text.strip()

        if text == "!status" or text == "/status":
            status_lines = ["📊 **Userbot 状态**", f"⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]

            if video_handler:
                stats = video_handler.get_stats()
                status_lines.append(f"📹 视频监控: ✅ 运行中")
                status_lines.append(f"  - 最小时长: {video_handler.min_duration}s")
                status_lines.append(f"  - 最小大小: {video_handler.min_size_mb}MB")
                status_lines.append(f"  - 转发目标: {video_handler.forward_to}")
                status_lines.append(f"  - 下载到本地: {'是' if video_handler.download_enabled else '否'}")
                status_lines.append(f"  - 已检查: {stats['total_checked']} | 已转发: {stats['total_forwarded']} | 已下载: {stats['total_downloaded']} | 跳过: {stats['total_skipped']}")
            else:
                status_lines.append("📹 视频监控: ❌ 未启用")

            if keyword_handler:
                stats = keyword_handler.get_stats()
                status_lines.append(f"🔑 关键词转发: ✅ 运行中")
                status_lines.append(f"  - 关键词: {keyword_handler.keywords}")
                status_lines.append(f"  - 匹配次数: {stats['total_matched']}")
                status_lines.append(f"  - 转发次数: {stats['total_forwarded']}")
                rl = stats["rate_limiter"]
                status_lines.append(f"  - 限速: {rl['minute_used']}/{rl['minute_limit']}/min, {rl['hour_used']}/{rl['hour_limit']}/h")
            else:
                status_lines.append("🔑 关键词转发: ❌ 未启用")

            await event.respond("\n".join(status_lines))

        elif text == "!help" or text == "/help":
            help_text = """
📖 **Userbot 命令帮助**

给自己发以下命令来管理：

`!status` - 查看运行状态
`!help` - 显示此帮助信息

⚙️ **功能配置请修改 config.yaml**
修改后需要重启生效。
"""
            await event.respond(help_text)

    logger.info("📋 管理命令已注册 (给自己发 !help 查看帮助)")
    logger.info("=" * 50)
    logger.info("🚀 Userbot 已启动，正在监听消息...")
    logger.info("按 Ctrl+C 停止")
    logger.info("=" * 50)

    # 运行直到断开
    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        logger.info("正在停止 Userbot...")
    finally:
        await client.disconnect()
        logger.info("👋 Userbot 已停止")


if __name__ == "__main__":
    asyncio.run(main())