"""
Playwright 工具定义 - 供 Claude Agent 调用
"""

from typing import Any
from playwright.sync_api import Page, Browser, BrowserContext
import base64
import json

# 工具定义，用于 Claude API
TOOLS = [
    {
        "name": "navigate",
        "description": "导航到指定的 URL 页面",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要访问的网页 URL"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "click",
        "description": "点击页面上的元素。可以使用 CSS 选择器、文本内容或 XPath",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "元素选择器，支持 CSS 选择器、text=文本内容、xpath=表达式"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "fill",
        "description": "在输入框中填入文本内容，会先清空原有内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "输入框的选择器"
                },
                "text": {
                    "type": "string",
                    "description": "要输入的文本内容"
                }
            },
            "required": ["selector", "text"]
        }
    },
    {
        "name": "type_text",
        "description": "模拟键盘逐字输入文本，适用于需要触发输入事件的场景",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "输入框的选择器"
                },
                "text": {
                    "type": "string",
                    "description": "要输入的文本内容"
                },
                "delay": {
                    "type": "number",
                    "description": "每个字符之间的延迟毫秒数，默认 50"
                }
            },
            "required": ["selector", "text"]
        }
    },
    {
        "name": "press_key",
        "description": "按下键盘按键，如 Enter、Tab、Escape 等",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "按键名称，如 Enter、Tab、Escape、ArrowDown 等"
                }
            },
            "required": ["key"]
        }
    },
    {
        "name": "screenshot",
        "description": "截取当前页面的屏幕截图，用于查看页面当前状态",
        "input_schema": {
            "type": "object",
            "properties": {
                "full_page": {
                    "type": "boolean",
                    "description": "是否截取整个页面（包括滚动区域），默认 false 只截取可视区域"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_text",
        "description": "获取指定元素的文本内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "目标元素的选择器"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "get_attribute",
        "description": "获取元素的指定属性值",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "目标元素的选择器"
                },
                "attribute": {
                    "type": "string",
                    "description": "属性名称，如 href、src、value 等"
                }
            },
            "required": ["selector", "attribute"]
        }
    },
    {
        "name": "wait_for_selector",
        "description": "等待指定元素出现在页面上",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "要等待的元素选择器"
                },
                "timeout": {
                    "type": "number",
                    "description": "超时时间（毫秒），默认 30000"
                },
                "state": {
                    "type": "string",
                    "description": "等待的状态：visible（可见）、hidden（隐藏）、attached（存在于DOM）",
                    "enum": ["visible", "hidden", "attached"]
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "wait_for_navigation",
        "description": "等待页面导航完成（页面跳转或刷新）",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeout": {
                    "type": "number",
                    "description": "超时时间（毫秒），默认 30000"
                }
            },
            "required": []
        }
    },
    {
        "name": "select_option",
        "description": "在下拉选择框中选择选项",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "select 元素的选择器"
                },
                "value": {
                    "type": "string",
                    "description": "要选择的选项的 value 值或可见文本"
                }
            },
            "required": ["selector", "value"]
        }
    },
    {
        "name": "check",
        "description": "勾选复选框或单选框",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "复选框/单选框的选择器"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "uncheck",
        "description": "取消勾选复选框",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "复选框的选择器"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "hover",
        "description": "将鼠标悬停在指定元素上",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "目标元素的选择器"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "scroll",
        "description": "滚动页面或指定元素",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "description": "滚动方向：up、down、left、right",
                    "enum": ["up", "down", "left", "right"]
                },
                "amount": {
                    "type": "number",
                    "description": "滚动像素数，默认 500"
                },
                "selector": {
                    "type": "string",
                    "description": "可选，指定要滚动的元素，默认滚动页面"
                }
            },
            "required": ["direction"]
        }
    },
    {
        "name": "get_page_content",
        "description": "获取页面的主要文本内容，用于分析页面信息",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "可选，指定获取某个区域的内容，默认获取 body"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_elements_info",
        "description": "获取匹配选择器的所有元素信息（文本、属性等）",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "元素选择器"
                },
                "limit": {
                    "type": "number",
                    "description": "最多返回多少个元素，默认 10"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "assert_visible",
        "description": "断言：验证元素是否可见",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "要验证的元素选择器"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "assert_text_contains",
        "description": "断言：验证元素文本是否包含指定内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "要验证的元素选择器"
                },
                "expected": {
                    "type": "string",
                    "description": "期望包含的文本"
                }
            },
            "required": ["selector", "expected"]
        }
    },
    {
        "name": "assert_url_contains",
        "description": "断言：验证当前 URL 是否包含指定内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "expected": {
                    "type": "string",
                    "description": "期望 URL 包含的内容"
                }
            },
            "required": ["expected"]
        }
    },
    {
        "name": "go_back",
        "description": "浏览器后退到上一页",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "go_forward",
        "description": "浏览器前进到下一页",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "refresh",
        "description": "刷新当前页面",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_current_url",
        "description": "获取当前页面的 URL",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_page_title",
        "description": "获取当前页面的标题",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "test_complete",
        "description": "标记测试执行完成，汇报最终结果",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "测试结果：passed（通过）、failed（失败）、blocked（阻塞）",
                    "enum": ["passed", "failed", "blocked"]
                },
                "summary": {
                    "type": "string",
                    "description": "测试结果摘要"
                },
                "details": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "string"},
                            "status": {"type": "string"},
                            "note": {"type": "string"}
                        }
                    },
                    "description": "每个步骤的执行详情"
                }
            },
            "required": ["status", "summary"]
        }
    }
]


class PlaywrightExecutor:
    """Playwright 工具执行器"""

    def __init__(self, page: Page):
        self.page = page
        self.screenshots: list[str] = []  # 存储截图路径

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """执行工具调用"""
        try:
            method = getattr(self, f"_tool_{tool_name}", None)
            if method is None:
                return {"success": False, "error": f"未知工具: {tool_name}"}
            return method(**tool_input)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_navigate(self, url: str) -> dict:
        self.page.goto(url, wait_until="domcontentloaded")
        return {"success": True, "message": f"已导航到 {url}", "current_url": self.page.url}

    def _tool_click(self, selector: str) -> dict:
        self.page.click(selector, timeout=10000)
        return {"success": True, "message": f"已点击元素: {selector}"}

    def _tool_fill(self, selector: str, text: str) -> dict:
        self.page.fill(selector, text, timeout=10000)
        return {"success": True, "message": f"已在 {selector} 中填入文本"}

    def _tool_type_text(self, selector: str, text: str, delay: int = 50) -> dict:
        self.page.locator(selector).press_sequentially(text, delay=delay)
        return {"success": True, "message": f"已在 {selector} 中逐字输入文本"}

    def _tool_press_key(self, key: str) -> dict:
        self.page.keyboard.press(key)
        return {"success": True, "message": f"已按下按键: {key}"}

    def _tool_screenshot(self, full_page: bool = False) -> dict:
        screenshot_bytes = self.page.screenshot(full_page=full_page)
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
        return {
            "success": True,
            "message": "截图成功",
            "screenshot_base64": screenshot_base64
        }

    def _tool_get_text(self, selector: str) -> dict:
        text = self.page.locator(selector).inner_text(timeout=10000)
        return {"success": True, "text": text}

    def _tool_get_attribute(self, selector: str, attribute: str) -> dict:
        value = self.page.locator(selector).get_attribute(attribute, timeout=10000)
        return {"success": True, "value": value}

    def _tool_wait_for_selector(self, selector: str, timeout: int = 30000, state: str = "visible") -> dict:
        self.page.wait_for_selector(selector, timeout=timeout, state=state)
        return {"success": True, "message": f"元素 {selector} 已{state}"}

    def _tool_wait_for_navigation(self, timeout: int = 30000) -> dict:
        self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
        return {"success": True, "message": "页面导航完成", "current_url": self.page.url}

    def _tool_select_option(self, selector: str, value: str) -> dict:
        self.page.select_option(selector, value, timeout=10000)
        return {"success": True, "message": f"已选择选项: {value}"}

    def _tool_check(self, selector: str) -> dict:
        self.page.check(selector, timeout=10000)
        return {"success": True, "message": f"已勾选: {selector}"}

    def _tool_uncheck(self, selector: str) -> dict:
        self.page.uncheck(selector, timeout=10000)
        return {"success": True, "message": f"已取消勾选: {selector}"}

    def _tool_hover(self, selector: str) -> dict:
        self.page.hover(selector, timeout=10000)
        return {"success": True, "message": f"已悬停在: {selector}"}

    def _tool_scroll(self, direction: str, amount: int = 500, selector: str = None) -> dict:
        delta_x, delta_y = 0, 0
        if direction == "down":
            delta_y = amount
        elif direction == "up":
            delta_y = -amount
        elif direction == "right":
            delta_x = amount
        elif direction == "left":
            delta_x = -amount

        if selector:
            self.page.locator(selector).scroll_into_view_if_needed()
        else:
            self.page.mouse.wheel(delta_x, delta_y)
        return {"success": True, "message": f"已向{direction}滚动 {amount} 像素"}

    def _tool_get_page_content(self, selector: str = "body") -> dict:
        text = self.page.locator(selector).inner_text(timeout=10000)
        # 限制返回长度
        if len(text) > 5000:
            text = text[:5000] + "\n... (内容已截断)"
        return {"success": True, "content": text}

    def _tool_get_elements_info(self, selector: str, limit: int = 10) -> dict:
        elements = self.page.locator(selector)
        count = elements.count()
        results = []
        for i in range(min(count, limit)):
            el = elements.nth(i)
            results.append({
                "index": i,
                "text": el.inner_text()[:200] if el.inner_text() else "",
                "tag": el.evaluate("e => e.tagName.toLowerCase()"),
                "visible": el.is_visible()
            })
        return {"success": True, "count": count, "elements": results}

    def _tool_assert_visible(self, selector: str) -> dict:
        is_visible = self.page.locator(selector).is_visible(timeout=10000)
        if is_visible:
            return {"success": True, "passed": True, "message": f"断言通过: {selector} 可见"}
        else:
            return {"success": True, "passed": False, "message": f"断言失败: {selector} 不可见"}

    def _tool_assert_text_contains(self, selector: str, expected: str) -> dict:
        text = self.page.locator(selector).inner_text(timeout=10000)
        if expected in text:
            return {"success": True, "passed": True, "message": f"断言通过: 文本包含 '{expected}'"}
        else:
            return {"success": True, "passed": False, "message": f"断言失败: 文本不包含 '{expected}'", "actual": text[:500]}

    def _tool_assert_url_contains(self, expected: str) -> dict:
        current_url = self.page.url
        if expected in current_url:
            return {"success": True, "passed": True, "message": f"断言通过: URL 包含 '{expected}'"}
        else:
            return {"success": True, "passed": False, "message": f"断言失败: URL 不包含 '{expected}'", "actual_url": current_url}

    def _tool_go_back(self) -> dict:
        self.page.go_back()
        return {"success": True, "message": "已后退", "current_url": self.page.url}

    def _tool_go_forward(self) -> dict:
        self.page.go_forward()
        return {"success": True, "message": "已前进", "current_url": self.page.url}

    def _tool_refresh(self) -> dict:
        self.page.reload()
        return {"success": True, "message": "已刷新页面"}

    def _tool_get_current_url(self) -> dict:
        return {"success": True, "url": self.page.url}

    def _tool_get_page_title(self) -> dict:
        return {"success": True, "title": self.page.title()}

    def _tool_test_complete(self, status: str, summary: str, details: list = None) -> dict:
        return {
            "success": True,
            "test_completed": True,
            "status": status,
            "summary": summary,
            "details": details or []
        }
