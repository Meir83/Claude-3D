"""Fabric / Flag style — depth-mapped displacement on a flat panel."""

from typing import Any

import numpy as np

from img2print.core.blender_ctx import fresh_scene
from img2print.core.exporter import count_stl_triangles, export_glb, export_stl, make_output_paths
from img2print.core.image_io import to_heightmap
from img2print.styles.base import StyleBase, StyleParam, StyleResult

_MAX_SUBDIVISIONS = 512


class FabricStyle(StyleBase):
    name = "fabric"
    display_name = "Fabric / Flag"
    description = (
        "Converts image to a flat panel with brightness zones rendered as depth differences. "
        "Great for flags, logos, and decorative relief plaques."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("panel_width_mm", "Panel Width (mm)", "float", 100.0, 20.0, 500.0, 1.0),
            StyleParam("panel_thickness_mm", "Base Thickness (mm)", "float", 2.0, 0.8, 10.0, 0.1),
            StyleParam("relief_depth_mm", "Relief Depth (mm)", "float", 0.6, 0.1, 5.0, 0.05),
            StyleParam(
                "subdivision_level", "Subdivision Level", "int", 128, 32, _MAX_SUBDIVISIONS, 32,
                help="Higher = more detail but slower. 128 is a good balance.",
            ),
            StyleParam("invert", "Invert (dark = high)", "bool", False),
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

        p_width_m = float(params.get("panel_width_mm", 100.0)) / 1000.0
        p_thick_m = float(params.get("panel_thickness_mm", 2.0)) / 1000.0
        p_relief_m = float(params.get("relief_depth_mm", 0.6)) / 1000.0
        subdiv = min(int(params.get("subdivision_level", 128)), _MAX_SUBDIVISIONS)
        invert = bool(params.get("invert", False))
        smoothing = float(params.get("smoothing", 0.3))
        add_border = bool(params.get("add_border", True))

        h, w = image.shape[:2]
        aspect = h / w
        p_height_m = p_width_m * aspect

        heightmap = to_heightmap(image, invert=invert, smoothing=smoothing)
        map_h = int(subdiv * aspect) or 1
        heightmap_resized = cv2.resize(heightmap, (subdiv, map_h))

        warnings: list[str] = []
        if subdiv > 256:
            warnings.append(f"High subdivision ({subdiv}) may produce a large file and slow slicing.")

        with fresh_scene():
            plane = _create_displaced_plane(
                p_width_m, p_height_m, subdiv, map_h,
                heightmap_resized, p_relief_m,
            )

            solidify = plane.modifiers.new("Solidify", "SOLIDIFY")
            solidify.thickness = p_thick_m
            solidify.offset = -1.0  # grow downward so top surface is displacement

            bpy.ops.object.modifier_apply(modifier="Solidify")

            if add_border:
                _add_border_frame(p_width_m, p_height_m, p_thick_m)
                bpy.ops.object.select_all(action="SELECT")
                bpy.context.view_layer.objects.active = plane
                bpy.ops.object.join()

            paths = make_output_paths(output_dir, "fabric", "output")
            stl_path = export_stl(paths["stl"])
            glb_path = export_glb(paths["glb"])

        tri_count = count_stl_triangles(stl_path)
        return StyleResult(
            mesh_path=stl_path,
            preview_path=glb_path,
            stats={
                "triangle_count": tri_count,
                "bbox_mm": [
                    round(p_width_m * 1000, 1),
                    round(p_height_m * 1000, 1),
                    round((p_thick_m + p_relief_m) * 1000, 1),
                ],
                "subdivision": subdiv,
            },
            warnings=warnings,
        )


def _create_displaced_plane(
    width: float, height: float,
    subdiv_x: int, subdiv_y: int,
    heightmap: np.ndarray,
    relief: float,
) -> Any:
    """Create a plane and displace Z via numpy forEach operations."""
    import bpy

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    plane = bpy.context.active_object
    plane.scale = (width, height, 1.0)
    bpy.ops.object.transform_apply(scale=True)

    # Subdivide to target resolution.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=subdiv_x - 1)
    bpy.ops.object.mode_set(mode="OBJECT")

    mesh = plane.data
    n = len(mesh.vertices)

    # Read all vertex coordinates in one fast batch call.
    coords = np.empty(n * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(n, 3)

    # Map vertex XY → UV → heightmap pixel.
    u = np.clip(coords[:, 0] / width + 0.5, 0.0, 1.0)
    v = np.clip(1.0 - (coords[:, 1] / height + 0.5), 0.0, 1.0)
    px = (u * (heightmap.shape[1] - 1)).astype(np.int32)
    py = (v * (heightmap.shape[0] - 1)).astype(np.int32)

    coords[:, 2] = heightmap[py, px].astype(np.float64) * relief

    # Write back in one fast batch call.
    mesh.vertices.foreach_set("co", coords.ravel())
    mesh.update()

    return plane


def _add_border_frame(width: float, height: float, thickness: float) -> None:
    """Add a 4-bar rectangular frame around the panel."""
    import bpy

    bw = min(width * 0.025, 0.004)  # 2.5% of width, max 4mm

    def make_bar(sx: float, sy: float, lx: float, ly: float) -> None:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        bar = bpy.context.active_object
        bar.scale = (sx, sy, thickness / 2.0)
        bar.location = (lx, ly, thickness / 2.0)
        bpy.ops.object.transform_apply(scale=True, location=True)

    # Top & bottom horizontal bars.
    make_bar(width + bw * 2, bw, 0.0, height / 2.0 + bw / 2.0)
    make_bar(width + bw * 2, bw, 0.0, -(height / 2.0 + bw / 2.0))
    # Left & right vertical bars.
    make_bar(bw, height, -(width / 2.0 + bw / 2.0), 0.0)
    make_bar(bw, height, width / 2.0 + bw / 2.0, 0.0)


