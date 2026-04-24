"""STL, 3MF, and GLB export helpers wrapping bpy."""

import os
from pathlib import Path


def export_stl(output_path: str) -> str:
    """Export active scene to STL. Returns the path."""
    try:
        import bpy
    except ImportError as e:
        raise RuntimeError("bpy not available") from e

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # bpy 4.2+ / Blender 5.x: wm.stl_export replaces export_mesh.stl
    bpy.ops.wm.stl_export(
        filepath=output_path,
        global_scale=1000.0,  # Blender meters → mm in STL
    )
    return output_path


def export_glb(output_path: str) -> str:
    """Export active scene to GLB for browser preview. Returns the path."""
    try:
        import bpy
    except ImportError as e:
        raise RuntimeError("bpy not available") from e

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
    )
    return output_path


def export_3mf(output_path: str) -> str:
    """Export active scene to 3MF. Falls back to STL for now. Returns the path."""
    try:
        import bpy
    except ImportError as e:
        raise RuntimeError("bpy not available") from e

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # TODO Phase 3: implement true 3MF export with color metadata for AD5X.
    fallback = output_path.replace(".3mf", ".stl")
    bpy.ops.wm.stl_export(filepath=fallback, global_scale=1000.0)
    return fallback


def make_output_paths(output_dir: str, style_name: str, basename: str) -> dict[str, str]:
    """Build predictable output file paths."""
    import time

    ts = int(time.time())
    stem = f"{style_name}_{basename}_{ts}"
    return {
        "stl": os.path.join(output_dir, f"{stem}.stl"),
        "glb": os.path.join(output_dir, f"{stem}.glb"),
        "3mf": os.path.join(output_dir, f"{stem}.3mf"),
    }
