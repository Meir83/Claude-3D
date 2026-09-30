"""
MCP server: lets Claude Desktop / Claude Code build CadQuery models directly.

This is the same idea as the Blender MCP connector — the assistant drives the
CAD tool and looks at a rendered image of its own result — but for precise,
parametric, print-ready parts instead of free-form mesh modelling.

Every build goes through the same pipeline as the web app:
    static sandbox check → isolated subprocess → STL/STEP export
    → 4-view preview render → printability report

Run (stdio transport, which is what Claude Desktop / Claude Code expect):
    cd backend && python -m app.mcp_server

Finished files are copied to $CLAUDE3D_OUTPUT_DIR (default ~/Claude3D/models).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

from mcp.server.mcpserver import Image, MCPServer

from app.config import settings
from app.services.executor import execute_script
from app.services.mesh_report import mesh_report
from app.services.renderer import render_preview
from app.utils.file_manager import job_preview_path, job_step_path, job_stl_path
from app.utils.sandbox import SandboxViolation, validate_script

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PREVIEW_SCRIPT = _REPO_ROOT / "preview.py"

OUTPUT_DIR = Path(
    os.environ.get("CLAUDE3D_OUTPUT_DIR", Path.home() / "Claude3D" / "models")
).expanduser()

_INSTRUCTIONS = """\
Claude-3D builds parametric, 3D-printable parts with CadQuery (Python, units in mm).

Workflow:
1. Call get_design_guide once per conversation before designing — it holds the
   script template, FDM rules and the review checklist.
2. Write a complete CadQuery script that assigns the final solid to `result`
   (bottom of the part at Z=0) and call build_model with it.
3. Look at the returned preview image AND the printability report. Fix anything
   wrong (errors, warnings, wrong dimensions) and build again before showing the
   user. Build in phases: base shape → features → fillets/finish.
4. Tell the user where the STL/STEP files were saved.
"""

mcp = MCPServer("claude-3d", instructions=_INSTRUCTIONS)


def _slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-").lower()
    return slug[:60] or "model"


def _read_guide() -> str:
    parts = [(_REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")]
    review = _REPO_ROOT / "design-review.md"
    if review.exists():
        parts.append(review.read_text(encoding="utf-8"))
    guide = "\n\n---\n\n".join(parts)
    # The web app renders previews itself; tell the MCP client to use the tool instead.
    return guide.replace(
        "python3 preview.py model.stl preview.png --views multi",
        "build_model(script=..., name=...)  # returns preview image + printability report",
    )


def _format_report(name: str, files: dict[str, str], report: dict, elapsed_ms: int) -> str:
    lines = [f"Built '{name}' in {elapsed_ms} ms.", "", "Files:"]
    lines += [f"  {kind}: {path}" for kind, path in files.items()]
    lines += ["", "Printability report:", json.dumps(report, indent=2)]
    if report.get("warnings"):
        lines += ["", "Fix or consciously accept every warning before delivering."]
    return "\n".join(lines)


@mcp.tool()
def get_design_guide() -> str:
    """Return the Claude-3D CAD design guide: script template, FDM printing rules,
    CadQuery patterns/pitfalls and the self-review checklist. Read it before the
    first build_model call."""
    return _read_guide()


@mcp.tool()
async def build_model(script: str, name: str = "model") -> list:
    """Execute a CadQuery script and return a 4-view preview image plus a
    printability report (real dimensions, watertightness, overhangs, bed contact).

    The script must `import cadquery as cq` and assign the final solid to a
    variable named `result`. Export calls are optional — STL and STEP are
    written automatically. Allowed imports: cadquery, math, numpy, typing,
    dataclasses, pathlib. File I/O, subprocesses and network access are blocked.

    Args:
        script: Complete CadQuery Python script.
        name: Short file name for the outputs, e.g. "phone-stand-v2".
    """
    try:
        validate_script(script, max_bytes=settings.max_script_size_bytes)
    except SandboxViolation as exc:
        return [f"BUILD REJECTED by sandbox: {exc}\nFix the script and call build_model again."]

    job_id = str(uuid.uuid4())
    result = await execute_script(script, job_id)
    if not result.success:
        error = (result.stderr or result.stdout or "no output").strip()
        return [
            "BUILD FAILED. Error output (last 3000 chars):\n\n"
            f"{error[-3000:]}\n\n"
            "Find the root cause, fix the script and call build_model again. If a "
            "fillet/shell/loft failed, simplify that operation instead of guessing."
        ]

    slug = _slug(name)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    stl_out = OUTPUT_DIR / f"{slug}.stl"
    shutil.copyfile(job_stl_path(job_id), stl_out)
    files["STL"] = str(stl_out)
    if result.step_exists:
        step_out = OUTPUT_DIR / f"{slug}.step"
        shutil.copyfile(job_step_path(job_id), step_out)
        files["STEP"] = str(step_out)

    report = await asyncio.to_thread(mesh_report, stl_out)
    content: list = []

    if await render_preview(job_id):
        preview_out = OUTPUT_DIR / f"{slug}_preview.png"
        shutil.copyfile(job_preview_path(job_id), preview_out)
        files["Preview"] = str(preview_out)
        content.append(Image(path=preview_out))
    else:
        report.setdefault("warnings", []).append(
            "Preview rendering failed (no OpenGL backend?) — rely on the numbers above."
        )

    content.insert(0, _format_report(name, files, report, result.execution_time_ms))
    return content


@mcp.tool()
async def inspect_stl(path: str) -> list:
    """Render a 4-view preview and printability report for an existing STL file
    (e.g. one downloaded from Printables/Thingiverse or produced elsewhere).

    Args:
        path: Absolute path to an .stl file.
    """
    stl = Path(path).expanduser().resolve()
    if stl.suffix.lower() != ".stl" or not stl.is_file():
        return [f"Not an STL file: {stl}"]

    report = await asyncio.to_thread(mesh_report, stl)
    content: list = [json.dumps(report, indent=2)]

    preview = OUTPUT_DIR / f"{_slug(stl.stem)}_inspect.png"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if sys.platform == "linux":
        env.setdefault("PYOPENGL_PLATFORM", "osmesa")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(_PREVIEW_SCRIPT), str(stl), str(preview),
        "--views", "multi", "--resolution", "500",
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, env=env,
    )
    try:
        await asyncio.wait_for(proc.wait(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
    if preview.exists():
        content.append(Image(path=preview))
    return content


@mcp.prompt()
def design_part(description: str) -> str:
    """Start a guided design session for a 3D-printable part."""
    return (
        f"I want to design a 3D-printable part: {description}\n\n"
        "Call get_design_guide first and follow its workflow: ask me only the "
        "questions that matter (critical dimensions, mounting, printer/material), "
        "research real-world dimensions if the part fits an existing product, then "
        "build it in phases with build_model, checking every preview and report."
    )


def main() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    mcp.run("stdio")


if __name__ == "__main__":
    main()
