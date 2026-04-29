"""Stencil / Cookie Cutter style — silhouette-based hollow wall.

Algorithm:
  1. Binarize image (threshold or Otsu)
  2. Find largest outer contour (the subject silhouette)
  3. Erode mask by wall_thickness to get inner contour
  4. Blender: 2D curve with outer spline + inner spline (hole) → hollow wall
  5. Extrude to wall_height
  6. Optional top handle
  7. Export STL + GLB
"""

from typing import Any

import cv2
import numpy as np

from img2print.core.blender_ctx import fresh_scene
from img2print.core.exporter import count_stl_triangles, export_glb, export_stl, make_output_paths
from img2print.styles.base import StyleBase, StyleParam, StyleResult

_CANVAS_PX = 512


class StencilStyle(StyleBase):
    name = "stencil"
    display_name = "Stencil / Cookie Cutter"
    description = (
        "Creates a silhouette-based cookie cutter with a hollow wall. "
        "Great for baking cutters, craft stencils, and spray-paint masks."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("size_mm", "Size (mm)", "float", 80.0, 20.0, 300.0, 5.0),
            StyleParam("wall_height_mm", "Wall Height (mm)", "float", 20.0, 5.0, 60.0, 1.0),
            StyleParam("wall_thickness_mm", "Wall Thickness (mm)", "float", 2.0, 0.8, 8.0, 0.1),
            StyleParam(
                "threshold", "Binarization Threshold", "int", 127, 0, 255, 1,
                help="0 = auto (Otsu). Increase to include lighter subject areas.",
            ),
            StyleParam(
                "simplify_tolerance", "Simplify Tolerance (px)", "float", 2.0, 0.1, 20.0, 0.5,
                help="Higher = smoother, fewer vertices.",
            ),
            StyleParam("include_top_handle", "Add Top Handle", "bool", True),
        ]

    def generate(
        self,
        image: np.ndarray,
        params: dict[str, Any],
        output_dir: str,
    ) -> StyleResult:
        size_mm = float(params.get("size_mm", 80.0))
        wall_h_mm = float(params.get("wall_height_mm", 20.0))
        wall_t_mm = float(params.get("wall_thickness_mm", 2.0))
        threshold = int(params.get("threshold", 127))
        simplify_tol = float(params.get("simplify_tolerance", 2.0))
        add_handle = bool(params.get("include_top_handle", True))

        warnings: list[str] = []

        h, w = image.shape[:2]
        aspect = h / w
        canvas_h_px = int(_CANVAS_PX * aspect)
        img_rs = cv2.resize(image, (_CANVAS_PX, canvas_h_px), interpolation=cv2.INTER_AREA)

        px_per_mm = _CANVAS_PX / size_mm
        wall_t_px = max(1, int(wall_t_mm * px_per_mm))

        gray = cv2.cvtColor(img_rs, cv2.COLOR_RGB2GRAY)
        binary = _binarize(gray, threshold)

        outer_pts_px, inner_pts_px = _extract_contours(binary, wall_t_px, simplify_tol, warnings)

        if outer_pts_px is None or len(outer_pts_px) < 3:
            raise ValueError(
                "Could not extract a silhouette. Adjust threshold or try a higher-contrast image."
            )

        canvas_w_m = size_mm / 1000.0
        canvas_h_m = canvas_w_m * aspect
        wall_h_m = wall_h_mm / 1000.0
        wall_t_m = wall_t_mm / 1000.0

        def to_blender(pts_px: np.ndarray) -> np.ndarray:
            bx = (pts_px[:, 0] / _CANVAS_PX) * canvas_w_m - canvas_w_m / 2.0
            by = ((canvas_h_px - pts_px[:, 1]) / canvas_h_px) * canvas_h_m - canvas_h_m / 2.0
            return np.column_stack([bx, by])

        outer_m = to_blender(outer_pts_px)
        inner_m = to_blender(inner_pts_px) if inner_pts_px is not None else None

        with fresh_scene():
            cutter_obj = _build_cutter(outer_m, inner_m, wall_h_m)

            if add_handle:
                _add_handle(canvas_h_m, wall_h_m, wall_t_m, cutter_obj)

            paths = make_output_paths(output_dir, "stencil", "output")
            stl_path = export_stl(paths["stl"])
            glb_path = export_glb(paths["glb"])

        return StyleResult(
            mesh_path=stl_path,
            preview_path=glb_path,
            stats={
                "triangle_count": count_stl_triangles(stl_path),
                "size_mm": size_mm,
                "wall_height_mm": wall_h_mm,
                "wall_thickness_mm": wall_t_mm,
            },
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------

def _binarize(gray: np.ndarray, threshold: int) -> np.ndarray:
    if threshold == 0:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    # Clean up noise
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    return binary


def _extract_contours(
    binary: np.ndarray,
    wall_t_px: int,
    simplify_tol: float,
    warnings: list[str],
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Return (outer_pts, inner_pts) in pixel coords."""
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    # Largest contour = main subject.
    outer_raw = max(contours, key=cv2.contourArea)
    outer_approx = cv2.approxPolyDP(outer_raw, simplify_tol, closed=True)
    outer_pts = outer_approx.reshape(-1, 2).astype(np.float64)

    # Inner contour by eroding the binary mask.
    kern_sz = wall_t_px * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kern_sz, kern_sz))
    inner_mask = cv2.erode(binary, kernel, iterations=1)
    inner_cnts, _ = cv2.findContours(inner_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not inner_cnts:
        warnings.append(
            "Shape too small for the requested wall thickness — cutter will be solid (no inner hole)."
        )
        return outer_pts, None

    inner_raw = max(inner_cnts, key=cv2.contourArea)
    inner_approx = cv2.approxPolyDP(inner_raw, simplify_tol, closed=True)
    inner_pts = inner_approx.reshape(-1, 2).astype(np.float64)

    return outer_pts, inner_pts


# ---------------------------------------------------------------------------
# Blender builders
# ---------------------------------------------------------------------------

def _build_cutter(
    outer_m: np.ndarray,
    inner_m: np.ndarray | None,
    wall_h_m: float,
) -> Any:
    """Create a hollow extruded 2D curve for the cookie cutter wall."""
    import bpy

    cd = bpy.data.curves.new("stencil", "CURVE")
    cd.dimensions = "2D"
    cd.fill_mode = "BOTH"
    cd.extrude = wall_h_m / 2.0  # symmetric extrusion → total height = wall_h_m

    # Outer spline (CCW for correct face normal).
    _add_spline(cd, outer_m, reverse=False)

    # Inner spline reversed → creates a hole in the fill.
    if inner_m is not None and len(inner_m) >= 3:
        _add_spline(cd, inner_m, reverse=True)

    obj = bpy.data.objects.new("stencil", cd)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.active_object


def _add_spline(cd: Any, pts: np.ndarray, reverse: bool) -> None:
    sp = cd.splines.new("POLY")
    sp.use_cyclic_u = True
    ordered = pts[::-1] if reverse else pts
    sp.points.add(len(ordered) - 1)
    for i, (x, y) in enumerate(ordered):
        sp.points[i].co = (float(x), float(y), 0.0, 1.0)


def _add_handle(
    canvas_h_m: float,
    wall_h_m: float,
    wall_t_m: float,
    cutter_obj: Any,
) -> None:
    """Add a small rectangular grip at the top centre."""
    import bpy

    handle_w = wall_t_m * 3.0   # 3× wall thickness
    handle_h = wall_h_m * 0.4   # 40% of wall height
    handle_d = wall_t_m * 1.5

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    handle = bpy.context.active_object
    handle.scale = (handle_w, handle_d, handle_h)
    handle.location = (0.0, canvas_h_m / 2.0 + handle_d / 2.0, 0.0)
    bpy.ops.object.transform_apply(scale=True, location=True)

    # Join handle to cutter.
    bpy.ops.object.select_all(action="DESELECT")
    cutter_obj.select_set(True)
    handle.select_set(True)
    bpy.context.view_layer.objects.active = cutter_obj
    bpy.ops.object.join()
