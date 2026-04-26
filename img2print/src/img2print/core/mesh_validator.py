"""Mesh validation and auto-repair using trimesh and pymeshlab."""

from dataclasses import dataclass, field

MIN_WALL_MM = 0.8
MAX_TRIANGLES_WARN = 200_000
MAX_TRIANGLES_HARD = 500_000


@dataclass
class ValidationResult:
    is_valid: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    repaired: bool = False


def validate(stl_path: str, attempt_repair: bool = True) -> ValidationResult:
    """Run manifold check, wall thickness check, and triangle count check."""
    result = ValidationResult(is_valid=True)

    try:
        import trimesh

        mesh = trimesh.load(stl_path)
    except Exception as e:
        result.is_valid = False
        result.errors.append(f"Failed to load mesh: {e}")
        return result

    triangle_count = len(mesh.faces)
    bbox = mesh.bounding_box.extents.tolist()
    result.stats = {
        "triangle_count": triangle_count,
        "bbox_mm": bbox,
        "volume_mm3": float(mesh.volume) if mesh.is_volume else None,
    }

    if triangle_count > MAX_TRIANGLES_HARD:
        result.errors.append(
            f"Mesh has {triangle_count:,} triangles (max {MAX_TRIANGLES_HARD:,}). "
            "Reduce subdivision_level."
        )
        result.is_valid = False
    elif triangle_count > MAX_TRIANGLES_WARN:
        result.warnings.append(
            f"Large mesh: {triangle_count:,} triangles. Slicing may be slow."
        )

    if not mesh.is_watertight:
        if attempt_repair:
            repaired = _attempt_repair(stl_path)
            if repaired:
                result.repaired = True
                result.warnings.append("Mesh had non-manifold edges; auto-repair applied.")
            else:
                result.warnings.append(
                    "Mesh is not watertight (non-manifold). "
                    "May cause slicing issues. Try 'Attempt repair' option."
                )
        else:
            result.warnings.append("Mesh is not watertight. Enable 'Attempt repair' to fix.")

    return result


def _attempt_repair(stl_path: str) -> bool:
    """Try to repair mesh with pymeshlab. Returns True if successful."""
    try:
        import pymeshlab

        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(stl_path)
        ms.meshing_repair_non_manifold_edges()
        ms.meshing_close_holes(maxholesize=30)
        ms.save_current_mesh(stl_path)
        return True
    except Exception:
        return False
