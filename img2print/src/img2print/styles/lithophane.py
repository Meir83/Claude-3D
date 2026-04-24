"""Lithophane style — grayscale image revealed when backlit."""

from typing import Any

import numpy as np

from img2print.core.blender_ctx import fresh_scene
from img2print.core.exporter import export_glb, export_stl, make_output_paths
from img2print.core.image_io import to_heightmap
from img2print.styles.base import StyleBase, StyleParam, StyleResult

# Minimum thickness must block light (dark zones must be thick).
_MIN_THICKNESS_DEFAULT = 0.8
_MAX_THICKNESS_DEFAULT = 3.0


class LithophaneStyle(StyleBase):
    name = "lithophane"
    display_name = "Lithophane"
    description = (
        "Creates a grayscale image that reveals detail when held up to light. "
        "Dark areas are thick (blocks light), bright areas are thin (passes light)."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("width_mm", "Width (mm)", "float", 100.0, 20.0, 400.0, 1.0),
            StyleParam("max_thickness_mm", "Max Thickness (mm)", "float", _MAX_THICKNESS_DEFAULT, 1.5, 8.0, 0.1,
                       help="Thickness at darkest points (blocks light)."),
            StyleParam("min_thickness_mm", "Min Thickness (mm)", "float", _MIN_THICKNESS_DEFAULT, 0.4, 3.0, 0.05,
                       help="Thickness at brightest points (passes light). Min 0.6mm recommended."),
            StyleParam("curvature", "Shape", "select", "flat",
                       choices=["flat", "curved", "cylindrical"],
                       help="Flat for frames; curved/cylindrical for lamp shades."),
            StyleParam("add_border", "Add Border", "bool", True),
            StyleParam("smoothing", "Smoothing", "float", 0.2, 0.0, 1.0, 0.05),
        ]

    def generate(
        self,
        image: np.ndarray,
        params: dict[str, Any],
        output_dir: str,
    ) -> StyleResult:
        import bpy
        import cv2

        width_m = float(params.get("width_mm", 100.0)) / 1000.0
        max_thick = float(params.get("max_thickness_mm", _MAX_THICKNESS_DEFAULT)) / 1000.0
        min_thick = float(params.get("min_thickness_mm", _MIN_THICKNESS_DEFAULT)) / 1000.0
        curvature = str(params.get("curvature", "flat"))
        add_border = bool(params.get("add_border", True))
        smoothing = float(params.get("smoothing", 0.2))

        warnings: list[str] = []
        if min_thick < 0.0006:
            warnings.append("Min thickness < 0.6mm — bright areas may be too fragile to print.")

        h, w = image.shape[:2]
        aspect = h / w
        height_m = width_m * aspect

        # Lithophane: dark = thick, light = thin → invert brightness.
        heightmap = to_heightmap(image, invert=True, smoothing=smoothing)
        subdiv = 256
        heightmap = cv2.resize(heightmap, (subdiv, int(subdiv * aspect)))

        with fresh_scene():
            bpy.ops.mesh.primitive_plane_add(size=1.0)
            plane = bpy.context.active_object
            plane.scale = (width_m, height_m, 1.0)
            bpy.ops.object.transform_apply(scale=True)

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.subdivide(number_cuts=subdiv - 1)
            bpy.ops.object.mode_set(mode="OBJECT")

            mesh = plane.data
            thick_range = max_thick - min_thick
            for v in mesh.vertices:
                u = (v.co.x / width_m + 0.5)
                t = (v.co.y / height_m + 0.5)
                px = int(np.clip(u, 0.0, 1.0) * (heightmap.shape[1] - 1))
                py = int(np.clip(1.0 - t, 0.0, 1.0) * (heightmap.shape[0] - 1))
                v.co.z = min_thick + float(heightmap[py, px]) * thick_range

            if curvature == "curved":
                _apply_curvature(plane, width_m)

            solidify = plane.modifiers.new("Solidify", "SOLIDIFY")
            solidify.thickness = min_thick
            solidify.offset = 0.0

            bpy.ops.object.modifier_apply(modifier="Solidify")

            paths = make_output_paths(output_dir, "lithophane", "output")
            stl_path = export_stl(paths["stl"])
            glb_path = export_glb(paths["glb"])

        return StyleResult(
            mesh_path=stl_path,
            preview_path=glb_path,
            stats={"min_thickness_mm": min_thick * 1000, "max_thickness_mm": max_thick * 1000},
            warnings=warnings,
        )


def _apply_curvature(obj: Any, width: float, radius_factor: float = 1.5) -> None:
    """Bend the panel into a gentle arc using a simple curve modifier."""
    import bpy

    radius = width * radius_factor
    curve = obj.modifiers.new("Curve", "SIMPLE_DEFORM")
    curve.deform_method = "BEND"
    curve.angle = width / radius
