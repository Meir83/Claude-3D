"""
Printability report for an STL mesh.

Gives the model (and the user) hard numbers to check a design against:
real dimensions, watertightness, bed contact and overhangs. Numbers catch
problems a preview image hides (e.g. a part that is 10x too large, or a
non-manifold mesh the slicer will choke on).
"""
from __future__ import annotations

import math
from pathlib import Path

# Faces steeper than this from vertical need support on FDM printers
OVERHANG_LIMIT_DEG = 45.0
# Tolerance for "touching the bed" / bottom-face detection
_Z_EPS = 0.05  # mm


def mesh_report(stl_path: str | Path) -> dict:
    import numpy as np  # noqa: PLC0415
    import trimesh  # noqa: PLC0415

    mesh = trimesh.load(str(stl_path), force="mesh")
    if mesh.is_empty:
        return {"error": "STL contains no geometry"}

    lo, hi = mesh.bounds
    size = hi - lo
    z_min = float(lo[2])

    normals = mesh.face_normals
    areas = mesh.area_faces
    face_min_z = mesh.triangles[:, :, 2].min(axis=1)

    # Downward-facing faces steeper than the limit, excluding the bed contact face
    cos_limit = math.cos(math.radians(90.0 - OVERHANG_LIMIT_DEG))
    downward = normals[:, 2] < -cos_limit
    on_bed = face_min_z <= z_min + _Z_EPS
    overhang_area = float(areas[downward & ~on_bed].sum())
    bed_contact_area = float(areas[(normals[:, 2] < -0.999) & on_bed].sum())

    bodies = len(mesh.split(only_watertight=False))

    warnings: list[str] = []
    if not mesh.is_watertight:
        warnings.append("Mesh is not watertight — slicers may produce holes or fail.")
    if bodies > 1:
        warnings.append(f"{bodies} separate bodies — check for floating/disconnected parts.")
    if abs(z_min) > _Z_EPS:
        warnings.append(f"Lowest point is at Z={z_min:.2f} mm, not Z=0 — model does not sit on the bed.")
    if bed_contact_area < 1.0:
        warnings.append("Almost no flat bottom face — the part will need a brim or supports.")
    if overhang_area > 0.05 * float(mesh.area):
        warnings.append(
            f"{overhang_area:.0f} mm² of overhangs steeper than {OVERHANG_LIMIT_DEG:.0f}° "
            "— expect supports or reorient the part."
        )
    if float(size.max()) > 250:
        warnings.append(f"Largest dimension {size.max():.0f} mm exceeds a typical 250 mm build plate.")
    if float(size.max()) < 2:
        warnings.append("Model is under 2 mm — units may be wrong (CadQuery works in mm).")

    return {
        "size_mm": {"x": round(float(size[0]), 2), "y": round(float(size[1]), 2), "z": round(float(size[2]), 2)},
        "volume_cm3": round(float(mesh.volume) / 1000.0, 2) if mesh.is_watertight else None,
        "surface_area_mm2": round(float(mesh.area), 1),
        "triangles": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "bodies": bodies,
        "z_min_mm": round(z_min, 3),
        "bed_contact_area_mm2": round(bed_contact_area, 1),
        "overhang_area_mm2": round(overhang_area, 1),
        "center_of_mass_mm": [round(float(c), 2) for c in np.asarray(mesh.center_mass)],
        "warnings": warnings,
    }
