"""Tests for the Lithophane style."""

import importlib.util

import pytest

from img2print.styles.lithophane import LithophaneStyle

_BPY_AVAILABLE = importlib.util.find_spec("bpy") is not None
_skip_no_bpy = pytest.mark.skipif(not _BPY_AVAILABLE, reason="bpy not installed")

_BASE_PARAMS = {
    "width_mm": 80.0,
    "max_thickness_mm": 3.0,
    "min_thickness_mm": 0.8,
    "curvature": "flat",
    "add_border": False,
    "smoothing": 0.2,
}


def test_lithophane_params_declared():
    params = LithophaneStyle.params()
    names = {p.name for p in params}
    assert {"width_mm", "max_thickness_mm", "min_thickness_mm", "curvature"} <= names


def test_lithophane_style_metadata():
    assert LithophaneStyle.name == "lithophane"
    assert LithophaneStyle.display_name
    assert LithophaneStyle.description


@_skip_no_bpy
def test_lithophane_generates_stl(portrait_path, tmp_path):
    import os

    from img2print.core.image_io import load_and_validate

    image = load_and_validate(portrait_path)
    result = LithophaneStyle().generate(image, _BASE_PARAMS, str(tmp_path))

    assert os.path.exists(result.mesh_path), "STL was not created"
    assert os.path.getsize(result.mesh_path) > 0, "STL is empty"
    assert result.preview_path and os.path.exists(result.preview_path), "GLB not created"


@_skip_no_bpy
def test_lithophane_triangle_count_in_expected_range(portrait_path, tmp_path):
    """Snapshot: ~2 000–60 000 triangles for an 80mm lithophane at default resolution."""
    from img2print.core.image_io import load_and_validate

    image = load_and_validate(portrait_path)
    result = LithophaneStyle().generate(image, _BASE_PARAMS, str(tmp_path))

    count = result.stats.get("triangle_count", -1)
    # We don't assert exact count — just a reasonable range that would catch regressions.
    assert 2_000 < count < 200_000, f"Triangle count {count} out of expected range"


@_skip_no_bpy
def test_lithophane_bbox_x_matches_width(portrait_path, tmp_path):
    import trimesh

    from img2print.core.image_io import load_and_validate

    image = load_and_validate(portrait_path)
    result = LithophaneStyle().generate(image, _BASE_PARAMS, str(tmp_path))

    mesh = trimesh.load(result.mesh_path)
    bbox = mesh.bounding_box.extents
    expected = _BASE_PARAMS["width_mm"]
    assert abs(bbox[0] - expected) < 5.0, (
        f"Mesh width {bbox[0]:.1f}mm != expected {expected}mm"
    )


@_skip_no_bpy
def test_lithophane_thickness_warning_on_thin_min(portrait_path, tmp_path):
    """Very thin min_thickness should produce a warning."""
    from img2print.core.image_io import load_and_validate

    image = load_and_validate(portrait_path)
    params = {**_BASE_PARAMS, "min_thickness_mm": 0.3}  # below 0.6mm threshold
    result = LithophaneStyle().generate(image, params, str(tmp_path))
    assert result.warnings, "Expected a warning for thin min_thickness"


@_skip_no_bpy
def test_lithophane_stats_contain_thickness(portrait_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    image = load_and_validate(portrait_path)
    result = LithophaneStyle().generate(image, _BASE_PARAMS, str(tmp_path))

    assert "min_thickness_mm" in result.stats
    assert "max_thickness_mm" in result.stats
    assert result.stats["min_thickness_mm"] == pytest.approx(
        _BASE_PARAMS["min_thickness_mm"], abs=0.01
    )
