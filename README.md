# ai-loop

AI-assisted repository for turning requirements into project changes, tests, and verification.

## Architecture

- `core/`: Python control plane. Handles task orchestration, agent coordination, Figma intake, and workflow steps.
- `app/`: target application under work. It is app-agnostic and may be Flutter today or another stack later.
- `dashboard/`: operator UI for tasks, logs, inputs/outputs, and artifact review. Built with `Next.js + Ant Design + ProComponents`.
- `docs/`: project notes, conventions, requirements, and decisions.
- `runs/`: per-task working directory for raw inputs, intermediate outputs, and logs.
- `artifacts/`: durable task outputs, exports, builds, and reports.
- `test/`: separate test project, not part of the main repository layout.

## Workflow

The repo is organized around a simple flow:

`requirements -> core orchestration -> app changes -> tests and verification -> artifacts and dashboard review`

## Run

Dashboard:

```bash
cd dashboard
npm install
npm run dev
```

Core:

```bash
cd core
uv run core
```

App:

```bash
cd app
flutter run
```

## Conventions

- Keep temporary data in `runs/` or `artifacts/`; do not move it into source folders.
- Keep `app/` generic; do not assume Flutter forever.
- Treat `dashboard/` as the main UI for tasks, logs, and artifact review.
- Update `README.md`, `AGENTS.md`, and `docs/` when the structure changes.
