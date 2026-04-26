"""Lithophane style — grayscale image revealed when backlit."""

from typing import Any

import numpy as np

from img2print.core.blender_ctx import fresh_scene
from img2print.core.exporter import count_stl_triangles, export_glb, export_stl, make_output_paths
from img2print.core.image_io import to_heightmap
from img2print.styles.base import StyleBase, StyleParam, StyleResult

_SUBDIVISIONS = 256


class LithophaneStyle(StyleBase):
    name = "lithophane"
    display_name = "Lithophane"
    description = (
        "Creates a backlit panel where dark areas are thick (blocks light) "
        "and bright areas are thin (passes light). Hold up to a lamp to reveal the image."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("width_mm", "Width (mm)", "float", 100.0, 20.0, 400.0, 1.0),
            StyleParam(
                "max_thickness_mm", "Max Thickness (mm)", "float", 3.0, 1.5, 8.0, 0.1,
                help="Thickness at darkest points — blocks light.",
            ),
            StyleParam(
                "min_thickness_mm", "Min Thickness (mm)", "float", 0.8, 0.4, 3.0, 0.05,
                help="Thickness at brightest points — passes light. Min 0.6mm recommended.",
            ),
            StyleParam(
                "curvature", "Shape", "select", "flat",
                choices=["flat", "curved"],
                help="Flat for picture frames; curved for lamp shades.",
            ),
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
        max_thick_m = float(params.get("max_thickness_mm", 3.0)) / 1000.0
        min_thick_m = float(params.get("min_thickness_mm", 0.8)) / 1000.0
        curvature = str(params.get("curvature", "flat"))
        add_border = bool(params.get("add_border", True))
        smoothing = float(params.get("smoothing", 0.2))

        warnings: list[str] = []
        if min_thick_m < 0.0006:
            warnings.append("Min thickness < 0.6mm — bright areas may be too fragile to print.")
        if max_thick_m <= min_thick_m:
            warnings.append("Max thickness must be greater than min thickness.")
            max_thick_m = min_thick_m + 0.002

        h, w = image.shape[:2]
        aspect = h / w
        height_m = width_m * aspect

        # Lithophane: dark = thick → invert brightness.
        heightmap = to_heightmap(image, invert=True, smoothing=smoothing)
        map_h = int(_SUBDIVISIONS * aspect) or 1
        heightmap = cv2.resize(heightmap, (_SUBDIVISIONS, map_h))

        with fresh_scene():
            plane = _create_lithophane_plane(
                width_m, height_m, _SUBDIVISIONS, map_h,
                heightmap, min_thick_m, max_thick_m,
            )

            if curvature == "curved":
                _apply_bend(plane, width_m)

            # Solidify adds a flat back wall at the minimum thickness.
            solidify = plane.modifiers.new("Solidify", "SOLIDIFY")
            solidify.thickness = min_thick_m
            solidify.offset = -1.0

            bpy.ops.object.modifier_apply(modifier="Solidify")

            if add_border:
                _add_border(width_m, height_m, max_thick_m + min_thick_m)
                bpy.ops.object.select_all(action="SELECT")
                bpy.context.view_layer.objects.active = plane
                bpy.ops.object.join()

            paths = make_output_paths(output_dir, "lithophane", "output")
            stl_path = export_stl(paths["stl"])
            glb_path = export_glb(paths["glb"])

        return StyleResult(
            mesh_path=stl_path,
            preview_path=glb_path,
            stats={
                "triangle_count": count_stl_triangles(stl_path),
                "min_thickness_mm": round(min_thick_m * 1000, 2),
                "max_thickness_mm": round(max_thick_m * 1000, 2),
                "bbox_mm": [
                    round(width_m * 1000, 1),
                    round(height_m * 1000, 1),
                    round((max_thick_m + min_thick_m) * 1000, 1),
                ],
            },
            warnings=warnings,
        )


def _create_lithophane_plane(
    width: float,
    height: float,
    subdiv_x: int,
    subdiv_y: int,
    heightmap: np.ndarray,
    min_thick: float,
    max_thick: float,
) -> Any:
    """Create lithophane surface: each vertex Z = thickness mapped from heightmap."""
    import bpy

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    plane = bpy.context.active_object
    plane.scale = (width, height, 1.0)
    bpy.ops.object.transform_apply(scale=True)

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=subdiv_x - 1)
    bpy.ops.object.mode_set(mode="OBJECT")

    mesh = plane.data
    n = len(mesh.vertices)

    coords = np.empty(n * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(n, 3)

    u = np.clip(coords[:, 0] / width + 0.5, 0.0, 1.0)
    v = np.clip(1.0 - (coords[:, 1] / height + 0.5), 0.0, 1.0)
    px = (u * (heightmap.shape[1] - 1)).astype(np.int32)
    py = (v * (heightmap.shape[0] - 1)).astype(np.int32)

    thick_range = max_thick - min_thick
    coords[:, 2] = min_thick + heightmap[py, px].astype(np.float64) * thick_range

    mesh.vertices.foreach_set("co", coords.ravel())
    mesh.update()

    return plane


def _apply_bend(plane: Any, width: float, radius_factor: float = 2.0) -> None:
    """Gentle cylindrical bend around the Y axis."""
    import bpy

    mod = plane.modifiers.new("Bend", "SIMPLE_DEFORM")
    mod.deform_method = "BEND"
    mod.deform_axis = "Z"
    mod.angle = width / (width * radius_factor)


def _add_border(width: float, height: float, thickness: float) -> None:
    import bpy

    bw = min(width * 0.025, 0.004)

    def make_bar(sx: float, sy: float, lx: float, ly: float) -> None:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        bar = bpy.context.active_object
        bar.scale = (sx, sy, thickness / 2.0)
        bar.location = (lx, ly, thickness / 2.0)
        bpy.ops.object.transform_apply(scale=True, location=True)

    make_bar(width + bw * 2, bw, 0.0, height / 2.0 + bw / 2.0)
    make_bar(width + bw * 2, bw, 0.0, -(height / 2.0 + bw / 2.0))
    make_bar(bw, height, -(width / 2.0 + bw / 2.0), 0.0)
    make_bar(bw, height, width / 2.0 + bw / 2.0, 0.0)
