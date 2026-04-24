"""Tests for the Fabric style.

Integration tests that require bpy are skipped if bpy is not installed.
"""

import os

import pytest

from img2print.styles.fabric import FabricStyle


def test_fabric_params_declared():
    params = FabricStyle.params()
    names = {p.name for p in params}
    assert "panel_width_mm" in names
    assert "relief_depth_mm" in names
    assert "add_border" in names


def test_fabric_style_metadata():
    assert FabricStyle.name == "fabric"
    assert FabricStyle.display_name
    assert FabricStyle.description


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("bpy"),
    reason="bpy not installed",
)
def test_fabric_generates_stl(israel_flag_path: str, tmp_path):
    import trimesh
    from img2print.core.image_io import load_and_validate

    image = load_and_validate(israel_flag_path)
    style = FabricStyle()
    result = style.generate(
        image,
        {
            "panel_width_mm": 50.0,
            "panel_thickness_mm": 2.0,
            "relief_depth_mm": 0.5,
            "subdivision_level": 32,
            "invert": False,
            "smoothing": 0.1,
            "add_border": False,
        },
        output_dir=str(tmp_path),
    )

    assert os.path.exists(result.mesh_path), "STL was not created"
    assert os.path.getsize(result.mesh_path) > 0, "STL is empty"

    mesh = trimesh.load(result.mesh_path)
    assert len(mesh.faces) > 0, "Mesh has no faces"
    assert len(mesh.faces) < 500_000, "Triangle count exceeds hard limit"
