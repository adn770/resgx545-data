# SPDX-License-Identifier: MIT
"""hu1.py: HU1, the page need U of a scene of the tool's default triangle (E773: sgx-pipe's TA model, 128 bytes a stream, a page per
macrotile that has streams, plus 1 global page; 15 of 15 held out).  Copied unchanged from closing2/r1-pixgeo/gen/r1models.py (the
model R1-pixgeo froze for E773), the HU1 part only.  Pure functions."""
from __future__ import annotations

import math


def tiling(w, h):
    tx, ty = -(-w // 32), -(-h // 16)
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = ((-(-tx // n)) + 3) & ~3, ((-(-ty // n)) + 3) & ~3
    return tx, ty, n, mx, my


def tile_lists(t, x0, y0):
    x1, y1 = x0 + 16.0, y0 + 16.0
    xs = [p[0] for p in t]
    ys = [p[1] for p in t]
    if max(xs) < x0 or max(ys) < y0 or min(xs) >= x1 or min(ys) >= y1:
        return False
    for i in range(3):
        a, b, c = t[i], t[(i + 1) % 3], t[(i + 2) % 3]
        nx, ny = b[1] - a[1], a[0] - b[0]
        side = nx * (c[0] - a[0]) + ny * (c[1] - a[1])
        if all((nx * (x - a[0]) + ny * (y - a[1])) * side < 0 for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))):
            return False
    return True


def default_tri(w, h, dx=0, dy=0):
    return [(8 * w / 64 + dx, 8 * h / 64 + dy), (56 * w / 64 + dx, 20 * h / 64 + dy),
            (20 * w / 64 + dx, 56 * h / 64 + dy)]


def streams(w, h, tris):
    """streams per macrotile (index m = column * n + row as ta.rs), a region counted once however many triangles."""
    tx, ty, n, mx, my = tiling(w, h)
    per = {}
    for m in range(n * n):
        k = 0
        for i in range(mx * my):
            c, r = (m // n) * mx + i % mx, (m % n) * my + i // mx
            if 32 * c >= w or 16 * r >= h:
                continue
            x0, y0 = 32.0 * c, 16.0 * r
            if any(tile_lists(t, x0, y0) or tile_lists(t, x0 + 16, y0) for t in tris):
                k += 1
        if k:
            per[m] = k
    return per


def hu1(w, h, tris, G=1, bps=128):
    """(U, streams per macrotile): sum of ceil(streams * bps / 4096) + G."""
    per = streams(w, h, tris)
    return sum(math.ceil(k * bps / 4096) for k in per.values()) + G, per


def moved(w, h, dx, dy):
    """The scene of `tri -n 1 --move 1:DX,DY` (E773's s275 = 4096x4096 moved (1024, 0)): the default triangle moved."""
    return [default_tri(w, h, dx, dy)]
