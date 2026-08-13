# ai-loop

AI 辅助的项目编排仓库。

## 目录

- `core/`：项目核心。负责调度、Figma 获取/解析、Agent 编排、流程控制。
- `app/`：目标应用项目。当前可以是 Flutter，后续可替换为其他技术栈。
- `dashboard/`：整个项目的可视化页面。默认使用 `Next.js + Ant Design + ProComponents`，参考 `Ant Design Pro` 的布局和风格。
- `docs/`：背景、需求、约定、目录说明。
- `runs/`：每次任务的临时过程产物。
- `artifacts/`：每次任务的an结果产物。

## 约定

- `runs/` 和 `artifacts/` 默认不提交到 git。
- `app/` 只表示目标应用层，不绑定 Flutter。
- `core/` 是整个项目的核心能力入口。
