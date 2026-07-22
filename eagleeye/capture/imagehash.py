"""Perceptual image hashing for screenshot dedup (difference hash / dHash).

dHash is robust to the tiny frame-to-frame noise a byte hash would trip on
(menu-bar clock ticking, cursor blink, sub-pixel JPEG jitter): it compares the
relative brightness of adjacent pixels in a downscaled grayscale thumbnail, so
two visually identical screens map to hashes a few bits apart at most.
"""

from __future__ import annotations

from typing import Optional

from PIL import Image

# 9x8 grayscale -> 8 horizontal comparisons per row -> a 64-bit hash.
_W, _H = 9, 8

try:  # Pillow >= 9.1
    _RESAMPLE = Image.Resampling.BILINEAR
except AttributeError:  # pragma: no cover - older Pillow
    _RESAMPLE = Image.BILINEAR


def dhash(path) -> Optional[int]:
    """64-bit difference hash of the image at ``path`` (None on read failure)."""
    try:
        img = Image.open(path).convert("L").resize((_W, _H), _RESAMPLE)
    except Exception:
        return None
    px = img.load()
    bits = 0
    for y in range(_H):
        for x in range(_W - 1):
            bits = (bits << 1) | (1 if px[x, y] > px[x + 1, y] else 0)
    return bits


def hamming(a: int, b: int) -> int:
    """Number of differing bits between two hashes (0 == identical)."""
    return bin(a ^ b).count("1")
