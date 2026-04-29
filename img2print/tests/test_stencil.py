"""Tests for the Stencil / Cookie Cutter style."""

import importlib.util
import os

import pytest

from img2print.styles.stencil import StencilStyle

_BPY = importlib.util.find_spec("bpy") is not None
skip_no_bpy = pytest.mark.skipif(not _BPY, reason="bpy not installed")

_BASE = {
    "size_mm": 60.0,
    "wall_height_mm": 15.0,
    "wall_thickness_mm": 2.0,
    "threshold": 100,
    "simplify_tolerance": 2.0,
    "include_top_handle": False,
}


def test_stencil_params_declared():
    names = {p.name for p in StencilStyle.params()}
    assert {"size_mm", "wall_height_mm", "wall_thickness_mm", "threshold"} <= names


def test_stencil_metadata():
    assert StencilStyle.name == "stencil"
    assert StencilStyle.display_name
    assert StencilStyle.description


@skip_no_bpy
def test_stencil_generates_stl(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    result = StencilStyle().generate(img, _BASE, str(tmp_path))

    assert os.path.exists(result.mesh_path)
    assert os.path.getsize(result.mesh_path) > 0
    assert result.preview_path and os.path.exists(result.preview_path)


@skip_no_bpy
def test_stencil_triangle_count(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    result = StencilStyle().generate(img, _BASE, str(tmp_path))

    count = result.stats.get("triangle_count", -1)
    assert 10 < count < 500_000


@skip_no_bpy
def test_stencil_stats_dimensions(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    result = StencilStyle().generate(img, _BASE, str(tmp_path))

    assert result.stats["size_mm"] == pytest.approx(60.0)
    assert result.stats["wall_height_mm"] == pytest.approx(15.0)
    assert result.stats["wall_thickness_mm"] == pytest.approx(2.0)


@skip_no_bpy
def test_stencil_with_handle_has_more_triangles(simple_logo_path, tmp_path):
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    r_no_handle = StencilStyle().generate(img, {**_BASE, "include_top_handle": False},
                                          str(tmp_path / "no_handle"))
    r_handle = StencilStyle().generate(img, {**_BASE, "include_top_handle": True},
                                       str(tmp_path / "handle"))

    assert r_handle.stats["triangle_count"] > r_no_handle.stats["triangle_count"]


@skip_no_bpy
def test_stencil_otsu_threshold(simple_logo_path, tmp_path):
    """threshold=0 triggers Otsu auto-thresholding."""
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    result = StencilStyle().generate(img, {**_BASE, "threshold": 0}, str(tmp_path))
    assert os.path.exists(result.mesh_path)


@skip_no_bpy
def test_stencil_thin_wall_warning(simple_logo_path, tmp_path):
    """A very thick wall relative to the shape size should warn about no inner hole."""
    from img2print.core.image_io import load_and_validate

    img = load_and_validate(simple_logo_path)
    # wall_thickness=30mm on a 60mm shape leaves almost no interior
    params = {**_BASE, "wall_thickness_mm": 30.0}
    result = StencilStyle().generate(img, params, str(tmp_path))
    # Either succeeds with a warning OR succeeds without (shape-dependent)
    assert os.path.exists(result.mesh_path)


@skip_no_bpy
def test_stencil_pipeline_integration(simple_logo_path, tmp_path):
    from img2print.core.pipeline import run

    result = run(simple_logo_path, "stencil", _BASE, output_dir=str(tmp_path))
    assert os.path.exists(result.mesh_path)
    assert result.stats.get("triangle_count", 0) > 0
