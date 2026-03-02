"""
配置文件加载模块
"""

import os
import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class AIConfig:
    """AI 提供商配置"""
    provider: str = "anthropic"  # anthropic, glm
    api_key: str = ""
    model: str = ""  # 留空使用默认模型


@dataclass
class BrowserConfig:
    """浏览器配置"""
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 720
    locale: str = "zh-CN"


@dataclass
class TargetConfig:
    """被测系统配置"""
    url: str = ""
    bearer_token: str = ""


@dataclass
class Config:
    """Agent 配置"""
    api_key: str = ""  # 兼容旧配置
    proxy: str = ""
    ai: AIConfig = field(default_factory=AIConfig)
    target: TargetConfig = field(default_factory=TargetConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    variables: dict = field(default_factory=dict)  # 运行时变量

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        加载配置文件

        优先级：
        1. 指定的配置文件路径
        2. 当前目录的 config.yaml
        3. 当前目录的 config.yml
        4. 默认配置
        """
        config = cls()

        # 确定配置文件路径
        if config_path:
            path = Path(config_path)
        else:
            # 查找默认配置文件
            for name in ["config.yaml", "config.yml"]:
                path = Path(name)
                if path.exists():
                    break
            else:
                path = None

        # 加载配置文件
        if path and path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            config = cls._from_dict(data)

        # 环境变量覆盖 API Key
        # 根据 provider 选择对应的环境变量
        if config.ai.provider == "anthropic":
            env_key = os.environ.get("ANTHROPIC_API_KEY")
            if env_key and not config.ai.api_key:
                config.ai.api_key = env_key
        elif config.ai.provider == "glm":
            env_key = os.environ.get("ZHIPUAI_API_KEY")
            if env_key and not config.ai.api_key:
                config.ai.api_key = env_key

        # 兼容旧配置：如果顶级 api_key 存在，同步到 ai.api_key
        if config.api_key and not config.ai.api_key:
            config.ai.api_key = config.api_key

        return config

    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """从字典创建配置"""
        config = cls()

        # 系统保留的配置键
        reserved_keys = {"api_key", "proxy", "target", "browser", "ai"}

        # 顶级配置
        config.api_key = data.get("api_key", "")
        config.proxy = data.get("proxy", "")

        # AI 配置
        ai_data = data.get("ai", {})
        config.ai = AIConfig(
            provider=ai_data.get("provider", "anthropic"),
            api_key=ai_data.get("api_key", ""),
            model=ai_data.get("model", "")
        )

        # 被测系统配置
        target_data = data.get("target", {})
        config.target = TargetConfig(
            url=target_data.get("url", ""),
            bearer_token=target_data.get("bearer_token", "")
        )

        # 浏览器配置
        browser_data = data.get("browser", {})
        viewport = browser_data.get("viewport", {})
        config.browser = BrowserConfig(
            headless=browser_data.get("headless", False),
            viewport_width=viewport.get("width", 1280),
            viewport_height=viewport.get("height", 720),
            locale=browser_data.get("locale", "zh-CN")
        )

        # 提取自定义变量（非保留键的都视为变量）
        for key, value in data.items():
            if key not in reserved_keys:
                config.variables[key] = value

        return config

    def get_variable(self, path: str, default=None):
        """
        获取变量值，支持点号分隔的路径

        例如: get_variable("login.username") 返回 config.variables["login"]["username"]
        """
        parts = path.split(".")
        value = self.variables

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def flatten_variables(self) -> dict:
        """
        将嵌套变量展平为点号分隔的键值对

        例如: {"login": {"username": "admin"}} -> {"login.username": "admin"}
        """
        result = {}

        def _flatten(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}.{key}" if prefix else key
                    _flatten(value, new_key)
            else:
                result[prefix] = obj

        _flatten(self.variables)
        return result

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "api_key": self.api_key,
            "proxy": self.proxy,
            "ai": {
                "provider": self.ai.provider,
                "api_key": self.ai.api_key,
                "model": self.ai.model
            },
            "target": {
                "url": self.target.url,
                "bearer_token": self.target.bearer_token
            },
            "browser": {
                "headless": self.browser.headless,
                "viewport": {
                    "width": self.browser.viewport_width,
                    "height": self.browser.viewport_height
                },
                "locale": self.browser.locale
            }
        }
