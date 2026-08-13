# Repository Guidelines

## Project Structure & Module Organization

This repository is organized around four top-level areas:

- `core/`: Python orchestration logic, agent control, and Figma parsing.
- `app/`: the target application project. It may be Flutter today and another app stack later.
- `dashboard/`: the visual task board and logs UI for the whole system.
- `docs/`: background, requirements, conventions, and directory notes.

Generated data belongs outside source folders:

- `runs/<task-id>/`: temporary raw inputs, intermediate output, and logs.
- `artifacts/<task-id>/`: task results, exports, builds, and reports.

## Build, Test, and Development Commands

No build system is defined at the repository root yet. Use the command set of the active subproject:

- `cd core && python ...`: run orchestration or pipeline scripts.
- `cd app && flutter run` or `flutter test`: work on the target app when it is Flutter.
- `cd dashboard && ...`: run the visual console once implemented.

Keep generated output in `runs/` or `artifacts/`, not in source directories.

## Coding Style & Naming Conventions

- Use ASCII filenames and lowercase directory names.
- Keep directories short and role-based: `core/`, `app/`, `dashboard/`.
- For Python, follow standard formatter conventions (`ruff`/`black` style if added later).
- For Flutter/Dart, use the default Dart formatter and `snake_case.dart` filenames.

## Testing Guidelines

Testing lives with each subproject. Prefer focused tests close to the code they cover.

- Python: add small `test_*.py` checks near the module or under a subproject test folder.
- Flutter: use `flutter test` for widget and unit coverage.

If a change affects orchestration or generated output, verify the files created under `runs/` or `artifacts/`.

## Commit & Pull Request Guidelines

There is no established commit history yet, so keep messages short and imperative, for example: `add repo guidelines` or `create core scaffold`.

Pull requests should include:

- a short summary of what changed,
- the directories touched,
- screenshots for dashboard/UI changes,
- notes on any generated artifacts or manual verification.

## Agent-Specific Instructions

- Do not move temporary data into source folders.
- Do not assume `app/` is permanently Flutter; keep it app-agnostic.
- Update `README.md` and `docs/` when the repository structure changes.
