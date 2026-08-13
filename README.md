# ai-loop

AI-assisted repository for orchestrating project work, target app delivery, and a visual dashboard.

## Structure

- `core/`: orchestration, agent control, and Figma processing.
- `app/`: the target application layer. It is app-agnostic and may be Flutter today or something else later.
- `dashboard/`: the visual control center. It uses `Next.js + Ant Design + ProComponents`.
- `docs/`: background, requirements, conventions, and project notes.
- `runs/`: temporary per-task inputs, intermediate output, and logs.
- `artifacts/`: task outputs, exports, builds, and reports.

## Run

Dashboard:

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:3000`.

## Conventions

- Keep temporary data in `runs/` or `artifacts/`; do not move it into source folders.
- Keep `app/` generic; do not assume Flutter forever.
- Treat `dashboard/` as the main UI for tasks, logs, and artifact review.
- Update `README.md`, `AGENTS.md`, and `docs/` when the structure changes.

## Notes

The `test/` directory is a separate test project and is not part of the main repository layout.
