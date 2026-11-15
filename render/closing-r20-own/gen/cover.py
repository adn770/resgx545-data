#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen/cover.py: the macrotiles a 1024x768 triangle covers on the 4 x 4 grid (256 x 192 each),
numbered down then across (column-major, E627), by two rules that must agree for a move to be
used: pixel centres inside the triangle (edges inclusive), and the conservative test (a 32 x 16
tile touched by the triangle, its closed rectangle meeting the closed triangle). The default
triangle is libsgxfive's sgxfive_tri_default (render.c at ec50498: (8,8), (56,20), (20,56) of 64,
scaled), so the default cover is E1087's {0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 13}.

  cover.py [DX,DY ...]   print each move's two covers"""
import sys

W, H, MW, MH, TW, TH = 1024, 768, 256, 192, 32, 16


def default(w=W, h=H):
    return [(8 * w // 64, 8 * h // 64), (56 * w // 64, 20 * h // 64), (20 * w // 64, 56 * h // 64)]


def moved(dx, dy):
    return [(x + dx, y + dy) for x, y in default()]


def _edge(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def inside(v, p):
    d = [_edge(v[i], v[(i + 1) % 3], p) for i in range(3)]
    return all(x >= 0 for x in d) or all(x <= 0 for x in d)


def mt(x, y):
    return (x // MW) * (H // MH) + y // MH


def cover_pixels(v):
    xs, ys = [p[0] for p in v], [p[1] for p in v]
    out = set()
    for y in range(max(0, min(ys) - 1), min(H, max(ys) + 1)):
        for x in range(max(0, min(xs) - 1), min(W, max(xs) + 1)):
            if inside(v, (x + 0.5, y + 0.5)):
                out.add(mt(x, y))
    return out


def _seg_rect(a, b, r):
    """the closed segment ab meets the closed rectangle r (x0, y0, x1, y1)"""
    x0, y0, x1, y1 = r
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    return t0 <= t1


def cover_tiles(v):
    out = set()
    for ty in range(H // TH):
        for tx in range(W // TW):
            r = (tx * TW, ty * TH, (tx + 1) * TW, (ty + 1) * TH)
            hit = any(r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3] for p in v) or \
                any(inside(v, c) for c in ((r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3]))) or \
                any(_seg_rect(v[i], v[(i + 1) % 3], r) for i in range(3))
            if hit:
                out.add(mt(tx * TW, ty * TH))
    return out


def cover(dx, dy):
    """the move's cover when both rules agree, else None"""
    v = moved(dx, dy)
    a, b = cover_pixels(v), cover_tiles(v)
    return sorted(a) if a == b else None


if __name__ == "__main__":
    for m in sys.argv[1:] or ["0,0"]:
        dx, dy = (int(x) for x in m.split(","))
        v = moved(dx, dy)
        print(m, v, sorted(cover_pixels(v)), sorted(cover_tiles(v)))
