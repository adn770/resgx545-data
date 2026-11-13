# SPDX-License-Identifier: MIT
"""clip.py: stages q261 and far (round 13 plan section 2; Q261, Q199; E979, E1005, E1012).

The model under test is E1012's clip (closing11/plan/c6-q261, post hoc on all 48 kept far rows):
a triangle is clipped against a guard rectangle (Sutherland-Hodgman, x then y, low then high
bound), each new vertex is the exact intersection rounded half up to 1/256 pixel, and the
polygon's edges are then tested exactly at the pixel centres with owning edges at a tie. The
engine is c6's own: q261_rule2.py (a byte copy of resgx545-data cited/closing11/plan/c6-q261/,
sha256 0997a099..., the file q261_rule3.py's scan imports): its `inter` (intersection and
rounding) and `decide` (the exact centre test). Only the bounds are generalised here: c6's
clip_poly takes one [lo, hi] for both axes, clip4 below takes four (and equals clip_poly when they
agree, tests/test_gen.py), so each side's own bound is a parameter of its own.

Families (bounds in pixels on a W x W target; the row's side names the free one):
  pos-x   G = 16 .. 22     x <= W + G   (E1012's survivors)
  neg-x   a = 8 .. 32      x >= -a      (E1012: any lower bound from -8 to -32 fits)
  neg-y,  g = 8 .. 32      y >= -g, y <= W + g (untested; assumed symmetric, the plan)
  pos-y
  abs     h = 80 .. 86     both axes in [-(h - 64), h]: a guard fixed in pixels (128 x 128 rows)
The other bounds stay at DEFAULT; tests/test_gen.py checks every row's image depends on its own
parameter only (each other bound moved over its range changes no pixel).

Vertices: the tool sends a window coordinate in 1/2^unit pixel as the float32 clip coordinate
px / (2^(unit-1) W) - 1 (render.c ndc_unit, computed in double); `submitted` gives the window
coordinate that float32 stands for. Where it is not the integer asked for (the 2^30 rows), the
hardware's own float32 viewport may land elsewhere: `variants` gives both, and a pixel on which
they disagree is undetermined ('?') for that model."""
import fractions
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import far as FA  # noqa: E402
import pivot as PIV  # noqa: E402
import q261_rule2 as R2  # noqa: E402

F = fractions.Fraction
MAIN = "tri --keep-going --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d"
FAMILY = {"pos-x": ("G", range(16, 23)), "neg-x": ("a", range(8, 33)),
          "neg-y": ("g", range(8, 33)), "pos-y": ("g", range(8, 33)), "abs": ("h", range(80, 87))}
DEFAULT = {"G": 19, "a": 20, "g": 16}
INTERP = "exact-halfup"


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def submitted(t, unit, size):
    """the window coordinate (pixels, a Fraction) of the float32 clip coordinate the tool sends
    for the integer t in 1/2^unit pixel"""
    ndc = f32(float(t) / ((1 << unit) / 2.0 * size) - 1.0)
    return (F(ndc) + 1) * F(size, 2)


def window_f32(p):
    """the nearest float32 to a window coordinate (a float32 viewport's result)"""
    return F(f32(float(p)))


def bounds(side, value, w):
    """(xlo, xhi, ylo, yhi) in pixels for the row's side and its parameter's value"""
    G, a, g = DEFAULT["G"], DEFAULT["a"], DEFAULT["g"]
    if side == "abs":
        return (-(value - 64), value, -(value - 64), value)
    if side == "pos-x":
        G = value
    elif side == "neg-x":
        a = value
    else:
        g = value
    return (-a, w + G, -g, w + g)


def clip4(V, b):
    """c6's clip_poly with four bounds: V in 1/256 (counter-clockwise as R2.prep orders them)"""
    poly = [tuple(v) for v in V]
    for axis, lo, hi in ((0, b[0], b[1]), (1, b[2], b[3])):
        for bound, keep_ge in ((lo, True), (hi, False)):
            B = bound * 256
            inside = (lambda v: v[axis] >= B) if keep_ge else (lambda v: v[axis] <= B)
            out = []
            n = len(poly)
            for i in range(n):
                cur, nxt = poly[i], poly[(i + 1) % n]
                ci, ni = inside(cur), inside(nxt)
                if ci:
                    out.append(cur)
                if ci != ni:
                    out.append(R2.inter(cur, nxt, axis, bound, INTERP))
            poly = out
            if not poly:
                return []
    return poly


def oriented(V):
    a, b, c = [tuple(v) for v in V]
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if area == 0:
        return None
    return [a, b, c] if area > 0 else [a, c, b]


def image(V, b, w, pixels=None):
    """[drawn] per pixel (raster order of a w x w target, or of `pixels`), V in 1/256 integers;
    b None: the exact triangle (no clip)"""
    W3 = oriented(V)
    if W3 is None:
        return [False] * (w * w if pixels is None else len(pixels))
    P = W3 if b is None else clip4(W3, b)
    if len(P) < 3:
        return [False] * (w * w if pixels is None else len(pixels))
    pts = pixels if pixels is not None else [(x, y) for y in range(w) for x in range(w)]
    return [R2.decide(None, P, x * 256 + 128, y * 256 + 128) for x, y in pts]


def g256(p):
    return FA.grid(p)


def variants(vt, unit, w):
    """the vertices (1/256 integers) the hardware may see: as submitted, and with the float32
    viewport; one entry when they agree"""
    sub = [(submitted(x, unit, w), submitted(y, unit, w)) for x, y in vt]
    out = [[(g256(x), g256(y)) for x, y in sub]]
    alt = [[(g256(window_f32(x)), g256(window_f32(y))) for x, y in sub]]
    return out if alt == out else out + alt


def merged(imgs):
    """one prediction from the variants' images: a pixel they disagree on is None"""
    return [v[0] if all(x == v[0] for x in v) else None for v in zip(*imgs)]


def bitmap(c, w):
    return "".join("".join("?" if v is None else "1" if v else "0" for v in c[y * w:(y + 1) * w]) + "\n"
                   for y in range(w))


def family_text(exact, fam, w):
    """per value of the family, the pixels whose prediction differs from `exact` (x,y:0/1/?)"""
    lines = []
    for val, img in fam:
        d = ["%d,%d:%s" % (i % w, i // w, "?" if v is None else "1" if v else "0")
             for i, v in enumerate(img) if v != exact[i]]
        lines.append("%s %s\n" % (val, " ".join(d) if d else "-"))
    return "".join(lines)


def family_parse(text, exact, w):
    out = {}
    for ln in text.splitlines():
        val, rest = ln.split(" ", 1)
        img = list(exact)
        if rest != "-":
            for t in rest.split():
                xy, v = t.split(":")
                x, y = map(int, xy.split(","))
                img[y * w + x] = None if v == "?" else v == "1"
        out[val] = img
    return out


def predict(vt, unit, w, side, abs_too=False):
    """{model: [drawn or None]} for H-EXACT and the family images [(label, img)] of the side
    (and of `abs` on a 128 target)"""
    vs = variants(vt, unit, w)
    exact = merged([image(v, None, w) for v in vs])
    fams = []
    sides = [side] + (["abs"] if abs_too else [])
    for s in sides:
        name, rng = FAMILY[s]
        for val in rng:
            b = bounds(s, val, w)
            fams.append(("%s=%d" % (name, val), merged([image(v, b, w) for v in vs])))
    return exact, fams


# ---------------------------------------------------------------- the rows' vertices
def side_of(vp):
    fi = PIV.far_index(vp)
    x, y = vp[fi]
    if abs(x) >= abs(y):
        return "pos-x" if x > 0 else "neg-x"
    return "pos-y" if y > 0 else "neg-y"


def to_units(vp, unit):
    out = []
    for x, y in vp:
        for c in (x, y):
            q = F(c) * (1 << unit)
            assert q.denominator == 1, (c, unit)
            assert -(1 << 31) <= q < (1 << 31), (c, unit)
            out.append(int(q))
    return out


def near_edge_pixels(V, w, eps=F(1, 100)):
    """the pixels whose centre lies within eps pixel of an edge line through the far vertex"""
    fi = max(range(3), key=lambda i: abs(V[i][0]) + abs(V[i][1]))
    out = []
    for k in range(3):
        if k == fi:
            continue
        p, q = V[k], V[fi]
        dx, dy = q[0] - p[0], q[1] - p[1]
        n2 = dx * dx + dy * dy
        for y in range(w):
            for x in range(w):
                e = dx * (y * 256 + 128 - p[1]) - dy * (x * 256 + 128 - p[0])
                if e * e < (eps * 256) ** 2 * n2:
                    out.append((x, y))
    return sorted(set(out))


OTHERS = {"G": (16, 19, 22), "a": (8, 20, 32), "g": (8, 16, 32)}


def independent(V, w, side, pixels=None):
    """True when the row's image under its family depends on its own parameter only: every
    other bound moved over OTHERS changes no pixel (V in 1/256, the variant as submitted)"""
    name, rng = FAMILY[side]
    for val in rng:
        b0 = bounds(side, val, w)
        ref = image(V, b0, w, pixels)
        for other, vals in OTHERS.items():
            if other == name:
                continue
            for ov in vals:
                saved = DEFAULT[other]
                DEFAULT[other] = ov
                try:
                    img = image(V, bounds(side, val, w), w, pixels)
                finally:
                    DEFAULT[other] = saved
                if img != ref:
                    return False
    return True


def design(side, w, near, xr, yr, n, pool, seed, grid=32):
    """n far vertices (1/grid pixel grid, x in xr, y in yr) whose images part the side's family
    best (greedy on the distinct signatures, as c6's q261_heldout.py did), each independent of
    the other bounds; near: the two near vertices in pixels"""
    rnd = random.Random(seed)
    name, rng = FAMILY[side]
    k = len(rng)
    cands = []
    for _ in range(pool):
        X = F(round(rnd.uniform(*xr) * grid), grid)
        Y = F(round(rnd.uniform(*yr) * grid), grid)
        vp = tuple(near) + ((X, Y),)
        V = [(g256(x), g256(y)) for x, y in vp]
        if side_of(vp) != side:
            continue
        px = near_edge_pixels(V, w)
        ex = image(V, None, w, px)
        sig = tuple(tuple(px[i] for i, (a, b) in enumerate(zip(ex, image(V, bounds(side, v, w), w, px)))
                          if a != b) for v in rng)
        cands.append((vp, sig, V, px))
    chosen, classes = [], [()] * k
    for _ in range(n):
        def score(c):
            return len(set(classes[j] + (c[1][j],) for j in range(k)))
        while True:
            best = max(cands, key=score)
            cands.remove(best)
            if independent(best[2], w, side, best[3]):
                break
        chosen.append(best[0])
        classes = [classes[j] + (best[1][j],) for j in range(k)]
    return chosen, len(set(classes))


# ---------------------------------------------------------------- the rows
PROPOSALS = "data:cited/closing11/plan/c6-q261/q261_proposals.json"
NEAR = {"pos-x": ((F(25, 4), F(37, 4)), (F(19, 2), F(215, 4))),      # E979 far-x24p (c6)
        "neg-x": ((F(225, 4), F(31, 4)), (F(113, 2), F(223, 4))),    # E979 far-x25n (c6)
        "neg-y": ((F(27, 4), F(233, 4)), (F(229, 4), F(219, 4))),    # E979 far-y22n (c6)
        "pos-y": ((F(29, 4), F(25, 4)), (F(225, 4), F(31, 4)))}      # E979 far-y23p
NEAR128 = ((F(25, 2), F(37, 2)), (F(19), F(215, 2)))                 # far-x24p's, doubled
KEPT = "data:render/closing-r9-x/out/20261113-081821/far/%s.txt.gz"  # E979's kept rows


def tri_args(w, unit, vt):
    """every row names its unit (E684's far21d0 too: --tri-unit 8 is the tool's default 1/256)"""
    return "%s --tri-unit %d --tri-v %s --pixels" % (MAIN % (w, w, w, w), unit, ",".join(map(str, vt)))


def e979(name):
    return dict(FA.FAR)[name]


def ctl_far21():
    n, v = FA.E684_CTL
    return list(v)


def q261_rows(proposals):
    """[(name, set, knobs, w, unit, vt (units), vp (pixels), side, abs_too)] in run order:
    E979's far-ctl (E684's far21d0) first, the held-out rows, E979's far-x24p (E1005's d = 0) last"""
    rows = []
    v = ctl_far21()
    vp = tuple((F(v[2 * i], 256), F(v[2 * i + 1], 256)) for i in range(3))
    rows.append(("q261-ctl-far21", "control", "expectdiff reads:job,pixels", 64, 8, v, vp, "pos-x", False))
    for i, (X, Y) in enumerate(proposals["pos-x"]):
        vp = NEAR["pos-x"] + ((F(X), F(Y)),)
        rows.append(("q261-px%d" % (i + 1), "heldout", "expectdiff", 64, 5, to_units(vp, 5), vp, "pos-x", False))
    for i, (X, Y) in enumerate(proposals["neg-x"]):
        vp = NEAR["neg-x"] + ((F(X), F(Y)),)
        rows.append(("q261-nx%d" % (i + 1), "heldout", "expectdiff", 64, 5, to_units(vp, 5), vp, "neg-x", False))
    ny, _ = design("neg-y", 64, NEAR["neg-y"], (-2 ** 21, 2 ** 21), (-2 ** 25 + 1, -2 ** 22), 4, 120, 13199)
    for i, vp in enumerate(ny):
        rows.append(("q261-ny%d" % (i + 1), "heldout", "expectdiff", 64, 5, to_units(vp, 5), vp, "neg-y", False))
    t128, _ = design("pos-x", 128, NEAR128, (2 ** 22, 2 ** 24 - 1), (-2 ** 22, 2 ** 23), 3, 60, 13261)
    for i, vp in enumerate(t128):
        rows.append(("q261-t128-%d" % (i + 1), "heldout", "expectdiff", 128, 5, to_units(vp, 5), vp, "pos-x", True))
    vp = e979("far-x24p")
    rows.append(("q261-ctl-x24p", "control", "expectdiff reads:job,pixels", 64, 5, to_units(vp, 5), vp, "pos-x", False))
    return rows


def rounded(p):
    return tuple((F(int(x + F(1, 2)) if x >= 0 else -int(-x + F(1, 2))), F(int(y + F(1, 2)) if y >= 0 else -int(-y + F(1, 2))))
                 for x, y in p)


FAR = (  # name, side (E979's near vertices of that side), k: the far vertex at 2^k pixels along it
    ("far-x26p", "pos-x", 26), ("far-y26n", "neg-y", 26), ("far-x28n", "neg-x", 28),
    ("far-y28p", "pos-y", 28), ("far-x30p", "pos-x", 30), ("far-y30n", "neg-y", 30))


def far_vertex(side, k, seed):
    """the far vertex (whole pixels): +-2^k along the side's axis, the other coordinate within
    +-2^(k-2) chosen as design() does, so the clip family's values part the image where it can"""
    near = rounded(NEAR[side])
    m, q = F(2 ** k), F(2 ** (k - 2))
    if side in ("pos-x", "neg-x"):
        xr, yr = ((m, m) if side == "pos-x" else (-m, -m)), (-q, q)
    else:
        xr, yr = (-q, q), ((m, m) if side == "pos-y" else (-m, -m))
    ch, _ = design(side, 64, near, xr, yr, 1, 60, seed, grid=1)
    return ch[0]


def far_rows():
    """[(name, set, knobs, w, unit, vt, vp, side, abs_too)]: E684's far21d0 (control), E979's
    far-x25n (replicate, its own args), then one far vertex at 2^26, 2^28, 2^30 pixels in x and in
    y (both signs on both axes), the near vertices E979's rounded to whole pixels (--tri-unit 0:
    2^30 pixels in an int32)"""
    rows = []
    v = ctl_far21()
    vp = tuple((F(v[2 * i], 256), F(v[2 * i + 1], 256)) for i in range(3))
    rows.append(("far-ctl", "control", "expectdiff reads:job,pixels", 64, 8, v, vp, "pos-x", False))
    vp = e979("far-x25n")
    rows.append(("far-x25n", "replicate", "expectdiff", 64, 5, to_units(vp, 5), vp, "neg-x", False))
    for name, side, k in FAR:
        vp = far_vertex(side, k, 13199 + k)
        rows.append((name, "heldout", "expectdiff", 64, 0, to_units(vp, 0), vp, side, False))
    return rows
