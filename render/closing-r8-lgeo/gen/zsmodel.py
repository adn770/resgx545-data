# SPDX-License-Identifier: MIT
"""zsmodel.py: r8-lgeo's Q260 model, standard library only (no numpy: the scorer, the fake laptop
and the generator import it under any python3 >= 3.10).

Coverage: E606's rule as r7-geo's gen/model1140.py states it (vertices on the 1/256 grid, every
pixel centre tested exactly in integers: inside iff every edge function is > 0, or == 0 on an
edge that owns it, an edge owning a sample on it iff dy < 0, or dy == 0 and dx > 0, after the
vertices are put in one winding), computed row by row as the interval each edge allows (the
triangle is convex), so a 512 x 256 image takes milliseconds. tests/test_zsmodel.py checks it
against r7-geo's frozen covered_sha of every zs row (HU and HA), which model1140 made.

Rounding of a vertex coordinate n in 1/4096 pixel to 1/256 (g = 16), E914's names:
  HU  floor((n + 8) / 16)                       half up (E607, E681 at x >= 0)
  HA  HU for n >= 0, floor((n + 7) / 16) for n < 0   half away from zero (E914: five sweeps)

Sweeps (E914's construction, r7-geo gen/models.py sweep_case, generalised): vertex A's swept
coordinate is p * 4096 + 8 + d (d in 1/4096 pixel from the 1/512 tie above the grid point p), its
other coordinate the centre of pixel 40; the edge A-B is aimed through the pixel centre C (index c
on the swept axis, `off` pixels from A on the other axis), B = C + 2 (C - A_tie) on the ray beyond
C; the third vertex T is 40 pixels beyond B on the swept axis, level with A. A transposed sweep
swaps x and y of every vertex (the same scene on the transposed target)."""
from __future__ import annotations

import hashlib

GREEN, BG = 0xFF00FF00, 0xFF203040
BAND_PX = 6.4e-4          # E914's band: the misses lay within 6.4e-4 pixel of an edge line
LONG_PX = 250.0           # ... of an edge at least this long (E914: 258 to 313 pixels)


def rnd(n, variant):
    n = int(n)
    if variant == "HU":
        return (n + 8) // 16
    if variant == "HA":
        return (n + 8) // 16 if n >= 0 else (n + 7) // 16
    raise ValueError(variant)


def _floordiv(a, b):
    return a // b


def _ceildiv(a, b):
    return -((-a) // b)


def spans(v256, w, h):
    """[(x0, x1)] per row y (x0 <= x < x1 covered; x1 <= x0 none) of the triangle with vertices on
    the 1/256 grid (six integers), E606's exact test."""
    a, b, c = (v256[0], v256[1]), (v256[2], v256[3]), (v256[4], v256[5])
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    out = [(0, 0)] * h
    if area == 0:
        return out
    if area < 0:
        b, c = c, b
    one, half = 256, 128
    edges = []
    for p, q in ((a, b), (b, c), (c, a)):
        dx, dy = q[0] - p[0], q[1] - p[1]
        edges.append((p[0], p[1], dx, dy, dy < 0 or (dy == 0 and dx > 0)))
    for y in range(h):
        sy = y * one + half
        lo, hi = 0, w
        for px, py, dx, dy, own in edges:
            # e(x) = dx (sy - py) - dy (X - px), X = x * 256 + 128; e = K - m x, m = dy * 256
            k = dx * (sy - py) - dy * (half - px)
            m = dy * one
            if m == 0:
                if not (k > 0 or (k == 0 and own)):
                    lo, hi = 0, 0
                continue
            if m < 0:           # e = k + |m| x grows with x: x > -k/|m| (>= when owned)
                mm = -m
                lo = max(lo, _ceildiv(-k, mm) if own else _floordiv(-k, mm) + 1)
            else:               # e = k - m x falls with x: x < k/m (<= when owned)
                hi = min(hi, _floordiv(k, m) + 1 if own else _ceildiv(k, m))
        out[y] = (lo, hi) if hi > lo else (0, 0)
    return out


def cover4096(v4096, w, h, variant):
    return spans([rnd(n, variant) for n in v4096], w, h)


def covered(sp, x, y):
    lo, hi = sp[y]
    return lo <= x < hi


def cov_bytes(sp, w):
    out = bytearray()
    for lo, hi in sp:
        row = bytearray(w)
        for x in range(max(lo, 0), min(hi, w)):
            row[x] = 1
        out += row
    return bytes(out)


def cov_sha(sp, w):
    """sha256 of the covered image, one byte a pixel (1 covered), row after row: r7-geo's cov_sha."""
    return hashlib.sha256(cov_bytes(sp, w)).hexdigest()


def count(sp):
    return sum(max(0, hi - lo) for lo, hi in sp)


def spans_text(sp):
    """The frozen form of an image: one line a row, `y lo hi` for a covered row only."""
    return "".join("%d %d %d\n" % (y, lo, hi) for y, (lo, hi) in enumerate(sp) if hi > lo)


def spans_parse(text, h):
    sp = [(0, 0)] * h
    for ln in text.splitlines():
        if ln.strip():
            y, lo, hi = (int(t) for t in ln.split())
            sp[y] = (lo, hi)
    return sp


def fnv_image(sp, w):
    """The tool's target hash: FNV-1a 64 over the colour image's bytes (0xff00ff00 covered,
    0xff203040 not), little endian, row after row (r7-geo models.fnv)."""
    v, mask = 0xCBF29CE484222325, 0xFFFFFFFFFFFFFFFF
    g, b = GREEN.to_bytes(4, "little"), BG.to_bytes(4, "little")
    for lo, hi in sp:
        for x in range(w):
            for byte in (g if lo <= x < hi else b):
                v = ((v ^ byte) * 0x100000001B3) & mask
    return v


# ---- sweeps ------------------------------------------------------------------------------------
def sweep(p, axis, d, c, off, transpose=False):
    """Six coordinates (1/4096) of one step: p the grid point (pixels, on the 1/256 grid), axis
    'x' or 'y' (the swept axis of the scene before any transpose), d the step from the tie, c the
    aimed centre's pixel index on the swept axis, off the centre's offset on the other axis."""
    g = int(round(p * 4096))
    assert g % 16 == 0, p
    tie, at = g + 8, g + 8 + d
    c_main, other = c * 4096 + 2048, 40 * 4096 + 2048
    c_other = other + off * 4096
    b_main, b_other = c_main + 2 * (c_main - tie), c_other + 2 * (c_other - other)
    t_main = b_main + (40 if b_main >= c_main else -40) * 4096
    if axis == "x":
        v = [at, other, b_main, b_other, t_main, other]
    else:
        v = [other, at, b_other, b_main, other, t_main]
    if transpose:
        v = [v[1], v[0], v[3], v[2], v[5], v[4]]
    return v


def aimed_pixel(axis, c, off, transpose=False):
    """(x, y) of the aimed centre C's pixel in the target."""
    main, oth = c, 40 + off
    x, y = (main, oth) if axis == "x" else (oth, main)
    return (y, x) if transpose else (x, y)


def tri_args(w, h, v):
    return ("tri --keep-overflow --wait-ms 20000 --width %d --height %d --tri-unit 12 --tri-v %s --pixels"
            % (w, h, ",".join(map(str, v))))


# ---- E914's band -------------------------------------------------------------------------------
def edges_px(v4096, variant):
    """[(ax, ay, bx, by, length)] of the triangle's three edges in pixels, vertices rounded."""
    r = [rnd(n, variant) / 256.0 for n in v4096]
    pts = [(r[0], r[1]), (r[2], r[3]), (r[4], r[5])]
    out = []
    for i in range(3):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % 3]
        out.append((ax, ay, bx, by, ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5))
    return out


def nearest_edge(v4096, variant, x, y):
    """(distance in pixels from pixel (x, y)'s centre to the nearest edge line, that edge's
    length): fold/zs_read.py's distance, on the frozen rounding's vertices."""
    best = None
    for ax, ay, bx, by, ln in edges_px(v4096, variant):
        dist = abs((bx - ax) * (y + 0.5 - ay) - (by - ay) * (x + 0.5 - ax)) / ln
        if best is None or dist < best[0]:
            best = (dist, ln)
    return best


def longest_edge(v4096, variant):
    return max(e[4] for e in edges_px(v4096, variant))


def diff_pixels(sp_a, sp_b, w):
    """[(x, y)] where two span images differ."""
    out = []
    for y, ((a0, a1), (b0, b1)) in enumerate(zip(sp_a, sp_b)):
        if (a0, a1) == (b0, b1):
            continue
        for x in range(w):
            if (a0 <= x < a1) != (b0 <= x < b1):
                out.append((x, y))
    return out


def in_band(v4096, variant, px):
    """Whether every pixel of px lies within BAND_PX of an edge line at least LONG_PX long."""
    for x, y in px:
        dist, ln = nearest_edge(v4096, variant, x, y)
        if not (dist <= BAND_PX and ln >= LONG_PX):
            return False
    return True
