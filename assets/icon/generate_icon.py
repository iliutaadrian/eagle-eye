"""Render the Eagle Eye app icon: an Orwellian amber-phosphor CRT eye.

A single staring eye on a dark rounded panel, drawn in classic amber-monochrome
(#FFB000) with a bloom glow, radial iris striations and horizontal scanlines —
"1985 surveillance terminal" watching you work. Pure PIL, no external assets.

    python assets/icon/generate_icon.py            # -> assets/icon/icon_1024.png
    python assets/icon/generate_icon.py --iconset  # + build EagleEye.icns

Sizes for the .icns are produced by downscaling the 1024 master.
"""

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
S = 1024
AMBER = (255, 176, 0)
AMBER_HI = (255, 214, 122)
AMBER_DIM = (176, 118, 0)


def _rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius, fill=255)
    return m


def _panel():
    """Dark CRT panel with a warm radial vignette."""
    bg = Image.new("RGB", (S, S), (0, 0, 0))
    px = bg.load()
    cx = cy = S / 2
    maxd = math.hypot(cx, cy)
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - cx, y - cy) / maxd  # 0 center -> 1 corner
            glow = max(0.0, 1.0 - d * 1.15)
            r = int(26 * glow + 4)
            g = int(16 * glow + 2)
            b = int(3 * glow)
            px[x, y] = (r, g, b)
    return bg


def _eye_layer():
    """The amber eye drawn on a transparent layer (RGBA)."""
    L = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    cx = cy = S / 2

    half_w = S * 0.40   # almond half-width
    half_h = S * 0.24   # almond half-height
    lw = int(S * 0.022)  # stroke width

    # --- almond eyelid outline: two arcs meeting at the corners ---
    def almond_point(t, upper):
        # t in [-1,1] across the width; parabola-ish lid curve
        x = cx + t * half_w
        lid = (1 - t * t)
        y = cy + (-lid if upper else lid) * half_h
        return x, y

    upper = [almond_point(i / 40 * 2 - 1, True) for i in range(41)]
    lower = [almond_point(i / 40 * 2 - 1, False) for i in range(41)]
    d.line(upper, fill=AMBER, width=lw, joint="curve")
    d.line(lower, fill=AMBER, width=lw, joint="curve")

    # clip everything inside the almond for the iris
    almond = Image.new("L", (S, S), 0)
    ImageDraw.Draw(almond).polygon(upper + lower[::-1], fill=255)

    iris = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    di = ImageDraw.Draw(iris)
    ir = S * 0.185   # iris radius
    # iris ring
    di.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], outline=AMBER, width=lw)
    # radial striations
    for k in range(48):
        a = k / 48 * 2 * math.pi
        x1 = cx + math.cos(a) * ir * 0.42
        y1 = cy + math.sin(a) * ir * 0.42
        x2 = cx + math.cos(a) * ir * 0.94
        y2 = cy + math.sin(a) * ir * 0.94
        di.line([x1, y1, x2, y2], fill=AMBER_DIM, width=max(2, lw // 3))
    # pupil
    pr = S * 0.072
    di.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=AMBER)
    di.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], outline=AMBER_HI, width=lw // 2)
    # catch-light
    hr = S * 0.022
    hx, hy = cx - pr * 0.35, cy - pr * 0.35
    di.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(0, 0, 0, 255))

    iris.putalpha(Image.composite(iris.getchannel("A"),
                                  Image.new("L", (S, S), 0), almond))
    L.alpha_composite(iris)

    # brow tick marks above the eye (surveillance / scanner feel)
    for i in range(-3, 4):
        x = cx + i * S * 0.075
        y0 = cy - half_h - S * 0.085
        d.line([x, y0, x, y0 + S * 0.045], fill=AMBER_DIM, width=lw // 2)

    return L


def _scanlines(img, mask):
    """Overlay horizontal CRT scanlines, clipped to the rounded panel."""
    lines = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lines)
    step = 6
    for y in range(0, S, step):
        dl.line([0, y, S, y], fill=(0, 0, 0, 70), width=2)
    img = img.convert("RGBA")
    img.alpha_composite(lines)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def render():
    mask = _rounded_mask(S, int(S * 0.225))
    panel = _panel()

    eye = _eye_layer()
    # bloom: blurred copy of the eye screened underneath for phosphor glow
    glow = eye.filter(ImageFilter.GaussianBlur(S * 0.02))
    base = panel.convert("RGBA")
    base.alpha_composite(glow)
    base.alpha_composite(glow)   # twice = stronger bloom
    base.alpha_composite(eye)

    out = _scanlines(base, mask)
    png = HERE / "icon_1024.png"
    out.save(png)
    print("wrote", png)
    return out


def build_icns(master):
    iconset = HERE / "EagleEye.iconset"
    iconset.mkdir(exist_ok=True)
    specs = [
        (16, "16x16"), (32, "16x16@2x"),
        (32, "32x32"), (64, "32x32@2x"),
        (128, "128x128"), (256, "128x128@2x"),
        (256, "256x256"), (512, "256x256@2x"),
        (512, "512x512"), (1024, "512x512@2x"),
    ]
    for px, name in specs:
        master.resize((px, px), Image.LANCZOS).save(iconset / f"icon_{name}.png")
    icns = HERE.parent.parent / "EagleEye.icns"
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns)],
                   check=True)
    print("wrote", icns)


if __name__ == "__main__":
    master = render()
    if "--iconset" in sys.argv:
        build_icns(master)
