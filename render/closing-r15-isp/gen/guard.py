# SPDX-License-Identifier: MIT
"""guard.py: the clip engine of stages g14 and clipr (round 14 plan section 2, r14-isp; Q261,
Q199; E1012, E1023, E1024).

The model is E1012's clip as E1023 and E1024 read it (c6's engine, q261_rule2.py, a byte copy):
a triangle is clipped against a guard box (Sutherland-Hodgman, x then y, low then high bound),
each new vertex is the exact intersection rounded to 1/256 pixel, and the polygon's edges are
then tested exactly at the pixel centres with owning edges at a tie (R2.decide; `cover` below is
the same test row by row, tests/test_gen.py checks the two agree). What is new here:

- a W x H target (r13's gen/clip.py took W x W) and a viewport: the tool sends the float32 clip
  coordinate px / (2^(unit-1) size) - 1 of each vertex (libsgxfive render.c ndc_unit, size the
  target's), and the viewport words 6 to 9 of the state block (x offset, x scale, y offset,
  y scale; sgxfive_tri_block writes W/2, W/2, H/2, H/2, which `--poke blk:N` may replace) map it
  to the window: x = ox + sx ndc. Every viewport a row pokes has offset = scale (the order of the
  two words does not enter);
- the guard boxes of the frozen hypotheses (BOXES): H-VP, a quarter of the viewport past each edge
  ([ox - 1.5 sx, ox + 1.5 sx], the clip coordinate within 1.5 w); H-TGT, a quarter of the target
  ([-W/4, 5W/4]); H-MAX4 and H-MIN4, a quarter of max(W, H) or min(W, H) on both axes; H-ABS, a
  guard fixed in pixels (E1023's 64 x 64 box: x >= -16, y in [-16, 80]; its x upper bound,
  refuted by E1023, is H-VP's); H-EXACT, no clip;
- the rounding of a clip-made vertex (CLIP_RULES): HU floor(q + 1/2) (E607, E1012), HA half away
  from zero (Q260's tie rule, E914, E943), RNE half to even, TR toward zero; and of a vertex the
  tool sends (IN_RULES): E607 (half up for x >= 0) with E943's half away from zero below 0, or
  half up everywhere (HU).
Vertices in 1/256 pixel units are integers; bounds in pixels are Fractions."""
import fractions
import math
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import q261_rule2 as R2  # noqa: E402

F = fractions.Fraction
MAIN = "tri --keep-going --wait-ms 20000 --width %d --height %d --max-width %d --max-height %d"


def f32(x):
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]


def f32hex(x):
    return struct.unpack("<I", struct.pack("<f", float(x)))[0]


# ---------------------------------------------------------------- rounding
def r_hu(q):
    return math.floor(q + F(1, 2))


def r_ha(q):
    return r_hu(q) if q >= 0 else -r_hu(-q)


def r_rne(q):
    f = math.floor(q)
    d = q - f
    if d > F(1, 2) or (d == F(1, 2) and f % 2):
        return f + 1
    return f


def r_tr(q):
    return int(q)


CLIP_RULES = {"HU": r_hu, "HA": r_ha, "RNE": r_rne, "TR": r_tr}
IN_RULES = {"E607": r_ha, "HU": r_hu, "RNE": r_rne, "TR": r_tr}  # E607: half up at x >= 0, E943's HA below


# ---------------------------------------------------------------- vertices
def default_vp(W, H):
    return (F(W, 2), F(W, 2), F(H, 2), F(H, 2))


def ndc(t, unit, size):
    """the float32 clip coordinate the tool sends for t in 1/2^unit pixel (render.c ndc_unit)"""
    return F(f32(float(t) / ((1 << unit) / 2.0 * size) - 1.0))


def windows(vt, unit, W, H, vp):
    """[(x, y)] window pixels (Fractions) of the six tool integers, exact through the viewport"""
    ox, sx, oy, sy = vp
    return [(ox + sx * ndc(vt[2 * i], unit, W), oy + sy * ndc(vt[2 * i + 1], unit, H)) for i in range(3)]


def variants(vt, unit, W, H, vp, rin="E607"):
    """the vertices (1/256 integers) the hardware may see: the exact window coordinate rounded by
    the input rule, and the nearest float32 window coordinate rounded (one entry when equal)"""
    r = IN_RULES[rin]
    win = windows(vt, unit, W, H, vp)
    out = [[(r(x * 256), r(y * 256)) for x, y in win]]
    alt = [[(r(F(f32(x)) * 256), r(F(f32(y)) * 256)) for x, y in win]]
    return out if alt == out else out + alt


# ---------------------------------------------------------------- the clip and the coverage
def oriented(V):
    a, b, c = [tuple(v) for v in V]
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if area == 0:
        return None
    return [a, b, c] if area > 0 else [a, c, b]


def inter(p, q, axis, B256, rule):
    """the intersection of p-q (1/256 integers) with coordinate[axis] == B256 (1/256, a Fraction),
    exact, the other coordinate rounded by the rule (c6's R2.inter with the rule a parameter)"""
    a, b = p[axis], q[axis]
    t = F(B256 - a, 1) / (b - a)
    o = 1 - axis
    r = [None, None]
    r[axis] = CLIP_RULES[rule](F(B256))
    r[o] = CLIP_RULES[rule](p[o] + t * (q[o] - p[o]))
    return tuple(r)


def clip(V, box, rule="HU"):
    """V (3 vertices, 1/256) clipped to box (xlo, xhi, ylo, yhi) pixels; box None: unclipped"""
    W3 = oriented(V)
    if W3 is None:
        return []
    if box is None:
        return W3
    poly = list(W3)
    for axis, lo, hi in ((0, box[0], box[1]), (1, box[2], box[3])):
        for bound, keep_ge in ((lo, True), (hi, False)):
            B = F(bound) * 256
            inside = (lambda v: v[axis] >= B) if keep_ge else (lambda v: v[axis] <= B)
            out = []
            n = len(poly)
            for i in range(n):
                cur, nxt = poly[i], poly[(i + 1) % n]
                ci, ni = inside(cur), inside(nxt)
                if ci:
                    out.append(cur)
                if ci != ni:
                    out.append(inter(cur, nxt, axis, B, rule))
            poly = out
            if not poly:
                return []
    return poly


def cdiv(a, b):
    return -((-a) // b)


def cover(P, W, H):
    """[drawn] in raster order of W x H for the convex polygon P (counter-clockwise in R2's sense,
    1/256 integers): R2.decide at every pixel centre, row by row in integers"""
    out = [False] * (W * H)
    if len(P) < 3:
        return out
    n = len(P)
    edges = []
    for i in range(n):
        p, q = P[i], P[(i + 1) % n]
        edges.append((p, q[0] - p[0], q[1] - p[1]))
    for y in range(H):
        Y = 256 * y + 128
        lo, hi, empty = 0, W - 1, False
        for p, dx, dy in edges:
            C = dx * (Y - p[1]) - dy * (128 - p[0])
            if dy == 0:
                if not (C > 0 or (C == 0 and R2.own(dx, dy))):
                    empty = True
                    break
            elif dy > 0:                            # e > 0 <=> x < C / (256 dy); not owning
                hi = min(hi, cdiv(C, 256 * dy) - 1)
            else:                                   # e >= 0 <=> x >= C / (256 dy); owning
                lo = max(lo, cdiv(-C, -256 * dy))
        if empty or lo > hi:
            continue
        out[y * W + lo:y * W + hi + 1] = [True] * (hi - lo + 1)
    return out


def image(V, box, W, H, rule="HU"):
    return cover(clip(V, box, rule), W, H)


def merged(imgs):
    return [v[0] if all(x == v[0] for x in v) else None for v in zip(*imgs)]


def predict(vt, unit, W, H, vp, box, rule="HU", rin="E607"):
    """[drawn or None] over the variants the hardware may see (a pixel they part is None)"""
    return merged([image(v, box, W, H, rule) for v in variants(vt, unit, W, H, vp, rin)])


# ---------------------------------------------------------------- the frozen guard hypotheses
def boxes(W, H, vp):
    ox, sx, oy, sy = vp
    q = F(3, 2)
    vpb = (ox - q * sx, ox + q * sx, oy - q * sy, oy + q * sy)
    M, m = F(max(W, H), 4), F(min(W, H), 4)
    return {"H-VP": vpb,
            "H-TGT": (-F(W, 4), F(5 * W, 4), -F(H, 4), F(5 * H, 4)),
            "H-MAX4": (-M, W + M, -M, H + M),
            "H-MIN4": (-m, W + m, -m, H + m),
            "H-ABS": (F(-16), vpb[1], F(-16), F(80)),
            "H-EXACT": None}


GUARD_MODELS = ("H-VP", "H-TGT", "H-MAX4", "H-MIN4", "H-ABS", "H-EXACT")
SIDES = {"pos-x": 1, "neg-x": 0, "pos-y": 3, "neg-y": 2}


def with_bound(box, side, value):
    """the box with the side's bound replaced (value: the bound's coordinate in pixels)"""
    b = list(box)
    b[SIDES[side]] = F(value)
    return tuple(b)


def family_values(W, H, side, vp=None):
    """the side's bound as a family of integers: from the target's edge to half the axis past it,
    widened to a quarter of the axis either side of H-VP's bound (a poked viewport's)"""
    size = W if side in ("pos-x", "neg-x") else H
    vb = boxes(W, H, vp or default_vp(W, H))["H-VP"][SIDES[side]]
    if side in ("pos-x", "pos-y"):
        return list(range(min(size, math.floor(vb) - size // 4), max(size + size // 2, math.ceil(vb) + size // 4) + 1))
    return list(range(min(-(size // 2), math.floor(vb) - size // 4), max(0, math.ceil(vb) + size // 4) + 1))


def side_of(vp_pts, W, H):
    """the side a row's far vertex lies on (the one farthest from the target, in window pixels)"""
    best, side = None, None
    for x, y in vp_pts:
        for s, d in (("pos-x", x - W), ("neg-x", -x), ("pos-y", y - H), ("neg-y", -y)):
            if best is None or d > best:
                best, side = d, s
    return side


# ---------------------------------------------------------------- designing the rows
def near_pixels(V, W, H, eps=F(1, 64)):
    """pixels whose centre lies within eps pixel of a line through two vertices of V (1/256)"""
    out = set()
    e256 = eps * 256
    for i in range(3):
        for j in range(i + 1, 3):
            p, q = V[i], V[j]
            dx, dy = q[0] - p[0], q[1] - p[1]
            n = math.isqrt(dx * dx + dy * dy) + 1
            if abs(dx) >= abs(dy):       # walk the columns
                for x in range(W):
                    X = 256 * x + 128
                    yl = p[1] + F(dy * (X - p[0]), dx)
                    for y in range(max(0, int((yl - 256) // 256)), min(H, int((yl + 256) // 256) + 1)):
                        e = dx * (256 * y + 128 - p[1]) - dy * (X - p[0])
                        if abs(e) <= e256 * n:
                            out.add((x, y))
            else:
                for y in range(H):
                    Y = 256 * y + 128
                    xl = p[0] + F(dx * (Y - p[1]), dy)
                    for x in range(max(0, int((xl - 256) // 256)), min(W, int((xl + 256) // 256) + 1)):
                        e = dx * (Y - p[1]) - dy * (256 * x + 128 - p[0])
                        if abs(e) <= e256 * n:
                            out.add((x, y))
    return sorted(out)


def at(P, pts):
    return tuple(R2.decide(None, P, 256 * x + 128, 256 * y + 128) for x, y in pts)


def design(W, H, vp, side, near, xr, yr, unit, n, pool, seed, parts, others, grid=32):
    """n far vertices whose images under the side's family (the other bounds at H-VP's) part H-VP's
    value from every other value of `parts` (in some row) and as many family values as possible,
    each image independent of the other bounds over `others` ({side: values}).
    A candidate aims one far edge at a pixel centre: the far vertex on the line from a near vertex
    through a centre of the target's far half (then on the 1/grid grid and as the tool submits it),
    so that the centre's side of the clipped edge is the sign of the clip vertex's rounding error.
    near: the two near vertices (window pixels). Returns [(window vertices)], the classes reached."""
    rnd = random.Random(seed)
    base = boxes(W, H, vp)["H-VP"]
    vpval = base[SIDES[side]]
    rivals = [p for p in parts if p != vpval]
    fam = family_values(W, H, side, vp)
    ax = 0 if side in ("pos-x", "neg-x") else 1
    pos = side in ("pos-x", "pos-y")
    cands, tries = [], 0
    while len(cands) < pool and tries < 400 * pool:
        tries += 1
        k = rnd.randrange(2)
        P = near[k]
        size = (W, H)[ax]
        c = [None, None]
        c[ax] = F(rnd.randrange(size // 2, size) if pos else rnd.randrange(0, size // 2)) + F(1, 2)
        c[1 - ax] = F(rnd.randrange(0, (H, W)[ax])) + F(1, 2)
        u = (c[0] - P[0], c[1] - P[1])
        if u[ax] == 0 or (u[ax] > 0) != pos:
            continue
        far = F(rnd.uniform(*(xr if ax == 0 else yr)))
        lam = (far - P[ax]) / u[ax]
        Vw = (P[0] + lam * u[0], P[1] + lam * u[1])
        lo, hi = yr if ax == 0 else xr
        if not lo <= Vw[1 - ax] <= hi:
            continue
        pts = tuple(near) + ((F(round(Vw[0] * grid), grid), F(round(Vw[1] * grid), grid)),)
        if side_of(pts, W, H) != side:
            continue
        vt = to_units(pts, unit, W, H, vp)
        vs = variants(vt, unit, W, H, vp)
        if len(vs) != 1:
            continue
        V = vs[0]
        px = near_pixels(V, W, H)
        if not px or oriented(V) is None:
            continue
        sig = {v: at(clip(V, with_bound(base, side, v)), px) for v in set(fam) | set(parts) | {vpval}}
        parted = frozenset(p for p in rivals if sig[p] != sig[vpval])
        if not parted:
            continue
        ok = True
        for v in [vpval] + rivals + [fam[0], fam[-1]]:
            for os_, vals in others.items():
                for ov in vals:
                    b = with_bound(with_bound(base, side, v), os_, ov)
                    if at(clip(V, b), px) != sig[v]:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            cands.append((pts, sig, parted))
    chosen, classes, covered = [], {v: () for v in fam}, set()
    for _ in range(n):
        if not cands:
            raise SystemExit("design: no candidate left for %s %dx%d" % (side, W, H))
        best = max(cands, key=lambda c: (len(covered | c[2]),
                                         len(set(classes[v] + (c[1][v],) for v in fam))))
        cands.remove(best)
        chosen.append(best[0])
        covered |= best[2]
        classes = {v: classes[v] + (best[1][v],) for v in fam}
    if covered != set(rivals):
        raise SystemExit("design: %s %dx%d parts %s, not %s" % (side, W, H, sorted(covered), rivals))
    return chosen, len(set(classes.values()))


def to_units(pts, unit, W, H, vp):
    """window pixels -> the tool's integers (1/2^unit pixel of the target), through the viewport"""
    ox, sx, oy, sy = vp
    out = []
    for x, y in pts:
        for c, o, s, size in ((x, ox, sx, W), (y, oy, sy, H)):
            px = ((F(c) - o) / s + 1) * F(size, 2)
            q = px * (1 << unit)
            assert q.denominator == 1, (c, unit)
            assert -(1 << 31) <= q < (1 << 31), (c, unit)
            out.append(int(q))
    return out


# ---------------------------------------------------------------- files
def bitmap(img, W):
    return "".join("".join("?" if v is None else "1" if v else "0" for v in img[y * W:(y + 1) * W]) + "\n"
                   for y in range(len(img) // W))


def bits(body):
    return [None if c == "?" else c == "1" for c in "".join(body.split())]


def diff_text(ref, labelled, W):
    """per label, the pixels whose prediction differs from ref (x,y:0/1/?), or '-'"""
    lines = []
    for lab, img in labelled:
        d = ["%d,%d:%s" % (i % W, i // W, "?" if v is None else "1" if v else "0")
             for i, v in enumerate(img) if v != ref[i]]
        lines.append("%s %s\n" % (lab, " ".join(d) if d else "-"))
    return "".join(lines)


def diff_parse(text, ref, W):
    out = {}
    for ln in text.splitlines():
        lab, rest = ln.split(" ", 1)
        img = list(ref)
        if rest != "-":
            for t in rest.split():
                xy, v = t.split(":")
                x, y = map(int, xy.split(","))
                img[y * W + x] = None if v == "?" else v == "1"
        out[lab] = img
    return out


def agree(got, want):
    if got is None:
        return None
    return all(w is None or g == w for g, w in zip(got, want))


def dist(P, x, y):
    """the distance (pixels, float) of the centre of pixel (x, y) to the nearest edge line of P"""
    best = None
    n = len(P)
    for i in range(n):
        p, q = P[i], P[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        e = dx * (256 * y + 128 - p[1]) - dy * (256 * x + 128 - p[0])
        d = abs(e) / math.hypot(dx, dy) / 256
        best = d if best is None else min(best, d)
    return best


def parting(polys, W, H):
    """{(a, b): [pixels]} where the coverage of polys[a] and polys[b] differ (a < b by name), and
    the least distance of those pixels to an edge of either polygon"""
    imgs = {k: cover(P, W, H) for k, P in polys.items()}
    out, least = {}, None
    ks = sorted(polys)
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            d = [j for j in range(W * H) if imgs[a][j] != imgs[b][j]]
            out[(a, b)] = d
            for j in d:
                m = min(dist(polys[a], j % W, j // W), dist(polys[b], j % W, j // W))
                least = m if least is None else min(least, m)
    return out, least


def clip_f32(p, q, axis, bound_ndc, size, off):
    """the clip-space float32 intersection of p-q (window pixels, Fractions on the 1/256 grid) with
    the plane ndc[axis] == bound_ndc, mapped back to window pixels (both coordinates): the
    arithmetic a float32 clipper would do (t = (b - a) / (c - a), x = a + t (c - a))"""
    def n(v, k):
        return f32((float(v) - float(off[k])) / float(size[k]))
    a = [n(p[0], 0), n(p[1], 1)]
    c = [n(q[0], 0), n(q[1], 1)]
    t = f32(f32(bound_ndc - a[axis]) / f32(c[axis] - a[axis]))
    r = [f32(a[k] + f32(t * f32(c[k] - a[k]))) for k in (0, 1)]
    r[axis] = bound_ndc
    return tuple(F(f32(r[k])) * size[k] + off[k] for k in (0, 1))
