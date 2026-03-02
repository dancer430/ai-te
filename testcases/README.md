# 测试用例目录

将测试用例文件放在此目录下。

## 支持的文件格式

- `.txt` - 纯文本自然语言描述
- `.feature` - Gherkin 语法（支持中英文关键字）

---

## 纯文本格式 (.txt)

直接用自然语言描述测试步骤：

```
测试目标：验证登录功能

测试步骤：
1. 在用户名输入框输入 admin
2. 在密码输入框输入 123456
3. 点击登录按钮

预期结果：
- 登录成功后跳转到首页
```

## 使用变量

在测试用例中可以使用配置文件中定义的变量，支持两种语法：

- `${变量路径}` - 例如 `${login.username}`
- `{{变量路径}}` - 例如 `{{login.password}}`

### 示例

config/config.yaml:
```yaml
login:
  username: "admin"
  password: "secret123"

search:
  keyword: "测试关键词"
```

testcases/login.txt:
```
测试步骤：
1. 在用户名输入框输入 ${login.username}
2. 在密码输入框输入 ${login.password}
3. 点击登录按钮
```

执行时会自动替换为：
```
测试步骤：
1. 在用户名输入框输入 admin
2. 在密码输入框输入 secret123
3. 点击登录按钮
```

### 变量的好处

1. **敏感信息分离**：密码等敏感信息不直接写在用例里
2. **环境切换**：不同环境使用不同的配置文件
3. **复用性**：同一套用例可以用不同的测试数据执行

---

## Gherkin 格式 (.feature)

使用标准的 Gherkin 语法编写测试用例，支持中英文关键字：

```gherkin
# language: zh-CN
@login @smoke
功能: 用户登录功能
  作为一个用户
  我希望能够登录系统
  以便访问系统的功能

  背景:
    假如 打开登录页面

  @positive
  场景: 使用正确的用户名和密码登录
    假如 用户名输入框已显示
    当 在用户名输入框输入 ${login.username}
    并且 在密码输入框输入 ${login.password}
    并且 点击登录按钮
    那么 应该成功跳转到首页

  @negative
  场景: 使用错误的密码登录
    当 在用户名输入框输入 ${login.username}
    并且 在密码输入框输入 wrong_password
    并且 点击登录按钮
    那么 应该显示登录失败的错误提示
```

### 支持的关键字

| 类型 | 英文关键字 | 中文关键字 |
|------|-----------|-----------|
| 功能 | Feature | 功能、特性 |
| 场景 | Scenario, Example | 场景、示例 |
| 背景 | Background | 背景 |
| 前提 | Given | 假如、前提、假设 |
| 操作 | When | 当 |
| 结果 | Then | 那么、则 |
| 连接 | And | 并且、而且、同时 |
| 转折 | But | 但是、但 |

### Gherkin 格式的优势

1. **标准化**：业界通用的 BDD 测试用例格式
2. **结构化**：清晰区分前提、操作、预期结果
3. **可读性**：非技术人员也能阅读理解
4. **多场景**：一个 Feature 文件包含多个场景，自动逐个执行
5. **标签支持**：@smoke、@regression 等标签便于分类

---

## 执行用例

```bash
# 执行纯文本用例
python main.py --file login.txt
python main.py --file examples/search.txt

# 执行 Gherkin 格式用例（自动识别 .feature 后缀）
python main.py --file examples/login.feature

# 执行后会自动生成 Allure 报告到 allure-results/ 目录
```

## 目录结构建议

```
testcases/
├── examples/               # 示例用例
│   ├── login.txt           # 纯文本格式
│   ├── login.feature       # Gherkin 格式（中文）
│   ├── login_en.feature    # Gherkin 格式（英文）
│   ├── search.txt
│   └── search.feature
├── smoke/                  # 冒烟测试
│   └── core-flow.feature
├── regression/             # 回归测试
├── module-xxx/             # 按模块分类
└── README.md
```

## 查看测试报告

执行测试后，报告会自动生成到 `allure-results/` 目录：

```bash
# 启动 Allure 报告服务器
allure serve allure-results
```
