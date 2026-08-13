from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from textwrap import indent
import urllib.request

from config import AGENT_ROLES, GLM_CONFIG

DEFAULT_TASK = "做一个H5的 登入页面 "
RUNS_DIR = Path(__file__).with_name("runs")


@dataclass
class Agent:
    name: str
    role: str

    def run(self, task: str) -> str:
        api_key = get_api_key(GLM_CONFIG)
        body = {
            "model": GLM_CONFIG["model"],
            "messages": [
                {"role": "system", "content": self.role},
                {"role": "user", "content": task},
            ],
            "temperature": GLM_CONFIG["temperature"],
            "max_tokens": GLM_CONFIG["max_tokens"],
            "stream": GLM_CONFIG["stream"],
        }
        request = urllib.request.Request(
            GLM_CONFIG["endpoint"],
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=GLM_CONFIG["timeout"]) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception as error:
            return f"{self.name} Agent 调用 GLM-5.2 失败：{error}"


def get_api_key(config: dict) -> str:
    key = os.environ.get(config["key_env"]) or config.get("api_key")
    if not key:
        raise RuntimeError(
            f"请先设置环境变量：export {config['key_env']}='你的智谱 API Key'，"
            "或在 config.py 的 api_key 填入 key。"
        )
    return key


def build_agents() -> list[Agent]:
    return [Agent(**role) for role in AGENT_ROLES]


def next_input(task: str, agent_name: str, output: str) -> str:
    return f"原始需求：{task}\n\n上一位 {agent_name} Agent 的输出：\n{output}"


def run_agent_step(task: str, agent: Agent, current_input: str, index: int) -> tuple[dict[str, str], str]:
    output = agent.run(current_input)
    record = {
        "step": str(index),
        "agent": agent.name,
        "input": current_input,
        "output": output,
    }
    return record, next_input(task, agent.name, output)


def run_workflow(task: str, agents: list[Agent]) -> list[dict[str, str]]:
    records = []
    current_input = task
    for index, agent in enumerate(agents, start=1):
        record, current_input = run_agent_step(task, agent, current_input, index)
        records.append(record)
    return records


def format_config_summary() -> str:
    return (
        "GLM-5.2 配置\n"
        f"- 接口地址：{GLM_CONFIG['endpoint']}\n"
        f"- 模型：{GLM_CONFIG['model']}\n"
        f"- temperature：{GLM_CONFIG['temperature']}\n"
        f"- max_tokens：{GLM_CONFIG['max_tokens']}\n"
        f"- stream：{GLM_CONFIG['stream']}\n"
        f"- timeout：{GLM_CONFIG['timeout']} 秒"
    )


def parse_task(argv: list[str]) -> str:
    args = [arg for arg in argv[1:] if arg not in {"figma", "agent"}]
    if "--agent" in args:
        index = args.index("--agent")
        args = args[:index] + args[index + 2 :]
    return " ".join(args).strip() or DEFAULT_TASK


def parse_agent_name(argv: list[str]) -> str:
    args = argv[1:]
    if "--agent" not in args:
        return ""
    index = args.index("--agent")
    return args[index + 1] if index + 1 < len(args) else ""


def select_agents(agents: list[Agent], name: str) -> list[Agent]:
    return [agent for agent in agents if agent.name == name] if name else agents


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", text).strip("_")
    return slug or "project"


def create_run_dir(project_name: str, timestamp: str = "") -> Path:
    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    return RUNS_DIR / f"{stamp}_{slugify(project_name)}"


def save_stage_files(
    run_dir: Path,
    stage: str,
    input_data: dict,
    report: str,
    html: str = "",
) -> dict[str, Path]:
    stage_dir = run_dir / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "input": stage_dir / "input.json",
        "report": stage_dir / "result.md",
    }
    paths["input"].write_text(json.dumps(input_data, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["report"].write_text(report, encoding="utf-8")
    if html:
        paths["html"] = stage_dir / "login.html"
        paths["html"].write_text(html, encoding="utf-8")
    return paths


def print_record(record: dict[str, str]) -> None:
    print(f"\nStep {record['step']} -> {record['agent']} Agent")
    print("输入：")
    print(indent(record["input"], "  "))
    print("输出：")
    print(indent(record["output"], "  "))
    print()


def format_report(task: str, records: list[dict[str, str]]) -> str:
    parts = [f"# Agent 运行结果\n\n## 原始需求\n{task}\n"]
    for record in records:
        parts.append(
            f"## Step {record['step']} - {record['agent']} Agent\n\n"
            f"### 输入\n{record['input']}\n\n"
            f"### 输出\n{record['output']}\n"
        )
    return "\n".join(parts)


def extract_html(text: str) -> str:
    match = re.search(r"```html\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    start = text.lower().find("<!doctype html")
    return text[start:].strip() if start >= 0 else ""


def fallback_login_html(task: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>登录</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f4f6f8;
      color: #1f2937;
    }}
    main {{
      width: min(360px, calc(100vw - 32px));
      padding: 28px 22px;
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    p {{ margin: 0 0 24px; color: #6b7280; }}
    label {{ display: block; margin: 14px 0 6px; font-size: 14px; }}
    input {{
      width: 100%;
      height: 44px;
      padding: 0 12px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 16px;
    }}
    button {{
      width: 100%;
      height: 44px;
      margin-top: 22px;
      border: 0;
      border-radius: 6px;
      background: #2563eb;
      color: white;
      font-size: 16px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>登录</h1>
    <p>{task}</p>
    <form onsubmit="event.preventDefault(); alert('登录示例');">
      <label for="phone">手机号</label>
      <input id="phone" name="phone" type="tel" placeholder="请输入手机号" required>
      <label for="password">密码</label>
      <input id="password" name="password" type="password" placeholder="请输入密码" required>
      <button type="submit">登录</button>
    </form>
  </main>
</body>
</html>
"""


def build_html_artifact(task: str, records: list[dict[str, str]]) -> str:
    developer_output = next((record["output"] for record in records if record["agent"] == "开发"), "")
    return extract_html(developer_output) or fallback_login_html(task)


def latest_run_dir() -> Path | None:
    if not RUNS_DIR.exists():
        return None
    runs = [path for path in RUNS_DIR.iterdir() if path.is_dir()]
    return max(runs, key=lambda path: path.stat().st_mtime) if runs else None


def read_text_if_exists(path: Path, limit: int = 20000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")[:limit]


def collect_figma_context(run_dir: Path) -> str:
    parts = [f"资料目录：{run_dir}"]
    for kind in ("requirement", "design"):
        stage_dir = run_dir / kind
        parts.append(f"\n# {kind}")
        parts.append(read_text_if_exists(stage_dir / "prototype.md"))
        parts.append(read_text_if_exists(stage_dir / "figma_layout.json"))
        for layout_file in sorted(stage_dir.glob("node_*/layout.md")):
            parts.append(read_text_if_exists(layout_file))
    return "\n".join(part for part in parts if part)


def analyze_requirement_from_figma(run_dir: Path) -> Path:
    agent = Agent(
        "需求分析",
        "你是产品需求分析 Agent。你要从 Figma 原型资料中提取业务需求，并检查高真设计是否足够支撑这些需求。",
    )
    prompt = (
        "请基于下面 Figma 资料生成需求文档。\n"
        "要求：\n"
        "1. 区分需求原生信息和高真设计信息。\n"
        "2. 输出业务目标、页面/状态、用户流程、交互规则、异常/空状态、验收点。\n"
        "3. 明确写出：高真设计是否足够支撑需求；缺哪些信息；需要向产品/设计确认什么。\n"
        "4. 不要只描述 UI 布局。\n\n"
        f"{collect_figma_context(run_dir)}"
    )
    output = agent.run(prompt)
    output_path = run_dir / "requirement.md"
    output_path.write_text(output, encoding="utf-8")
    return output_path


def run_agent_flow(argv: list[str]) -> None:
    task = parse_task(argv)
    agent_name = parse_agent_name(argv)
    agents = select_agents(build_agents(), agent_name)
    records = []
    stage = agent_name or "all"
    run_dir = create_run_dir(slugify(task)[:30])

    print("1. 创建 Agent")
    for agent in agents:
        print(f"- {agent.name}：{agent.role}")

    print(f"\n2. 输入原始需求\n{task}")

    print("\n3. 调度流程")
    current_input = task
    for index, agent in enumerate(agents, start=1):
        print(f"\n正在调度 Step {index} -> {agent.name} Agent ...", flush=True)
        record, current_input = run_agent_step(task, agent, current_input, index)
        records.append(record)
        print_record(record)

    report = format_report(task, records)
    html = build_html_artifact(task, records)
    paths = save_stage_files(
        run_dir,
        stage,
        {"task": task, "agent": agent_name, "stage": stage},
        report,
        html,
    )

    print("4. 模型配置")
    print(format_config_summary())
    print(f"\n本次目录：{run_dir}")
    print(f"阶段目录：{run_dir / stage}")
    print(f"报告已保存：{paths['report']}")
    print(f"页面已保存：{paths['html']}")


def run_figma_flow() -> None:
    from figma_fetch import fetch_figma_links

    requirement_links = input("请输入需求原生 Figma 链接，多个用英文逗号分割：").strip()
    design_links = input("请输入高真设计 Figma 链接，多个用英文逗号分割：").strip()
    project = input("请输入项目名（直接回车默认 figma）：").strip() or "figma"
    try:
        if requirement_links:
            req_dir = fetch_figma_links(requirement_links, slugify(project), "requirement")
            print(f"需求原生目录：{req_dir}")
        if design_links:
            des_dir = fetch_figma_links(design_links, slugify(project), "design")
            print(f"高真设计目录：{des_dir}")
    except Exception as error:
        print(f"Figma 获取失败：{error}")
        return


def run_requirement_analysis_flow() -> None:
    raw = input("请输入要分析的 run 目录（直接回车用最新）：").strip()
    run_dir = Path(raw).expanduser() if raw else latest_run_dir()
    if not run_dir or not run_dir.exists():
        print("没有找到可分析的 run 目录。")
        return
    print(f"正在分析：{run_dir}")
    output_path = analyze_requirement_from_figma(run_dir)
    print(f"需求文档已生成：{output_path}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "figma":
        run_figma_flow()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "agent":
        run_agent_flow(sys.argv)
        return

    print("请选择要调试的功能：")
    print("1. 获取 Figma 信息")
    print("2. 创建 Agent / 调用大模型")
    print("3. 分析 Figma 需求")
    choice = input("输入 1、2 或 3：").strip()
    if choice == "1":
        run_figma_flow()
    elif choice == "3":
        run_requirement_analysis_flow()
    else:
        run_agent_flow(["main.py"])


if __name__ == "__main__":
    main()

# https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?m=dev&focus-id=1280-4791,https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?m=dev&focus-id=1280-5041,https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?m=dev&focus-id=1280-5197,https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?m=dev&focus-id=1593-952,https://www.figma.com/design/W0M3jAZpdBP7OdWfZwrqJE/%E7%A4%BE%E5%8C%BA%EF%BC%88%E6%AF%8F%E5%91%A8%E6%9B%B4%E6%96%B0%E7%89%88%EF%BC%89?m=dev&focus-id=1593-1307

# https://www.figma.com/design/Wri0aaE2EIaesO0u2LTDAS/%E8%BF%AD%E4%BB%A3%E7%89%88%E7%A4%BE%E5%8C%BA?node-id=2099-215&m=dev&focus-id=2099-215