"""
AI 测试执行 Agent

基于 AI API 和 Playwright 的智能测试执行工具
支持多个 AI 提供商：Anthropic Claude、智谱 GLM 等
"""

from .agent import TestAgent
from .config import Config
from .reporter import AllureReporter
from .gherkin import Feature, Scenario, parse_feature, parse_feature_file, feature_to_testcase
from .ai_client import AIClient, AnthropicClient, GLMClient, create_ai_client

__version__ = "0.2.0"
__all__ = [
    "TestAgent",
    "Config",
    "AllureReporter",
    "Feature",
    "Scenario",
    "parse_feature",
    "parse_feature_file",
    "feature_to_testcase",
    "AIClient",
    "AnthropicClient",
    "GLMClient",
    "create_ai_client",
]
