"""Blender bpy context management. NOT thread-safe — use concurrency_count=1."""

from contextlib import contextmanager
from typing import Generator

try:
    import bpy

    _BPY_AVAILABLE = True
except ImportError:
    _BPY_AVAILABLE = False
    bpy = None  # type: ignore[assignment]


def is_available() -> bool:
    return _BPY_AVAILABLE


@contextmanager
def fresh_scene() -> Generator[None, None, None]:
    """Reset Blender to a clean state before each generation."""
    if not _BPY_AVAILABLE:
        raise RuntimeError(
            "bpy (Blender as Python module) is not installed. "
            "Run: uv add bpy"
        )

    # Remove all objects, meshes, materials, and curves.
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Set unit system to metric, scale to millimeter-friendly values.
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.001  # 1 BU = 1 mm

    try:
        yield
    finally:
        pass  # caller is responsible for exporting before scope ends


def save_debug_blend(path: str = "/tmp/img2print_debug.blend") -> None:
    """Dump current Blender scene to disk for inspection."""
    if not _BPY_AVAILABLE:
        return
    bpy.ops.wm.save_as_mainfile(filepath=path)
