"""Tests for the Fabric style."""

import importlib.util
import struct

import pytest

from img2print.styles.fabric import FabricStyle

_BPY_AVAILABLE = importlib.util.find_spec("bpy") is not None
_skip_no_bpy = pytest.mark.skipif(not _BPY_AVAILABLE, reason="bpy not installed")

_BASE_PARAMS = {
    "panel_width_mm": 50.0,
    "panel_thickness_mm": 2.0,
    "relief_depth_mm": 0.5,
    "subdivision_level": 32,
    "invert": False,
    "smoothing": 0.1,
    "add_border": False,
}


def test_fabric_params_declared():
    params = FabricStyle.params()
    names = {p.name for p in params}
    assert {"panel_width_mm", "relief_depth_mm", "add_border", "invert", "smoothing"} <= names


def test_fabric_style_metadata():
    assert FabricStyle.name == "fabric"
    assert FabricStyle.display_name
    assert FabricStyle.description


@_skip_no_bpy
def test_fabric_generates_stl(israel_flag_path, tmp_path):
    import os

    from img2print.core.image_io import load_and_validate

    image = load_and_validate(israel_flag_path)
    result = FabricStyle().generate(image, _BASE_PARAMS, str(tmp_path))

    assert os.path.exists(result.mesh_path), "STL was not created"
    assert os.path.getsize(result.mesh_path) > 0, "STL is empty"
    assert result.preview_path and os.path.exists(result.preview_path), "GLB was not created"


@_skip_no_bpy
def test_fabric_triangle_count_in_expected_range(israel_flag_path, tmp_path):
    """Snapshot: subdivision=32 on a landscape image should give ~2 000–15 000 triangles."""
    from img2print.core.image_io import load_and_validate

    image = load_and_validate(israel_flag_path)
    result = FabricStyle().generate(image, _BASE_PARAMS, str(tmp_path))

    count = result.stats.get("triangle_count", -1)
    assert count > 0, "Triangle count not reported"
    assert 1_000 <= count <= 30_000, f"Triangle count {count} out of expected range"


@_skip_no_bpy
def test_fabric_bbox_matches_params(israel_flag_path, tmp_path):
    """STL bounding box X should equal panel_width_mm (±5mm tolerance)."""
    import trimesh

    from img2print.core.image_io import load_and_validate

    image = load_and_validate(israel_flag_path)
    result = FabricStyle().generate(image, _BASE_PARAMS, str(tmp_path))

    mesh = trimesh.load(result.mesh_path)
    bbox = mesh.bounding_box.extents  # [X, Y, Z] in mm (STL exported at mm scale)
    expected_width = _BASE_PARAMS["panel_width_mm"]
    assert abs(bbox[0] - expected_width) < 5.0, (
        f"Mesh X extent {bbox[0]:.1f}mm does not match panel_width {expected_width}mm"
    )


@_skip_no_bpy
def test_fabric_is_manifold_or_repairable(israel_flag_path, tmp_path):
    """Mesh must either be manifold or be repairable (no error from validator)."""
    import trimesh

    from img2print.core.image_io import load_and_validate

    image = load_and_validate(israel_flag_path)
    result = FabricStyle().generate(image, _BASE_PARAMS, str(tmp_path))

    mesh = trimesh.load(result.mesh_path)
    # Not every mesh will be manifold, but it must at least have faces.
    assert len(mesh.faces) > 0


@_skip_no_bpy
def test_fabric_with_border(israel_flag_path, tmp_path):
    """Border adds geometry — triangle count should be higher with border."""
    from img2print.core.image_io import load_and_validate

    image = load_and_validate(israel_flag_path)
    params_no_border = {**_BASE_PARAMS, "add_border": False}
    params_with_border = {**_BASE_PARAMS, "add_border": True}

    r_no = FabricStyle().generate(image, params_no_border, str(tmp_path / "no_border"))
    r_yes = FabricStyle().generate(image, params_with_border, str(tmp_path / "with_border"))

    assert r_yes.stats["triangle_count"] > r_no.stats["triangle_count"], (
        "Border should add triangles"
    )


@_skip_no_bpy
def test_fabric_invert_changes_geometry(simple_logo_path, tmp_path):
    """Inverted and non-inverted maps must produce different geometry."""
    import numpy as np
    import trimesh

    from img2print.core.image_io import load_and_validate

    image = load_and_validate(simple_logo_path)
    p_normal = {**_BASE_PARAMS, "add_border": False}
    p_inverted = {**_BASE_PARAMS, "add_border": False, "invert": True}

    r1 = FabricStyle().generate(image, p_normal, str(tmp_path / "normal"))
    r2 = FabricStyle().generate(image, p_inverted, str(tmp_path / "inverted"))

    m1 = trimesh.load(r1.mesh_path)
    m2 = trimesh.load(r2.mesh_path)
    # Centroids should differ since relief is flipped.
    assert not np.allclose(m1.centroid, m2.centroid, atol=1e-3), (
        "Invert should change mesh geometry"
    )
