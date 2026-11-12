"""R3GC models (laptop add-on session L1b: C1 = Q287 + Q122, C2 = Q211).  Pure functions, no I/O; the generator, the scorers and
the tests all import this one file (it is frozen with them).

C1  the ZLS store band.  E730 (post hoc, 12 of 12 jobs, widths 2 mod 4 and heights 2 mod 8): the stored (not 1.0f) dwords of a
    full-screen triangle's depth store are the pixels with x < 1.25 W and y < 1.25 H of the tile area.  Frozen rule A: the
    pixel centre test x + 0.5 < 1.25 W, i.e. x < ceil(1.25 W - 0.5), the same for y with H.  Alternatives that agree with E730's
    fraction .5 or not: FLOOR x < floor(1.25 W), ROUND x < floor(1.25 W + 0.5), CEIL x < ceil(1.25 W), RSTRICT x + 1 < 1.25 W.
    The depth buffer layout is the one E730's post-hoc reader used (post/post_1141tex.py): tiles of 32 x 16 pixels,
    512 dwords a tile, tile row pitch G + 1 tiles, Morton order inside the tile (mort).
C2  Q211, the count of partial renders: E625's family  1 + floor((U + k - thr0) / (thr0 + s)),  thr0 = P - 0x22.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import hashlib  # noqa: E402
import math  # noqa: E402
from fractions import Fraction  # noqa: E402

# ------------------------------------------------------------------------------------------------------------- C1
DEPTH_CTL = 0x171004          # E730's control word with the pitch field (bits 3..11) = 0; pitch G puts G << 3 in (0x17100c = G 1)
BG = 0x3F800000               # the background depth 1.0f: "stored" = not this (E465's observable; E730's recompute used the wrong one)
FILL = 0xDEADBEEF             # the buffer's pre-fill: a dword still holding it was not written by the store
RAMP_X, RAMP_Y = "0.25,0.75,0.25", "0.25,0.25,0.75"
TILE_W, TILE_H = 32, 16

RULES = {
    "A": ("A (x + 0.5 < 1.25 W: x < ceil(1.25 W - 0.5), frozen)", lambda v: math.ceil(Fraction(5, 4) * v - Fraction(1, 2))),
    "FLOOR": ("FLOOR (x < floor(1.25 W))", lambda v: math.floor(Fraction(5, 4) * v)),
    "ROUND": ("ROUND (x < floor(1.25 W + 0.5))", lambda v: math.floor(Fraction(5, 4) * v + Fraction(1, 2))),
    "CEIL": ("CEIL (x < ceil(1.25 W))", lambda v: math.ceil(Fraction(5, 4) * v)),
    "RSTRICT": ("RSTRICT (x + 1 < 1.25 W: x < ceil(1.25 W - 1))", lambda v: math.ceil(Fraction(5, 4) * v - 1)),
}
# The tool refuses odd sizes (libsgxfive render.c: width % 2, height % 2 -> EINVAL), so 1.25 W has the fraction .0 (W = 0 mod 4) or
# .5 (W = 2 mod 4) only: the fractions .25 / .75 the proposal named cannot be run (DEVIATION).  E730's .5 cells already fix
# A = FLOOR against ROUND and CEIL; at the fraction .0, A (= FLOOR = ROUND = CEIL) differs from RSTRICT only, which agrees with A at .5.


def mort(x, y):
    """Dword index inside a 32 x 16 tile of the pixel (x, y) (post_1141tex.py's reader)."""
    r = 0
    for k, (v, b) in enumerate([(y, 0), (x, 0), (y, 1), (x, 1), (y, 2), (x, 2), (y, 3), (x, 3)]):
        r |= ((v >> b) & 1) << k
    return r | (((x >> 4) & 1) << 8)


def tiles(w, h):
    return (w + TILE_W - 1) // TILE_W, (h + TILE_H - 1) // TILE_H


def pitch_g(w):
    """E730's choice: the tile row pitch minus 1, at least 1 (0x17100c up to 64 wide, 0x171014 at 66)."""
    return max(1, tiles(w, 1)[0] - 1)


def depth_ctl(w):
    return DEPTH_CTL | pitch_g(w) << 3


def depth_pages(w, h):
    g = pitch_g(w)
    tw, th = tiles(w, h)
    n = (th - 1) * (g + 1) + tw
    return max((w * h * 4 + 4095) // 4096, n // 2) + 16


def dword_index(x, y, w, h):
    g = pitch_g(w)
    return 512 * ((y // TILE_H) * (g + 1) + x // TILE_W) + mort(x % TILE_W, y % TILE_H)


def area(w, h):
    tw, th = tiles(w, h)
    return tw * TILE_W, th * TILE_H


def extent(rule, w, h):
    f = RULES[rule][1]
    return f(w), f(h)


def band_set(rule, w, h):
    """Tile-area pixels a full-screen triangle (0,0), (3W,0), (0,3H) stores under the rule (the hypotenuse never bounds: the
    band's far corner is at 0.83 of it)."""
    aw, ah = area(w, h)
    xm, ym = extent(rule, w, h)
    return {(x, y) for y in range(ah) for x in range(aw) if x < xm and y < ym}


def set_sha(pts):
    return hashlib.sha256(repr(sorted(pts)).encode()).hexdigest()


def stored_set(words, w, h):
    """(stored pixels = tile-area dwords not 1.0f, number of tile-area dwords still holding the pre-fill) from a depth dump."""
    aw, ah = area(w, h)
    st, dead = set(), 0
    for y in range(ah):
        for x in range(aw):
            v = words[dword_index(x, y, w, h)]
            if v == FILL:
                dead += 1
            elif v != BG:
                st.add((x, y))
    return st, dead


def separating(w, h):
    """The rules whose stored extents differ from rule A's at this size, per axis: ('x' | 'y', [rule names])."""
    ax, ay = extent("A", w, h)
    return {"x": [r for r in RULES if r != "A" and extent(r, w, h)[0] != ax],
            "y": [r for r in RULES if r != "A" and extent(r, w, h)[1] != ay]}


def tri_raster(v256, rule, w, h, margin=Fraction(1, 16)):
    """A single triangle (vertices in 1/256 pixel) clipped by the band rule: (definite pixels, ambiguous pixels).  Rasterisation
    model: the pixel centre (x + 0.5, y + 0.5) inside the triangle; a centre within `margin` pixels (edge distance, measured by the
    normalised edge function) of an edge is ambiguous (top-left tie rules and sub-pixel conventions are not modelled)."""
    pts = [(Fraction(v256[i], 256), Fraction(v256[i + 1], 256)) for i in (0, 2, 4)]
    (x0, y0), (x1, y1), (x2, y2) = pts
    area2 = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    sgn = 1 if area2 > 0 else -1
    edges = []
    for (ax, ay), (bx, by) in ((pts[0], pts[1]), (pts[1], pts[2]), (pts[2], pts[0])):
        ln = math.sqrt(float((bx - ax) ** 2 + (by - ay) ** 2))
        edges.append((ax, ay, bx, by, ln))
    xm, ym = extent(rule, w, h)
    aw, ah = area(w, h)
    definite, ambiguous = set(), set()
    for y in range(min(ym, ah)):
        for x in range(min(xm, aw)):
            cx, cy = Fraction(2 * x + 1, 2), Fraction(2 * y + 1, 2)
            dmin = None
            for ax, ay, bx, by, ln in edges:
                d = sgn * ((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))
                dist = float(d) / ln
                dmin = dist if dmin is None else min(dmin, dist)
            if dmin > float(margin):
                definite.add((x, y))
            elif dmin >= -float(margin):
                ambiguous.add((x, y))
    return definite, ambiguous


# ------------------------------------------------------------------------------------------------------------- C2
U_DEFAULT = 287                # E625 / E625's boundary: the default triangle at 4096x4096


def count(U, k, s, P):
    """E625's family: partial renders of a scene of need U at render_pb_pages P (thr0 = P - 0x22)."""
    t = P - 0x22
    return 1 + max(0, U + k - t) // (t + s)


# the claims of E625 (4096x4096, default triangle) and E779: the 19 cells the 20 surviving pairs were fitted on
E625_COUNTS = {0x23: 10, 0x40: 5, 0x60: 3, 0x80: 2, 0x90: 2, 0xa0: 2, 0xb0: 1, 0xb8: 1, 0xc0: 1, 0x100: 1}
E779_COUNTS = {0xa0: 2, 0xa3: 1, 0xa4: 1, 0xa5: 1, 0xa6: 1, 0xa7: 1, 0xa8: 1, 0xa9: 1, 0xb0: 1}


def fit_pairs(cells=None, U=U_DEFAULT):
    """Pairs of the grid (k in -60..60, s in 1..0x5f, the offline fit's own search range) that fit every (P, count)."""
    cells = cells or {**E625_COUNTS, **E779_COUNTS}
    return [(k, s) for k in range(-60, 61) for s in range(1, 0x60) if all(count(U, k, s, P) == n for P, n in cells.items())]


PAIRS = fit_pairs()         # the 20 (k, s) pairs that fit all 19 cells of E625 and E779 (closing3/rank/q211_fit.out)
assert len(PAIRS) == 20


def split_cells(pairs=None, lo=0x23, hi=0x141, U=U_DEFAULT):
    """Cells P in [lo, hi) where the pairs predict different counts at U (the 19 fit cells at U = 287)."""
    pairs = pairs or PAIRS
    return [P for P in range(lo, hi) if len({count(U, k, s, P) for k, s in pairs}) > 1]


SCENES = {                  # E773: the held-out scenes (U measured by the 0x0724 peak and the free-list walk, HU1 exact)
    "s275": (275, "-n 1 --move 1:1024,0 --keep-going"),
    "s438": (438, "-n 2 --geometry 1 --move 2:0,1024 --keep-going"),
}
MAX_PARTS = 9               # held-out cells stay at or below 9 predicted partial renders (E625 ran up to 10)


def classes(pairs, cells):
    """Partition of the pairs by their count vector over cells [(U, P)]."""
    d = {}
    for k, s in pairs:
        d.setdefault(tuple(count(U, k, s, P) for U, P in cells), []).append((k, s))
    return list(d.values())


def pick_heldout(pairs=None, fit_P=None, per_scene=6):
    """Held-out cells per scene.  Greedy: the cell (either scene, predicted counts <= MAX_PARTS, pairs split) that splits the
    classes of pairs most, ties by the lowest P then the scene order; until every pair is its own class; then split cells by
    most distinct counts; the last cell of each scene is one where all pairs AGREE (a plain test of the family at the new U),
    the mid-range P with the count nearest 3.  Deterministic.  Returns {scene: [P, ...]} in ascending P."""
    pairs = pairs or PAIRS
    fit_P = fit_P if fit_P is not None else split_cells(pairs)
    fitc = [(U_DEFAULT, P) for P in fit_P]
    cand = {sc: [P for P in range(0x23, 0x140) if max(count(U, k, s, P) for k, s in pairs) <= MAX_PARTS
                 and len({count(U, k, s, P) for k, s in pairs}) > 1] for sc, (U, _) in SCENES.items()}
    chosen = {sc: [] for sc in SCENES}
    sel = list(fitc)
    scenes = list(SCENES)
    while True:
        base = len(classes(pairs, sel))
        best = None                       # (classes, -P, -scene index, scene, P)
        for i, sc in enumerate(scenes):
            if len(chosen[sc]) >= per_scene - 1:
                continue
            U = SCENES[sc][0]
            for P in cand[sc]:
                if P in chosen[sc]:
                    continue
                n = len(classes(pairs, sel + [(U, P)]))
                if n > base and (best is None or (n, -P, -i) > best[:3]):
                    best = (n, -P, -i, sc, P)
        if best is None:
            break
        chosen[best[3]].append(best[4])
        sel.append((SCENES[best[3]][0], best[4]))
    for sc, (U, _) in SCENES.items():        # fill with the most divisive remaining cells, then one agreeing cell
        rest = sorted((P for P in cand[sc] if P not in chosen[sc]),
                      key=lambda P: (-len({count(U, k, s, P) for k, s in pairs}), P))
        while len(chosen[sc]) < per_scene - 1 and rest:
            chosen[sc].append(rest.pop(0))
        agree = [P for P in range(0x23, 0x140) if len({count(U, k, s, P) for k, s in pairs}) == 1
                 and 2 <= count(U, *pairs[0], P) <= 4]
        if agree:
            mid = [P for P in agree if P >= 0x40]
            chosen[sc].append(min(mid or agree, key=lambda P: (abs(count(U, *pairs[0], P) - 3), P)))
        chosen[sc].sort()
    return chosen
