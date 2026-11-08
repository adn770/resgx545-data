"""The generator's side of the 11.31 models: placement of the first triangle's vertices through the
viewport words, and the predictions declared before any run. recompute/recompute_p1131.py has its
own implementation of the same models (no import of this file), so that a disagreement between the
declared table and the recomputation shows a bug in one of them."""
from __future__ import annotations

import math
import struct

NDC = [(-0.75, -0.75), (0.75, -0.375), (-0.375, 0.75)]


def fbits(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", x))[0]


def hx(w: int) -> str:
    return "0x%08x" % w


def vp_args(ox: float, sx: float, oy: float, sy: float) -> list[str]:
    """The state block's viewport words 6 (x offset), 7 (x scale), 8 (y offset), 9 (y scale)."""
    return ["--blk %d=%s" % (i, hx(fbits(v))) for i, v in ((6, ox), (7, sx), (8, oy), (9, sy))]


def vertices(w: int, h: int, ox: float, sx: float, oy: float, sy: float, n: int):
    """Window coordinates of vertex k: copy c = k // 3 is moved c / (8 w) in NDC x, c / (8 h) in y."""
    out = []
    for k in range(n):
        c, i = divmod(k, 3)
        out.append((ox + sx * (NDC[i][0] + c / (8 * w)), oy + sy * (NDC[i][1] + c / (8 * h))))
    return out


def regions(w: int, h: int):
    """The 32 x 16 regions with their origin inside the target."""
    return [(x, y) for y in range(0, h, 16) for x in range(0, w, 32)]


# ---- triangles. H70-T1 (post hoc on E180's 26 shifted triangles: 472 of 472 regions, presence and
# tile class): every 16 x 16 tile is half-open on its high sides, the bounding box is tested against
# it, then the three edge lines against its corners (closed: a corner on an edge counts). H70-T0 is
# the landed record's: closed tiles, half-open only on the line between a region's tiles (it
# predicts 21 regions of the 26 jobs that have no stream).
def _overlaps(t, x0, y0, x1, y1, closed=False):
    bx0, bx1 = min(p[0] for p in t), max(p[0] for p in t)
    by0, by1 = min(p[1] for p in t), max(p[1] for p in t)
    if bx1 < x0 or by1 < y0 or (bx0 > x1 or by0 > y1 if closed else bx0 >= x1 or by0 >= y1):
        return False
    corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    for i in range(3):
        a, b, c = t[i], t[(i + 1) % 3], t[(i + 2) % 3]
        nx, ny = b[1] - a[1], a[0] - b[0]
        side = nx * (c[0] - a[0]) + ny * (c[1] - a[1])
        if all((nx * (x - a[0]) + ny * (y - a[1])) * side < 0 for x, y in corners):
            return False
    return True


def tri_classes(verts, w, h):
    """{(x0, y0): 'L' | 'R' | 'B'} for the regions the triangles (3 vertices each) meet (H70-T1)."""
    tris = [verts[i:i + 3] for i in range(0, len(verts) - 2, 3)]
    out = {}
    for (x0, y0) in regions(w, h):
        left = any(_overlaps(t, x0, y0, x0 + 16, y0 + 16) for t in tris)
        right = any(_overlaps(t, x0 + 16, y0, x0 + 32, y0 + 16) for t in tris)
        if left or right:
            out[(x0, y0)] = "B" if left and right else "L" if left else "R"
    return out


# ---- lines: exact segment against the 32 x 16 region, closed (H70-L2)
def seg_rect(a, b, x0, y0, x1, y1, infl=0.0):
    x0, y0, x1, y1 = x0 - infl, y0 - infl, x1 + infl, y1 + infl
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                t0 = max(t0, r)
            else:
                if r < t0:
                    return False
                t1 = min(t1, r)
    return t0 <= t1


def line_regions(verts, nlines, w, h):
    """{(x0, y0): sorted indices of the lines (vertex 2i to 2i + 1) that meet the region}."""
    out = {}
    for (x0, y0) in regions(w, h):
        hit = [i for i in range(nlines) if seg_rect(verts[2 * i], verts[2 * i + 1], x0, y0, x0 + 32, y0 + 16)]
        if hit:
            out[(x0, y0)] = hit
    return out


# ---- points: the region and tile holding the vertex, half-open at the low side (H70-P0)
def point_regions(verts, npoints, w, h):
    out = {}
    for p in verts[:npoints]:
        x, y = p
        if not (0 <= x < w and 0 <= y < h):
            continue
        x0, y0 = int(x // 32) * 32, int(y // 16) * 16
        side = "L" if x < x0 + 16 else "R"
        out.setdefault((x0, y0), set()).add(side)
    return {k: ("B" if len(v) == 2 else next(iter(v))) for k, v in out.items()}


def point_pixels(verts, npoints, width16, w, h):
    """Pixels whose centre is strictly inside the square of side width16 / 16 round a point
    (H117-W); the points' sets are added (overlaps counted once)."""
    s = width16 / 16.0
    px = set()
    for (x, y) in verts[:npoints]:
        xs = [k for k in range(w) if abs(k + 0.5 - x) < s / 2]
        ys = [k for k in range(h) if abs(k + 0.5 - y) < s / 2]
        px.update((i, j) for i in xs for j in ys)
    return len(px)


# ---- the object format (H70-F, H70-M): from the coordinate size and format words
def object_format(n: int, cs: int, cf: int):
    """(stored dwords, iterated dwords, four masks) of a vertex with n coordinate outputs (n = 0:
    none); sets of four then the rest, 3 bits a set in cs, one bit a set in cf."""
    sets = max(1, -(-n // 4)) if n else 0
    nsets = max(sets, 1)
    for i in range(8):
        if (cs >> (3 * i)) & 7 or (cf >> i) & 1:
            nsets = max(nsets, i + 1)
    stored = 1
    for i in range(sets):
        d = min(4, n - 4 * i)
        stored += -(-d // 2) if (cf >> i) & 1 else d
    masks = [0, 0, 0, 0]
    for i in range(nsets):
        s = (cs >> (3 * i)) & 7
        bit = 1 << (i + 1)
        if (cf >> i) & 1:
            masks[0] |= bit
        if s == 1:
            masks[1] |= bit
        if s in (3, 5):
            masks[2] |= bit
        if s in (4, 5):
            masks[3] |= bit
    return stored, 1 + n, masks
