"""Tests for Line Art style (Phase 2 stub)."""

import pytest

from img2print.styles.line_art import LineArtStyle


def test_line_art_params_declared():
    params = LineArtStyle.params()
    names = {p.name for p in params}
    assert "canvas_width_mm" in names
    assert "line_thickness_mm" in names
    assert "ensure_connectivity" in names


def test_line_art_raises_not_implemented(simple_logo_path: str, tmp_path):
    import numpy as np
    from img2print.core.image_io import load_and_validate

    image = load_and_validate(simple_logo_path)
    style = LineArtStyle()
    with pytest.raises(NotImplementedError):
        style.generate(image, {}, str(tmp_path))
