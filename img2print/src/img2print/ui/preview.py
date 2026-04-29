"""3D preview helpers — returns GLB path for Gradio Model3D component."""

import os
from pathlib import Path


def get_preview_path(result_glb: str | None) -> str | None:
    """Validate preview GLB path before handing to Gradio Model3D."""
    if result_glb is None:
        return None
    if not os.path.exists(result_glb):
        return None
    if Path(result_glb).stat().st_size == 0:
        return None
    return result_glb
