#!/usr/bin/env python3
"""
测试执行 Agent 命令行入口
"""

import argparse
import re
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from test_agent import TestAgent, Config, parse_feature_file, feature_to_testcase
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
CONFIG_DIR = PROJECT_ROOT / "config"
TESTCASES_DIR = PROJECT_ROOT / "testcases"


def load_testcase(testcase_path: str) -> str:
    """加载测试用例文件"""
    path = Path(testcase_path)

    # 如果是相对路径，从 testcases 目录查找
    if not path.is_absolute():
        path = TESTCASES_DIR / path

    if not path.exists():
        raise FileNotFoundError(f"测试用例文件不存在: {path}")

    return path.read_text(encoding="utf-8").strip()


def substitute_variables(text: str, config: Config) -> str:
    """
    替换测试用例中的变量占位符

    支持格式：
    - ${login.username} 或 ${login.password}
    - {{login.username}} 或 {{login.password}}
    """
    flat_vars = config.flatten_variables()

    def replace_var(match):
        var_name = match.group(1)
        value = flat_vars.get(var_name)
        if value is not None:
            return str(value)
        # 变量不存在，保留原样
        console.print(f"[yellow]警告: 变量 '{var_name}' 未定义[/yellow]")
        return match.group(0)

    # 替换 ${var} 格式
    text = re.sub(r'\$\{([^}]+)\}', replace_var, text)
    # 替换 {{var}} 格式
    text = re.sub(r'\{\{([^}]+)\}\}', replace_var, text)

    return text


def main():
    parser = argparse.ArgumentParser(
        description="AI 测试执行 Agent - 使用自然语言执行 Web UI 测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 使用配置文件启动交互模式
  python main.py

  # 指定配置文件
  python main.py --config config/my-config.yaml

  # 直接执行测试用例（命令行输入）
  python main.py --test "点击登录按钮，验证登录成功"

  # 执行测试用例文件
  python main.py --file testcases/login.txt

目录结构:
  config/           配置文件目录
  testcases/        测试用例目录
"""
    )

    parser.add_argument(
        "--config", "-c",
        type=str,
        help="配置文件路径，默认读取 config/config.yaml"
    )

    parser.add_argument(
        "--test", "-t",
        type=str,
        help="要执行的测试用例（自然语言描述）"
    )

    parser.add_argument(
        "--file", "-f",
        type=str,
        help="测试用例文件路径（相对于 testcases 目录）"
    )

    args = parser.parse_args()

    # 确定配置文件路径
    config_path = args.config
    if not config_path:
        # 按优先级查找配置文件
        for candidate in [
            CONFIG_DIR / "config.yaml",
            CONFIG_DIR / "config.yml",
            PROJECT_ROOT / "config.yaml",
            PROJECT_ROOT / "config.yml",
        ]:
            if candidate.exists():
                config_path = str(candidate)
                break

    # 加载配置
    config = Config.load(config_path)

    if not config_path or not Path(config_path).exists():
        console.print("[yellow]未找到配置文件[/yellow]")
        console.print(f"[dim]请复制 config/config.example.yaml 为 config/config.yaml 并修改[/dim]\n")

    # 检查 API Key
    if not config.ai.api_key:
        console.print("[red]错误: 未配置 API Key[/red]")
        if config.ai.provider == "glm":
            console.print("[dim]请在配置文件中设置 ai.api_key，或设置环境变量 ZHIPUAI_API_KEY[/dim]")
        else:
            console.print("[dim]请在配置文件中设置 ai.api_key，或设置环境变量 ANTHROPIC_API_KEY[/dim]")
        sys.exit(1)

    # 检查 Bearer Token，如果未配置且在交互模式下则提示输入
    if not config.target.bearer_token and sys.stdin.isatty():
        console.print("[yellow]未配置 Bearer Token[/yellow]")
        token = Prompt.ask("请输入 Bearer Token（留空跳过）", default="", password=True)
        if token:
            config.target.bearer_token = token

    # 创建 Agent
    try:
        agent = TestAgent.from_config(config)
    except Exception as e:
        console.print(f"[red]初始化失败: {e}[/red]")
        sys.exit(1)

    # 显示配置信息
    console.print("\n[bold]当前配置:[/bold]")
    ai_info = f"{config.ai.provider}"
    if config.ai.model:
        ai_info += f" ({config.ai.model})"
    console.print(f"  AI 提供商: {ai_info}")
    console.print(f"  目标 URL: {config.target.url or '(未设置)'}")
    console.print(f"  代理: {config.proxy or '(无)'}")
    console.print(f"  认证: {'Bearer Token 已配置' if config.target.bearer_token else '(无)'}")
    console.print(f"  无头模式: {config.browser.headless}")

    # 显示可用变量
    if config.variables:
        console.print(f"  变量: {', '.join(config.variables.keys())}")
    console.print()

    # 获取测试用例
    test_case = None
    feature_file = None

    if args.file:
        file_path = Path(args.file)
        # 如果是相对路径，从 testcases 目录查找
        if not file_path.is_absolute():
            file_path = TESTCASES_DIR / file_path

        if not file_path.exists():
            console.print(f"[red]测试用例文件不存在: {file_path}[/red]")
            sys.exit(1)

        # 检测是否为 .feature 文件
        if file_path.suffix.lower() == ".feature":
            feature_file = file_path
            console.print(f"[blue]加载 Feature 文件:[/blue] {args.file}")
        else:
            try:
                test_case = load_testcase(args.file)
                console.print(f"[blue]加载测试用例:[/blue] {args.file}")
            except FileNotFoundError as e:
                console.print(f"[red]{e}[/red]")
                sys.exit(1)
    elif args.test:
        test_case = args.test

    # 变量替换
    if test_case:
        original_case = test_case
        test_case = substitute_variables(test_case, config)
        if test_case != original_case:
            console.print("[dim]已替换变量[/dim]")
        console.print()

    # 执行模式
    if feature_file:
        # 执行 .feature 文件中的所有场景
        feature = parse_feature_file(str(feature_file))
        console.print(f"\n[bold]Feature:[/bold] {feature.name}")
        if feature.description:
            console.print(f"[dim]{feature.description}[/dim]")
        console.print(f"[dim]共 {len(feature.scenarios)} 个场景[/dim]\n")

        results = []
        for i, scenario in enumerate(feature.scenarios, 1):
            console.print(f"[bold cyan]━━━ 场景 {i}/{len(feature.scenarios)}: {scenario.name} ━━━[/bold cyan]")

            # 将 Gherkin 场景转换为自然语言测试用例
            test_case_text = feature_to_testcase(feature, scenario)

            # 变量替换
            test_case_text = substitute_variables(test_case_text, config)

            # 执行测试
            result = agent.run_test(
                test_case_text,
                start_url=config.target.url or None,
                variables=config.variables,
                feature_name=feature.name,
                scenario_name=scenario.name
            )
            results.append((scenario.name, result))

            console.print(Panel(Markdown(result), title=f"场景结果: {scenario.name}", border_style="green"))
            console.print()

        # 汇总结果
        console.print("\n[bold]━━━ 测试汇总 ━━━[/bold]")
        # 与 TestAgent.run_test 中的一致性：
        # run_test 只有在结果文本包含“失败”或“failed”时才将测试标记为 failed，
        # 否则认为通过。因此这里的通过/失败统计也按这个规则来判断，
        # 避免出现终端统计与 Allure 报告不一致的情况。
        passed = sum(
            1
            for _, r in results
            if "失败" not in r and "failed" not in r.lower()
        )
        failed = len(results) - passed
        console.print(f"  总场景数: {len(results)}")
        console.print(f"  [green]通过: {passed}[/green]")
        if failed > 0:
            console.print(f"  [red]失败: {failed}[/red]")
        console.print(f"\n[dim]Allure 报告已生成到: allure-results/[/dim]")
        console.print("[dim]运行 'allure serve allure-results' 查看报告[/dim]")

    elif test_case:
        # 直接执行测试用例
        console.print("[bold]执行测试用例...[/bold]\n")
        result = agent.run_test(test_case, start_url=config.target.url or None, variables=config.variables)
        console.print("\n[bold]测试结果:[/bold]")
        console.print(result)
        console.print(f"\n[dim]Allure 报告已生成到: allure-results/[/dim]")
    else:
        # 交互模式
        if config.target.url:
            # 先导航到指定 URL
            agent.start_browser()
            agent.page.goto(config.target.url, wait_until="domcontentloaded")
            console.print(f"[green]已打开页面: {config.target.url}[/green]")

            # 进入交互循环
            console.print("\n[bold]进入交互模式，输入测试指令开始测试[/bold]")
            console.print("[dim]输入 'quit' 或 'exit' 退出[/dim]\n")

            try:
                while True:
                    try:
                        user_input = console.input("[bold cyan]你:[/bold cyan] ").strip()
                    except EOFError:
                        break

                    if not user_input:
                        continue

                    if user_input.lower() in ["quit", "exit", "q"]:
                        break

                    console.print()
                    response = agent.chat(user_input)
                    console.print(Panel(Markdown(response), title="Agent", border_style="green"))

                    if agent.test_completed:
                        console.print("\n[yellow]测试已完成。继续输入新的测试用例，或输入 'quit' 退出[/yellow]")
                        agent.test_completed = False
                        agent.messages = []

            finally:
                agent.stop_browser()
        else:
            # 纯交互模式
            agent.interactive_mode()


if __name__ == "__main__":
    main()
