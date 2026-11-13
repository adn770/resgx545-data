# Q261 / E1005 candidate set-up arithmetics, declared BEFORE scoring (frozen by sha256).
# Everything below is exact rational arithmetic (fractions) with an explicit software float of
# m significant bits (m = 24 is float32 without exponent limits) and rounding RN (ties to even) or
# RZ.  Vertices are on E607's 1/256 pixel grid (integers); pixel centres likewise.
#
# PASS CRITERION (frozen): a candidate "fits" iff on all 47 hardware rows (E1005's 36 pivot rows
# with far-x23p/x24p/x25n at d = 0..-544, E979's 10 far rows, E684's control far21d0) the candidate's
# image is pixel-exact (all 4096 pixels), i.e. every pixel within 0.05 pixel of an edge line is
# decided as the hardware drew it and every pixel outside is the exact coverage (E979 H-EXACT-BAND,
# checked on the hardware rows once).  Equivalent for the three intervals: band drawn at d >= -288
# and not at -416/-544 for far-x24p (D in (339.4, 467.4)), drawn at every d for far-x23p and
# far-x25n (D > 586).  Everything is [post hoc]: the intervals were read before these candidates.
import fractions
F = fractions.Fraction

M_LADDER = (24, 22, 20, 18, 16, 15, 14, 13, 12, 11, 10, 8)
MODES = ("RN", "RZ")
FORMS = (
    "abs-cX",      # a=y0-y1, b=x1-x0 exact ints rounded; c=x0*y1-x1*y0 exact then rounded; ((a px + b py) + c)
    "abs-cF",      # as abs-cX but c from rounded products x0*y1, x1*y0 and a rounded difference
    "abs-cfirst",  # as abs-cX, evaluated ((c + a px) + b py)
    "tile32",      # abs-cX at the 32 x 32 tile corner, then rounded increments inside the tile
    "tile16",      # the same with 16 x 16 tiles
    "start",       # relative to the edge's start vertex: dx*(py-y0) - dy*(px-x0), dx,dy,products rounded
    "near",        # the same, origin = the edge's vertex nearer the target centre (32,32)
    "slope-start", # line y = y0 + m (x - x0) (x for steep edges), m = fl(dy/dx), origin start vertex
    "slope-near",  # the same, origin the vertex nearer the target centre
)
LSB_SHIFTS = (16, 20, 24, 28, 32)   # fixed point: c truncated (floor) or rounded to a multiple of 2^s
VTRUNC_K = (4, 5, 6, 7, 8, 9, 10)   # far vertex coordinates floored to a 2^k pixel grid
# vertex-level: "wrap32" = 1/256 coordinates wrapped to signed 32 bit, "sat32" = saturated to it
# (E979 refuted both for the whole image; scored for completeness)


def rnd(x, m, mode):
    """x (Fraction/int) to m significant bits, RN ties-to-even or RZ"""
    x = F(x)
    if x == 0 or m >= 200:
        return x
    s = 1 if x > 0 else -1
    a = abs(x)
    n, d = a.numerator, a.denominator
    # exponent e with 2^e <= a < 2^(e+1)
    e = n.bit_length() - d.bit_length()
    if F(n, d) < F(2) ** e:
        e -= 1
    ulp = F(2) ** (e - (m - 1))
    q = a / ulp
    fl = q.numerator // q.denominator
    if mode == "RN":
        r = q - fl
        if r > F(1, 2) or (r == F(1, 2) and fl % 2 == 1):
            fl += 1
    return s * fl * ulp


def lsb(x, s, mode):
    u = 1 << s
    x = F(x)
    fl = (x / u).__floor__()
    if mode == "RN":
        r = x / u - fl
        if r > F(1, 2) or (r == F(1, 2) and fl % 2 == 1):
            fl += 1
    return fl * u


class Cand:
    def __init__(self, cid, kind, **kw):
        self.id, self.kind, self.kw = cid, kind, kw


def candidates():
    out = [Cand("exact", "exact")]
    for form in FORMS:
        for m in M_LADDER:
            for mode in MODES:
                out.append(Cand("%s/m%d/%s" % (form, m, mode), "fp", form=form, m=m, mode=mode))
    for s in LSB_SHIFTS:
        for mode in ("floor", "RN"):
            out.append(Cand("lsbC/s%d/%s" % (s, mode), "lsb", s=s, mode="RZ" if mode == "floor" else "RN"))
    for k in VTRUNC_K:
        out.append(Cand("vtrunc/k%d" % k, "vtrunc", k=k))
    out.append(Cand("vwrap32", "vwrap"))
    out.append(Cand("vsat32", "vsat"))
    return out


def own(dx, dy):
    return dy < 0 or (dy == 0 and dx > 0)


def far_index(V):
    return max(range(3), key=lambda i: abs(V[i][0]) + abs(V[i][1]))


def prep(V, cand):
    """normalised vertices (clockwise positive, as the exact rule) after vertex-level candidates"""
    V = [tuple(v) for v in V]
    k = cand.kind
    if k in ("vwrap", "vsat", "vtrunc"):
        fi = far_index(V)
        a = []
        for i, (x, y) in enumerate(V):
            if k == "vtrunc":
                if i == fi:
                    g = (1 << cand.kw["k"]) * 256
                    x, y = (x // g) * g, (y // g) * g
            else:
                lim = 1 << 31
                for_c = []
                for c in (x, y):
                    if k == "vwrap":
                        c = (c + lim) % (2 * lim) - lim
                    else:
                        c = max(-lim, min(lim - 1, c))
                    for_c.append(c)
                x, y = for_c
            a.append((x, y))
        V = a
    a, b, c = V
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if area == 0:
        return None
    return [a, b, c] if area > 0 else [a, c, b]


def edge_e(cand, p, q, px, py):
    """the candidate's edge function of the pixel centre (px, py) for the edge p -> q"""
    x0, y0 = p
    x1, y1 = q
    dx, dy = x1 - x0, y1 - y0
    k = cand.kind
    if k in ("exact", "vwrap", "vsat", "vtrunc"):
        return dx * (py - y0) - dy * (px - x0)
    if k == "lsb":
        c = x0 * y1 - x1 * y0
        cq = lsb(c, cand.kw["s"], cand.kw["mode"])
        return (-dy) * px + dx * py + cq
    form, m, md = cand.kw["form"], cand.kw["m"], cand.kw["mode"]
    R = lambda v: rnd(v, m, md)
    if form in ("abs-cX", "abs-cF", "abs-cfirst", "tile32", "tile16"):
        a, b = R(y0 - y1), R(x1 - x0)
        if form == "abs-cF":
            c = R(R(x0 * y1) - R(x1 * y0))
        else:
            c = R(x0 * y1 - x1 * y0)
        if form == "abs-cfirst":
            return R(R(c + R(a * px)) + R(b * py))
        if form in ("tile32", "tile16"):
            t = (32 if form == "tile32" else 16) * 256
            tx, ty = (px // t) * t, (py // t) * t
            et = R(R(R(a * tx) + R(b * ty)) + c)
            return R(et + R(R(a * (px - tx)) + R(b * (py - ty))))
        return R(R(R(a * px) + R(b * py)) + c)
    near = form.endswith("near")
    if near:
        dp = (x0 - 32 * 256) ** 2 + (y0 - 32 * 256) ** 2
        dq = (x1 - 32 * 256) ** 2 + (y1 - 32 * 256) ** 2
        ox, oy = (x1, y1) if dq < dp else (x0, y0)
    else:
        ox, oy = x0, y0
    if form.startswith("slope"):
        if abs(dx) >= abs(dy):
            mm = R(F(dy, dx))
            yl = R(oy + R(mm * (px - ox)))
            s = (py - yl)
            return s * (1 if dx > 0 else -1)
        mm = R(F(dx, dy))
        xl = R(ox + R(mm * (py - oy)))
        s = (px - xl)
        return -s * (1 if dy > 0 else -1)
    dxr, dyr = R(dx), R(dy)
    return R(R(dxr * R(py - oy)) - R(dyr * R(px - ox)))


def decide(cand, W, px, py):
    inside = True
    for i in range(3):
        p, q = W[i], W[(i + 1) % 3]
        dx, dy = q[0] - p[0], q[1] - p[1]
        e = edge_e(cand, p, q, px, py)
        inside &= e > 0 or (e == 0 and own(dx, dy))
    return inside
