"""
Render a multi-view preview PNG from an STL file.

Calls preview.py as a subprocess so the pyrender/OpenGL context lives in
its own process and cannot corrupt the FastAPI event loop.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from app.utils.file_manager import job_stl_path, job_preview_path

# Path to preview.py (at the repo root)
_PREVIEW_SCRIPT = Path(__file__).resolve().parents[3] / "preview.py"


async def render_preview(job_id: str) -> bool:
    """
    Generate a multi-view preview PNG for the given job's STL.

    Returns True on success, False on failure.
    """
    stl = job_stl_path(job_id)
    preview = job_preview_path(job_id)

    if not stl.exists():
        return False

    cmd = [
        sys.executable,
        str(_PREVIEW_SCRIPT),
        str(stl),
        str(preview),
        "--views", "multi",
        "--resolution", "500",
    ]

    loop = asyncio.get_event_loop()

    def _run() -> int:
        import subprocess  # noqa: PLC0415
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "PYTHONPATH": ":".join(sys.path),
                "HOME": "/tmp",
                "PYOPENGL_PLATFORM": "osmesa",  # CPU fallback for CI/headless
            },
        )
        return result.returncode

    try:
        returncode = await loop.run_in_executor(None, _run)
        return returncode == 0 and preview.exists()
    except Exception:
        return False
