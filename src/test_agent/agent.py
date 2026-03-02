"""
测试执行 Agent - 基于 Claude API 和 Playwright
"""

import os
import json
import base64
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, Page
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from .tools import TOOLS, PlaywrightExecutor
from .reporter import AllureReporter
from .ai_client import AIClient, create_ai_client

console = Console()

SYSTEM_PROMPT = """你是一个专业的 Web 测试执行 Agent，能够理解自然语言描述的测试用例并自动执行。

## 核心能力
1. 解析用户的自然语言测试用例
2. 使用 Playwright 工具执行 Web UI 测试
3. 验证测试结果并生成报告

## 行为约束（重要）
1. **STRICT 模式执行用例**：严格按照测试用例中给出的步骤顺序执行，不要自己设计新的测试点或扩展测试范围。
2. **只做用例要求的事情**：只执行测试用例中明确提到的关键步骤，以及为完成这些步骤所必需的少量辅助操作（如等待、截图）。不要测试其它模块、菜单或功能。
3. **避免重复尝试同一选择器**：对于同一个工具名称和完全相同的选择器参数（例如 `get_elements_info` + 相同的 `selector`），连续尝试次数最多不超过 3 次。如果仍然无法满足需求，应改变策略或给出失败原因，而不是继续重复调用。
4. **优先完成主线步骤**：在执行完测试用例中描述的主要操作和断言之前，不要把精力花在“退出/Exit 按钮”“额外菜单”等与当前测试目标无关的元素上。
5. **验证完成立即结束当前用例**：一旦测试用例中列出的所有前置条件、执行步骤和预期结果都已被成功验证，必须立刻调用 `test_complete` 工具报告结果，并结束当前用例，不要继续在页面上做额外探索。
6. **无法完成时直接报告**：如果因为元素不存在、权限不足、数据缺失等原因导致无法完成用例中的某一步，应说明原因并将该用例标记为失败，而不是绕开用例继续做其它无关检查。
7. **禁止臆造新的模块/菜单名称**：除非测试用例文本中明确提到，否则不要自行引入新的业务模块或菜单名称（例如“DevOps”“Users”“Settings”等）作为导航目标，更不要围绕这些自创模块设计新的测试步骤。
8. **Bearer Token 已配置时不要重复登录**：如果系统已经通过 Bearer Token 完成认证（即页面已可正常访问业务功能），则不要再尝试通过登录表单输入用户名/密码进行登录；只有在页面明确显示登录表单且无法访问用例要求的页面时，才考虑执行登录步骤。

## 工作流程

### 第一步：理解测试用例
当用户给出测试用例后，首先确认你理解的内容：
- 测试目标是什么
- 需要执行哪些步骤
- 预期结果是什么

如果有不明确的地方，询问用户澄清。

### 第二步：执行测试
- 先使用 screenshot 查看当前页面状态
- 逐步执行每个操作
- 每个关键步骤后截图确认
- 遇到问题时分析并尝试解决

### 第三步：验证与报告
- 使用断言工具验证预期结果
- 执行完成后调用 test_complete 汇报结果

## 执行原则

1. **观察优先**：执行操作前先截图了解页面状态
2. **逐步执行**：一次执行一个操作，确认成功后再继续
3. **充分等待**：页面加载后再操作，必要时使用 wait_for_selector
4. **灵活定位**：
   - 优先使用文本内容定位：`text=登录`
   - 使用占位符定位输入框：`[placeholder="请输入用户名"]`
   - 使用 role 定位：`role=button[name="提交"]`
   - CSS 选择器作为备选
5. **错误恢复**：如果操作失败，分析原因并尝试其他方式

## 多语言页面适配（重要）

被测页面可能是中文或英文界面。测试用例通常用中文描述，但页面实际显示可能是英文。

**执行策略**：
1. 先截图观察页面实际使用的语言
2. 根据页面实际语言选择对应的文本进行定位
3. 如果定位失败，自动尝试另一种语言的等效文本

**常见中英文对照**：
| 中文 | 英文 |
|------|------|
| 登录 | Login / Sign in / Log in |
| 注册 | Register / Sign up |
| 退出/登出 | Logout / Sign out / Log out |
| 提交 | Submit |
| 确认/确定 | Confirm / OK / Yes |
| 取消 | Cancel / No |
| 搜索 | Search |
| 保存 | Save |
| 编辑 | Edit |
| 删除 | Delete / Remove |
| 添加/新增 | Add / Create / New |
| 下一步 | Next |
| 上一步 | Back / Previous |
| 完成 | Done / Finish / Complete |
| 用户名 | Username |
| 密码 | Password |
| 邮箱 | Email |
| 设置 | Settings |
| 首页 | Home |
| 更多 | More |

**示例**：
- 用例说"点击登录按钮"，页面是英文 → 使用 `text=Login` 或 `text=Sign in`
- 用例说"输入用户名"，页面是英文 → 定位 `[placeholder="Username"]` 或 `[placeholder="Enter username"]`

**执行时**：
1. 不要机械翻译用例，而是理解意图
2. 根据截图中看到的实际文本来定位
3. 优先使用页面上实际显示的文字

## 选择器使用技巧

Playwright 支持多种选择器：
- `text=确认` - 按文本内容匹配
- `text="确认"` - 精确匹配文本
- `button:has-text("登录")` - 包含文本的按钮
- `[placeholder="搜索"]` - 按属性匹配
- `input[type="text"]` - 按标签和属性
- `#id` - ID 选择器
- `.class` - 类选择器
- `role=button[name="Submit"]` - ARIA role
- `xpath=//button[@type="submit"]` - XPath

## 注意事项

- 根据截图判断页面语言，使用对应语言的文本定位
- 如果元素不存在或不可见，先检查页面状态
- 对于动态加载的内容，使用 wait_for_selector 等待
- 复杂页面可以先 get_page_content 了解结构
"""


class TestAgent:
    """测试执行 Agent"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        headless: bool = False,
        proxy: Optional[str] = None,
        bearer_token: Optional[str] = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        locale: str = "zh-CN",
        report_dir: str = "allure-results",
        ai_provider: str = "anthropic",
        ai_model: Optional[str] = None
    ):
        """
        初始化测试 Agent

        Args:
            api_key: AI API 密钥
            headless: 是否无头模式
            proxy: 代理服务器地址，支持 http://、https://、socks5:// 协议
            bearer_token: Bearer Token 认证令牌
            viewport_width: 浏览器视口宽度
            viewport_height: 浏览器视口高度
            locale: 浏览器语言
            report_dir: Allure 报告输出目录
            ai_provider: AI 提供商 (anthropic, glm)
            ai_model: AI 模型名称
        """
        # 如果未配置代理，清除环境变量中的代理设置，避免 HTTP 客户端自动使用
        if not proxy:
            proxy_env_vars = [
                "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                "http_proxy", "https_proxy", "all_proxy"
            ]
            for var in proxy_env_vars:
                os.environ.pop(var, None)

        # 创建 AI 客户端
        self.ai_provider = ai_provider
        self.client = create_ai_client(
            provider=ai_provider,
            api_key=api_key,
            model=ai_model
        )
        self.headless = headless
        self.proxy = proxy
        self.bearer_token = bearer_token
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.locale = locale
        self.messages: list[dict] = []
        # 为了避免上下文过长导致模型报错，限制保留的历史消息条数
        self.max_history_messages: int = 40
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.executor: Optional[PlaywrightExecutor] = None
        self.playwright = None
        self.test_completed = False
        self.reporter = AllureReporter(report_dir)
        self.current_step_name = ""

    @classmethod
    def from_config(cls, config: "Config", report_dir: str = "allure-results") -> "TestAgent":
        """从配置对象创建 Agent"""
        from .config import Config
        return cls(
            api_key=config.ai.api_key,
            headless=config.browser.headless,
            proxy=config.proxy or None,
            bearer_token=config.target.bearer_token or None,
            viewport_width=config.browser.viewport_width,
            viewport_height=config.browser.viewport_height,
            locale=config.browser.locale,
            report_dir=report_dir,
            ai_provider=config.ai.provider,
            ai_model=config.ai.model or None
        )

    def start_browser(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()

        # 浏览器启动参数
        launch_options = {"headless": self.headless}

        # 配置代理（浏览器级别）
        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}
            console.print(f"[blue]使用代理:[/blue] {self.proxy}")

        self.browser = self.playwright.chromium.launch(**launch_options)

        # 浏览器上下文参数（默认忽略证书错误，便于内网测试）
        context_options = {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "locale": self.locale,
            "ignore_https_errors": True
        }

        # 配置 Bearer Token 认证
        if self.bearer_token:
            context_options["extra_http_headers"] = {
                "Authorization": f"Bearer {self.bearer_token}"
            }
            console.print("[blue]已配置 Bearer Token 认证[/blue]")

        context = self.browser.new_context(**context_options)
        self.page = context.new_page()
        self.executor = PlaywrightExecutor(self.page)
        console.print("[green]浏览器已启动[/green]")

    def stop_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        console.print("[yellow]浏览器已关闭[/yellow]")

    def chat(self, user_message: str) -> str:
        """发送消息并获取响应"""
        self.messages.append({"role": "user", "content": user_message})

        while True:
            # 控制对话历史长度，避免上下文无限增长
            if len(self.messages) > self.max_history_messages:
                self.messages = self.messages[-self.max_history_messages :]

            response = self.client.chat(
                messages=self.messages,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                max_tokens=4096
            )

            # 添加助手消息到历史
            assistant_message = self.client.format_assistant_message(response)
            self.messages.append(assistant_message)

            # 检查是否有工具调用
            if not response.tool_calls:
                # 没有工具调用，返回文本响应
                return response.content

            # 执行工具调用
            tool_results = []
            for tool_call in response.tool_calls:
                result = self._execute_tool(tool_call.name, tool_call.input)

                # 检查是否包含截图
                is_image = "screenshot_base64" in result
                image_base64 = result.get("screenshot_base64")

                # 格式化工具结果
                formatted_result = self.client.format_tool_result(
                    tool_call_id=tool_call.id,
                    result=result,
                    is_image=is_image,
                    image_base64=image_base64
                )
                tool_results.append(formatted_result)

                # 检查是否测试完成
                if result.get("test_completed"):
                    self.test_completed = True

            self.messages.append({"role": "user", "content": tool_results})

            # 如果测试完成，获取最终响应后退出
            if self.test_completed:
                final_response = self.client.chat(
                    messages=self.messages,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    max_tokens=4096
                )
                final_message = self.client.format_assistant_message(final_response)
                self.messages.append(final_message)
                return final_response.content

    def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """执行工具"""
        # 生成步骤描述
        step_desc = self._get_step_description(tool_name, tool_input)
        console.print(f"[cyan]执行工具:[/cyan] {tool_name}")

        if tool_input:
            # 不显示 base64 截图内容
            display_input = {k: v[:100] + "..." if isinstance(v, str) and len(v) > 100 else v
                          for k, v in tool_input.items()}
            console.print(f"[dim]参数: {json.dumps(display_input, ensure_ascii=False)}[/dim]")

        # 开始记录步骤
        self.reporter.start_step(step_desc)

        result = self.executor.execute(tool_name, tool_input)

        # 处理截图 - 保存到报告
        if "screenshot_base64" in result:
            screenshot_bytes = base64.b64decode(result["screenshot_base64"])
            self.reporter.add_screenshot(screenshot_bytes, f"{tool_name}_screenshot")

        if result.get("success"):
            console.print(f"[green]✓[/green] {result.get('message', '成功')}")
            self.reporter.end_step("passed")
        else:
            console.print(f"[red]✗[/red] {result.get('error', '失败')}")
            self.reporter.end_step("failed")

        return result

    def _get_step_description(self, tool_name: str, tool_input: dict) -> str:
        """生成步骤的可读描述"""
        descriptions = {
            "navigate": lambda i: f"打开页面: {i.get('url', '')}",
            "click": lambda i: f"点击元素: {i.get('selector', '')}",
            "fill": lambda i: f"输入文本: {i.get('selector', '')} = {i.get('text', '')}",
            "type_text": lambda i: f"键入文本: {i.get('text', '')}",
            "press_key": lambda i: f"按键: {i.get('key', '')}",
            "screenshot": lambda i: "截取屏幕截图",
            "get_text": lambda i: f"获取文本: {i.get('selector', '')}",
            "wait_for_selector": lambda i: f"等待元素: {i.get('selector', '')}",
            "assert_visible": lambda i: f"验证可见: {i.get('selector', '')}",
            "assert_text_contains": lambda i: f"验证文本包含: {i.get('expected', '')}",
            "assert_url_contains": lambda i: f"验证URL包含: {i.get('expected', '')}",
            "scroll": lambda i: f"滚动页面: {i.get('direction', '')}",
            "hover": lambda i: f"悬停元素: {i.get('selector', '')}",
            "select_option": lambda i: f"选择选项: {i.get('value', '')}",
            "test_complete": lambda i: f"测试完成: {i.get('status', '')}",
        }

        if tool_name in descriptions:
            return descriptions[tool_name](tool_input or {})
        return f"{tool_name}: {json.dumps(tool_input, ensure_ascii=False)[:50]}"

    def _format_tool_result(self, tool_name: str, result: dict) -> list:
        """格式化工具结果，处理截图等特殊内容"""
        content = []

        # 处理截图
        if "screenshot_base64" in result:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": result["screenshot_base64"]
                }
            })
            # 移除 base64 数据，添加说明
            result_copy = {k: v for k, v in result.items() if k != "screenshot_base64"}
            result_copy["message"] = "截图已捕获，请查看图片"
            content.append({"type": "text", "text": json.dumps(result_copy, ensure_ascii=False)})
        else:
            content.append({"type": "text", "text": json.dumps(result, ensure_ascii=False)})

        return content

    def run_test(
        self,
        test_case: str,
        start_url: Optional[str] = None,
        variables: Optional[dict] = None,
        feature_name: str = "",
        scenario_name: str = ""
    ) -> str:
        """执行测试用例"""
        # 提取测试名称
        test_name = scenario_name or self._extract_test_name(test_case)

        # 开始记录测试
        self.reporter.start_test(
            name=test_name,
            description=test_case,
            feature=feature_name,
            scenario=scenario_name
        )

        # 添加测试参数
        if start_url:
            self.reporter.add_parameter("URL", start_url)
        if variables:
            for key in variables:
                self.reporter.add_parameter(f"变量.{key}", str(variables[key]))

        test_status = "passed"
        error_message = ""

        try:
            self.start_browser()

            # 如果指定了起始 URL，先导航
            if start_url:
                console.print(f"[blue]导航到起始页面:[/blue] {start_url}")
                self.page.goto(start_url, wait_until="domcontentloaded")

            # 构建变量说明
            variables_info = ""
            if variables:
                variables_info = "\n\n## 可用变量\n以下变量已在配置文件中定义，可在执行时参考：\n```\n"
                variables_info += json.dumps(variables, ensure_ascii=False, indent=2)
                variables_info += "\n```\n"

            # 构建初始消息
            initial_message = f"""请执行以下测试用例：

{test_case}
{variables_info}
{"起始页面已打开: " + start_url if start_url else "请先确认需要访问的页面 URL"}

请先截图查看当前页面状态，然后开始执行测试。"""

            console.print(Panel(test_case, title="测试用例", border_style="blue"))

            # 执行测试
            result = self.chat(initial_message)

            # 检查测试结果
            if "失败" in result or "failed" in result.lower():
                test_status = "failed"
                error_message = result

            return result

        except Exception as e:
            test_status = "broken"
            error_message = str(e)
            raise

        finally:
            # 结束测试记录
            self.reporter.end_test(status=test_status, error_message=error_message)
            self.stop_browser()

    def _extract_test_name(self, test_case: str) -> str:
        """从测试用例中提取名称"""
        lines = test_case.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("场景:") or line.startswith("场景："):
                return line.split(":", 1)[-1].split("：", 1)[-1].strip()
            if line.startswith("Scenario:"):
                return line.split(":", 1)[-1].strip()
            if line.startswith("测试目标:") or line.startswith("测试目标："):
                return line.split(":", 1)[-1].split("：", 1)[-1].strip()
        # 返回第一行作为名称
        return lines[0][:50] if lines else "未命名测试"

    def interactive_mode(self):
        """交互模式 - 与 Agent 对话执行测试"""
        console.print(Panel.fit(
            "[bold]测试执行 Agent[/bold]\n"
            "输入测试用例或指令，Agent 会帮你执行\n"
            "输入 'quit' 或 'exit' 退出",
            border_style="green"
        ))

        try:
            self.start_browser()

            while True:
                try:
                    user_input = console.input("\n[bold cyan]你:[/bold cyan] ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit", "q"]:
                    break

                console.print()
                response = self.chat(user_input)
                console.print(Panel(Markdown(response), title="Agent", border_style="green"))

                if self.test_completed:
                    console.print("\n[yellow]测试已完成。继续输入新的测试用例，或输入 'quit' 退出[/yellow]")
                    self.test_completed = False
                    self.messages = []  # 重置对话历史

        finally:
            self.stop_browser()
