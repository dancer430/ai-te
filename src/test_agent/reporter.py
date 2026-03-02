"""
Allure 格式测试报告生成模块
"""

import json
import uuid
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum


class Status(str, Enum):
    """测试状态"""
    PASSED = "passed"
    FAILED = "failed"
    BROKEN = "broken"
    SKIPPED = "skipped"


class StepStatus(str, Enum):
    """步骤状态"""
    PASSED = "passed"
    FAILED = "failed"
    BROKEN = "broken"
    SKIPPED = "skipped"


@dataclass
class Attachment:
    """附件（截图等）"""
    name: str
    source: str  # 文件名
    type: str = "image/png"


@dataclass
class Step:
    """测试步骤"""
    name: str
    status: str = "passed"
    start: int = 0  # 毫秒时间戳
    stop: int = 0
    attachments: List[Attachment] = field(default_factory=list)
    parameters: List[dict] = field(default_factory=list)

    def set_passed(self):
        self.status = StepStatus.PASSED.value

    def set_failed(self):
        self.status = StepStatus.FAILED.value


@dataclass
class TestResult:
    """单个测试用例结果（Allure 格式）"""
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    historyId: str = ""
    name: str = ""
    fullName: str = ""
    description: str = ""
    status: str = "passed"
    start: int = 0
    stop: int = 0
    steps: List[Step] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    parameters: List[dict] = field(default_factory=list)
    labels: List[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.historyId:
            self.historyId = str(uuid.uuid4())


class AllureReporter:
    """Allure 报告生成器"""

    def __init__(self, results_dir: str = "allure-results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.current_test: Optional[TestResult] = None
        self.current_step: Optional[Step] = None
        self.screenshot_counter = 0

    def start_test(self, name: str, description: str = "", feature: str = "", scenario: str = ""):
        """开始一个测试用例"""
        self.current_test = TestResult(
            name=name,
            fullName=f"{feature}/{scenario}" if feature else name,
            description=description,
            start=self._current_time_ms()
        )

        # 添加标签
        if feature:
            self.current_test.labels.append({"name": "feature", "value": feature})
        if scenario:
            self.current_test.labels.append({"name": "story", "value": scenario})

        self.current_test.labels.append({"name": "suite", "value": "AI Test Agent"})

    def end_test(self, status: str = "passed", error_message: str = ""):
        """结束当前测试用例"""
        if not self.current_test:
            return

        self.current_test.stop = self._current_time_ms()
        self.current_test.status = status

        if error_message and status == "failed":
            self.current_test.description += f"\n\n**Error:** {error_message}"

        # 写入结果文件
        self._write_result(self.current_test)
        self.current_test = None

    def start_step(self, name: str):
        """开始一个测试步骤"""
        self.current_step = Step(
            name=name,
            start=self._current_time_ms()
        )

    def end_step(self, status: str = "passed"):
        """结束当前步骤"""
        if not self.current_step or not self.current_test:
            return

        self.current_step.stop = self._current_time_ms()
        self.current_step.status = status
        self.current_test.steps.append(self.current_step)
        self.current_step = None

    def add_screenshot(self, screenshot_bytes: bytes, name: str = "screenshot"):
        """添加截图"""
        self.screenshot_counter += 1
        filename = f"{self.current_test.uuid}-{self.screenshot_counter}.png"
        filepath = self.results_dir / filename

        # 保存截图文件
        with open(filepath, "wb") as f:
            f.write(screenshot_bytes)

        attachment = Attachment(
            name=name,
            source=filename,
            type="image/png"
        )

        # 添加到当前步骤或测试
        if self.current_step:
            self.current_step.attachments.append(attachment)
        elif self.current_test:
            self.current_test.attachments.append(attachment)

    def add_parameter(self, name: str, value: str):
        """添加测试参数"""
        if self.current_test:
            self.current_test.parameters.append({"name": name, "value": value})

    def _write_result(self, result: TestResult):
        """写入测试结果到 JSON 文件"""
        filename = f"{result.uuid}-result.json"
        filepath = self.results_dir / filename

        # 转换为字典
        data = self._to_dict(result)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _to_dict(self, obj) -> dict:
        """递归转换为字典"""
        if hasattr(obj, "__dataclass_fields__"):
            result = {}
            for field_name in obj.__dataclass_fields__:
                value = getattr(obj, field_name)
                result[field_name] = self._to_dict(value)
            return result
        elif isinstance(obj, list):
            return [self._to_dict(item) for item in obj]
        elif isinstance(obj, Enum):
            return obj.value
        else:
            return obj

    def _current_time_ms(self) -> int:
        """当前时间戳（毫秒）"""
        return int(time.time() * 1000)

    def generate_environment(self, env_info: dict):
        """生成环境信息文件"""
        env_file = self.results_dir / "environment.properties"
        with open(env_file, "w", encoding="utf-8") as f:
            for key, value in env_info.items():
                f.write(f"{key}={value}\n")

    def generate_categories(self):
        """生成分类配置文件"""
        categories = [
            {
                "name": "测试通过",
                "matchedStatuses": ["passed"]
            },
            {
                "name": "测试失败",
                "matchedStatuses": ["failed"]
            },
            {
                "name": "测试中断",
                "matchedStatuses": ["broken"]
            }
        ]
        categories_file = self.results_dir / "categories.json"
        with open(categories_file, "w", encoding="utf-8") as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
