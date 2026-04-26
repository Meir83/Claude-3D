"""Tests for the core pipeline — registry, image_io, and pipeline.run()."""

import pytest

from img2print.core import registry
from img2print.core.image_io import ImageError, load_and_validate, preprocess, to_heightmap


def test_list_styles_returns_all_six():
    styles = registry.list_styles()
    names = {s["name"] for s in styles}
    assert {"fabric", "lithophane", "line_art", "stencil", "relief_depth", "multi_color"} == names


def test_get_known_style():
    cls = registry.get("fabric")
    assert cls.name == "fabric"


def test_get_unknown_style_raises():
    with pytest.raises(KeyError):
        registry.get("nonexistent_style_xyz")


def test_load_and_validate_missing_file():
    with pytest.raises(ImageError):
        load_and_validate("/tmp/does_not_exist_xyz123.png")


def test_load_and_validate_synthetic(simple_logo_path: str):
    img = load_and_validate(simple_logo_path)
    assert img.ndim == 3
    assert img.shape[2] == 3


def test_preprocess_resizes_large_image(simple_logo_path: str):
    import numpy as np
    img = load_and_validate(simple_logo_path)
    # Create a large image by tiling.
    large = np.tile(img, (20, 20, 1))
    result = preprocess(large, target_max_dim=512)
    assert max(result.shape[:2]) <= 512


def test_to_heightmap_range(simple_logo_path: str):
    img = load_and_validate(simple_logo_path)
    hmap = to_heightmap(img)
    assert hmap.min() >= 0.0
    assert hmap.max() <= 1.0


def test_to_heightmap_invert(simple_logo_path: str):
    import numpy as np
    img = load_and_validate(simple_logo_path)
    hmap = to_heightmap(img, invert=False)
    hmap_inv = to_heightmap(img, invert=True)
    assert np.allclose(hmap + hmap_inv, 1.0, atol=0.01)


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("bpy"),
    reason="bpy not installed",
)
def test_pipeline_run_fabric(israel_flag_path: str, tmp_path):
    """End-to-end: pipeline.run() → STL exists, stats populated, no unhandled exception."""
    import os

    from img2print.core.pipeline import run

    result = run(
        israel_flag_path,
        "fabric",
        {
            "panel_width_mm": 60.0,
            "panel_thickness_mm": 2.0,
            "relief_depth_mm": 0.4,
            "subdivision_level": 32,
            "invert": False,
            "smoothing": 0.2,
            "add_border": False,
        },
        output_dir=str(tmp_path),
    )

    assert os.path.exists(result.mesh_path)
    assert result.stats.get("triangle_count", 0) > 0
    # Warnings from validator are acceptable; errors would raise exceptions.
