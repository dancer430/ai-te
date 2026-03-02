"""
Gherkin 语法解析模块

支持的关键字（中英文）：
- Feature / 功能
- Scenario / 场景
- Given / 假如 / 前提
- When / 当
- Then / 那么 / 则
- And / 并且 / 而且
- But / 但是
"""

import re
from typing import List, Optional
from dataclasses import dataclass, field


# 关键字映射（支持中英文）
KEYWORDS = {
    "feature": ["Feature", "功能", "特性"],
    "scenario": ["Scenario", "场景", "Example", "示例"],
    "given": ["Given", "假如", "前提", "假设"],
    "when": ["When", "当"],
    "then": ["Then", "那么", "则"],
    "and": ["And", "并且", "而且", "同时"],
    "but": ["But", "但是", "但"],
    "background": ["Background", "背景"],
}


@dataclass
class Step:
    """Gherkin 步骤"""
    keyword: str  # given, when, then, and, but
    text: str
    original_keyword: str  # 原始关键字文本


@dataclass
class Scenario:
    """Gherkin 场景"""
    name: str
    steps: List[Step] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class Feature:
    """Gherkin Feature"""
    name: str
    description: str = ""
    scenarios: List[Scenario] = field(default_factory=list)
    background: Optional[List[Step]] = None
    tags: List[str] = field(default_factory=list)


def _match_keyword(line: str) -> tuple[Optional[str], Optional[str], str]:
    """
    匹配关键字

    返回: (keyword_type, original_keyword, remaining_text)
    """
    line = line.strip()

    for keyword_type, keywords in KEYWORDS.items():
        for kw in keywords:
            if line.startswith(kw + ":") or line.startswith(kw + "："):
                # Feature/Scenario 类型，冒号后面是名称
                remaining = line[len(kw) + 1:].strip()
                return keyword_type, kw, remaining
            elif line.startswith(kw + " ") or line == kw:
                # Given/When/Then 类型，空格后面是步骤描述
                remaining = line[len(kw):].strip()
                return keyword_type, kw, remaining

    return None, None, line


def parse_feature(content: str) -> Feature:
    """
    解析 Gherkin feature 文件内容

    Args:
        content: feature 文件内容

    Returns:
        Feature 对象
    """
    lines = content.strip().split("\n")
    feature = Feature(name="")
    current_scenario: Optional[Scenario] = None
    current_tags: List[str] = []
    in_background = False
    last_step_keyword = "given"  # 用于 And/But 继承

    for line in lines:
        line = line.strip()

        # 跳过空行和注释
        if not line or line.startswith("#"):
            continue

        # 处理标签 @tag
        if line.startswith("@"):
            tags = re.findall(r"@(\w+)", line)
            current_tags.extend(tags)
            continue

        keyword_type, original_kw, text = _match_keyword(line)

        if keyword_type == "feature":
            feature.name = text
            feature.tags = current_tags
            current_tags = []

        elif keyword_type == "background":
            in_background = True
            feature.background = []

        elif keyword_type == "scenario":
            # 保存之前的场景
            if current_scenario:
                feature.scenarios.append(current_scenario)

            current_scenario = Scenario(name=text, tags=current_tags)
            current_tags = []
            in_background = False
            last_step_keyword = "given"

        elif keyword_type in ("given", "when", "then"):
            step = Step(keyword=keyword_type, text=text, original_keyword=original_kw)
            last_step_keyword = keyword_type

            if in_background:
                feature.background.append(step)
            elif current_scenario:
                current_scenario.steps.append(step)

        elif keyword_type in ("and", "but"):
            # And/But 继承上一个步骤的类型
            step = Step(keyword=last_step_keyword, text=text, original_keyword=original_kw)

            if in_background:
                feature.background.append(step)
            elif current_scenario:
                current_scenario.steps.append(step)

        elif not keyword_type and feature.name and not current_scenario:
            # Feature 描述（多行）
            if feature.description:
                feature.description += "\n" + line
            else:
                feature.description = line

    # 添加最后一个场景
    if current_scenario:
        feature.scenarios.append(current_scenario)

    return feature


def feature_to_testcase(feature: Feature, scenario: Scenario) -> str:
    """
    将 Feature/Scenario 转换为自然语言测试用例

    Args:
        feature: Feature 对象
        scenario: Scenario 对象

    Returns:
        自然语言描述的测试用例
    """
    lines = []

    # 添加 Feature 信息
    lines.append(f"功能: {feature.name}")
    if feature.description:
        lines.append(f"描述: {feature.description}")
    lines.append(f"场景: {scenario.name}")
    lines.append("")

    # 添加 Background 步骤
    if feature.background:
        lines.append("前置条件:")
        for step in feature.background:
            lines.append(f"  - {step.text}")
        lines.append("")

    # 添加场景步骤
    lines.append("测试步骤:")

    # 按类型分组显示
    given_steps = [s for s in scenario.steps if s.keyword == "given"]
    when_steps = [s for s in scenario.steps if s.keyword == "when"]
    then_steps = [s for s in scenario.steps if s.keyword == "then"]

    if given_steps:
        lines.append("  前提条件:")
        for step in given_steps:
            lines.append(f"    - {step.text}")

    if when_steps:
        lines.append("  执行操作:")
        for step in when_steps:
            lines.append(f"    - {step.text}")

    if then_steps:
        lines.append("  预期结果:")
        for step in then_steps:
            lines.append(f"    - {step.text}")

    return "\n".join(lines)


def parse_feature_file(filepath: str) -> Feature:
    """解析 .feature 文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return parse_feature(content)
