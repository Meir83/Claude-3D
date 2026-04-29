"""Progress reporting helpers for long-running style operations."""

from typing import Callable


ProgressCallback = Callable[[float, str], None]


def noop_progress(pct: float, msg: str) -> None:
    pass


def make_gradio_progress(gr_progress: object) -> ProgressCallback:
    """Wrap a Gradio progress object into our ProgressCallback type."""

    def _cb(pct: float, msg: str) -> None:
        try:
            gr_progress(pct, desc=msg)  # type: ignore[call-arg]
        except Exception:
            pass

    return _cb
