"""Line Art style — image edges become 3D-printable flat filled shapes.

Algorithm:
  1. Edge detection (Canny / Sobel / adaptive)
  2. Dilate to target line_thickness
  3. Connected-component analysis; filter tiny fragments
  4. MST bridges between isolated regions (optional)
  5. Find contours of dilated edge regions
  6. Simplify contours (Douglas-Peucker)
  7. Blender: one 2D filled+extruded curve per contour → solid
  8. Boolean-drill hanging hole (optional)
  9. Export STL + GLB
"""

from typing import Any

import cv2
import networkx as nx
import numpy as np

from img2print.core.blender_ctx import fresh_scene
from img2print.core.exporter import count_stl_triangles, export_glb, export_stl, make_output_paths
from img2print.styles.base import StyleBase, StyleParam, StyleResult

_CANVAS_PX = 512  # internal raster resolution (width)


class LineArtStyle(StyleBase):
    name = "line_art"
    display_name = "Line Art"
    description = (
        "Converts image edges into connected flat filled shapes that can be hung as wall art. "
        "Isolated pieces are automatically bridged."
    )

    @classmethod
    def params(cls) -> list[StyleParam]:
        return [
            StyleParam("canvas_width_mm", "Canvas Width (mm)", "float", 150.0, 50.0, 500.0, 5.0),
            StyleParam(
                "line_thickness_mm", "Line Thickness (mm)", "float", 2.0, 1.2, 10.0, 0.1,
                help="Min 1.2mm for reliable printing.",
            ),
            StyleParam("depth_mm", "Depth (mm)", "float", 3.0, 1.0, 20.0, 0.5),
            StyleParam(
                "edge_algorithm", "Edge Algorithm", "select", "canny",
                choices=["canny", "sobel", "adaptive"],
            ),
            StyleParam("edge_threshold_low", "Edge Threshold Low", "int", 50, 0, 255, 5),
            StyleParam("edge_threshold_high", "Edge Threshold High", "int", 150, 0, 255, 5),
            StyleParam(
                "simplify_tolerance", "Simplify Tolerance (px)", "float", 1.5, 0.1, 10.0, 0.1,
                help="Higher = fewer points, smoother curves.",
            ),
            StyleParam("ensure_connectivity", "Ensure Connectivity (MST bridges)", "bool", True),
            StyleParam("hanging_hole", "Add Hanging Hole", "bool", True),
            StyleParam(
                "min_feature_size_mm", "Min Feature Size (mm)", "float", 2.0, 0.5, 20.0, 0.5,
                help="Fragments smaller than this are removed.",
            ),
        ]

    def generate(
        self,
        image: np.ndarray,
        params: dict[str, Any],
        output_dir: str,
    ) -> StyleResult:
        canvas_w_mm = float(params.get("canvas_width_mm", 150.0))
        thickness_mm = float(params.get("line_thickness_mm", 2.0))
        depth_mm = float(params.get("depth_mm", 3.0))
        edge_algo = str(params.get("edge_algorithm", "canny"))
        thr_low = int(params.get("edge_threshold_low", 50))
        thr_high = int(params.get("edge_threshold_high", 150))
        simplify_tol = float(params.get("simplify_tolerance", 1.5))
        ensure_conn = bool(params.get("ensure_connectivity", True))
        hanging_hole = bool(params.get("hanging_hole", True))
        min_feat_mm = float(params.get("min_feature_size_mm", 2.0))

        warnings: list[str] = []

        h, w = image.shape[:2]
        aspect = h / w
        canvas_h_px = int(_CANVAS_PX * aspect)
        img_rs = cv2.resize(image, (_CANVAS_PX, canvas_h_px), interpolation=cv2.INTER_AREA)

        px_per_mm = _CANVAS_PX / canvas_w_mm
        thickness_px = max(1, int(thickness_mm * px_per_mm))
        min_area_px = max(1, int((min_feat_mm * px_per_mm) ** 2))

        gray = cv2.cvtColor(img_rs, cv2.COLOR_RGB2GRAY)
        edges = _detect_edges(gray, edge_algo, thr_low, thr_high)

        if edges.sum() == 0:
            raise ValueError(
                "No edges detected. Try lowering 'Edge Threshold Low' "
                "or switching to the 'adaptive' algorithm."
            )

        # Dilate to desired line thickness.
        kern_sz = thickness_px * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kern_sz, kern_sz))
        thick = cv2.dilate(edges, kernel, iterations=1)

        # Filter small connected components.
        n, labeled = cv2.connectedComponents(thick)
        for comp in range(1, n):
            if (labeled == comp).sum() < min_area_px:
                thick[labeled == comp] = 0
        n, labeled = cv2.connectedComponents(thick)

        active_components = n - 1  # subtract background
        if active_components == 0:
            raise ValueError("No edges remain after filtering. Lower 'Min Feature Size'.")

        # MST connectivity bridges.
        if ensure_conn and active_components > 1:
            thick, n_bridges = _mst_bridges(thick, labeled, n - 1, thickness_px)
            if n_bridges > 0:
                warnings.append(
                    f"Added {n_bridges} connectivity bridge(s) to prevent floating pieces."
                )
            n, labeled = cv2.connectedComponents(thick)

        # Find and simplify contours.
        contours_raw, _ = cv2.findContours(thick, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours_raw:
            raise ValueError("No closed contours found in edge image.")

        canvas_w_m = canvas_w_mm / 1000.0
        canvas_h_m = canvas_w_m * aspect

        contours_m = _simplify_and_scale(
            contours_raw, simplify_tol, min_area_px,
            _CANVAS_PX, canvas_h_px, canvas_w_m, canvas_h_m,
        )

        if not contours_m:
            raise ValueError(
                "No valid contours after simplification. Lower 'Simplify Tolerance'."
            )

        depth_m = depth_mm / 1000.0

        with fresh_scene():
            _build_line_art(contours_m, depth_m)

            if hanging_hole:
                _drill_hole(canvas_h_m, depth_m, warnings)

            paths = make_output_paths(output_dir, "line_art", "output")
            stl_path = export_stl(paths["stl"])
            glb_path = export_glb(paths["glb"])

        return StyleResult(
            mesh_path=stl_path,
            preview_path=glb_path,
            stats={
                "triangle_count": count_stl_triangles(stl_path),
                "contour_count": len(contours_m),
                "canvas_mm": [round(canvas_w_m * 1000, 1), round(canvas_h_m * 1000, 1)],
                "depth_mm": depth_mm,
            },
            warnings=warnings,
        )


# ---------------------------------------------------------------------------
# Image processing helpers
# ---------------------------------------------------------------------------

def _detect_edges(gray: np.ndarray, algo: str, low: int, high: int) -> np.ndarray:
    if algo == "canny":
        return cv2.Canny(gray, low, high)
    elif algo == "sobel":
        sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        mag = np.sqrt(sx ** 2 + sy ** 2)
        if mag.max() == 0:
            return np.zeros_like(gray, dtype=np.uint8)
        mag8 = (mag / mag.max() * 255).astype(np.uint8)
        _, result = cv2.threshold(mag8, low, 255, cv2.THRESH_BINARY)
        return result
    elif algo == "adaptive":
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
    return cv2.Canny(gray, low, high)


def _mst_bridges(
    edges_img: np.ndarray, labeled: np.ndarray, n_comp: int, thickness_px: int
) -> tuple[np.ndarray, int]:
    """Draw minimum spanning tree bridges between disconnected components."""
    centroids: dict[int, tuple[int, int]] = {}
    for comp in range(1, n_comp + 1):
        ys, xs = np.where(labeled == comp)
        if len(xs):
            centroids[comp] = (int(xs.mean()), int(ys.mean()))

    labels = list(centroids.keys())
    if len(labels) < 2:
        return edges_img, 0

    G: nx.Graph = nx.Graph()
    for i, l1 in enumerate(labels):
        for l2 in labels[i + 1 :]:
            x1, y1 = centroids[l1]
            x2, y2 = centroids[l2]
            G.add_edge(l1, l2, weight=np.hypot(x2 - x1, y2 - y1))

    mst = nx.minimum_spanning_tree(G)
    result = edges_img.copy()
    for l1, l2 in mst.edges():
        x1, y1 = centroids[l1]
        x2, y2 = centroids[l2]
        cv2.line(result, (x1, y1), (x2, y2), 255, thickness_px)

    return result, len(mst.edges())


def _simplify_and_scale(
    contours: list,
    simplify_tol: float,
    min_area_px: int,
    canvas_w_px: int,
    canvas_h_px: int,
    canvas_w_m: float,
    canvas_h_m: float,
) -> list[np.ndarray]:
    """Simplify contours and convert pixel coords to Blender meters."""
    result = []
    for c in contours:
        if cv2.contourArea(c) < min_area_px:
            continue
        approx = cv2.approxPolyDP(c, simplify_tol, closed=True)
        if len(approx) < 3:
            continue
        pts = approx.reshape(-1, 2).astype(np.float64)
        # OpenCV (col, row) → Blender (x, y) with Y-flip and centering.
        bx = (pts[:, 0] / canvas_w_px) * canvas_w_m - canvas_w_m / 2.0
        by = ((canvas_h_px - pts[:, 1]) / canvas_h_px) * canvas_h_m - canvas_h_m / 2.0
        result.append(np.column_stack([bx, by]))
    return result


# ---------------------------------------------------------------------------
# Blender mesh builders
# ---------------------------------------------------------------------------

def _build_line_art(contours_m: list[np.ndarray], depth_m: float) -> None:
    """Create one 2D filled+extruded curve per contour, then join into one mesh."""
    import bpy

    created: list[Any] = []
    for i, pts in enumerate(contours_m):
        if len(pts) < 3:
            continue

        cd = bpy.data.curves.new(f"la_{i}", "CURVE")
        cd.dimensions = "2D"
        cd.fill_mode = "BOTH"
        cd.extrude = depth_m / 2.0  # symmetric: −depth/2 to +depth/2

        sp = cd.splines.new("POLY")
        sp.use_cyclic_u = True
        sp.points.add(len(pts) - 1)
        for j, (x, y) in enumerate(pts):
            sp.points[j].co = (float(x), float(y), 0.0, 1.0)

        obj = bpy.data.objects.new(f"la_{i}", cd)
        bpy.context.collection.objects.link(obj)
        created.append(obj)

    if not created:
        return

    bpy.ops.object.select_all(action="DESELECT")
    for obj in created:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = created[0]
    bpy.ops.object.convert(target="MESH")

    if len(created) > 1:
        bpy.ops.object.join()


def _drill_hole(canvas_h_m: float, depth_m: float, warnings: list[str]) -> None:
    """Boolean-subtract a hanging hole at the top centre."""
    import bpy

    hole_r = 0.003  # 3mm radius hole
    hole_y = canvas_h_m / 2.0 - 0.01  # 10mm from top edge

    bpy.ops.mesh.primitive_cylinder_add(
        radius=hole_r,
        depth=depth_m * 4,
        location=(0.0, hole_y, 0.0),
    )
    cylinder = bpy.context.active_object

    target = next(
        (o for o in bpy.context.scene.objects if o != cylinder and o.type == "MESH"), None
    )
    if target is None:
        bpy.data.objects.remove(cylinder, do_unlink=True)
        warnings.append("Hanging hole skipped — no mesh to drill into.")
        return

    mod = target.modifiers.new("Hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cylinder
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier="Hole")
    bpy.data.objects.remove(cylinder, do_unlink=True)
