"""Stencil / Cookie Cutter style — silhouette-based cutter shape.

Phase 2 implementation stub.
"""

from typing import Any

import numpy as np

from img2print.styles.base import StyleBase, StyleParam, StyleResult


class StencilStyle(StyleBase):
    name = "stencil"
    display_name = "Stencil / Cookie Cutter"
    description = (
        "Creates a silhouette-based cutter with outer wall and cutting edge. "
        "Great for cookie cutters and spray-paint stencils."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("size_mm", "Size (mm)", "float", 80.0, 20.0, 300.0, 5.0),
            StyleParam("wall_height_mm", "Wall Height (mm)", "float", 20.0, 5.0, 60.0, 1.0),
            StyleParam("wall_thickness_mm", "Wall Thickness (mm)", "float", 2.0, 0.8, 8.0, 0.1),
            StyleParam("cutting_edge_angle", "Cutting Edge Angle (°)", "float", 45.0, 15.0, 75.0, 5.0),
            StyleParam("include_top_handle", "Include Top Handle", "bool", True),
            StyleParam("threshold", "Binarization Threshold", "int", 127, 0, 255, 1),
        ]

    def generate(
        self,
        image: np.ndarray,
        params: dict[str, Any],
        output_dir: str,
    ) -> StyleResult:
        # TODO Phase 2: binarize → contour extraction → extrude with tapered cutting edge.
        raise NotImplementedError("Stencil style is not yet implemented (Phase 2).")
