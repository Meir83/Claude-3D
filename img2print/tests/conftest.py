"""Shared pytest fixtures."""

import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def simple_logo_path(tmp_path: Path) -> str:
    """Generate a simple synthetic 128x128 test image if the fixture doesn't exist."""
    fixture = FIXTURES_DIR / "simple_logo.png"
    if fixture.exists():
        return str(fixture)
    # Fallback: create a synthetic image (white background, blue circle, red rect).
    img = np.ones((128, 128, 3), dtype=np.uint8) * 255
    import cv2
    cv2.circle(img, (64, 64), 40, (0, 0, 200), -1)
    cv2.rectangle(img, (20, 20), (50, 50), (200, 0, 0), -1)
    out = tmp_path / "simple_logo.png"
    cv2.imwrite(str(out), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return str(out)


@pytest.fixture
def portrait_path(tmp_path: Path) -> str:
    """Simple portrait-like test image."""
    fixture = FIXTURES_DIR / "portrait.jpg"
    if fixture.exists():
        return str(fixture)
    # Fallback synthetic portrait.
    img = Image.new("RGB", (256, 256), "#F5DEB3")
    draw = ImageDraw.Draw(img)
    draw.ellipse([96, 80, 116, 100], fill="black")
    draw.ellipse([140, 80, 160, 100], fill="black")
    out = tmp_path / "portrait.jpg"
    img.save(str(out))
    return str(out)


@pytest.fixture
def israel_flag_path(tmp_path: Path) -> str:
    """Synthetic Israel flag: white with two blue stripes and Star of David."""
    fixture = FIXTURES_DIR / "israel_flag.png"
    if fixture.exists():
        return str(fixture)
    # Fallback synthetic flag.
    img = np.ones((200, 300, 3), dtype=np.uint8) * 255
    import cv2
    cv2.rectangle(img, (0, 30), (300, 60), (0, 56, 184), -1)
    cv2.rectangle(img, (0, 140), (300, 170), (0, 56, 184), -1)
    out = tmp_path / "israel_flag.png"
    cv2.imwrite(str(out), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return str(out)
