"""Image loading, validation, and preprocessing."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

MAX_DIM = 2048
SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".tif"}


class ImageError(ValueError):
    pass


def load_and_validate(path: str) -> np.ndarray:
    p = Path(path)
    if not p.exists():
        raise ImageError(f"File not found: {path}")
    if p.suffix.lower() not in SUPPORTED_EXTS:
        raise ImageError(f"Unsupported format '{p.suffix}'. Use: {SUPPORTED_EXTS}")

    img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ImageError(f"Failed to decode image: {path}")

    # Normalize to uint8 RGB.
    if img.dtype != np.uint8:
        img = (img / img.max() * 255).astype(np.uint8)
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    elif img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    return img


def preprocess(
    image: np.ndarray,
    target_max_dim: int = MAX_DIM,
    grayscale: bool = False,
) -> np.ndarray:
    h, w = image.shape[:2]
    if max(h, w) > target_max_dim:
        scale = target_max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    if grayscale:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    return image


def to_heightmap(
    image: np.ndarray,
    invert: bool = False,
    smoothing: float = 0.0,
) -> np.ndarray:
    """Convert image to normalized [0, 1] float32 heightmap."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()

    hmap = gray.astype(np.float32) / 255.0

    if invert:
        hmap = 1.0 - hmap

    if smoothing > 0:
        kernel_size = max(3, int(smoothing * min(hmap.shape) * 0.1))
        if kernel_size % 2 == 0:
            kernel_size += 1
        sigma = smoothing * 10
        hmap = cv2.GaussianBlur(hmap, (kernel_size, kernel_size), sigma)

    return hmap


def open_pil(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")
