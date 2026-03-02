# AI 测试执行 Agent

基于大语言模型和 Playwright 的智能测试执行工具，支持用自然语言描述测试用例，由 AI 自动执行。

**支持多个 AI 提供商**：Anthropic Claude、智谱 GLM 等。

## 目录

- [设计思路](#设计思路)
  - [要解决的核心痛点](#要解决的核心痛点)
  - [本项目的解决方案](#本项目的解决方案)
- [系统架构](#系统架构)
- [业务流程](#业务流程)
- [核心组件](#核心组件)
- [安装配置](#安装配置)
- [AI 提供商配置](#ai-提供商配置)
- [使用方法](#使用方法)
- [测试用例示例](#测试用例示例)
- [Gherkin 语法支持](#gherkin-语法支持)
- [Allure 测试报告](#allure-测试报告)

---

## 设计思路

### 要解决的核心痛点

#### 痛点一：手工测试效率低，重复劳动多

测试人员要执行大量重复性的手工测试用例：

- 同样的测试流程，每次发版都要手动走一遍
- 核心业务路径的回归测试，耗时且枯燥
- 多环境（开发/测试/预发/生产）重复验证
- 人工执行容易疲劳、遗漏步骤、出错

**期望**：有个"助手"能帮我执行这些重复的手工测试，我只需要告诉他要测什么。

#### 痛点二：自动化测试门槛高，投入产出比低

传统 UI 自动化测试需要：

- **编程能力**：掌握 Python/JavaScript + Selenium/Playwright/Cypress
- **选择器知识**：理解 CSS Selector、XPath、DOM 结构
- **框架搭建**：POM 模式、数据驱动、测试报告
- **持续维护**：页面改版 → 选择器失效 → 批量修复脚本

投入大量时间写自动化脚本，结果：
- 页面一改，脚本就废
- 维护成本比手工测试还高
- 最后沦为"僵尸脚本"，无人维护

**期望**：能不能不写代码，用大白话描述测试步骤，系统自动执行？

#### 痛点三：测试用例与执行脱节

传统模式下：
- 测试用例写在 Excel/TestRail/禅道里（自然语言）
- 执行时要么手工操作，要么转成自动化代码
- 用例更新后，自动化脚本往往忘记同步

**期望**：测试用例本身就是可执行的，写完用例直接运行。

#### 痛点四：内网环境测试不便

企业内部系统通常：
- 部署在内网，外部无法访问
- 需要认证（Token/Cookie/SSO）
- 使用自签名 HTTPS 证书
- 通过代理访问

现有的云端测试平台难以触达这些环境。

**期望**：能在内网环境本地运行，支持认证和代理。

---

### 本项目的解决方案

针对以上痛点，本项目提供：

| 痛点 | 解决方案 |
|------|----------|
| 手工测试效率低 | AI Agent 自动执行，人只需描述和验收 |
| 自动化门槛高 | 自然语言输入，无需编程 |
| 选择器维护难 | AI 智能定位 + 视觉理解，页面变化自适应 |
| 用例与执行脱节 | 用例即指令，写完直接执行 |
| 内网环境限制 | 本地部署，支持代理和 Token 认证 |

### 核心理念

> **让测试人员用自然语言描述测试用例，AI 自动理解并执行**

就像一个懂技术的测试助手，你告诉他"打开登录页，输入用户名密码，点击登录，验证跳转到首页"，他就能自己完成操作。

### 设计目标

1. **零代码门槛**：测试人员无需编写 Playwright/Selenium 代码
2. **自然语言交互**：用中文描述测试步骤，支持模糊表达
3. **视觉理解**：Agent 通过截图"看到"页面，像人一样判断状态
4. **智能容错**：定位失败时自动尝试其他方式，而非直接报错
5. **可观测性**：每步操作都有日志和截图，便于问题定位

### 技术选型

| 组件 | 选择理由 |
|------|----------|
| **大语言模型** | 支持 Tool Use / Function Calling，能理解自然语言测试指令 |
| **Playwright** | 现代浏览器自动化框架，API 简洁，自动等待机制，跨浏览器支持 |

**支持的 AI 提供商：**

| 提供商 | 模型 | 特点 |
|--------|------|------|
| Anthropic | Claude Sonnet 4 | 原生 Tool Use，多模态能力强，中文理解优秀 |
| 智谱 AI | GLM-4 系列 | 国产大模型，支持 Function Calling，访问稳定 |

### 与传统方案对比

| 维度 | 传统自动化测试 | AI Agent 测试 |
|------|---------------|---------------|
| 编写方式 | 代码 (Python/JS) | 自然语言 |
| 元素定位 | 硬编码选择器 | AI 智能定位 |
| 维护成本 | 高（页面变动需改代码） | 低（AI 自适应） |
| 调试方式 | 断点/日志 | 截图 + 对话 |
| 学习曲线 | 需要编程基础 | 会说话就行 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户交互层                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  命令行 CLI  │  │  交互模式   │  │  直接执行模式            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Agent 核心层                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      TestAgent                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │  │
│  │  │ 消息管理器   │  │  对话循环   │  │  工具执行调度器  │    │  │
│  │  │ (messages)  │  │  (chat)     │  │  (_execute_tool) │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   AI 客户端抽象层                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                 │  │
│  │  │ AnthropicClient │  │   GLMClient     │   ...更多适配器  │  │
│  │  │ (Claude)        │  │   (智谱)         │                 │  │
│  │  └─────────────────┘  └─────────────────┘                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                                          │
          ▼                                          ▼
┌─────────────────────┐                 ┌─────────────────────────┐
│  AI API (可切换)     │                 │   Playwright 执行层      │
│  ┌───────────────┐  │                 │  ┌───────────────────┐  │
│  │ Claude/GLM    │  │  ◄───────────►  │  │ PlaywrightExecutor│  │
│  │ Tool Use      │  │    工具调用     │  │ (25+ 工具方法)     │  │
│  │ 自然语言处理   │  │                 │  └───────────────────┘  │
│  └───────────────┘  │                 │           │             │
└─────────────────────┘                 │           ▼             │
                                        │  ┌───────────────────┐  │
                                        │  │  Chromium 浏览器   │  │
                                        │  └───────────────────┘  │
                                        └─────────────────────────┘
                                                    │
                                                    ▼
                                        ┌─────────────────────────┐
                                        │       被测系统           │
                                        │   (Web 应用 / 内网服务)   │
                                        └─────────────────────────┘
```

### 数据流向

```
用户输入 ──► TestAgent ──► AI 客户端 ──► AI API ──► 返回工具调用指令
                │                                        │
                │              ◄─────────────────────────┘
                ▼
        PlaywrightExecutor ──► 执行浏览器操作 ──► 返回结果/截图
                │
                │           (结果发送给 AI 分析)
                ▼
            AI API ──► 分析结果，决定下一步 ──► 循环继续...
                │
                │           (直到调用 test_complete)
                ▼
         输出测试报告 (Allure 格式)
```

---

## 业务流程

### 整体流程图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Agent 主循环                                    │
└──────────────────────────────────────────────────────────────────────────┘

     ┌─────────┐
     │  开始   │
     └────┬────┘
          │
          ▼
┌─────────────────┐
│  启动浏览器      │ ◄─── 配置代理、视口大小、语言等
└────────┬────────┘
          │
          ▼
┌─────────────────┐
│ 接收用户输入     │ ◄─── 自然语言测试用例
└────────┬────────┘
          │
          ▼
┌─────────────────┐
│ 发送给 AI API   │ ◄─── 包含系统提示词 + 工具定义 + 对话历史
└────────┬────────┘
          │
          ▼
    ┌───────────┐     是      ┌─────────────────┐
    │ 有工具调用？├────────────►│ 执行工具调用     │
    └─────┬─────┘              └────────┬────────┘
          │ 否                          │
          │                             ▼
          │                   ┌─────────────────┐
          │                   │ 收集执行结果     │ ◄─── 包含截图(base64)
          │                   └────────┬────────┘
          │                             │
          │                             ▼
          │                   ┌─────────────────┐
          │                   │ 结果发回 AI API  │
          │                   └────────┬────────┘
          │                             │
          │         ┌───────────────────┘
          │         │
          ▼         ▼
    ┌───────────────────┐
    │  AI 返回文本响应   │
    └─────────┬─────────┘
              │
              ▼
      ┌──────────────┐    是    ┌─────────────┐
      │ 测试完成？    ├─────────►│ 输出报告     │
      └──────┬───────┘          └──────┬──────┘
             │ 否                       │
             │                          ▼
             │                    ┌──────────┐
             │                    │   结束    │
             ▼                    └──────────┘
      ┌──────────────┐
      │ 等待用户输入  │ ◄─── 交互模式下继续对话
      └──────────────┘
```

### 详细步骤说明

#### 阶段一：初始化

```python
# 1. 创建 Agent 实例
agent = TestAgent(
    api_key="sk-xxx",        # Claude API 密钥
    headless=False,          # 是否无头模式
    proxy="socks5://...",    # 可选代理
    ignore_https_errors=True # 忽略证书错误
)

# 2. 启动浏览器
agent.start_browser()
# - 创建 Playwright 实例
# - 启动 Chromium（可配置代理）
# - 创建浏览器上下文（视口 1280x720，中文语言）
# - 创建页面实例
# - 初始化工具执行器 PlaywrightExecutor
```

#### 阶段二：对话循环（核心）

这是 Agent 的核心机制，基于 **ReAct (Reasoning + Acting)** 模式：

```
┌────────────────────────────────────────────────────────────────┐
│                        ReAct 循环                               │
│                                                                │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│   │ Observe  │ ──►│  Think   │ ──►│   Act    │ ──┐           │
│   │  观察    │    │   思考   │    │   行动   │   │           │
│   └──────────┘    └──────────┘    └──────────┘   │           │
│        ▲                                          │           │
│        └──────────────────────────────────────────┘           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**具体流程：**

1. **用户输入** → 添加到消息历史
2. **调用 AI API**
   - 发送：系统提示词 + 工具定义 + 完整对话历史
   - 返回：文本响应 和/或 工具调用请求
3. **检查响应类型**
   - 如果只有文本 → 直接返回给用户
   - 如果有工具调用 → 进入执行流程
4. **执行工具调用**
   - 解析工具名称和参数
   - 调用 `PlaywrightExecutor.execute()`
   - 收集执行结果
5. **处理执行结果**
   - 普通结果 → 转为 JSON 文本
   - 截图结果 → 转为 base64 图片 + 文本说明（Anthropic）或文本描述（GLM）
6. **结果发回 AI**
   - AI 根据结果理解页面状态
   - 决定下一步操作
7. **循环继续** 直到：
   - AI 返回纯文本（无工具调用）
   - 或调用 `test_complete` 工具标记测试结束

#### 阶段三：工具执行

```
┌─────────────────────────────────────────────────────────────────┐
│                      工具执行流程                                 │
│                                                                  │
│   Claude 请求:                                                   │
│   {                                                              │
│     "type": "tool_use",                                         │
│     "name": "click",                                            │
│     "input": {"selector": "text=登录"}                          │
│   }                                                              │
│                        │                                         │
│                        ▼                                         │
│   ┌────────────────────────────────────┐                        │
│   │     PlaywrightExecutor.execute()    │                        │
│   │  1. 解析工具名称: "click"            │                        │
│   │  2. 查找对应方法: _tool_click()      │                        │
│   │  3. 执行: page.click("text=登录")   │                        │
│   │  4. 捕获异常，返回结果               │                        │
│   └────────────────────────────────────┘                        │
│                        │                                         │
│                        ▼                                         │
│   返回结果:                                                      │
│   {"success": true, "message": "已点击元素: text=登录"}          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 阶段四：视觉反馈机制

这是本 Agent 的关键设计——**让 AI "看到" 页面**：

```
┌─────────────────────────────────────────────────────────────────┐
│                      视觉反馈流程                                 │
│                                                                  │
│   Agent 调用 screenshot 工具                                     │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │ Playwright 截图  │ ──► PNG 图片 ──► Base64 编码              │
│   └─────────────────┘                                           │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────────────────────────┐                       │
│   │ 构造消息发送给 AI                    │                       │
│   │                                      │                       │
│   │ Anthropic: 多模态消息（含截图）      │                       │
│   │ GLM: 文本描述（截图已获取提示）      │                       │
│   │                                      │                       │
│   └─────────────────────────────────────┘                       │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────────────────────────┐                       │
│   │ AI 分析结果                          │                       │
│   │ - 识别页面元素                       │                       │
│   │ - 判断操作是否成功                   │                       │
│   │ - 决定下一步操作                     │                       │
│   └─────────────────────────────────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**为什么需要视觉反馈？**

1. **验证操作结果**：点击后页面是否变化？输入框内容是否正确？
2. **智能决策**：看到错误提示后，可以判断登录失败并报告
3. **处理动态内容**：SPA 应用的异步加载，需要看到才知道完成
4. **调试定位**：当选择器失效时，看截图找到正确的元素

---

## 核心组件

### 1. TestAgent (agent.py)

Agent 的主控制器，负责协调各组件：

```python
class TestAgent:
    """
    职责：
    1. 管理浏览器生命周期
    2. 维护对话历史 (messages)
    3. 通过 AI 客户端抽象层与 AI API 通信
    4. 调度工具执行
    5. 生成 Allure 测试报告
    """

    def chat(self, user_message: str) -> str:
        """核心对话循环"""
        # 1. 添加用户消息
        # 2. 调用 AI API（通过抽象层）
        # 3. 处理工具调用
        # 4. 返回最终响应

    def run_test(self, test_case: str, ...) -> str:
        """执行完整测试用例"""

    def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """执行单个工具，记录到 Allure 报告"""
```

### 2. AI 客户端抽象层 (ai_client.py)

支持多个 AI 提供商的统一接口：

```python
class AIClient(ABC):
    """AI 客户端抽象基类"""

    def chat(self, messages, system, tools, max_tokens) -> AIResponse:
        """发送对话请求"""

    def format_tool_result(self, tool_call_id, result, ...) -> Dict:
        """格式化工具执行结果"""

class AnthropicClient(AIClient):
    """Anthropic Claude 客户端"""

class GLMClient(AIClient):
    """智谱 GLM 客户端"""
```

### 3. PlaywrightExecutor (tools.py)

浏览器操作的执行器：

```python
class PlaywrightExecutor:
    """
    职责：
    1. 封装所有 Playwright 操作
    2. 统一的错误处理
    3. 返回结构化结果
    """

    def execute(self, tool_name: str, tool_input: dict) -> dict:
        """通用执行入口，动态分发到具体方法"""

    # 25+ 工具方法
    def _tool_navigate(self, url): ...
    def _tool_click(self, selector): ...
    def _tool_fill(self, selector, text): ...
    def _tool_screenshot(self, full_page=False): ...
    # ...
```

### 4. 工具定义 (tools.py - TOOLS)

符合 Claude Tool Use 规范的工具描述：

```python
TOOLS = [
    {
        "name": "click",
        "description": "点击页面上的元素...",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "元素选择器..."
                }
            },
            "required": ["selector"]
        }
    },
    # ... 更多工具
]
```

### 5. 系统提示词 (agent.py - SYSTEM_PROMPT)

指导 Claude 如何执行测试的核心指令：

- 定义 Agent 角色和能力
- 规定工作流程（观察→执行→验证）
- 提供选择器使用技巧
- 设定执行原则

---

## 工具清单

| 类别 | 工具名 | 功能 |
|------|--------|------|
| **导航** | `navigate` | 打开 URL |
| | `go_back` | 后退 |
| | `go_forward` | 前进 |
| | `refresh` | 刷新 |
| **交互** | `click` | 点击元素 |
| | `fill` | 填入文本（清空后输入） |
| | `type_text` | 逐字输入（触发输入事件） |
| | `press_key` | 按键（Enter/Tab/Escape） |
| | `select_option` | 下拉框选择 |
| | `check` / `uncheck` | 复选框操作 |
| | `hover` | 鼠标悬停 |
| | `scroll` | 滚动页面 |
| **获取信息** | `screenshot` | 截图（可全页） |
| | `get_text` | 获取元素文本 |
| | `get_attribute` | 获取元素属性 |
| | `get_page_content` | 获取页面文本内容 |
| | `get_elements_info` | 批量获取元素信息 |
| | `get_current_url` | 当前 URL |
| | `get_page_title` | 页面标题 |
| **等待** | `wait_for_selector` | 等待元素出现 |
| | `wait_for_navigation` | 等待页面跳转 |
| **断言** | `assert_visible` | 验证元素可见 |
| | `assert_text_contains` | 验证文本包含 |
| | `assert_url_contains` | 验证 URL 包含 |
| **流程** | `test_complete` | 标记测试完成 |

---

## 安装配置

```bash
cd test-agent

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 创建配置文件

复制示例配置文件并修改：

```bash
cp config/config.example.yaml config/config.yaml
```

编辑 `config.yaml`：

```yaml
# AI 配置
ai:
  provider: "glm"           # anthropic 或 glm
  api_key: "your-api-key"   # API 密钥
  model: ""                 # 可选，留空使用默认模型

# 被测系统配置
target:
  url: "http://internal-app.local:8080"
  bearer_token: ""          # Bearer Token（留空则启动时提示输入）

# 代理配置（可选，支持 http/https/socks5）
proxy: ""

# 浏览器配置
browser:
  headless: false
  viewport:
    width: 1280
    height: 720
  locale: "zh-CN"
```

### 配置项说明

| 配置项 | 说明 |
|--------|------|
| `ai.provider` | AI 提供商：`anthropic`（Claude）或 `glm`（智谱） |
| `ai.api_key` | API 密钥，也可通过环境变量设置 |
| `ai.model` | 模型名称，留空使用默认模型 |
| `target.url` | 被测系统的起始 URL |
| `target.bearer_token` | Bearer Token 认证令牌，留空则启动时交互输入 |
| `proxy` | 代理服务器地址，支持 http://、https://、socks5:// |
| `browser.headless` | 是否无头模式运行 |
| `browser.viewport` | 浏览器视口大小 |
| `browser.locale` | 浏览器语言 |

> **说明**：默认忽略 HTTPS 证书错误，可直接测试使用自签名证书的内网服务

---

## AI 提供商配置

### 智谱 GLM（推荐国内用户）

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/) 注册账号
2. 创建 API Key
3. 配置：

```yaml
ai:
  provider: "glm"
  api_key: "your-zhipuai-api-key"
  model: "glm-4-plus"  # 或 glm-4, glm-4-flash 等
```

或设置环境变量：
```bash
export ZHIPUAI_API_KEY="your-api-key"
```

**支持的模型：**
- `glm-4-plus` - 高性能版本（推荐）
- `glm-4` - 标准版本
- `glm-4-flash` - 快速版本
- `glm-4-air` - 轻量版本

### Anthropic Claude

1. 访问 [Anthropic Console](https://console.anthropic.com/) 注册账号
2. 创建 API Key
3. 配置：

```yaml
ai:
  provider: "anthropic"
  api_key: "sk-ant-xxx"
  model: "claude-sonnet-4-20250514"  # 可选
```

或设置环境变量：
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

**支持的模型：**
- `claude-sonnet-4-20250514` - Claude Sonnet 4（默认，推荐）
- `claude-opus-4-20250514` - Claude Opus 4（更强大）

### 环境变量优先级

API Key 的读取优先级：
1. 配置文件 `ai.api_key`
2. 环境变量（`ZHIPUAI_API_KEY` 或 `ANTHROPIC_API_KEY`）

---

## 使用方法

### 交互模式（推荐）

```bash
# 使用 config.yaml 启动
python main.py

# 指定配置文件
python main.py --config /path/to/config.yaml
```

启动后会显示当前配置，然后进入交互模式：

```
当前配置:
  AI 提供商: glm (glm-4-plus)
  目标 URL: https://your-app.example.com
  代理: (无)
  认证: Bearer Token 已配置
  无头模式: False
  变量: login, search

已打开页面: https://your-app.example.com

进入交互模式，输入测试指令开始测试

你: 点击登录按钮，验证跳转到登录页面

Agent: [开始执行测试...]
```

### 直接执行模式

```bash
# 命令行输入测试用例
python main.py --test "在搜索框输入关键词，点击搜索，验证结果"

# 执行测试用例文件
python main.py --file examples/login.txt
python main.py --file examples/search.txt
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--config, -c` | 配置文件路径，默认读取 config/config.yaml |
| `--test, -t` | 直接执行的测试用例（命令行输入） |
| `--file, -f` | 测试用例文件路径（相对于 testcases 目录） |

---

## 测试用例示例

### 搜索功能测试
```
打开百度首页，在搜索框中输入"Python教程"，点击搜索按钮，验证搜索结果页面显示正常
```

### 登录功能测试
```
访问登录页面，在用户名输入框输入"admin"，在密码输入框输入"123456"，点击登录按钮，验证是否跳转到首页或显示错误信息
```

### 表单填写测试
```
打开注册页面，填写以下信息：
- 用户名：testuser
- 邮箱：test@example.com
- 密码：Test123456
点击注册按钮，验证注册成功提示
```

### 购物流程测试
```
1. 在商品列表页面搜索"手机"
2. 点击第一个商品进入详情
3. 点击"加入购物车"按钮
4. 进入购物车页面
5. 验证购物车中有刚才添加的商品
```

---

## 项目结构

```
test-agent/
├── main.py                     # 命令行入口
├── pyproject.toml              # 项目配置
├── requirements.txt            # Python 依赖
├── README.md                   # 说明文档
│
├── src/                        # 源代码目录
│   └── test_agent/             # Agent 包
│       ├── __init__.py
│       ├── agent.py            # Agent 核心逻辑
│       ├── ai_client.py        # AI 客户端抽象层（多提供商支持）
│       ├── tools.py            # Playwright 工具定义
│       ├── config.py           # 配置加载模块
│       ├── reporter.py         # Allure 报告生成模块
│       └── gherkin.py          # Gherkin 语法解析模块
│
├── config/                     # 配置文件目录
│   ├── config.example.yaml     # 配置示例（提交到 Git）
│   └── config.yaml             # 用户配置（不提交，含敏感信息）
│
├── testcases/                  # 测试用例目录
│   ├── README.md               # 用例编写说明
│   └── examples/               # 示例用例
│       └── administrator/      # 管理员功能测试
│           └── cluster-search.feature
│
└── allure-results/             # Allure 报告输出目录（自动生成）
```

---

## Gherkin 语法支持

本项目支持使用 Gherkin 语法编写测试用例（.feature 文件），可以兼容中英文关键字。

### 支持的关键字

| 类型 | 英文 | 中文 |
|------|------|------|
| 功能 | Feature | 功能、特性 |
| 场景 | Scenario, Example | 场景、示例 |
| 前提 | Given | 假如、前提、假设 |
| 操作 | When | 当 |
| 结果 | Then | 那么、则 |
| 连接 | And | 并且、而且、同时 |
| 转折 | But | 但是、但 |
| 背景 | Background | 背景 |

### 示例 .feature 文件

```gherkin
# language: zh-CN
@login @smoke
功能: 集群搜索功能
  作为一个管理员用户
  我希望能够进入管理员页面-集群列表，搜索平台上是否存在特定集群

  背景:
    假如 进入平台并打开Administrator页面

  @positive
  场景: 集群列表中存在 Global 集群
    假如 点击 集群 - 集群 菜单
    那么 可以在集群列表中看到有名为global的集群存在
    并且 global集群状态正常

  @positive
  场景: 输入正确的关键字可以过滤出集群
    假如 点击 集群 - 集群 菜单
    当 在集群列表的名称关键字输入中输入 ${search.keyword}
    并且 点击搜索图标
    那么 集群列表中展示的集群只包括满足关键字信息的集群
```

### 执行 .feature 文件

```bash
# 执行单个 feature 文件
python main.py --file examples/administrator/cluster-search.feature

# 会自动执行文件中的所有场景，并生成 Allure 报告
```

### 在 Gherkin 中使用变量

.feature 文件同样支持变量替换：

- `${login.username}` - 从 config.yaml 读取 login.username
- `{{search.keyword}}` - 另一种变量语法

---

## Allure 测试报告

每次测试执行都会自动生成 Allure 格式的测试报告。

### 报告特性

- **用例级别报告**：每个场景作为独立测试用例
- **步骤记录**：记录每个工具调用作为测试步骤
- **截图附件**：自动保存执行过程中的截图
- **状态分类**：passed / failed / broken / skipped

### 查看报告

```bash
# 1. 安装 Allure 命令行工具（首次）
brew install allure   # macOS
# 或 npm install -g allure-commandline

# 2. 运行测试后，查看报告
python main.py --file examples/login.feature

# 3. 启动 Allure 报告服务器
allure serve allure-results

# 或生成静态报告
allure generate allure-results -o allure-report
allure open allure-report
```

### 报告文件结构

```
allure-results/
├── xxx-result.json          # 测试结果
├── xxx-1.png                 # 截图附件
├── xxx-2.png
├── environment.properties    # 环境信息
└── categories.json           # 分类配置
```

### Allure 报告示例

报告中包含：

- **Overview**：测试总览（通过/失败数量、趋势图）
- **Suites**：按 Feature 分组的测试套件
- **Graphs**：各种统计图表
- **Timeline**：执行时间线
- **Behaviors**：按 Feature/Scenario 分组的行为视图

---

## 扩展方向

**已完成：**
- ✅ **测试报告持久化**：支持 Allure 格式报告
- ✅ **批量执行**：支持 .feature 文件批量执行场景
- ✅ **多 AI 提供商**：支持 Anthropic Claude 和智谱 GLM

**规划中：**
- **更多 AI 提供商**：OpenAI、千问、Kimi等
- **录制回放**：录制用户操作生成自然语言用例
- **CI/CD 集成**：作为流水线的一环自动执行
- **多浏览器支持**：Firefox、WebKit
- **并行执行**：多个浏览器实例并行测试
- **视觉对比**：页面截图对比，检测 UI 变化
