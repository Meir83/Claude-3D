from datetime import datetime
from pydantic import BaseModel


class JobOut(BaseModel):
    id: str
    session_id: str
    status: str
    phase: int | None
    error_message: str | None
    execution_time_ms: int | None
    has_stl: bool
    has_preview: bool
    has_step: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, job: object) -> "JobOut":  # type: ignore[override]
        return cls(
            id=job.id,  # type: ignore[attr-defined]
            session_id=job.session_id,  # type: ignore[attr-defined]
            status=job.status,  # type: ignore[attr-defined]
            phase=job.phase,  # type: ignore[attr-defined]
            error_message=job.error_message,  # type: ignore[attr-defined]
            execution_time_ms=job.execution_time_ms,  # type: ignore[attr-defined]
            has_stl=bool(job.stl_path),  # type: ignore[attr-defined]
            has_preview=bool(job.preview_path),  # type: ignore[attr-defined]
            has_step=bool(job.step_path),  # type: ignore[attr-defined]
            created_at=job.created_at,  # type: ignore[attr-defined]
            started_at=job.started_at,  # type: ignore[attr-defined]
            finished_at=job.finished_at,  # type: ignore[attr-defined]
        )


class JobListOut(BaseModel):
    items: list[JobOut]
    total: int
    limit: int
    offset: int
