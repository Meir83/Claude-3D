"""
Sandboxed execution of Claude-generated CadQuery scripts.

Security layers:
  1. Static analysis via sandbox.validate_script() (caller's responsibility)
  2. Subprocess with minimal environment
  3. Hard timeout (SIGKILL after N seconds)
  4. Resource limits via setrlimit (Linux only)
  5. Artifact path is pre-determined; script cannot choose output location
"""
from __future__ import annotations

import os
import sys
import time
import asyncio
import subprocess
from pathlib import Path

from app.config import settings
from app.utils.file_manager import job_script_path, job_stl_path, job_step_path, job_log_path


def _set_rlimits() -> None:
    """Called in forked child (Linux only). Sets hard resource limits."""
    try:
        import resource  # noqa: PLC0415

        # Virtual memory
        resource.setrlimit(
            resource.RLIMIT_AS,
            (settings.max_virtual_memory_bytes, settings.max_virtual_memory_bytes),
        )
        # CPU time
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (settings.script_timeout_seconds, settings.script_timeout_seconds),
        )
        # Max file size
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (settings.max_stl_size_bytes, settings.max_stl_size_bytes),
        )
        # No spawning subprocesses
        resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
    except Exception:
        pass  # Non-Linux or missing permissions — best-effort


def _build_script(script: str, job_id: str) -> str:
    """
    Wrap the user script so that all CadQuery export calls use the
    pre-determined artifact paths, regardless of what the script contains.
    We append an override block that re-exports any 'result' variable.
    """
    stl_out = str(job_stl_path(job_id))
    step_out = str(job_step_path(job_id))

    return f"""{script}

# --- Auto-injected export block ---
import cadquery as _cq
import pathlib as _pl

_exported_stl = False
_exported_step = False

# Try to export the last-assigned 'result' variable
try:
    _r = result  # type: ignore[name-defined]
    _cq.exporters.export(_r, {stl_out!r})
    _exported_stl = True
except (NameError, Exception) as _e:
    print(f"STL export failed: {{_e}}", flush=True)

# Optionally export STEP for phase-3 models
try:
    _r = result  # type: ignore[name-defined]
    _cq.exporters.export(_r, {step_out!r}, "STEP")
    _exported_step = True
except (NameError, Exception):
    pass

if _exported_stl:
    print(f"OK: STL exported to {stl_out!r}", flush=True)
if _exported_step:
    print(f"OK: STEP exported to {step_out!r}", flush=True)
"""


class ExecutionResult:
    __slots__ = ("success", "stdout", "stderr", "execution_time_ms", "stl_exists", "step_exists")

    def __init__(
        self,
        success: bool,
        stdout: str,
        stderr: str,
        execution_time_ms: int,
        stl_exists: bool,
        step_exists: bool,
    ) -> None:
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.execution_time_ms = execution_time_ms
        self.stl_exists = stl_exists
        self.step_exists = step_exists


async def execute_script(script: str, job_id: str) -> ExecutionResult:
    """Run a CadQuery script in a sandboxed subprocess (async, non-blocking)."""
    wrapped = _build_script(script, job_id)

    # Write the script to disk for reference/debugging
    script_path = job_script_path(job_id)
    script_path.write_text(wrapped, encoding="utf-8")

    log_path = job_log_path(job_id)

    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONPATH": ":".join(sys.path),
        "HOME": "/tmp",
        "TMPDIR": "/tmp",
        # Pyrender headless on Linux
        "PYOPENGL_PLATFORM": "egl",
    }

    preexec = _set_rlimits if sys.platform == "linux" else None

    t0 = time.monotonic()
    loop = asyncio.get_event_loop()

    def _run_sync() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=settings.script_timeout_seconds,
            env=env,
            preexec_fn=preexec,
        )

    try:
        proc = await loop.run_in_executor(None, _run_sync)
        returncode = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return ExecutionResult(
            success=False,
            stdout="",
            stderr=f"Script timed out after {settings.script_timeout_seconds}s",
            execution_time_ms=elapsed_ms,
            stl_exists=False,
            step_exists=False,
        )

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    # Log stderr for debugging
    if stderr:
        log_path.write_text(stderr, encoding="utf-8")

    stl_path = job_stl_path(job_id)
    step_path = job_step_path(job_id)
    stl_ok = stl_path.exists() and stl_path.stat().st_size > 0
    step_ok = step_path.exists() and step_path.stat().st_size > 0

    success = returncode == 0 and stl_ok

    return ExecutionResult(
        success=success,
        stdout=stdout,
        stderr=stderr,
        execution_time_ms=elapsed_ms,
        stl_exists=stl_ok,
        step_exists=step_ok,
    )
