# core

`ai-loop` 的 Python 核心层。

## 职责

`core/` 负责核心自动化逻辑，重点是创建和调度不同角色的 agent，
把一个任务拆成可执行的步骤并串起来。

- 接收来自 `dashboard/` 的任务输入；
- 处理需求、上下文和外部资料，形成可执行任务；
- 按角色创建 agent，并负责它们的调度顺序；
- 汇总 agent 的输出，生成编码、测试和验收所需的中间结果；
- 保存运行日志、输入、决策和产物。

`core/` 不负责 UI，也不直接承载目标应用代码。

## Agent 模型

一个任务通常会拆成多个角色 agent，按需创建、按顺序或并行调度：

- 需求分析 agent：整理输入，补齐任务背景和约束；
- 反馈整理 agent：接收用户反馈，转成可执行修订点；
- 任务编排 agent：拆分步骤，决定后续执行顺序；
- 编码 agent：对 `app/` 执行代码修改；
- 测试 agent：运行检查，验证修改结果；
- 验收 agent：检查结果是否满足任务目标。

不同任务不一定都需要完整角色集，但 `core/` 需要能组合这些角色，
并把它们组织成一次完整任务流。

## 主流程

1. 接收任务输入。
2. 解析需求和上下文。
3. 创建对应角色的 agent。
4. 调度 agent 执行任务步骤。
5. 汇总输出、日志和验证结果。
6. 写入 `runs/` 和 `artifacts/`。

## 当前状态

目前已经实现的主要是 Figma 输入采集和落盘：

1. 解析一个或多个 Figma 设计链接。
2. 通过 Figma API 拉取 file、node、comments、components、styles、image fills、
   versions、dev resources 和节点渲染图。
3. 把原始响应和精简 manifest 保存到 `runs/<task-id>/`。
4. 生成 `prototype.md` 和 `figma_layout.json`，供后续流程使用。

通用编排、agent 执行、应用改动、测试、验收和结果固化流程还没有完成。

## 运行

```bash
cd core
uv run core
```

Figma 输入采集需要：

```bash
export FIGMA_ACCESS_TOKEN="your Figma token"
```

## 输出

运行产物放在源码目录外：

- `runs/<task-id>/`：原始输入、中间数据和日志。
- `artifacts/<task-id>/`：需要保留的结果、构建产物、导出文件和报告。

## 约定

- 这个目录只放编排和输入处理相关逻辑。
- 临时数据和生成数据放在 `runs/` 或 `artifacts/`。
- 系统结构变化时，同步更新根目录 `README.md` 和 `docs/`。
