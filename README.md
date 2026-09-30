# Claude-3D

Describe a part in plain language and get a print-ready, parametric 3D model
(STL + STEP). Claude writes CadQuery code, the code runs in a sandbox, and the
result is rendered and checked before you see it.

There are three ways to use it:

| Mode | Best for | Needs |
|------|----------|-------|
| **MCP server** in Claude Desktop / Claude Code | Day-to-day design. Uses your Claude subscription, no API key | Python 3.10–3.12 |
| **Web app** (FastAPI + Next.js) | Browser UI with a 3D viewer, multiple LLM providers | API key for Claude, Gemini or a local Ollama |
| **Skill only** (`SKILL.md` + `preview.py`) | Claude Code sessions without the server | Python 3.10–3.12 |

## Build → look → fix loop

Both the MCP server and the web app close the loop automatically. You don't
have to paste tracebacks back to the model.

1. The model writes a CadQuery script with all dimensions as parameters.
2. The script is statically checked (only allowed imports, no file or network
   access) and runs in a resource-limited subprocess.
3. **If the build fails**, the error goes straight back to the model for a fix.
   The web app retries up to `AUTO_REPAIR_ATTEMPTS` times (default 2).
4. **If it succeeds**, you get STL + STEP, a 4-view preview image and a
   printability report: real dimensions, watertightness, separate bodies,
   bed contact, overhangs over 45° and build-plate fit.
   Over MCP, Claude sees the image and report and fixes problems before showing
   you the model.

## MCP server setup (Claude Desktop / Claude Code)

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[mcp]"
pip install "PyOpenGL==3.1.7"   # see "Known issues" below
which claude3d-mcp              # copy this absolute path
```

**Claude Code**

```bash
claude mcp add claude-3d -- /absolute/path/to/backend/.venv/bin/claude3d-mcp
```

**Claude Desktop**: in Settings → Developer → Edit Config, add:

```json
{
  "mcpServers": {
    "claude-3d": {
      "command": "/absolute/path/to/backend/.venv/bin/claude3d-mcp",
      "env": { "CLAUDE3D_OUTPUT_DIR": "~/Claude3D/models" }
    }
  }
}
```

Restart Claude, then ask for a part, for example: *"Design a wall mount for a
Raspberry Pi 5 with M2.5 screws, printed in PETG."* The `design_part` prompt
starts a guided session.

Tools the server exposes:

| Tool | What it does |
|------|--------------|
| `get_design_guide` | Returns the CAD guide (`SKILL.md` + `design-review.md`): template, FDM rules, pitfalls |
| `build_model(script, name)` | Sandbox check, build, export STL/STEP, render preview, printability report |
| `inspect_stl(path)` | Preview + report for any existing STL (e.g. from Printables) |

Output files go to `$CLAUDE3D_OUTPUT_DIR` (default `~/Claude3D/models`).

## Web app

```bash
cp .env.example .env              # add at least one provider key
cd backend && pip install -e ".[dev]" && pip install "PyOpenGL==3.1.7"
uvicorn app.main:app --reload     # http://localhost:8000/api/docs
cd ../frontend && npm install && npm run dev   # http://localhost:3000
```

Tests: `cd backend && pytest`.

## Why CadQuery and not Blender?

Blender with an MCP connector, like the official Blender Lab add-on (Blender
5.1+), is the better tool for organic, artistic and rendered work: characters,
scenes, materials, animation. For **functional printed parts** it is the worse
tool. Blender models meshes, so exact dimensions, tolerances, fillets and STEP
export for later CAD edits are all hard. CadQuery is a true B-rep CAD kernel
(OpenCASCADE), so every model is exact, watertight and re-generated from named
parameters ("make it 5 mm taller" is a one-line change).

The two work together: run the Blender connector and this MCP server side by
side in Claude Desktop, and use `inspect_stl` to check meshes from Blender or
from AI mesh generators before you print them.

## Known issues

- **Headless preview on Linux** needs `libosmesa6` (or EGL) **and**
  `PyOpenGL>=3.1.5`. `pyrender` pins `PyOpenGL==3.1.0`, which cannot create a
  headless context, so install `PyOpenGL==3.1.7` after the other requirements.
  Without it, builds still work, but there is no preview image.
- CadQuery has no wheels for Python 3.13+.
