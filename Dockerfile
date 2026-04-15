FROM python:3.11-slim

LABEL maintainer="userbot"
LABEL description="Telegram Userbot - 视频监控与关键词转发"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要目录
RUN mkdir -p /app/downloads /app/logs

# 启动
CMD ["python", "main.py"]