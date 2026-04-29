"""Tests for the Line Art style."""

import importlib.util
import os

import pytest

from img2print.styles.line_art import LineArtStyle

_BPY = importlib.util.find_spec("bpy") is not None
skip_no_bpy = pytest.mark.skipif(not _BPY, reason="bpy not installed")

_BASE = {
    "canvas_width_mm": 80.0,
    "line_thickness_mm": 2.0,
    "depth_mm": 3.0,
    "edge_algorithm": "canny",
    "edge_threshold_low": 30,
    "edge_threshold_high": 100,
    "simplify_tolerance": 1.5,
    "ensure_connectivity": True,
    "hanging_hole": False,
    "min_feature_size_mm": 1.0,
}


def test_line_art_params_declared():
    names = {p.name for p in LineArtStyle.params()}
    assert {
        "canvas_width_mm", "line_thickness_mm", "depth_mm",
        "edge_algorithm", "ensure_connectivity", "hanging_hole",
    } <= names


def test_line_art_metadata():
    assert LineArtStyle.name == "line_art"
    assert LineArtStyle.display_name
    assert LineArtStyle.description


@skip_no_bpy
def test_line_art_generates_stl(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    result = LineArtStyle().generate(img, _BASE, str(tmp_path))

    assert os.path.exists(result.mesh_path)
    assert os.path.getsize(result.mesh_path) > 0
    assert result.preview_path and os.path.exists(result.preview_path)


@skip_no_bpy
def test_line_art_triangle_count(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    result = LineArtStyle().generate(img, _BASE, str(tmp_path))

    count = result.stats.get("triangle_count", -1)
    assert count > 0, "Triangle count not reported"
    assert count < 500_000, "Triangle count exceeds hard limit"


@skip_no_bpy
def test_line_art_reports_contour_count(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    result = LineArtStyle().generate(img, _BASE, str(tmp_path))

    assert result.stats.get("contour_count", 0) >= 1


@skip_no_bpy
def test_line_art_raises_on_blank_image(tmp_path):
    """A pure white image has no edges — should raise ValueError."""
    import numpy as np

    blank = np.ones((128, 128, 3), dtype=np.uint8) * 255
    with pytest.raises(ValueError, match="No edges detected"):
        LineArtStyle().generate(blank, _BASE, str(tmp_path))


@skip_no_bpy
def test_line_art_sobel_algorithm(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    params = {**_BASE, "edge_algorithm": "sobel", "edge_threshold_low": 20}
    result = LineArtStyle().generate(img, params, str(tmp_path))
    assert os.path.exists(result.mesh_path)


@skip_no_bpy
def test_line_art_adaptive_algorithm(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    params = {**_BASE, "edge_algorithm": "adaptive"}
    result = LineArtStyle().generate(img, params, str(tmp_path))
    assert os.path.exists(result.mesh_path)


@skip_no_bpy
def test_line_art_mst_bridges_on_logo(simple_logo_path, tmp_path):
    """With connectivity on, bridges appear in the warnings for fragmented images."""
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    # High min feature size forces more filtering and potential bridge use.
    params = {**_BASE, "ensure_connectivity": True, "min_feature_size_mm": 0.5}
    result = LineArtStyle().generate(img, params, str(tmp_path))
    # Just verify it completes without error; warnings may or may not be present.
    assert os.path.exists(result.mesh_path)


@skip_no_bpy
def test_line_art_with_hanging_hole(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    params = {**_BASE, "hanging_hole": True}
    result = LineArtStyle().generate(img, params, str(tmp_path))
    assert os.path.exists(result.mesh_path)


@skip_no_bpy
def test_line_art_pipeline_integration(simple_logo_path, tmp_path):
    """End-to-end via pipeline.run() — mesh validator also runs."""
    from img2print.core.pipeline import run

    result = run(
        simple_logo_path, "line_art", {**_BASE, "canvas_width_mm": 60.0},
        output_dir=str(tmp_path),
    )
    assert os.path.exists(result.mesh_path)
    assert result.stats.get("triangle_count", 0) > 0
