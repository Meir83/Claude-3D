# img2print — Instructions for Claude Code

## Conventions
- Python 3.11+. Use `uv` for all package operations (`uv add`, `uv run`, `uv sync`).
- All user-facing text in English. Internal logs in English.
- After every code change: run tests, then commit with message format:
  `<type>(<scope>): <what> — <why> — <impact>`
  Example: `feat(fabric): add border option — user request — enables picture-frame outputs`
- Never use `os.system`. Use `subprocess` with explicit args.
- Never write secrets, API keys, or local paths to committed files.
- Type-hint everything. Ruff + mypy must pass (`uv run ruff check src/ tests/` and `uv run mypy src/`).

## Architecture rules
- Styles MUST NOT import other styles.
- Styles MUST NOT touch Gradio code.
- Core MUST NOT know about specific styles — only the registry.
- Blender scene MUST be reset at the start of every `generate()` call via `fresh_scene()`.
- All params use millimeters as units. Blender uses meters internally; scale at export.
- Gradio `concurrency_count=1` for Blender operations — bpy is NOT thread-safe.

## Testing
- Every new style needs a minimal unit test with a fixture image, asserting:
  (a) STL file exists, (b) is manifold, (c) triangle count in expected range.
- Don't snapshot full mesh bytes — snapshot hash + triangle count + bbox.
- Run tests: `uv run pytest`

## When adding a new style
1. Create `src/img2print/styles/<name>.py` inheriting `StyleBase`.
2. Declare params via `StyleParam` list in `cls.params()`.
3. Implement `generate()` — MUST call `fresh_scene()` first.
4. Add fixture image to `tests/fixtures/` if not already present.
5. Add `tests/test_<name>.py`.
6. Update README gallery section.

## Debugging Blender
- `bpy.ops.wm.save_as_mainfile(filepath="/tmp/debug.blend")` to inspect state.
- If `bpy` import fails: check `pip show bpy` — must be 4.x.
- Blender units: always work in meters internally, convert mm→m by dividing by 1000.

## Key file map
- `src/img2print/app.py` — Gradio entry point, `main()` function
- `src/img2print/core/pipeline.py` — main orchestrator `run()`
- `src/img2print/core/registry.py` — plugin discovery, `list_styles()`, `get(name)`
- `src/img2print/core/blender_ctx.py` — `fresh_scene()` context manager
- `src/img2print/styles/base.py` — `StyleBase`, `StyleParam`, `StyleResult`
