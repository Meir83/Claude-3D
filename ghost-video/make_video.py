#!/usr/bin/env python3
"""Procedural animated video: the ghost mascot "Vote for Me" pitch (8 slides).

Usage:
    python3 make_video.py out.mp4            # full render
    python3 make_video.py --stills DIR       # one still per scene (for review)
"""
import math, random, subprocess, sys, os, wave
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SS = 1280, 720, 30, 2
N = 8
TL = None  # timeline (slide durations + narration timing), see narration.py


def load_timeline():
    global TL
    import narration
    TL = narration.build(os.path.join(narration.HERE, "_tts"))
    return TL

FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

PURPLE, VIOLET, LAV = (168, 85, 247), (124, 58, 237), (205, 170, 255)
GREEN = (70, 255, 130)
BODY, SHADE = (246, 244, 255), (186, 168, 236)


@lru_cache(maxsize=None)
def F(path, size):
    return ImageFont.truetype(path, max(1, int(size)))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def back(x):
    x = clamp(x)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def lerp(a, b, u):
    return a + (b - a) * u


def bob(t, a=9, f=0.45, ph=0.0):
    return a * math.sin(2 * math.pi * f * t + ph)


# ----------------------------------------------------------------- canvas
class Cv:
    """RGB canvas drawn in logical (1280x720) units, scaled by k."""

    def __init__(s, w, h, k, im=None):
        s.k, s.w, s.h = k, w, h
        s.im = im if im is not None else Image.new("RGB", (max(1, int(w * k)), max(1, int(h * k))))
        s.d = ImageDraw.Draw(s.im, "RGBA")

    def _p(s, pts):
        return [(x * s.k, y * s.k) for x, y in pts]

    def _w(s, w):
        return max(1, int(round(w * s.k)))

    def poly(s, pts, fill=None):
        s.d.polygon(s._p(pts), fill=fill)

    def line(s, pts, fill, w=1):
        s.d.line(s._p(pts), fill=fill, width=s._w(w), joint="curve")

    def ell(s, x0, y0, x1, y1, fill=None, outline=None, w=1):
        k = s.k
        s.d.ellipse([x0 * k, y0 * k, x1 * k, y1 * k], fill=fill, outline=outline,
                    width=s._w(w) if outline else 0)

    def circ(s, x, y, r, fill=None, outline=None, w=1):
        s.ell(x - r, y - r, x + r, y + r, fill, outline, w)

    def rr(s, x0, y0, x1, y1, r, fill=None, outline=None, w=1):
        k = s.k
        s.d.rounded_rectangle([x0 * k, y0 * k, x1 * k, y1 * k], radius=r * k, fill=fill,
                              outline=outline, width=s._w(w) if outline else 0)

    def arc(s, x0, y0, x1, y1, a0, a1, fill, w=1):
        k = s.k
        s.d.arc([x0 * k, y0 * k, x1 * k, y1 * k], a0, a1, fill=fill, width=s._w(w))

    def text(s, xy, t, font, size, fill, anchor="mm"):
        s.d.text((xy[0] * s.k, xy[1] * s.k), t, font=F(font, size * s.k), fill=fill, anchor=anchor)

    def add_glow(s, g, tight=3, wide=12, a=0.9, b=1.0):
        t1 = g.im.filter(ImageFilter.GaussianBlur(tight)).point(lambda v: int(v * a))
        t2 = g.im.filter(ImageFilter.GaussianBlur(wide)).point(lambda v: min(255, int(v * b * 1.6)))
        up = ImageChops.add(t1, t2).resize(s.im.size, Image.BILINEAR)
        s.im = ImageChops.add(s.im, up)
        s.d = ImageDraw.Draw(s.im, "RGBA")

    def paste_spr(s, spr, x, y, angle=0.0, scale=1.0, pivot=None):
        """Paste sprite so that its `pivot` (logical sprite coords) lands on (x, y)."""
        if scale < 0.02:
            return
        im = spr.im
        pw, ph = spr.w, spr.h
        px, py = pivot if pivot else (pw / 2, ph / 2)
        if scale != 1.0:
            im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
        px, py = px * scale, py * scale
        w0, h0 = im.width / s.k, im.height / s.k
        vx, vy = px - w0 / 2, py - h0 / 2
        if angle:
            im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
            a = math.radians(angle)
            vx, vy = vx * math.cos(a) + vy * math.sin(a), -vx * math.sin(a) + vy * math.cos(a)
        cx, cy = x - vx, y - vy
        s.im.paste(im, (int(cx * s.k - im.width / 2), int(cy * s.k - im.height / 2)), im)


class Spr(Cv):
    def __init__(s, w, h, k):
        super().__init__(w, h, k, Image.new("RGBA", (int(w * k), int(h * k)), (0, 0, 0, 0)))
        s.d = ImageDraw.Draw(s.im)


# ---------------------------------------------------------------- backdrop
@lru_cache(maxsize=None)
def gradient(top, bot, glow_center=None, glow_col=None):
    ys = np.linspace(0, 1, H * SS)[:, None, None]
    xs = np.linspace(-1, 1, W * SS)[None, :, None]
    top, bot = np.array(top, float), np.array(bot, float)
    img = top * (1 - ys) + bot * ys
    img = np.broadcast_to(img, (H * SS, W * SS, 3)).copy()
    vig = 1 - 0.35 * (xs ** 2) * np.ones_like(ys)
    img *= vig
    if glow_center:
        gx, gy = glow_center
        yy = np.linspace(0, 1, H * SS)[:, None]
        xx = np.linspace(0, 1, W * SS)[None, :]
        d = np.sqrt(((xx - gx) * 1.6) ** 2 + (yy - gy) ** 2)
        img += (np.exp(-d * 3.2)[..., None]) * np.array(glow_col, float) * 0.55
    return Image.fromarray(np.clip(img, 0, 255).astype("uint8"))


def floor_grid(c, horizon=0.62, col=(150, 90, 255, 55), vp_x=640):
    hy = H * horizon
    for i in range(-14, 15):
        c.line([(vp_x + i * 28, hy), (vp_x + i * 150, H + 10)], col, 1)
    y, step = hy, 6.0
    while y < H:
        c.line([(0, y), (W, y)], col, 1)
        step *= 1.32
        y += step


def rack(c, x0, y0, w, h, rows, alpha=255):
    c.rr(x0, y0, x0 + w, y0 + h, 6, fill=(20, 15, 38, alpha), outline=(88, 62, 150, alpha), w=2)
    rh = h / rows
    for j in range(rows):
        yy = y0 + j * rh
        c.rr(x0 + 6, yy + 4, x0 + w - 6, yy + rh - 4, 3, fill=(30, 24, 54, alpha), outline=(60, 44, 104, alpha), w=1)
        for v in range(3):
            c.line([(x0 + 14, yy + rh / 2 - 5 + v * 5), (x0 + w * 0.55, yy + rh / 2 - 5 + v * 5)], (52, 40, 90, alpha), 1)


RACKS1 = [(30, 130, 170, 520, 11), (215, 200, 120, 430, 9), (1080, 130, 170, 520, 11), (945, 200, 120, 430, 9)]


@lru_cache(maxsize=None)
def bg(i):
    palettes = [
        ((6, 3, 18), (34, 12, 70), (0.5, 0.45), (110, 40, 200)),
        ((3, 6, 8), (26, 12, 48), (0.7, 0.5), (0, 90, 40)),
        ((8, 4, 24), (24, 10, 58), (0.5, 0.5), (120, 50, 220)),
        ((7, 5, 20), (20, 12, 46), (0.28, 0.55), (110, 50, 210)),
        ((6, 4, 18), (22, 10, 50), (0.5, 0.6), (120, 50, 220)),
        ((6, 3, 20), (28, 10, 62), (0.5, 0.5), (120, 40, 230)),
        ((5, 4, 16), (24, 10, 50), (0.75, 0.5), (110, 40, 210)),
        ((7, 3, 22), (30, 10, 64), (0.55, 0.5), (130, 50, 230)),
    ]
    top, bot, gc, gcol = palettes[i]
    c = Cv(W, H, SS, gradient(top, bot, gc, gcol).copy())
    if i == 0:
        floor_grid(c)
        for (x, y, w, h, r) in RACKS1:
            rack(c, x, y, w, h, r)
    elif i == 1:
        floor_grid(c, 0.72, (80, 255, 140, 22))
    elif i == 2:
        floor_grid(c, 0.7, (150, 90, 255, 40))
        for rx in (640,):
            c.ell(rx - 360, 560, rx + 360, 640, outline=(150, 90, 255, 60), w=2)
    elif i == 3:
        floor_grid(c, 0.78, (150, 90, 255, 35))
    elif i == 4:
        for gx in range(120, 1220, 80):
            c.line([(gx, 90), (gx, 560)], (150, 100, 255, 28), 1)
        for gy in range(90, 570, 52):
            c.line([(110, gy), (1180, gy)], (150, 100, 255, 28), 1)
        c.line([(140, 90), (140, 560), (1180, 560)], (205, 170, 255, 130), 3)
    elif i == 5:
        floor_grid(c, 0.75, (150, 90, 255, 38))
    elif i == 6:
        floor_grid(c, 0.74, (150, 90, 255, 38))
    elif i == 7:
        floor_grid(c, 0.76, (150, 90, 255, 34))
    return c.im


def ambient(c, g, t, seed, n=34, col=(190, 140, 255)):
    rnd = random.Random(seed)
    for _ in range(n):
        x0, y0, v, r, ph = rnd.random() * W, rnd.random() * H, rnd.uniform(6, 22), rnd.uniform(1.2, 3.2), rnd.random() * 6
        x = (x0 + 14 * math.sin(t * 0.7 + ph)) % W
        y = (y0 - v * t) % H
        a = int(70 + 60 * math.sin(t * 1.6 + ph))
        c.circ(x, y, r, fill=(*col, a))
        g.circ(x, y, r * 1.5, fill=(*[int(q * 0.5) for q in col],))


# ------------------------------------------------------------------- ghost
@lru_cache(maxsize=None)
def body_gradient(w, h):
    yy = np.linspace(0, 1, h)[:, None]
    xx = np.linspace(0, 1, w)[None, :]
    k = np.clip(xx * 0.45 + yy * 0.7 - 0.25, 0, 1) ** 1.4
    base, sh = np.array(BODY, float), np.array(SHADE, float)
    img = base * (1 - k[..., None]) + sh * k[..., None]
    return Image.fromarray(img.astype("uint8"))


def ghost_body(c, g, cx, cy, s, t, mood="happy", wink=False, look=(0, 0), blink_phase=0.0):
    R = 70 * s
    base = cy + R * 1.30
    amp = 0.14 * R
    pts = []
    for i in range(31):
        a = math.pi + math.pi * i / 30
        pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    n, ph = 4, t * 2.2
    for i in range(81):
        u = i / 80
        pts.append((cx + R - 2 * R * u, base + amp * abs(math.sin(math.pi * n * u + ph))))
    # aura (added under the body so it never washes out the face)
    k = c.k
    pad = 40 * s
    ax0, ay0 = cx - R - pad, cy - R - pad
    aw, ah = 2 * R + 2 * pad, (base + amp + pad) - (cy - R - pad)
    al = Cv(aw, ah, 0.5)
    al.poly([(x - ax0, y - ay0) for x, y in pts], fill=(100, 48, 190))
    up = al.im.filter(ImageFilter.GaussianBlur(8)).resize((int(aw * k), int(ah * k)), Image.BILINEAR)
    box = (int(ax0 * k), int(ay0 * k))
    c.im.paste(ImageChops.add(c.im.crop(box + (box[0] + up.width, box[1] + up.height)), up), box)
    # body with gradient shading
    x0, y0 = int((cx - R - 6) * k), int((cy - R - 6) * k)
    x1, y1 = int((cx + R + 6) * k), int((base + amp + 6) * k)
    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(mask).polygon([(x * k - x0, y * k - y0) for x, y in pts], fill=255)
    c.im.paste(body_gradient(x1 - x0, y1 - y0), (x0, y0), mask)
    # face
    ex = [cx - 0.31 * R + look[0], cx + 0.31 * R + look[0]]
    ey = cy + 0.06 * R + look[1]
    blink = ((t + blink_phase) % 3.4) < 0.13
    dark = (34, 26, 58)
    for idx, x in enumerate(ex):
        rx = 0.085 * R
        ry = 0.135 * R * (0.12 if blink else 1.0)
        if mood == "confused" and idx == 1:
            rx, ry = rx * 1.15, ry * 1.15
        if wink and idx == 1:
            c.line([(x - 0.12 * R, ey + 0.03 * R), (x, ey - 0.07 * R), (x + 0.12 * R, ey + 0.03 * R)], dark, 0.05 * R)
            continue
        c.ell(x - rx, ey - ry, x + rx, ey + ry, fill=dark)
        if not blink:
            c.circ(x - rx * 0.3, ey - ry * 0.35, rx * 0.32, fill=(255, 255, 255))
    if mood == "frustrated":
        c.line([(ex[0] - 0.14 * R, ey - 0.22 * R), (ex[0] + 0.1 * R, ey - 0.13 * R)], dark, 0.045 * R)
        c.line([(ex[1] + 0.14 * R, ey - 0.22 * R), (ex[1] - 0.1 * R, ey - 0.13 * R)], dark, 0.045 * R)
    if mood == "confused":
        c.line([(ex[0] - 0.12 * R, ey - 0.2 * R), (ex[0] + 0.12 * R, ey - 0.24 * R)], dark, 0.04 * R)
        c.line([(ex[1] - 0.12 * R, ey - 0.27 * R), (ex[1] + 0.12 * R, ey - 0.2 * R)], dark, 0.04 * R)
    my = cy + 0.40 * R
    mx = cx + look[0]
    if mood in ("happy", "proud"):
        c.arc(mx - 0.11 * R, my - 0.08 * R, mx + 0.11 * R, my + 0.1 * R, 20, 160, dark, 0.045 * R)
    elif mood == "frustrated":
        zz = [(mx + (i - 3) * 0.045 * R, my + (0.025 if i % 2 else -0.025) * R) for i in range(7)]
        c.line(zz, dark, 0.04 * R)
    else:
        zz = [(mx - 0.12 * R + i * 0.03 * R, my + 0.03 * R * math.sin(i * 1.3 + t * 3)) for i in range(9)]
        c.line(zz, dark, 0.04 * R)
    for sx in (-1, 1):
        c.ell(cx + sx * 0.52 * R - 0.12 * R + look[0], cy + 0.25 * R, cx + sx * 0.52 * R + 0.12 * R + look[0],
              cy + 0.40 * R, fill=(255, 150, 190, 85))


def arm(c, g, sx, sy, hx, hy, s, bend=0.25, glow=True):
    w = 0.27 * 70 * s
    mx, my = (sx + hx) / 2, (sy + hy) / 2
    dx, dy = hx - sx, hy - sy
    cxp, cyp = mx - dy * bend, my + dx * bend
    for i in range(19):
        u = i / 18
        x = (1 - u) ** 2 * sx + 2 * u * (1 - u) * cxp + u * u * hx
        y = (1 - u) ** 2 * sy + 2 * u * (1 - u) * cyp + u * u * hy
        c.circ(x, y, w / 2, fill=(238, 235, 252))
    c.circ(hx, hy, w / 2, fill=(246, 244, 255))


def arms(c, g, cx, cy, s, left=None, right=None, t=0.0):
    R = 70 * s
    if left is None:
        left = (cx - 1.22 * R, cy + 0.95 * R + 5 * math.sin(t * 2.1))
    if right is None:
        right = (cx + 1.22 * R, cy + 0.95 * R + 5 * math.sin(t * 2.1 + 1.5))
    arm(c, g, cx - 0.78 * R, cy + 0.55 * R, left[0], left[1], s, bend=-0.2)
    arm(c, g, cx + 0.78 * R, cy + 0.55 * R, right[0], right[1], s, bend=0.2)


def shoulder(cx, cy, s, side):
    R = 70 * s
    return (cx + side * 0.78 * R, cy + 0.55 * R)


def sparkle(c, g, x, y, r, col, a=255):
    for ang in (0, 90):
        a_r = math.radians(ang)
        c.line([(x - r * math.cos(a_r), y - r * math.sin(a_r)), (x + r * math.cos(a_r), y + r * math.sin(a_r))], (*col, a), max(1, r * 0.22))
    c.circ(x, y, r * 0.3, fill=(255, 255, 255, a))
    g.circ(x, y, r * 0.9, fill=tuple(int(q * 0.6) for q in col))


# ------------------------------------------------------------------ scenes
@lru_cache(maxsize=None)
def sign_sprite():
    sp = Spr(380, 340, SS)
    sp.rr(6, 6, 374, 156, 10, fill=(150, 104, 62))
    sp.rr(12, 12, 368, 150, 8, fill=(205, 158, 104), outline=(120, 80, 46), w=3)
    for x in range(30, 360, 22):
        sp.line([(x, 16), (x, 146)], (190, 142, 90), 2)
    sp.rr(172, 150, 208, 330, 4, fill=(120, 84, 52))
    sp.text((148, 82), "VOTE FOR ME!", FB, 31, (62, 36, 20))
    # robot icon (stand-in for the emoji)
    rx, ry = 322, 82
    sp.line([(rx, ry - 34), (rx, ry - 22)], (62, 36, 20), 3)
    sp.circ(rx, ry - 36, 4, fill=(190, 40, 60))
    sp.rr(rx - 24, ry - 22, rx + 24, ry + 18, 8, fill=(80, 90, 120), outline=(62, 36, 20), w=3)
    sp.circ(rx - 10, ry - 4, 5, fill=(150, 255, 240))
    sp.circ(rx + 10, ry - 4, 5, fill=(150, 255, 240))
    sp.line([(rx - 10, ry + 8), (rx + 10, ry + 8)], (230, 230, 240), 3)
    return sp


def scene1(c, g, t):
    for ri, (x, y, w, h, rows) in enumerate(RACKS1):
        rh = h / rows
        for j in range(rows):
            for v in range(2):
                on = math.sin(t * (2 + (j + ri) % 4) + j * 1.7 + v) > -0.2
                col = (200, 120, 255) if (j + v) % 3 else (110, 230, 255)
                ledx = x + w - 18 - v * 12
                ledy = y + j * rh + rh / 2
                if on:
                    c.circ(ledx, ledy, 3, fill=(*col, 255))
                    g.circ(ledx, ledy, 4, fill=col)
    ambient(c, g, t, 11)
    gx, gy = 560, 392 + bob(t)
    ghost_body(c, g, gx, gy, 1.3, t, "happy")
    p = back((t - 0.4) / 0.8)
    sway = 2.6 * math.sin(t * 1.7)
    hand = (770, 458 + bob(t, 6, 0.45, 0.4))
    c.paste_spr(sign_sprite(), hand[0], hand[1], angle=sway, scale=p, pivot=(190, 300))
    R = 91
    sh = shoulder(gx, gy, 1.3, 1)
    arms(c, g, gx, gy, 1.3, left=(gx - 1.45 * R, gy - 0.1 * R + 16 * math.sin(t * 5)),
         right=(hand[0] - 6, hand[1] - 4), t=t)
    sparkle_t = clamp((t - 1.0) / 0.6)
    if 0 < sparkle_t < 1:
        for i in range(6):
            a = i * math.pi / 3 + 0.3
            r = 40 + 90 * sparkle_t
            sparkle(c, g, 740 + r * math.cos(a), 245 + r * 0.55 * math.sin(a), 9 * (1 - sparkle_t), LAV, int(255 * (1 - sparkle_t)))


TERM = None


def term_lines():
    rnd = random.Random(7)
    lines = []
    tpl = [
        ("IEF450I JOBA01 STEP1 - ABEND=S0C7 U0000 REASON=00000004", "err"),
        ("//SYSIN   DD  DSN=PROD.CUST.MASTER,DISP=SHR", ""),
        ("PERFORM 2100-UPDATE-REC THRU 2100-EXIT", ""),
        ("01  WS-CUST-REC.   05 WS-ID  PIC 9(8) COMP-3.", ""),
        ("DFHAC2206 TRANSACTION 'CUPD' ABEND ASRA", "err"),
        ("IKJ56500I COMMAND NOT FOUND - REENTER", "err"),
        ("MOVE SPACES TO WS-ERR-MSG. IF SQLCODE NOT = 0", ""),
        ("COND CODE 0012  SYSOUT=A  LRECL=133", ""),
        ("ISPF  OPTION ===>  _", ""),
        ("HASP395 JOBA01 ENDED - RC=0012", "err"),
    ]
    for _ in range(70):
        if rnd.random() < 0.3:
            lines.append((" ".join("%08X" % rnd.getrandbits(32) for _ in range(5)), ""))
        else:
            lines.append(rnd.choice(tpl))
    return lines


@lru_cache(maxsize=None)
def term_cache():
    return term_lines()


def scene2(c, g, t):
    x0, y0, x1, y1 = 700, 170, 1190, 520
    c.rr(x0 - 24, y0 - 24, x1 + 24, y1 + 24, 28, fill=(28, 26, 32), outline=(78, 74, 88), w=3)
    c.rr(x0, y0, x1, y1, 14, fill=(2, 14, 7))
    g.rr(x0, y0, x1, y1, 14, fill=(0, 42, 20))
    sp = Spr(x1 - x0, y1 - y0, SS)
    lh = 16
    lines = term_cache()
    off = (t * 34) % (len(lines) * lh)
    for rep in range(2):
        for i, (tx, kind) in enumerate(lines):
            y = i * lh + rep * len(lines) * lh - off + 10
            if -lh < y < y1 - y0 + lh:
                col = (255, 120, 90, 255) if kind == "err" else (70, 255, 130, 230)
                sp.text((12, y), tx, FM, 12.5, col, "lm")
    c.paste_spr(sp, (x0 + x1) / 2, (y0 + y1) / 2)
    for y in range(int(y0), int(y1), 3):
        c.line([(x0, y), (x1, y)], (0, 0, 0, 70), 1)
    flash = (t % 1.3) < 0.65 and t > 0.8
    if flash:
        c.rr(795, 300, 1095, 380, 8, fill=(30, 0, 0, 225), outline=(255, 70, 60), w=3)
        c.text((945, 326), "*** SYSTEM ERROR ***", FB, 20, (255, 90, 80))
        c.text((945, 355), "ABEND S0C7  RC=0012", FM, 15, (255, 150, 120))
        g.rr(795, 300, 1095, 380, 8, fill=(70, 10, 5))
    if (t * 2) % 1 < 0.5:
        c.rr(x0 + 14, y1 - 28, x0 + 28, y1 - 12, 1, fill=(70, 255, 130))
    # ghost
    shake = 4 * math.sin(t * 38) if (t % 1.5) > 1.15 else 0
    gx, gy = 410 + shake, 400 + bob(t, 7, 0.5)
    ghost_body(c, g, gx, gy, 1.2, t, "frustrated" if t > 1.6 else "confused", look=(14, 0))
    R = 84
    if t > 1.6:
        # hands on head, frustrated
        arms(c, g, gx, gy, 1.2, left=(gx - 0.85 * R, gy - 0.55 * R), right=(gx + 0.85 * R, gy - 0.55 * R), t=t)
    else:
        arms(c, g, gx, gy, 1.2, right=(gx + 1.4 * R, gy + 0.2 * R), t=t)
    for i, ch in enumerate("?!?"[:3]):
        tt = t - 0.5 - i * 0.35
        if tt > 0:
            a = int(255 * ease(tt * 2))
            qx = gx - 70 + i * 70
            qy = gy - 1.5 * R - 20 - 28 * (i % 2) + bob(t, 6, 0.8, i)
            col = (255, 170, 80) if ch == "!" else (205, 170, 255)
            c.text((qx, qy), "?" if ch != "!" else "?", FB, 54, (*col, a))
            g.text((qx, qy), "?", FB, 54, tuple(int(q * 0.4) for q in col))
    if t > 2.0:
        d = ease((t - 2.0) * 2)
        c.ell(gx + 0.9 * R, gy - 0.9 * R + 12 * d, gx + 0.9 * R + 12, gy - 0.9 * R + 30 + 12 * d, fill=(150, 210, 255, int(200 * (1 - d * 0.4))))


def holo_stroke(a=1.0):
    return (205, 160, 255, int(235 * a))


def icon_db(cv, x, y, s, a, glow=False):
    w, h = 50 * s, 15 * s
    top, bot = y - 52 * s, y + 42 * s
    ol = (150, 80, 255) if glow else holo_stroke(a)
    fl = None if glow else (140, 80, 240, int(70 * a))
    if not glow:
        cv.rr(x - w, top, x + w, bot, 2, fill=fl)
        cv.ell(x - w, bot - h, x + w, bot + h, fill=fl)
        cv.ell(x - w, top - h, x + w, top + h, fill=(180, 120, 255, int(90 * a)))
    cv.ell(x - w, top - h, x + w, top + h, outline=ol, w=3 * s)
    cv.line([(x - w, top), (x - w, bot)], ol, 3 * s)
    cv.line([(x + w, top), (x + w, bot)], ol, 3 * s)
    for yy in (top + (bot - top) * 0.33, top + (bot - top) * 0.66, bot):
        cv.arc(x - w, yy - h, x + w, yy + h, 0, 180, ol, 3 * s)


def icon_server(cv, x, y, s, a, glow=False, t=0.0):
    ol = (150, 80, 255) if glow else holo_stroke(a)
    for j in range(3):
        yy = y - 62 * s + j * 44 * s
        if not glow:
            cv.rr(x - 58 * s, yy, x + 58 * s, yy + 36 * s, 6 * s, fill=(140, 80, 240, int(70 * a)))
        cv.rr(x - 58 * s, yy, x + 58 * s, yy + 36 * s, 6 * s, outline=ol, w=3 * s)
        for v in range(3):
            cv.line([(x - 44 * s, yy + (10 + v * 8) * s), (x + 8 * s, yy + (10 + v * 8) * s)], ol, 2 * s)
        on = math.sin(t * 4 + j * 2) > -0.3
        if on or glow:
            cv.circ(x + 38 * s, yy + 18 * s, 4.5 * s, fill=(120, 255, 235) if not glow else (60, 150, 140))


def icon_net(cv, x, y, s, a, glow=False, t=0.0):
    ol = (150, 80, 255) if glow else holo_stroke(a)
    nodes = [(-58, -34), (60, -42), (-52, 44), (58, 40)]
    for i, (dx, dy) in enumerate(nodes):
        cv.line([(x, y), (x + dx * s, y + dy * s)], ol, 3 * s)
        u = (t * 0.8 + i * 0.25) % 1
        if not glow:
            cv.circ(x + dx * s * u, y + dy * s * u, 4 * s, fill=(255, 255, 255, int(220 * a)))
    for dx, dy in nodes:
        if not glow:
            cv.circ(x + dx * s, y + dy * s, 13 * s, fill=(140, 80, 240, int(90 * a)))
        cv.circ(x + dx * s, y + dy * s, 13 * s, outline=ol, w=3 * s)
    if not glow:
        cv.circ(x, y, 24 * s, fill=(180, 120, 255, int(110 * a)))
    cv.circ(x, y, 24 * s, outline=ol, w=3.5 * s)


def scene3(c, g, t):
    ambient(c, g, t, 31)
    cx0, cy0 = 640, 395
    items = []
    names = ["Database", "Servers", "Network"]
    spots = [(255, 410), (1025, 410), (640, 168)]
    for i in range(3):
        appear = back((t - 0.3 - i * 0.35) / 0.7)
        x, y = spots[i]
        s = 1.05 * clamp(appear, 0, 1.15)
        items.append((-1, i, x, y, s, clamp(appear)))

    def draw_item(it):
        depth, i, x, y, s, ap = it
        a = ap * (0.7 + 0.3 * (depth + 1) / 2)
        if a <= 0.02:
            return
        yy = y + bob(t, 7, 0.5, i * 2)
        c.ell(x - 80 * s, yy + 66 * s, x + 80 * s, yy + 92 * s, outline=holo_stroke(a), w=2.5)
        g.ell(x - 80 * s, yy + 66 * s, x + 80 * s, yy + 92 * s, outline=(120, 60, 230), w=3)
        # light cone
        c.poly([(x - 70 * s, yy + 78 * s), (x + 70 * s, yy + 78 * s), (x + 44 * s, yy - 70 * s), (x - 44 * s, yy - 70 * s)],
               fill=(160, 100, 255, int(18 * a)))
        if i == 0:
            icon_db(c, x, yy, s, a)
            icon_db(g, x, yy, s, a, glow=True)
        elif i == 1:
            icon_server(c, x, yy, s, a, t=t)
            icon_server(g, x, yy, s, a, glow=True, t=t)
        else:
            icon_net(c, x, yy, s, a, t=t)
            icon_net(g, x, yy, s, a, glow=True, t=t)
        for k in range(0, int(140 * s), 5):
            c.line([(x - 60 * s, yy - 70 * s + k), (x + 60 * s, yy - 70 * s + k)], (190, 140, 255, int(14 * a)), 1)
        c.text((x, yy + 112 * s), names[i], FB, 20 * s, (225, 205, 255, int(230 * a)))

    gx, gy = cx0, cy0 + 22 + bob(t, 10, 0.4)
    for it in items:
        if it[0] < 0:
            draw_item(it)
    for it in items:
        d = it[5]
        if d > 0:
            c.line([(gx, gy), (it[2], it[3])], (200, 150, 255, int(60 * d)), 2)
    ghost_body(c, g, gx, gy, 1.25, t, "happy")
    R = 87.5
    arms(c, g, gx, gy, 1.25, left=(gx - 1.5 * R, gy - 0.15 * R + 12 * math.sin(t * 2)),
         right=(gx + 1.5 * R, gy - 0.15 * R + 12 * math.sin(t * 2 + 1)), t=t)


@lru_cache(maxsize=None)
def ide_static():
    sp = Spr(640, 430, SS)
    sp.rr(2, 2, 638, 428, 14, fill=(20, 18, 32), outline=(110, 84, 170), w=3)
    sp.rr(2, 2, 638, 34, 14, fill=(30, 26, 48))
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        sp.circ(24 + i * 20, 18, 6, fill=col)
    sp.text((320, 18), "mainframe-assistant  —  CUSTOMER.cbl", FR, 12, (170, 160, 200))
    sp.rr(2, 34, 92, 428, 0, fill=(24, 21, 40))
    for i, wdt in enumerate([54, 40, 62, 46, 58, 36, 50]):
        sp.rr(14, 52 + i * 26, 14 + wdt, 62 + i * 26, 4, fill=(70, 60, 110))
    sp.line([(318, 34), (318, 428)], (60, 50, 96), 2)
    return sp


def scene4(c, g, t):
    ox, oy = 570, 120
    ambient(c, g, t, 41)
    c.rr(ox + 250, oy + 430, ox + 390, oy + 480, 4, fill=(36, 30, 56))
    c.ell(ox + 180, oy + 466, ox + 460, oy + 496, fill=(36, 30, 56))
    c.paste_spr(ide_static(), ox + 320, oy + 215)
    g.rr(ox, oy, ox + 640, oy + 430, 14, outline=(110, 50, 220), w=6)
    rnd = random.Random(4)
    nl = int(t * 5)
    for i in range(14):
        if i >= nl:
            break
        indent = rnd.choice([0, 0, 18, 18, 36])
        x = ox + 108 + indent
        y = oy + 56 + i * 24
        for _ in range(rnd.randint(2, 4)):
            wd = rnd.randint(18, 54)
            col = rnd.choice([(255, 123, 114), (121, 192, 255), (210, 168, 255), (126, 231, 135), (255, 166, 87)])
            if x + wd < ox + 308:
                c.rr(x, y, x + wd, y + 9, 3, fill=(*col, 200))
            x += wd + 8
    # chat panel
    cx0 = ox + 326
    c.text((cx0 + 150, oy + 56), "AI Assistant", FB, 14, (205, 170, 255))
    c.line([(cx0 + 6, oy + 72), (cx0 + 296, oy + 72)], (80, 66, 130), 1)
    if t > 0.9:
        a = ease((t - 0.9) * 3)
        c.rr(cx0 + 60, oy + 86, cx0 + 296, oy + 130, 12, fill=(70, 56, 120, int(255 * a)))
        c.text((cx0 + 178, oy + 108), "Explain CUSTOMER-UPDATE", FR, 13.5, (240, 235, 255, int(255 * a)))
    if 1.7 < t < 2.3:
        for i in range(3):
            c.circ(cx0 + 24 + i * 14, oy + 166, 4, fill=(190, 150, 255, int(120 + 120 * math.sin(t * 9 - i))))
    if t > 2.3:
        full = ["It validates the record,", "updates the balance and", "logs the change."]
        shown = int((t - 2.3) * 24)
        c.rr(cx0 + 8, oy + 146, cx0 + 270, oy + 232, 12, fill=(100, 56, 200, 235))
        cnt = 0
        for i, ln in enumerate(full):
            part = ln[:max(0, shown - cnt)]
            cnt += len(ln)
            c.text((cx0 + 20, oy + 168 + i * 22), part, FR, 13.5, (250, 245, 255), "lm")
    # ghost, pointing
    gx, gy = 300, 410 + bob(t, 9)
    ghost_body(c, g, gx, gy, 1.25, t, "happy", look=(10, -2))
    R = 87.5
    pt = ease((t - 0.2) / 0.6)
    arms(c, g, gx, gy, 1.25, left=(gx - 1.4 * R, gy + 0.8 * R),
         right=(lerp(gx + 1.2 * R, ox - 40, pt), lerp(gy + 0.9 * R, gy - 0.2 * R, pt)), t=t)
    # data flow particles
    for i in range(46):
        life = (t * 0.3 + i * 0.0937) % 1
        sx = ox + 120 + (i * 97) % 500
        sy = oy + 60 + (i * 53) % 340
        x = sx + 60 * life * math.sin(i) + 40 * math.sin(life * 7 + i)
        y = sy - life * 430
        a = math.sin(math.pi * life)
        col = (190, 130, 255)
        c.circ(x, y, 2 + 3 * (i % 3) / 2, fill=(*col, int(230 * a)))
        g.circ(x, y, 3 + 2 * (i % 3), fill=tuple(int(q * 0.7 * a) for q in col))
    for k in range(3):
        pts = []
        for j in range(40):
            u = j / 39
            pts.append((ox + 140 + k * 170 + 40 * math.sin(u * 5 + t * 2 + k), oy - 10 - u * 110))
        g.line(pts, (80, 40, 160), 3)


def curve_pt(u):
    x = 150 + u * 960
    y = 548 - 320 * (0.12 * u + 0.88 * u ** 2.3) + 9 * math.sin(u * 16) * (1 - u * 0.5)
    return x, y


@lru_cache(maxsize=None)
def board_sprite():
    sp = Spr(190, 40, SS)
    sp.ell(4, 6, 186, 34, fill=(250, 248, 255))
    sp.ell(14, 14, 176, 28, fill=(168, 85, 247))
    sp.ell(4, 6, 186, 34, outline=(205, 170, 255), w=2)
    return sp


def scene5(c, g, t):
    ambient(c, g, t, 51, 22)
    p = ease(t / 3.4)
    if p > 0.003:
        n = max(2, int(p * 120))
        pts = [curve_pt(p * i / n) for i in range(n + 1)]
        c.poly(pts + [(pts[-1][0], 560), (pts[0][0], 560)], fill=(124, 58, 237, 48))
        g.line(pts, (170, 90, 255), 14)
        c.line(pts, (150, 80, 255), 12)
        c.line(pts, (225, 200, 255), 4)
        tip = pts[-1]
        prev = pts[-6] if len(pts) > 6 else pts[0]
        ang = math.atan2(tip[1] - prev[1], tip[0] - prev[0])
        ah = [(tip[0] + 34 * math.cos(ang), tip[1] + 34 * math.sin(ang)),
              (tip[0] + 14 * math.cos(ang + 2.4), tip[1] + 14 * math.sin(ang + 2.4)),
              (tip[0] + 14 * math.cos(ang - 2.4), tip[1] + 14 * math.sin(ang - 2.4))]
        # arrow head sits just ahead of the ghost, shown only once the line is done
        if p > 0.995:
            c.poly(ah, fill=(225, 200, 255))
            g.poly(ah, fill=(170, 90, 255))
        # ghost surfing at the tip
        u = p * 0.995
        px, py = curve_pt(u)
        qx, qy = curve_pt(max(0, u - 0.02))
        slope = math.degrees(math.atan2(py - qy, px - qx))
        wob = 2.5 * math.sin(t * 5)
        c.paste_spr(board_sprite(), px, py - 8, angle=-slope + wob)
        s = 0.85
        R = 70 * s
        gy = py - 8 - 13 - 1.3 * R - 6 + bob(t, 3, 1.3)
        ghost_body(c, g, px, gy, s, t, "happy", look=(8, 0))
        arms(c, g, px, gy, s, left=(px - 1.7 * R, gy + 0.2 * R + 10 * math.sin(t * 4)),
             right=(px + 1.7 * R, gy - 0.3 * R + 10 * math.sin(t * 4 + 2)), t=t)
        for k in range(6):
            tt = (t * 2 + k * 0.17) % 1
            sx = px - 40 - tt * 90
            sy = py + 8 + tt * 36
            c.circ(sx, sy, 3.5 * (1 - tt), fill=(215, 180, 255, int(220 * (1 - tt))))
            g.circ(sx, sy, 5 * (1 - tt), fill=(120, 60, 220))
    tags = [(0.3, "Efficiency"), (0.62, "Growth"), (0.96, "ROI")]
    for k, (thr, lab) in enumerate(tags):
        if p > thr:
            a = ease((p - thr) * 12)
            x, y = curve_pt(thr)
            w = 14 * len(lab) * 0.62 + 34
            off = 56
            c.line([(x, y + 8), (x + 10, y + off - 16)], (205, 170, 255, int(120 * a)), 2)
            c.rr(x + 10 - w / 2, y + off - 16, x + 10 + w / 2, y + off + 16, 16, fill=(40, 24, 80, int(235 * a)),
                 outline=(205, 170, 255, int(255 * a)), w=2)
            c.text((x + 10, y + off), lab, FB, 17, (240, 228, 255, int(255 * a)))


SH = 1.2


def shield_pts(cx, cy, s):
    pts = []
    for i in range(25):
        x = -1 + 2 * i / 24
        pts.append((cx + x * 120 * s, cy + (-1.0 - 0.08 * (1 - x * x)) * 130 * s))
    for i in range(1, 21):
        u = i / 20
        pts.append((cx + (1 - u) ** 0.75 * 120 * s, cy + (0.2 + 1.05 * u) * 130 * s))
    for i in range(1, 20):
        u = 1 - i / 20
        pts.append((cx - (1 - u) ** 0.75 * 120 * s, cy + (0.2 + 1.05 * u) * 130 * s))
    return pts


def shield_halfwidth(yn):
    if yn < 0.2:
        return 1.0
    return max(0.0, 1 - (yn - 0.2) / 1.05) ** 0.75


@lru_cache(maxsize=None)
def hex_sprite():
    sp = Spr(int(300 * SH), int(420 * SH), SS)
    for r in range(-1, 14):
        for q in range(-1, 9):
            x = q * 46 + (23 if r % 2 else 0)
            y = r * 40
            hp = [(x + 26 * math.cos(math.radians(60 * k + 30)), y + 26 * math.sin(math.radians(60 * k + 30))) for k in range(6)]
            sp.line(hp + [hp[0]], (215, 185, 255, 90), 1.5)
    mask = Image.new("L", sp.im.size, 0)
    pts = shield_pts(sp.w / 2, sp.h / 2 - 11 * SH, SH)
    ImageDraw.Draw(mask).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
    a = ImageChops.multiply(sp.im.getchannel("A"), mask)
    sp.im.putalpha(a)
    return sp


def scene6(c, g, t):
    ambient(c, g, t, 61)
    gx, gy = 800, 205 + bob(t, 8, 0.4)
    scx, scy = 800, 428 + bob(t, 8, 0.4)
    # incoming threats
    rnd = random.Random(6)
    for i in range(14):
        per = 2.1
        t0 = rnd.random() * per
        local = ((t - t0) % per)
        ang = rnd.uniform(-2.6, -0.5) if i % 2 else rnd.uniform(-0.2, 0.2) + math.pi * (i % 3 == 0)
        sx = 800 + rnd.uniform(-700, 440)
        sy = rnd.choice([40, 90, 150])
        if i % 4 == 0:
            sx, sy = rnd.choice([30, 1250]), rnd.uniform(200, 500)
        tx = scx + rnd.uniform(-120, 120)
        ty = scy + rnd.uniform(-90, 130)
        dur = 1.2
        if local < dur:
            u = local / dur
            x, y = lerp(sx, tx, u), lerp(sy, ty, u)
            c.text((x, y), rnd.choice(["01", "10", "!!", "0xF"]), FM, 20, (255, 120, 130, int(235 * u + 20)))
            g.circ(x, y, 7, fill=(100, 20, 30))
        elif local < dur + 0.3:
            u = (local - dur) / 0.3
            for k in range(6):
                a = k * math.pi / 3
                c.circ(tx + 34 * u * math.cos(a), ty + 34 * u * math.sin(a), 2.5 * (1 - u), fill=(255, 200, 230, int(255 * (1 - u))))
            g.circ(tx, ty, 26 * (1 - u), fill=(120, 40, 160))
    ghost_body(c, g, gx, gy, 1.15, t, "happy")
    pulse = 0.5 + 0.5 * math.sin(t * 3)
    pts = shield_pts(scx, scy, SH)
    c.poly(pts, fill=(110, 52, 215, 120))
    g.poly(pts, fill=(int(14 + 12 * pulse), int(6 + 5 * pulse), int(36 + 20 * pulse)))
    inner = shield_pts(scx, scy + 4, SH * 0.9)
    c.line(inner + [inner[0]], (205, 170, 255, 110), 2)
    c.paste_spr(hex_sprite(), scx, scy + 11 * SH)
    c.line(pts + [pts[0]], (225, 200, 255), 6)
    g.line(pts + [pts[0]], (150, 80, 255), 9)
    # scan band
    sy_ = scy - 140 * SH + ((t * 0.7) % 1) * 330 * SH
    yn = (sy_ - scy) / (130 * SH)
    hw = shield_halfwidth(yn) * 120 * SH
    if hw > 5 and -1.1 < yn < 1.2:
        c.line([(scx - hw, sy_), (scx + hw, sy_)], (240, 225, 255, 120), 3)
    # padlock
    q = ease((t - 1.3) / 0.3)
    lift = 20 * (1 - q)
    lx, ly = scx, scy + 26
    c.rr(lx - 38, ly - 12, lx + 38, ly + 52, 9, fill=(236, 226, 255), outline=(255, 255, 255), w=2)
    c.circ(lx, ly + 15, 8, fill=(88, 48, 170))
    c.rr(lx - 3.5, ly + 17, lx + 3.5, ly + 38, 3, fill=(88, 48, 170))
    c.arc(lx - 24, ly - 56 - lift, lx + 24, ly - 8 - lift, 180, 360, (236, 226, 255), 10)
    c.line([(lx - 24, ly - 32 - lift), (lx - 24, ly - 12)], (236, 226, 255), 10)
    c.line([(lx + 24, ly - 32 - lift), (lx + 24, ly - 12 - (0 if q >= 1 else lift))], (236, 226, 255), 10)
    g.rr(lx - 38, ly - 56 - lift, lx + 38, ly + 52, 12, fill=(120, 70, 220))
    if 1.55 < t < 2.3:
        u = (t - 1.55) / 0.75
        c.circ(lx, ly + 10, 40 + 260 * u, outline=(225, 200, 255, int(220 * (1 - u))), w=4)
        g.circ(lx, ly + 10, 40 + 260 * u, outline=(120, 70, 220), w=8)
    R = 80.5
    arms(c, g, gx, gy, 1.15, left=(scx - 128 * SH, scy - 70), right=(scx + 128 * SH, scy - 70), t=t)


@lru_cache(maxsize=None)
def dev_sprite(thumb):
    sp = Spr(300, 340, SS)
    col = (10, 5, 24, 255)
    sp.circ(130, 96, 40, fill=col)
    sp.rr(112, 120, 148, 160, 8, fill=col)
    sp.poly([(40, 330), (52, 190), (90, 160), (170, 160), (208, 190), (220, 330)], fill=col)
    sp.line([(52, 196), (44, 280)], col, 28)
    if thumb:
        sp.line([(206, 196), (246, 170), (250, 118)], col, 28)
        sp.circ(250, 104, 20, fill=col)
        sp.rr(242, 58, 260, 98, 8, fill=col)
    else:
        sp.line([(206, 196), (214, 280)], col, 28)
    im = sp.im.filter(ImageFilter.GaussianBlur(5.5 * SS))
    sp.im = im
    return sp


@lru_cache(maxsize=None)
def rack_big():
    sp = Spr(280, 540, SS)
    sp.rr(4, 4, 276, 536, 10, fill=(26, 20, 46), outline=(110, 84, 180), w=4)
    for j in range(10):
        y = 16 + j * 51
        sp.rr(16, y, 264, y + 43, 5, fill=(36, 28, 64), outline=(72, 56, 124), w=2)
        for v in range(4):
            sp.line([(30, y + 11 + v * 7), (150, y + 11 + v * 7)], (60, 46, 104), 2)
    return sp


def bez(p0, p1, p2, u):
    return ((1 - u) ** 2 * p0[0] + 2 * u * (1 - u) * p1[0] + u * u * p2[0],
            (1 - u) ** 2 * p0[1] + 2 * u * (1 - u) * p1[1] + u * u * p2[1])


def scene7(c, g, t):
    # blurred developer silhouette in the background
    halo = Spr(520, 420, SS)
    halo.ell(60, 40, 460, 380, fill=(150, 96, 255, 150))
    halo.im = halo.im.filter(ImageFilter.GaussianBlur(40 * SS))
    c.paste_spr(halo, 235, 400)
    c.paste_spr(dev_sprite(t > 2.8), 235, 430, scale=1.2)
    ambient(c, g, t, 71, 26)
    rx, ry = 780, 100
    c.paste_spr(rack_big(), rx + 140, ry + 270)
    P = (rx + 12, ry + 255)
    conn = clamp((t - 2.25) / 0.01) >= 1
    for j in range(10):
        for v in range(3):
            lit = conn and t > 2.4 + j * 0.12
            on = lit and math.sin(t * (3 + v) + j) > -0.5
            col = [(190, 120, 255), (110, 235, 255), (150, 255, 170)][v]
            x, y = rx + 232 + v * 11 - 8, ry + 16 + j * 51 + 22
            if on:
                c.circ(x, y, 3.6, fill=(*col, 255))
                g.circ(x, y, 5, fill=col)
            else:
                c.circ(x, y, 3.2, fill=(52, 44, 80))
    c.rr(rx - 4, ry + 232, rx + 40, ry + 280, 6, fill=(12, 8, 24), outline=(150, 120, 220), w=2)
    u = ease((t - 0.9) / 1.35)
    gxp = lerp(380, 640, u)
    gy = 410 + bob(t, 8, 0.45) * (1 - u)
    s = 1.2
    R = 84
    rest = (gxp + 1.35 * R, gy + 0.35 * R)
    plug = (lerp(rest[0], P[0] - 6, u), lerp(rest[1], P[1], u))
    # cable
    p0 = (-30, 640)
    ctrl = ((p0[0] + plug[0]) / 2, 735)
    pts = [bez(p0, ctrl, plug, i / 60) for i in range(61)]
    g.line(pts, (150, 70, 255), 14)
    c.line(pts, (118, 54, 225), 10)
    c.line(pts, (210, 170, 255), 4)
    if t > 2.25:
        for i in range(7):
            uu = (t * 0.7 + i / 7) % 1
            bx, by = bez(p0, ctrl, plug, uu)
            c.circ(bx, by, 4, fill=(255, 255, 255, 235))
            g.circ(bx, by, 6, fill=(150, 90, 255))
    c.rr(plug[0] - 40, plug[1] - 12, plug[0] - 2, plug[1] + 12, 4, fill=(190, 190, 210), outline=(110, 110, 140), w=2)
    c.rr(plug[0] - 2, plug[1] - 7, plug[0] + 8, plug[1] + 7, 2, fill=(240, 200, 90))
    ghost_body(c, g, gxp, gy, s, t, "happy", wink=t > 2.45, look=(10, 0))
    arms(c, g, gxp, gy, s, left=(gxp - 1.3 * R, gy + 0.2 * R + 10 * math.sin(t * 3)), right=plug, t=t)
    if 2.25 < t < 2.9:
        v = (t - 2.25) / 0.65
        c.circ(P[0], P[1], 18 + 80 * v, outline=(235, 215, 255, int(240 * (1 - v))), w=4)
        g.circ(P[0], P[1], 18 + 80 * v, fill=(120, 70, 220) if v < 0.5 else (0, 0, 0), outline=(170, 110, 255), w=8)
        for k in range(8):
            a = k * math.pi / 4
            sparkle(c, g, P[0] + 70 * v * math.cos(a), P[1] + 70 * v * math.sin(a), 6 * (1 - v), (255, 240, 180), int(255 * (1 - v)))
    if t > 2.8:
        pop = back((t - 2.8) / 0.4)
        sparkle(c, g, 372, 322, 14 * pop, LAV, 230)


def check(c, g, x, y, prog, col=GREEN, w=7):
    pts = [(x - 17, y + 2), (x - 5, y + 14), (x + 19, y - 14)]
    seg = []
    total = 0
    lens = [math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])]
    tot = sum(lens)
    d = prog * tot
    seg.append(pts[0])
    if d <= lens[0]:
        f = d / lens[0]
        seg.append((lerp(pts[0][0], pts[1][0], f), lerp(pts[0][1], pts[1][1], f)))
    else:
        seg.append(pts[1])
        f = (d - lens[0]) / lens[1]
        seg.append((lerp(pts[1][0], pts[2][0], f), lerp(pts[1][1], pts[2][1], f)))
    c.line(seg, col, w)
    g.line(seg, col, w + 4)


def scene8(c, g, t):
    ambient(c, g, t, 81, 28)
    gx, gy = 470, 408 + bob(t, 8)
    s = 1.25
    R = 87.5
    sway = 1.8 * math.sin(t * 1.3)
    bx, by = 800, 380 + bob(t, 6, 0.45, 1)
    bw, bh = 300, 410
    sp = Spr(bw, bh, SS)
    sp.rr(0, 14, bw, bh, 18, fill=(22, 16, 42), outline=(190, 140, 255), w=5)
    sp.rr(16, 46, bw - 16, bh - 16, 8, fill=(36, 28, 66))
    sp.rr(bw / 2 - 52, 0, bw / 2 + 52, 36, 10, fill=(190, 188, 210), outline=(240, 238, 255), w=2)
    sp.text((bw / 2, 66), "KPIs", FB, 18, (225, 205, 255))
    rows = 4
    marks = []
    for i in range(rows):
        y = 112 + i * 72
        sp.rr(28, y - 22, 80, y + 22, 8, outline=(150, 110, 220), w=3)
        sp.rr(96, y - 14, 96 + [150, 120, 160, 130][i], y - 4, 5, fill=(130, 110, 190))
        sp.rr(96, y + 6, 258, y + 14, 4, fill=(54, 44, 94))
        prog = ease((t - (0.9 + i * 0.65)) / 0.45)
        if prog > 0:
            sp.rr(96, y + 6, 96 + 162 * prog, y + 14, 4, fill=(*GREEN, 255))
        marks.append((54, y, prog))
    # checks drawn into the sprite and glow
    for (mx, my, prog) in marks:
        if prog > 0:
            check(sp, Cv(1, 1, 1), mx, my, ease(prog * 1.2 - 0.0))
            check(g, g, bx - bw / 2 + mx, by - bh / 2 + my, prog)
    g.rr(bx - bw / 2, by - bh / 2 + 14, bx + bw / 2, by + bh / 2, 18, outline=(110, 60, 220), w=7)
    ghost_body(c, g, gx, gy, s, t, "proud")
    c.paste_spr(sp, bx, by, angle=sway)
    celebrate = t > 3.4
    left = (gx - 1.3 * R, gy - 0.1 * R) if not celebrate else (gx - 1.25 * R, gy - 0.9 * R + 12 * math.sin(t * 8))
    arms(c, g, gx, gy, s, left=left, right=(bx - bw / 2 + 4, by + 30), t=t)
    for i in range(4):
        done = 0.9 + i * 0.65 + 0.45
        tt = t - done
        if 0 < tt < 0.7:
            u = tt / 0.7
            mx, my = bx - bw / 2 + 54, by - bh / 2 + 112 + i * 72
            for k in range(7):
                a = k * 2 * math.pi / 7
                sparkle(c, g, mx + 120 * u * math.cos(a) * 0.7 + 60 * u, my + 70 * u * math.sin(a), 6 * (1 - u), GREEN, int(255 * (1 - u)))
    if celebrate:
        rnd = random.Random(8)
        for k in range(26):
            x = 150 + rnd.random() * 980
            y0 = rnd.random() * 300
            y = (y0 + (t - 3.4) * rnd.uniform(60, 150)) % 720 if t - 3.4 > 0 else -50
            col = rnd.choice([GREEN, LAV, (255, 220, 120)])
            c.rr(x - 4, y - 7, x + 4, y + 7, 2, fill=(*col, 220))


SCENES = [scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8]
TITLES = [
    ("Intro", "The “Vote for Me” sign"),
    ("The Problem", "Frustration with green screens"),
    ("Target Audience", "Holographic transparent icons"),
    ("The Vision", "Modern IDE & chat"),
    ("Business Value", "ROI & efficiency"),
    ("Tech Solution & Security", "The shield — safe Mainframe access"),
    ("Minimal Pilot", "Connecting cables + wink"),
    ("Success Metrics", "KPIs on the clipboard"),
]


def wrap_rtl(text, size, maxw):
    f = F(FB, size)
    lines, cur = [], ""
    for w in text.split(" "):
        trial = (cur + " " + w).strip()
        if cur and f.getlength(trial, direction="rtl", language="he") > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    return lines


def caption(c, si, t):
    sl = TL["slides"][si]
    cur = None
    for it in sl["sentences"]:
        if it["t0"] - 0.05 <= t:
            cur = it
    if cur is None or t > cur["t1"] + 0.7:
        return
    a = ease((t - cur["t0"] + 0.05) / 0.25) * (1 - ease((t - cur["t1"] - 0.3) / 0.4))
    if a <= 0.01:
        return
    size = 29
    lines = wrap_rtl(cur["caption"], size, 960)
    hbox = 26 + len(lines) * 40
    y1 = 664
    c.rr(130, y1 - hbox, 1150, y1, 18, fill=(10, 6, 28, int(205 * a)), outline=(168, 85, 247, int(170 * a)), w=2)
    for i, ln in enumerate(lines):
        y = y1 - hbox + 13 + 20 + i * 40
        c.d.text((640 * c.k, y * c.k), ln, font=F(FB, size * c.k), fill=(255, 255, 255, int(255 * a)),
                 anchor="mm", direction="rtl", language="he")


def overlay(c, si, t):
    a = ease((t - 0.15) / 0.5)
    off = (1 - ease((t - 0.15) / 0.6)) * -50
    ttl, sub = TITLES[si]
    x = 56 + off
    c.rr(x, 44, x + 118, 74, 15, fill=(124, 58, 237, int(235 * a)))
    c.text((x + 59, 59), "SLIDE %d / %d" % (si + 1, N), FB, 13.5, (255, 255, 255, int(255 * a)))
    c.text((x, 112), ttl, FB, 42, (255, 255, 255, int(255 * a)), "lm")
    c.text((x, 152), sub, FR, 22, (205, 170, 255, int(235 * a)), "lm")
    for i in range(N):
        cx = W / 2 + (i - (N - 1) / 2) * 24
        c.circ(cx, H - 22, 4 if i != si else 6, fill=(205, 170, 255, 255 if i == si else 90))
    caption(c, si, t)


def locate(T):
    for si, sl in enumerate(TL["slides"]):
        if T < sl["start"] + sl["dur"] or si == N - 1:
            return si, T - sl["start"]


def render_frame(fi):
    T = fi / FPS
    si, t = locate(T)
    dur = TL["slides"][si]["dur"]
    ts = clamp(4.2 / dur, 0.45, 1.0)  # slow the animation down to match the longer voice-over
    c = Cv(W, H, SS, bg(si).copy())
    g = Cv(W, H, 0.5)
    SCENES[si](c, g, t * ts)
    c.add_glow(g)
    overlay(c, si, t)
    im = c.im.reduce(SS)
    a = min(1.0, t / 0.35, (dur - t) / 0.35)
    if a < 1:
        im = Image.blend(Image.new("RGB", im.size, (0, 0, 0)), im, clamp(a))
    return im.tobytes()


# ------------------------------------------------------------------- audio
def make_audio(path):
    sr = 44100
    total = TL["total"]
    n = int(total * sr) + sr
    x = np.arange(n) / sr
    music = np.zeros(n)
    chords = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (261.6, 329.6, 392.0), (196.0, 246.9, 293.7)]
    for si, sl in enumerate(TL["slides"]):
        ch = chords[si % 4]
        i0, i1 = int(sl["start"] * sr), int((sl["start"] + sl["dur"]) * sr)
        tt = x[i0:i1] - sl["start"]
        env = np.minimum(1, tt / 0.8) * np.minimum(1, (sl["dur"] - tt) / 0.8)
        seg = np.zeros(i1 - i0)
        for f in ch:
            for det in (0.997, 1.0, 1.003):
                seg += np.sin(2 * np.pi * f * det * tt + 0.3 * np.sin(2 * np.pi * 0.2 * tt))
            seg += 0.4 * np.sin(2 * np.pi * f * 2 * tt)
        seg *= env * 0.03
        notes = [ch[2] * 2, ch[1] * 2, ch[2] * 2, ch[0] * 4]
        for k in range(int(sl["dur"] / 1.5)):
            t0 = 0.35 + k * 1.5
            m = tt > t0
            pl = np.zeros_like(tt)
            pl[m] = np.sin(2 * np.pi * notes[k % 4] * (tt[m] - t0)) * np.exp(-(tt[m] - t0) * 3.0)
            seg += pl * 0.035 * env
        music[i0:i1] += seg
    voice = np.zeros(n)
    for sl in TL["slides"]:
        for it in sl["sentences"]:
            with wave.open(it["wav"]) as w:
                raw = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768
                r = w.getframerate()
            up = np.interp(np.arange(int(len(raw) * sr / r)) / sr * r, np.arange(len(raw)), raw)
            i0 = int((sl["start"] + it["t0"]) * sr)
            voice[i0:i0 + len(up)] += up
    peak = max(1e-6, np.abs(voice).max())
    out = np.tanh(music * 1.4) * 0.5 + voice / peak * 0.85
    out = out[: int(total * sr)]
    st = np.stack([out, out], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype("<i2").tobytes())


def main():
    load_timeline()
    if len(sys.argv) >= 3 and sys.argv[1] == "--stills":
        d = sys.argv[2]
        os.makedirs(d, exist_ok=True)
        times = [float(a) for a in sys.argv[3:]] or [3.0]
        for si, sl in enumerate(TL["slides"]):
            for tl in times:
                fi = int((sl["start"] + tl) * FPS)
                Image.frombytes("RGB", (W, H), render_frame(fi)).save("%s/s%d_%.1f.png" % (d, si + 1, tl))
        return
    out = sys.argv[1] if len(sys.argv) > 1 else "vote_for_ghost.mp4"
    wav = out + ".wav"
    make_audio(wav)
    nf = int(TL["total"] * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, fr in enumerate(pool.imap(render_frame, range(nf), chunksize=4)):
            ff.stdin.write(fr)
            if i % 60 == 0:
                print("frame %d/%d" % (i, nf), flush=True)
    ff.stdin.close()
    ff.wait()
    os.remove(wav)


if __name__ == "__main__":
    main()
