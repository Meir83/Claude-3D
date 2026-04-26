"""Multi-Color Layered style — AD5X-specific multi-filament output.

Phase 3 implementation stub. Outputs aligned STLs or 3MF with color metadata.
"""

from typing import Any

import numpy as np

from img2print.styles.base import StyleBase, StyleParam, StyleResult


class MultiColorStyle(StyleBase):
    name = "multi_color"
    display_name = "Multi-Color Layers (AD5X)"
    description = (
        "Separates image into color zones and exports multiple aligned STLs "
        "or a single 3MF with color assignments. Optimized for FlashForge AD5X."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("num_colors", "Number of Colors", "int", 3, 2, 4, 1),
            StyleParam("color_quantization_algo", "Quantization Algorithm", "select", "kmeans",
                       choices=["kmeans", "median_cut"]),
            StyleParam("layer_thickness_mm", "Layer Thickness (mm)", "float", 0.2, 0.1, 2.0, 0.05),
            StyleParam("palette_override", "Override Palette (hex, comma-separated)", "select", "",
                       choices=["", "#FF0000,#FFFFFF,#0000FF", "#000000,#FFFFFF"]),
        ]

    def generate(
        self,
        image: np.ndarray,
        params: dict[str, Any],
        output_dir: str,
    ) -> StyleResult:
        # TODO Phase 3: k-means quantize → per-color mask → extrude → stack → 3MF export.
        raise NotImplementedError(
            "Multi-Color style is not yet implemented (Phase 3)."
        )
