from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class StyleParam:
    """Declarative parameter description — Gradio renders accordingly."""

    name: str
    label: str
    type: str  # "float" | "int" | "bool" | "select" | "color"
    default: Any
    min: float | None = None
    max: float | None = None
    step: float | None = None
    choices: list[str] = field(default_factory=list)
    help: str = ""


@dataclass
class StyleResult:
    mesh_path: str       # path to output STL/3MF
    preview_path: str    # GLB for browser preview
    stats: dict          # {triangle_count, bbox_mm, est_print_time, ...}
    warnings: list[str]  # non-fatal issues (thin walls, etc.)


class StyleBase(ABC):
    """Every style plugin inherits this."""

    name: str          # "fabric", "line_art", ...
    display_name: str  # shown in dropdown
    description: str   # shown in UI tooltip

    @classmethod
    @abstractmethod
    def params(cls) -> list[StyleParam]:
        """Declares all tunable parameters."""

    @abstractmethod
    def generate(
        self,
        image: np.ndarray,
        params: dict[str, Any],
        output_dir: str,
    ) -> StyleResult:
        """Core logic. Must reset bpy scene at start. Must export STL + GLB."""
