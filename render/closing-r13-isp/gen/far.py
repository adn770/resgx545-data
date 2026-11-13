# SPDX-License-Identifier: MIT
"""far.py: stage far (R9-E, Q199 and Q261): one or two vertices far outside a 64 x 64 target, past
E684's 2^21 pixels, in tool t4's `tri --tri-v` with --tri-unit 5 (1/32 pixel).

The plan's check 2 (`--tri-unit 0` at 2^30): t4 takes --tri-unit 5 to 20 only and --tri-v values
of magnitude below 2^30 units (-2^30 included; sgxfive-test.c at 4623753, parse_opts and
parse_tri_v), so the plan's whole-pixel unit is refused: the unit is 1/32, which reaches 2^24 pixels
both ways and -2^25 (-2^30 units); +2^25 and the plan's 2^26 are out of reach and not run. The
tool's clip coordinate px / (16 * 64) - 1 is exact in float32 for every value used (tests). The
plan's two tie rows (a far vertex at 2^20 + 1/512) are dropped: moving a vertex 2^20 pixels away
by 1/256 moves the edges inside the target by about 2.4e-7 pixel, far inside E684's 1e-3 band, so
no image could tell the rounding [infer].

Frozen per row, images from E606/E607's coverage rule (isp/coverage-envelope model1140.py's
`coverage`, re-written here in integers: vertices rounded half up to 1/256, a pixel centre inside
when every edge function is > 0, or 0 on an owning edge, either winding):
  H-EXACT   the vertex as given
  H-SAT     every coordinate clamped to the 24.8 range [-2^23, 2^23 - 1/256] pixels
  H-WRAP    every coordinate wrapped into that range (two's complement of 24.8)
  H-CULL    nothing drawn
A pixel within 1e-3 pixel of an edge of a rival's triangle is undetermined for that rival (E684's
band); a rival matches a row when every other pixel agrees. Control (can fail): E684's far21d0
case (1401720: 64 x 64, one vertex at 2^21 pixels, unit 1/256), exact in E684."""
import fractions

STAGE = "far"
MAIN = "tri --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64"
UNIT = 5
F = fractions.Fraction
MODELS = ("H-EXACT", "H-SAT", "H-WRAP", "H-CULL")
TRI_COLOUR = 0xFF00FF00
BAND = F(1, 1000)


def px(v, unit=UNIT):
    return F(v, 1 << unit)


def u(p, unit=UNIT):
    """pixels -> tool units (an integer)"""
    q = F(p) * (1 << unit)
    assert q.denominator == 1, p
    return int(q)


# name, the three vertices in pixels (Fractions) -- one far vertex unless named 2a/2b
FAR = [
    ("far-x22p", ((F(33, 4), F(27, 4)), (F(11, 2), F(229, 4)), (F(2 ** 22), F(61, 2)))),
    ("far-x23p", ((F(229, 4), F(27, 4)), (F(2 ** 23), F(2 ** 21)), (F(117, 2), F(229, 4)))),
    ("far-x24p", ((F(25, 4), F(37, 4)), (F(19, 2), F(215, 4)), (F(2 ** 24), F(2 ** 22)))),
    ("far-x25n", ((F(225, 4), F(31, 4)), (F(-2 ** 25), F(-2 ** 23)), (F(113, 2), F(223, 4)))),
    ("far-y22n", ((F(27, 4), F(233, 4)), (F(119, 4), F(-2 ** 22)), (F(229, 4), F(219, 4)))),
    ("far-y23p", ((F(29, 4), F(25, 4)), (F(225, 4), F(31, 4)), (F(2 ** 21), F(2 ** 23)))),
    ("far-y24n", ((F(23, 4), F(229, 4)), (F(2 ** 22), F(-2 ** 24)), (F(231, 4), F(221, 4)))),
    ("far-y25n", ((F(21, 4), F(231, 4)), (F(-2 ** 23), F(-2 ** 25)), (F(233, 4), F(225, 4)))),
    ("far-2a", ((F(2 ** 23), F(21, 2)), (F(-2 ** 23), F(203, 4)), (F(129, 4), F(29, 4)))),
    ("far-2b", ((F(2 ** 24), F(2 ** 22)), (F(123, 4), F(241, 4)), (F(-2 ** 24), F(-2 ** 22)))),
]
# E684's control case 1401720 (far21d0), vertices in 1/256 pixel
E684_CTL = ("far-ctl", (4066, 8385, 7356, 9765, 536870912, 11776))


def grid(p):
    """a coordinate in pixels to 1/256 units, rounded half up (E607)"""
    q = F(p) * 256
    return (q.numerator * 2 + q.denominator) // (2 * q.denominator)


LIM = 1 << 31     # 2^23 pixels in 1/256


def limit(v, kind):
    if kind == "H-SAT":
        return max(-LIM, min(LIM - 1, v))
    if kind == "H-WRAP":
        return (v + LIM) % (2 * LIM) - LIM
    return v


def coverage(V):
    """{(x, y): (inside, near)} of a 64 x 64 target for three vertices in 1/256 pixel."""
    a, b, c = V
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    out = {}
    if area == 0:
        return {(x, y): (False, False) for y in range(64) for x in range(64)}
    if area < 0:
        b, c = c, b
    edges = []
    for p, q in ((a, b), (b, c), (c, a)):
        dx, dy = q[0] - p[0], q[1] - p[1]
        edges.append((p, dx, dy, dy < 0 or (dy == 0 and dx > 0)))
    for y in range(64):
        sy = y * 256 + 128
        for x in range(64):
            sx = x * 256 + 128
            inside, near = True, False
            for (p0, dx, dy, own) in edges:
                e = dx * (sy - p0[1]) - dy * (sx - p0[0])
                inside &= e > 0 or (e == 0 and own)
                # distance of the centre to the edge's line, in pixels: |e| / (256 * |d|)
                if e * e * BAND.denominator ** 2 < 65536 * (dx * dx + dy * dy):
                    near = True
            out[(x, y)] = (inside, near)
    return out


def predictions(verts_px):
    """{model: [(drawn or None) per pixel, raster order]}: None for a band pixel."""
    v = [(grid(x), grid(y)) for x, y in verts_px]
    out = {}
    for m in MODELS:
        if m == "H-CULL":
            out[m] = [False] * 4096
            continue
        cov = coverage([(limit(x, m), limit(y, m)) for x, y in v])
        out[m] = [None if cov[(i % 64, i // 64)][1] else cov[(i % 64, i // 64)][0]
                  for i in range(4096)]
    return out


def jobs():
    """[(name, set, knobs, args, {model: [drawn per pixel]})]"""
    out = []
    n, v = E684_CTL
    pv = [(F(v[2 * i], 256), F(v[2 * i + 1], 256)) for i in range(3)]
    out.append((n, "control", "expectdiff reads:pixels",
                f"{MAIN} --tri-v {','.join(map(str, v))} --pixels",
                {"H-EXACT": predictions(pv)["H-EXACT"]}))
    for name, verts in FAR:
        tv = ",".join(str(u(c)) for p in verts for c in p)
        out.append((name, "heldout", "expectdiff",
                    f"{MAIN} --tri-unit {UNIT} --tri-v {tv} --pixels", predictions(verts)))
    return out
