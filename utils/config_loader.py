"""配置加载器"""
import os
import yaml
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """加载和管理配置"""

    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.load()

    def load(self):
        """从 YAML 文件加载配置"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        logger.info(f"配置已从 {self.config_path} 加载")
        return self.config

    def get(self, key_path, default=None):
        """
        获取嵌套配置值
        用法: config.get("telegram.api_id")
        """
        keys = key_path.split(".")
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    @property
    def telegram(self):
        return self.config.get("telegram", {})

    @property
    def video_monitor(self):
        return self.config.get("video_monitor", {})

    @property
    def keyword_forward(self):
        return self.config.get("keyword_forward", {})

    @property
    def logging_config(self):
        return self.config.get("logging", {})