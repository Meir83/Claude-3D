"""Fabric / Flag style — depth-mapped displacement on a flat panel."""

from typing import Any

import numpy as np

from img2print.core.blender_ctx import fresh_scene
from img2print.core.exporter import export_glb, export_stl, make_output_paths
from img2print.core.image_io import to_heightmap
from img2print.styles.base import StyleBase, StyleParam, StyleResult

_MAX_SUBDIVISIONS = 1024


class FabricStyle(StyleBase):
    name = "fabric"
    display_name = "Fabric / Flag"
    description = (
        "Converts image to a flat panel with color zones rendered as depth differences. "
        "Great for flags, logos, and decorative relief plaques."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("panel_width_mm", "Panel Width (mm)", "float", 100.0, 20.0, 500.0, 1.0),
            StyleParam("panel_thickness_mm", "Base Thickness (mm)", "float", 2.0, 0.8, 10.0, 0.1),
            StyleParam("relief_depth_mm", "Relief Depth (mm)", "float", 0.6, 0.1, 5.0, 0.05),
            StyleParam("subdivision_level", "Subdivision Level", "int", 256, 32, _MAX_SUBDIVISIONS, 32),
            StyleParam("invert", "Invert (dark=high)", "bool", False),
            StyleParam("smoothing", "Smoothing", "float", 0.3, 0.0, 1.0, 0.05),
            StyleParam("add_border", "Add Border Frame", "bool", True),
        ]

    def generate(
        self,
        image: np.ndarray,
        params: dict[str, Any],
        output_dir: str,
    ) -> StyleResult:
        import bpy
        import cv2

        p_width = float(params.get("panel_width_mm", 100.0)) / 1000.0
        p_thick = float(params.get("panel_thickness_mm", 2.0)) / 1000.0
        p_relief = float(params.get("relief_depth_mm", 0.6)) / 1000.0
        subdiv = min(int(params.get("subdivision_level", 256)), _MAX_SUBDIVISIONS)
        invert = bool(params.get("invert", False))
        smoothing = float(params.get("smoothing", 0.3))
        add_border = bool(params.get("add_border", True))

        h, w = image.shape[:2]
        aspect = h / w
        p_height = p_width * aspect

        heightmap = to_heightmap(image, invert=invert, smoothing=smoothing)
        heightmap_resized = cv2.resize(heightmap, (subdiv, int(subdiv * aspect)))

        with fresh_scene():
            # Create subdivided plane.
            bpy.ops.mesh.primitive_plane_add(size=1.0)
            plane = bpy.context.active_object
            plane.scale = (p_width, p_height, 1.0)
            bpy.ops.object.transform_apply(scale=True)

            # Subdivide.
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.subdivide(number_cuts=subdiv - 1)
            bpy.ops.object.mode_set(mode="OBJECT")

            # Apply displacement via vertex Z.
            mesh = plane.data
            verts = mesh.vertices
            for v in verts:
                u = (v.co.x / p_width + 0.5)
                t = (v.co.y / p_height + 0.5)
                px = int(np.clip(u, 0.0, 1.0) * (heightmap_resized.shape[1] - 1))
                py = int(np.clip(1.0 - t, 0.0, 1.0) * (heightmap_resized.shape[0] - 1))
                v.co.z = float(heightmap_resized[py, px]) * p_relief

            # Solidify: add base thickness.
            solidify = plane.modifiers.new("Solidify", "SOLIDIFY")
            solidify.thickness = p_thick
            solidify.offset = 1.0

            if add_border:
                _add_border(p_width, p_height, p_thick + p_relief)

            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.join()
            bpy.ops.object.modifier_apply(modifier="Solidify")

            paths = make_output_paths(output_dir, "fabric", "output")
            stl_path = export_stl(paths["stl"])
            glb_path = export_glb(paths["glb"])

        return StyleResult(
            mesh_path=stl_path,
            preview_path=glb_path,
            stats={"subdivision": subdiv, "aspect": round(aspect, 3)},
            warnings=[],
        )


def _add_border(width: float, height: float, total_thick: float) -> None:
    """Add a thin raised rectangular frame around the panel."""
    import bpy

    border_w = width * 0.02
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    frame = bpy.context.active_object

    # Top bar.
    frame.scale = (width + border_w * 2, border_w, total_thick * 0.5)
    frame.location = (0.0, height / 2 + border_w / 2, total_thick * 0.5)
    bpy.ops.object.duplicate()
    dup = bpy.context.active_object
    dup.location.y = -(height / 2 + border_w / 2)
