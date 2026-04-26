"""Line Art / Wire Frame style — image edges become 3D printable thick lines.

Phase 2 implementation. This stub contains param declarations and the algorithm
skeleton. Full implementation in Phase 2 sprint.
"""

from typing import Any

import numpy as np

from img2print.core.blender_ctx import fresh_scene
from img2print.core.exporter import export_glb, export_stl, make_output_paths
from img2print.styles.base import StyleBase, StyleParam, StyleResult

_NOT_IMPLEMENTED_MSG = (
    "Line Art style is not yet implemented (Phase 2). "
    "Available styles: fabric, lithophane."
)


class LineArtStyle(StyleBase):
    name = "line_art"
    display_name = "Line Art"
    description = (
        "Converts image edges into connected 3D-printable lines. "
        "Produces hangable decorative art pieces."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("canvas_width_mm", "Canvas Width (mm)", "float", 150.0, 50.0, 500.0, 5.0),
            StyleParam("line_thickness_mm", "Line Thickness (mm)", "float", 2.0, 1.2, 10.0, 0.1,
                       help="Min 1.2mm for reliable printing."),
            StyleParam("depth_mm", "Extrusion Depth (mm)", "float", 3.0, 1.0, 20.0, 0.5),
            StyleParam("edge_algorithm", "Edge Algorithm", "select", "canny",
                       choices=["canny", "sobel", "adaptive"]),
            StyleParam("edge_threshold_low", "Edge Threshold Low", "int", 50, 0, 255, 5),
            StyleParam("edge_threshold_high", "Edge Threshold High", "int", 150, 0, 255, 5),
            StyleParam("simplify_tolerance", "Simplify Tolerance", "float", 1.0, 0.1, 10.0, 0.1),
            StyleParam("ensure_connectivity", "Ensure Connectivity (MST bridges)", "bool", True),
            StyleParam("hanging_hole", "Add Hanging Hole", "bool", True),
            StyleParam("min_feature_size_mm", "Min Feature Size (mm)", "float", 2.0, 0.5, 20.0, 0.5,
                       help="Remove isolated fragments smaller than this."),
        ]

    def generate(
        self,
        image: np.ndarray,
        params: dict[str, Any],
        output_dir: str,
    ) -> StyleResult:
        # TODO Phase 2: implement full edge→skeleton→MST→curve→mesh pipeline.
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG)
