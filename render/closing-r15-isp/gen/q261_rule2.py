# Q261 round 2 [post hoc]: declared after round 1 (q261_rule.py, sha256 in q261_rule.sha256) had been
# scored and had fitted no candidate.  Hypothesis family "clip": a triangle with a vertex outside a
# guard rectangle is clipped (Sutherland-Hodgman against the four planes) before the edges are set
# up; each new vertex is the intersection with the plane, rounded to E607's 1/256 pixel grid; the
# polygon's edges are then tested exactly (centre inside all, owning edges at a tie).  The far edge
# is then the line through the near vertex and the ROUNDED clip vertex, which turns about the near
# vertex by (rounding error) / (distance to the clip vertex): a displacement of the far vertex of
# about L / R times 1/512 pixel, 300-ish pixels at L = 2^24 and R = 60-ish pixels.
# Bounds: [-G, 64+G] (guard around the 64 x 64 target) and [-G, +G] (guard around the origin),
# G in the ladders below.  Interpolation variants: exact then half-up to 1/256 (E607's rounding),
# exact then truncated toward zero, float32 interpolation then half up.
# PASS CRITERION (frozen): all 48 hardware rows pixel-exact, as round 1 (all 4096 pixels decided).
import fractions
F = fractions.Fraction
G_AROUND_TARGET = (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096)
G_AROUND_ORIGIN = (128, 256, 512, 1024, 2048, 4096, 8192)
INTERP = ("exact-halfup", "exact-trunc", "f32-halfup")


class Cand:
    def __init__(self, cid, kind, **kw):
        self.id, self.kind, self.kw = cid, kind, kw


def candidates():
    out = [Cand("exact", "exact")]
    for g in G_AROUND_TARGET:
        for it in INTERP:
            out.append(Cand("clip[-%d,64+%d]/%s" % (g, g, it), "clip", lo=-g, hi=64 + g, interp=it))
    for g in G_AROUND_ORIGIN:
        for it in INTERP:
            out.append(Cand("clip[-%d,%d]/%s" % (g, g, it), "clip", lo=-g, hi=g, interp=it))
    return out


def own(dx, dy):
    return dy < 0 or (dy == 0 and dx > 0)


def f32(x):
    import numpy as np
    return F(float(np.float32(float(x))))


def halfup(q):
    q = F(q)
    return (q.numerator * 2 + q.denominator) // (2 * q.denominator)


def trunc(q):
    q = F(q)
    return int(q)


def to_grid(v, interp):
    """v in 1/256 pixel units (Fraction) -> integer 1/256"""
    return trunc(v) if interp == "exact-trunc" else halfup(v)


def inter(p, q, axis, X, interp):
    """intersection of segment p-q with the plane coordinate[axis] == X (pixels), p, q in 1/256"""
    X256 = X * 256
    a, b = p[axis], q[axis]
    if interp == "f32-halfup":
        t = f32(F(X256 - a) / F(b - a))
        r = []
        for i in range(2):
            r.append(f32(p[i] + f32(t * (q[i] - p[i]))))
    else:
        t = F(X256 - a, b - a)
        r = [p[i] + t * (q[i] - p[i]) for i in range(2)]
    r[axis] = F(X256)
    return (to_grid(r[0], interp), to_grid(r[1], interp))


def clip_poly(V, lo, hi, interp):
    poly = [tuple(v) for v in V]
    for axis in (0, 1):
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
                    out.append(inter(cur, nxt, axis, bound, interp))
            poly = out
            if not poly:
                return []
    return poly


def prep(V, cand):
    a, b, c = [tuple(v) for v in V]
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if area == 0:
        return None
    W = [a, b, c] if area > 0 else [a, c, b]
    if cand.kind == "clip":
        W = clip_poly(W, cand.kw["lo"], cand.kw["hi"], cand.kw["interp"])
        if len(W) < 3:
            return None
    return W


def decide(cand, W, px, py):
    n = len(W)
    for i in range(n):
        p, q = W[i], W[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        e = dx * (py - p[1]) - dy * (px - p[0])
        if not (e > 0 or (e == 0 and own(dx, dy))):
            return False
    return True
