"""Tests for mesh_validator — runs against a known-good STL if available."""

import os

import pytest


def _write_minimal_stl(path: str) -> None:
    """Write a minimal valid ASCII STL (a single triangle — not manifold, for testing load)."""
    with open(path, "w") as f:
        f.write(
            "solid test\n"
            "  facet normal 0 0 1\n"
            "    outer loop\n"
            "      vertex 0 0 0\n"
            "      vertex 1 0 0\n"
            "      vertex 0 1 0\n"
            "    endloop\n"
            "  endfacet\n"
            "endsolid test\n"
        )


def test_validate_nonexistent_file():
    from img2print.core.mesh_validator import validate

    result = validate("/tmp/does_not_exist_abc.stl", attempt_repair=False)
    assert not result.is_valid
    assert result.errors


def test_validate_minimal_stl(tmp_path):
    from img2print.core.mesh_validator import validate

    stl_path = str(tmp_path / "minimal.stl")
    _write_minimal_stl(stl_path)
    result = validate(stl_path, attempt_repair=False)
    # Single triangle is not watertight — should produce a warning, not an error.
    assert "triangle_count" in result.stats
    assert result.stats["triangle_count"] == 1
