from pathlib import Path

from app.config import settings
from app.utils.sandbox import safe_job_path


def get_job_dir(job_id: str) -> Path:
    """Return the job artifact directory, creating it if needed."""
    path = safe_job_path(settings.storage_dir, job_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def job_script_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "script.py"


def job_stl_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "output.stl"


def job_preview_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "output_preview.png"


def job_step_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "output.step"


def job_log_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "stderr.log"
