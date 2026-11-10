"""The offline models whose predictions R1 freezes (all pure functions, no I/O).

  HU1  page need U of a scene (closing2/geometry/u_model.py: sgx-pipe's TA model, 128 B a stream, a page per
       macrotile that has streams, + 1 global page); HU2 = macrotiles with streams + 8
  SH   Sutherland-Hodgman clip of the three input edges A->B, B->C, C->A against z <= w and z >= -w, the strip
       zigzag order, the prim-list words (index | edge flag << 4), depth = 0.5 + 0.5 z/w
  RZ/RN reciprocal words of a float32 (the clamp ladder)
Every number a model gives here was derived from data measured BEFORE this file (a FIT: closing2/geometry
round 2); the frozen predictions are what the new runs hold out.  Tests check each model against the dumps of
S1 and S1b (tests/test_models.py).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import math  # noqa: E402
import struct  # noqa: E402
from fractions import Fraction  # noqa: E402


# ------------------------------------------------------------------------------------------------ HU1 / HU2
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


def hu2(w, h, tris, c=8):
    return len(streams(w, h, tris)) + c


def scene(w, h, moves):
    """base triangle at (0,0) plus one moved triangle a move (the tool's render k + 2 is moves[k])."""
    return [default_tri(w, h)] + [default_tri(w, h, dx, dy) for dx, dy in moves]


# ------------------------------------------------------------------------------------------------ clipping
CLIP = [(-0.75, -0.75), (0.75, -0.375), (-0.375, 0.75)]           # the three vertices' clip x, y (w = 1)


def sh_clip(poly, inside, cross):
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ia, ib = inside(a), inside(b)
        if ia and ib:
            out.append(b)
        elif ia and not ib:
            out.append(cross(a, b))
        elif not ia and ib:
            out.append(cross(a, b))
            out.append(b)
    return out


def zigzag(n):
    """strip order of a convex polygon p0..p(n-1): p1, p2, p0, p3, p(n-1), p4, p(n-2), ..."""
    order = [1, 2, 0]
    lo, hi, turn = 3, n - 1, 0
    while lo <= hi:
        if turn % 2 == 0:
            order.append(lo)
            lo += 1
        else:
            order.append(hi)
            hi -= 1
        turn += 1
    return order[:n]


def strip_tris(n):
    return [(i, i + 1, i + 2) if i % 2 == 0 else (i + 1, i, i + 2) for i in range(n - 2)]


def predict_zclip(A, B, axis="x", plane_order=("+w", "-w")):
    """Predicted object of the vertex program z = A u + B (u = clip x for axis x, clip y for axis y), w = 1,
    x, y unscaled: dict(xy=[(px, py)], depth=[float], prims=[(a, b, c)]), vertices in STORED order.
    Exact arithmetic (Fractions); window = 32 + 32 clip; depth = 0.5 + 0.5 z."""
    A, B = Fraction(A), Fraction(B)
    iu = 0 if axis == "x" else 1
    pts = [(Fraction(x).limit_denominator(1 << 20), Fraction(y).limit_denominator(1 << 20)) for x, y in CLIP]
    z = lambda p: A * p[iu] + B

    def plane(name):
        if name == "+w":
            ins = lambda p: z(p) <= 1
            tgt = Fraction(1)
        else:
            ins = lambda p: z(p) >= -1
            tgt = Fraction(-1)

        def cross(a, b):
            za, zb = z(a), z(b)
            t = (tgt - za) / (zb - za)
            return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        return ins, cross
    poly, clipped = pts, False
    for nm in plane_order:
        if not poly:
            break
        ins, cross = plane(nm)
        if all(ins(p) for p in poly):      # a plane no vertex crosses is not run: a pass rotates the polygon by one
            continue                        # (S1/S1b: cut-p's stored order is the zigzag of ONE pass, 41 of 41 objects)
        poly, clipped = sh_clip(poly, ins, cross), True
    # an unclipped triangle keeps its input order (S1/S1b e3z-flat099, the default object); a clipped polygon is stored
    # in strip zigzag order
    zz = zigzag(len(poly)) if clipped else list(range(len(poly)))
    stored = [poly[i] for i in zz]
    # boundary edges of the polygon in STORED indices: poly index p_i is stored at position zz.index(i)
    pos = {pi: si for si, pi in enumerate(zz)}
    bnd = {frozenset((pos[i], pos[(i + 1) % len(poly)])) for i in range(len(poly))}
    prims = []
    for t in strip_tris(len(poly)):
        prims.append(tuple(t[k] | (16 if frozenset((t[k], t[(k + 1) % 3])) in bnd else 0) for k in range(3)))
    return dict(xy=[(float(32 + 32 * p[0]), float(32 + 32 * p[1])) for p in stored],
                depth=[float(Fraction(1, 2) + Fraction(1, 2) * z(p)) for p in stored], prims=prims, nv=len(poly))


# ------------------------------------------------------------------------------------------------ float words
def bits(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", x))[0]


def fval(b: int) -> float:
    return struct.unpack("<f", struct.pack("<I", b & 0xffffffff))[0]


def rz_word(x: Fraction) -> int:
    """float32 word of the positive rational x rounded toward zero."""
    b = bits(float(x))
    while Fraction(fval(b)) > x:
        b -= 1
    while Fraction(fval(b + 1)) <= x:
        b += 1
    return b


def recip_words(wbits: int) -> tuple[int, int]:
    """(RZ, RN) words of the exact reciprocal of the float32 word wbits."""
    x = 1 / Fraction(fval(wbits))
    lo = rz_word(x)
    dl, dh = x - Fraction(fval(lo)), Fraction(fval(lo + 1)) - x
    return lo, (lo if dl < dh else lo + 1 if dh < dl else (lo if lo % 2 == 0 else lo + 1))
