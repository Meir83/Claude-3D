"""Tests for the STL printability report."""
from __future__ import annotations

import pytest

trimesh = pytest.importorskip("trimesh")

from app.services.mesh_report import mesh_report  # noqa: E402


def _export(mesh, tmp_path):
    path = tmp_path / "part.stl"
    mesh.export(path)
    return path


def test_box_on_bed_is_clean(tmp_path):
    box = trimesh.creation.box(extents=(60, 40, 20))
    box.apply_translation((0, 0, 10))  # bottom at Z=0

    report = mesh_report(_export(box, tmp_path))

    assert report["size_mm"] == {"x": 60.0, "y": 40.0, "z": 20.0}
    assert report["watertight"] is True
    assert report["bodies"] == 1
    assert report["volume_cm3"] == pytest.approx(48.0)
    assert report["bed_contact_area_mm2"] == pytest.approx(2400.0)
    assert report["overhang_area_mm2"] == 0
    assert report["warnings"] == []


def test_floating_part_and_overhang_are_flagged(tmp_path):
    # A T shape: the top bar's underside is a 90° overhang
    stem = trimesh.creation.box(extents=(10, 10, 20))
    stem.apply_translation((0, 0, 10))
    bar = trimesh.creation.box(extents=(60, 10, 5))
    bar.apply_translation((0, 0, 22.5))
    floating = trimesh.creation.box(extents=(5, 5, 5))
    floating.apply_translation((50, 50, 30))
    mesh = trimesh.util.concatenate([stem, bar, floating])

    report = mesh_report(_export(mesh, tmp_path))
    warnings = " ".join(report["warnings"])

    assert report["bodies"] == 3
    assert "separate bodies" in warnings
    assert "overhangs" in warnings


def test_model_below_bed_is_flagged(tmp_path):
    box = trimesh.creation.box(extents=(20, 20, 20))  # centred on origin
    report = mesh_report(_export(box, tmp_path))
    assert any("not Z=0" in w for w in report["warnings"])
