# 🤖 Telegram Userbot

一个基于 [Telethon](https://github.com/LonamiWebs/Telethon) 的 Telegram Userbot，提供以下功能：

## ✨ 功能

### 📹 功能1: 视频监控与自动转发
- 监控指定聊天（群组/频道/私聊）中的视频消息
- 根据视频**时长**或**文件大小**条件自动转发到目标聊天
- 支持设置最小时长（秒）和最小大小（MB），满足其一即转发
- 支持普通视频和以文档形式发送的视频

### 🔑 功能2: 关键词转发
- 监控指定聊天中的文本消息
- 当消息包含设定的关键词时，自动转发到指定机器人
- **内置限速机制**，防止被 Telegram 限制：
  - 每分钟最大转发次数
  - 每小时最大转发次数
  - 两次转发最小间隔
- 转发时附带来源信息（发送者、群组、时间）

### 📋 管理命令
给自己（Saved Messages）发以下命令：
- `!status` - 查看运行状态和统计
- `!help` - 显示帮助信息

## 🚀 快速开始

### 1. 获取 Telegram API 凭证
1. 访问 https://my.telegram.org
2. 登录并进入 **API development tools**
3. 创建应用获取 `api_id` 和 `api_hash`

### 2. 配置
编辑 `config.yaml`，填入你的信息：
```yaml
telegram:
  api_id: 你的API_ID        # 数字
  api_hash: "你的API_HASH"   # 字符串
  phone_number: "+86xxxxxxxxx"  # 带国际区号的手机号
```

### 3. 启动
```bash
# 方式1: 使用启动脚本（推荐）
./start.sh

# 方式2: 手动启动
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

首次启动需要输入验证码登录。

## ⚙️ 配置说明

### 视频监控配置
```yaml
video_monitor:
  enabled: true
  watch_chats: ["all"]       # 监控所有聊天，或指定 ID/用户名
  exclude_chats: []           # 排除的聊天
  min_duration: 60            # 最小时长（秒）
  min_size_mb: 10             # 最小大小（MB）
  forward_to: "target_chat"   # 转发目标聊天（用户名或ID）
  include_documents: true     # 是否包括以文档发送的视频
```

### 关键词转发配置
```yaml
keyword_forward:
  enabled: true
  watch_chats: ["all"]
  keywords: ["紧急", "重要", "通知"]
  forward_to: "your_bot_username"  # 转发目标
  rate_limit:
    max_per_minute: 5    # 每分钟最多5次
    max_per_hour: 30     # 每小时最多30次
    min_interval: 3      # 两次转发至少间隔3秒
```

## ⚠️ 注意事项

1. **Session 文件安全**: `.session` 文件包含你的登录凭证，**绝对不能分享或上传到公开仓库**
2. **遵守 Telegram ToS**: 不建议过度频繁操作，可能被封号
3. **限速设置**: 建议保持默认限速设置，避免触发 Telegram 的反滥用机制
4. **首次运行**: 需要交互式输入验证码，请在终端中运行

## 📁 项目结构

```
userbot/
├── config.yaml              # 配置文件
├── main.py                  # 主程序入口
├── requirements.txt         # Python 依赖
├── start.sh                 # 启动脚本
├── handlers/
│   ├── video_handler.py     # 视频监控处理器
│   └── keyword_handler.py   # 关键词转发处理器
├── utils/
│   ├── config_loader.py     # 配置加载器
│   └── rate_limiter.py      # 限速器
└── logs/                    # 日志文件（自动创建）
```

## 🔧 依赖

- Python 3.8+
- Telethon >= 1.34.0
- PyYAML >= 6.0
- aiofiles >= 23.0

## License

MIT