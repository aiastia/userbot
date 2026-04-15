#!/bin/bash
# Telegram Userbot 启动脚本

set -e

echo "🚀 Telegram Userbot 启动脚本"
echo "================================"

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

# 检查并创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建 Python 虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "📥 安装/更新依赖..."
pip install -q -r requirements.txt

# 创建必要目录
mkdir -p downloads
mkdir -p logs

# 启动
echo ""
echo "▶️  启动 Userbot..."
python main.py