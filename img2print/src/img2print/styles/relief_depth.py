"""Depth Relief style — AI-estimated depth map drives 3D relief.

Phase 3 implementation stub. Requires optional 'depth' extras:
  uv add "img2print[depth]"

First run downloads ~400MB MiDaS model from Hugging Face.
"""

from typing import Any

import numpy as np

from img2print.styles.base import StyleBase, StyleParam, StyleResult


class ReliefDepthStyle(StyleBase):
    name = "relief_depth"
    display_name = "Depth Relief (AI)"
    description = (
        "Uses AI depth estimation (MiDaS) to create a true 3D relief from a single image. "
        "First run downloads ~400MB model."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("base_depth_mm", "Base Depth (mm)", "float", 2.0, 0.8, 10.0, 0.1),
            StyleParam("max_relief_mm", "Max Relief (mm)", "float", 8.0, 1.0, 30.0, 0.5),
            StyleParam("depth_model", "Depth Model", "select", "dpt_small",
                       choices=["dpt_small", "dpt_large"],
                       help="dpt_small ~400MB, faster. dpt_large ~800MB, more accurate."),
            StyleParam("smoothing", "Smoothing", "float", 0.2, 0.0, 1.0, 0.05),
        ]

    def generate(
        self,
        image: np.ndarray,
        params: dict[str, Any],
        output_dir: str,
    ) -> StyleResult:
        # TODO Phase 3: MiDaS depth estimation → displacement pipeline.
        raise NotImplementedError(
            "Depth Relief style is not yet implemented (Phase 3). "
            "Also requires: uv add 'img2print[depth]'"
        )
