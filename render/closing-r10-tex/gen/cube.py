# SPDX-License-Identifier: MIT
"""cube.py: stage cube3 (S10-tex, Q284, seeds plan closing10/seeds/exp-seeds-r10.md section 3):
r9-geo's gen/cube.py (resgx545-data render/closing-r9-geo/gen/cube.py, itself r8-geo's extended)
copied; r10-tex adds the cube3 jobs, the tie rivals by ramp kind and the H-SEAM-FLOAT edge rival
at the end of the file. Standard library only. r9-geo's text follows unchanged.

The (s, t) rule is r8-geo's frozen q284_rule.json (sha256 52162471..., E923, held out by E930 at
16 and 8): the face is the coordinate of largest magnitude and its sign (face = 2 axis + (c < 0),
+x, -x, +y, -y, +z, -z = 0 to 5); per face the minor axis to s, the signs and the order of
q284_rule.json; texel = floor((q + 1) / 2 * N) with q = sign * c / |ma|. Two kinds of pixel are no
prediction ("cannot tell"): a face tie (the two largest magnitudes equal) and a texel tie
((q + 1) / 2 * N exactly an integer while |ma| is no power of two; E930, E931).

The face-local index, per law (the rivals of the stage; "lo" is the coordinate the face's order
puts in bit 0, "hi" the other: order "ty" has t low, "sx" s low):
  MORTON    E923's: Morton(lo, hi) over log2 N bits each (E930 refuted it at 32 x 32)
  E561      E561's law for 32-bit twiddled textures: Morton(lo & 15, hi & 15) in bits 0 to 7, then
            the 16 x 16 tiles in raster order with hi as x (the fast axis): + 256 (hi >> 4) +
            256 (N / 16) (lo >> 4). At 32 x 32 it is E930's post hoc index (bit 8 = hi4, bit 9 =
            lo4); at N <= 16 it is MORTON.
  PAIRSWAP  MORTON with every bit pair above bit 7 in the other order (bit 2k = hi_k, bit 2k + 1
            = lo_k for k >= 4): E561 at 32, not at 64.
The face's base: face * N * N dwords (FACE_N); at N = 4 H-PAD64 puts it at face * 64 [infer, from
E940's padding] against H-NN's face * 16."""
import hashlib
import json

import pins
import texprog as T

RULE_PIN = "data:render/closing-r9-geo/gen/q284_rule.json"
RULE_SHA = "52162471d1c80fd1d17a969b2de3216dfcab6fd76b34f824af9a23f81631bd61"
SMP = "smp3d r10, r24, r20, drc0"
T0_POINT = 0x07fe0000          # E726's: no LOD bias, level 0 only, nearest, repeat
T0_LINEAR = 0x07fe1400         # the same with T0.MAGFILTER (13:12) and T0.MINFILTER (11:10) 1
T1 = {4: 0x4c003003, 8: 0x4c007007, 16: 0x4c00f00f, 32: 0x4c01f01f, 64: 0x4c03f03f}
T23 = (0x5caf0000, 0x00800800)  # the scratch buffer's address (SCRATCH_IMM), E726's T3
PAGES64 = 32                   # 64 x 64 faces: 6 x 4096 dwords = 24 pages, --scratch-pages 32


def rule():
    blob = pins.blob(RULE_PIN)
    if hashlib.sha256(blob).hexdigest() != RULE_SHA:
        raise SystemExit(RULE_PIN + " is not the frozen rule")
    return json.loads(blob)


def twid(s, t, order, nb):
    i = 0
    for b in range(nb):
        lo, hi = (t, s) if order == "ty" else (s, t)
        i |= ((lo >> b) & 1) << (2 * b) | ((hi >> b) & 1) << (2 * b + 1)
    return i


def local(s, t, order, n, law):
    """The face-local dword index of texel (s, t) under a law (module docstring)."""
    nb = n.bit_length() - 1
    lo, hi = (t, s) if order == "ty" else (s, t)
    if law == "MORTON" or n <= 16:
        return twid(s, t, order, nb)
    if law == "E561":
        return twid(s & 15, t & 15, order, 4) + 256 * (hi >> 4) + 256 * (n // 16) * (lo >> 4)
    if law == "PAIRSWAP":
        i = twid(s, t, order, nb)
        for b in range(4, nb):
            i &= ~(3 << (2 * b))
            i |= ((hi >> b) & 1) << (2 * b) | ((lo >> b) & 1) << (2 * b + 1)
        return i
    raise ValueError(law)


def pow2(q):
    q = abs(q)
    return q > 0 and q.numerator & (q.numerator - 1) == 0 and q.denominator & (q.denominator - 1) == 0


def face_of(c):
    a = [abs(t) for t in c]
    m = max(a)
    axes = [i for i in range(3) if a[i] == m]
    if len(axes) > 1:
        return None, None
    ax = axes[0]
    return 2 * ax + (c[ax] < 0), ax


def tied_axes(c):
    a = [abs(t) for t in c]
    return [i for i in range(3) if a[i] == max(a)]


def st(R, c, N):
    """(face, s texel coordinate, t texel coordinate, |ma|, order) as exact fractions of texels,
    or None at a face tie."""
    face, ax = face_of(c)
    if face is None:
        return None
    return st_on(R, c, N, ax)


def st_on(R, c, N, ax):
    """The same on the face of axis ax (taken as the major axis)."""
    face = 2 * ax + (c[ax] < 0)
    r = R[str(face)]
    mi = [i for i in range(3) if i != ax]
    sa, ta = mi[r["s_minor"]], mi[1 - r["s_minor"]]
    ma = abs(c[ax])
    vs = (r["s_sign"] * c[sa] / ma + 1) / 2 * N
    vt = (r["t_sign"] * c[ta] / ma + 1) / 2 * N
    return face, vs, vt, ma, r["order"]


def flo(v):
    return v.numerator // v.denominator


def predict(R, c, N, law="MORTON", face_n=None):
    """("ok", value) | ("face-tie", None) | ("texel-tie", None). face_n: the faces' distance in
    dwords (default N * N)."""
    p = st(R, c, N)
    if p is None:
        return "face-tie", None
    face, vs, vt, ma, order = p
    if not pow2(ma) and (vs.denominator == 1 or vt.denominator == 1):
        return "texel-tie", None
    s = min(max(flo(vs), 0), N - 1)
    t = min(max(flo(vt), 0), N - 1)
    fn = N * N if face_n is None else face_n
    return "ok", 0xD0000000 | (face * fn + local(s, t, order, N, law))


def lin(ax, k, c):
    return ("lin", ax, T.bits(k), T.bits(c))


def const(v):
    return ("bits", T.bits(v))


ONE, NEG = const(1.0), const(-1.0)
RX, RY = lin("x", 1.5, -2.25), lin("y", 1.5, -2.25)
# r8-geo's four off-axis programs (E930 (a)); b1, b2, b3 its sized directions
OFF = {
    "a1": (lin("x", 1.5, -2.25), lin("y", 1.5, -2.25), const(-0.625)),
    "a2": (const(0.625), lin("x", 1.5, -2.5), lin("y", 1.5, -2.0)),
    "a3": (lin("y", 2.0, -3.0), const(0.6875), lin("x", 1.5, -2.25)),
    "a4": (lin("x", 1.5, -2.0), const(-0.6875), lin("y", 1.5, -2.5)),
}
SIZED = {"b1": OFF["a1"], "b2": OFF["a2"], "b3": OFF["a4"]}
# 32 x 32: three directions no job has run (one constant coordinate, two ramps, the dominant axis
# changing inside each image)
NEW32 = {
    "c1": (const(-0.6875), lin("x", 1.5, -2.25), lin("y", 1.5, -2.0)),
    "c2": (lin("y", 1.5, -2.5), lin("x", 1.5, -2.0), const(0.625)),
    "c3": (lin("x", 1.5, -2.5), const(-0.625), lin("y", 2.0, -3.0)),
}
# face ties of the other pairs: the constant axis at +-0.75, the tied axis a ramp crossing its
# magnitude at x = 32 (1/1024 a column, as r8-geo's), of the other sign; the third coordinate
# 0.25 (1 + y / 32) - 0.375 runs from -0.125 through 0 (row 16) to 0.117 down the image
_UP, _DN = lin("x", 0.0625, 0.65625), lin("x", -0.0625, -0.65625)
_THIRD = lin("y", 0.25, -0.375)
FTIE = {
    "xy-pn": (const(0.75), _DN, _THIRD),      # x = +0.75, y -> -0.75
    "xy-np": (const(-0.75), _UP, _THIRD),     # x = -0.75, y -> +0.75
    "yz-pn": (_THIRD, const(0.75), _DN),      # y = +0.75, z -> -0.75
    "yz-np": (_THIRD, const(-0.75), _UP),     # y = -0.75, z -> +0.75
}
# texel ties: w = |ma| constant (face +z), u = ma (x / 64 - 1/2), v = ma (y / 32 - 1/2), as
# r8-geo's; |ma| 1.5 and 1.25 (no power of two)
TTIE = {"t%04d" % int(m * 1000): (lin("x", m, -1.5 * m), lin("y", m, -1.5 * m), const(m))
        for m in (1.5, 1.25)}
# bilinear at two new face edges: the major coordinate 0.75, one minor a ramp from 0.564 to 0.749
# of it along x (2 texels a 64-pixel row), the other minor on a texel centre (0.046875: texel 8.5)
# (the plan's -y/+z edge cannot part the rivals: across it the faces' (s, t) of q284_rule.json line
# up, so H-SEAM-ADJ = H-SEAM-WRAP on 96 of 96 out pixels, as on +y/+z, -y/-z, +z/+-y and -z/+y;
# -y towards +x parts them on 96 of 96, tests/test_r9geo.py)
_RAMP = lin("x", 0.1875, 0.376953125)
EDGE = {
    "zx": (_RAMP, const(0.046875), const(0.75)),       # +z towards +x
    "yx": (_RAMP, const(-0.75), const(0.046875)),      # -y towards +x
}
# the control: E726's cu-xn program (byte for byte the published p1141-cube__4.bin)
CONTROL = {"ctl-xn": (NEG, RX, RY)}
# the rivals of each kind of job
SIZE_LAWS = ("E561", "MORTON", "PAIRSWAP")
TIE_RIVALS = ("H-HIGHAXIS", "H-LOWAXIS", "H-POS")
N4_RIVALS = {"H-NN": 16, "H-PAD64": 64}
EDGE_RIVALS = ("H-SEAM-ADJ", "H-SEAM-WRAP")


def jobs():
    """[(name, set, coords, N, T0, kind)] in run order: the control first."""
    out = [("cube-ctl-xn", "control", CONTROL["ctl-xn"], 16, T0_POINT, "control")]
    out += [("cube-n32-" + k, "heldout", v, 32, T0_POINT, "size") for k, v in NEW32.items()]
    out += [("cube-n64-" + k, "heldout", v, 64, T0_POINT, "size") for k, v in SIZED.items()]
    out += [("cube-n4-" + k, "heldout", v, 4, T0_POINT, "n4") for k in ("b1", "b2")
            for v in (SIZED[k],)]
    out += [("cube-ftie-" + k, "heldout", v, 16, T0_POINT, "facetie") for k, v in FTIE.items()]
    out += [("cube-ttie-" + k, "explore", v, 16, T0_POINT, "texeltie") for k, v in TTIE.items()]
    out += [("cube-edge-" + k, "heldout", v, 16, T0_LINEAR, "edge") for k, v in EDGE.items()]
    return out


def pages(n):
    return PAGES64 if n == 64 else None


def twords(n, t0):
    return (t0, T1[n]) + T23


def coords_of(spec):
    return {(x, y): tuple(T.coord(s, x, y) for s in spec) for y in range(T.H) for x in range(T.W)}


def pixel_predictions(R, spec, n, law="MORTON", face_n=None):
    """{(x, y): (state, value)} for every pixel under the rule and a law."""
    return {p: predict(R, c, n, law, face_n) for p, c in coords_of(spec).items()}


# ---- face ties -------------------------------------------------------------------------------
def tie_face(c, rival):
    """The face a tie pixel reads under a rival: H-HIGHAXIS the tied axis of the higher index
    (z > y > x; E931's w over u), H-LOWAXIS the lower one, H-POS the tied axis whose coordinate
    is positive, the higher one when both are [infer: E931's two rows read +z with u = +-0.75]."""
    ax = tied_axes(c)
    if rival == "H-HIGHAXIS":
        a = max(ax)
    elif rival == "H-LOWAXIS":
        a = min(ax)
    elif rival == "H-POS":
        pos = [i for i in ax if c[i] > 0]
        a = max(pos) if pos else max(ax)
    else:
        raise ValueError(rival)
    return 2 * a + (c[a] < 0)


def tie_cells(spec):
    """{(x, y): coordinates} of the face-tie pixels of a program."""
    return {p: c for p, c in coords_of(spec).items() if len(tied_axes(c)) > 1}


# ---- bilinear at a face edge -------------------------------------------------------------------
def taps(v, n):
    """[(texel, weight)] of one axis's bilinear footprint (texel coordinate - 1/2)."""
    u = v - T.F(1, 2)
    f0 = flo(u)
    w = u - f0
    return [(f0, 1 - w), (f0 + 1, w)]


def edge_cells(R, spec, n=16, wmin=0.4):
    """{(x, y): (face, kind)}: "out" when the outer tap of exactly one axis lies past the face
    with a weight of at least wmin, "in" when every tap of non-zero weight is inside the face and
    one axis has a weight in [1/4, 3/4] (r8-geo's definition)."""
    out = {}
    for p, c in coords_of(spec).items():
        q = st(R, c, n)
        if q is None:
            continue
        face, vs, vt, ma, order = q
        outer, blend = [], 0
        for v in (vs, vt):
            (f0, w0), (f1, w) = taps(v, n)
            if (f0 < 0 and w < 1) or (f1 > n - 1 and w > 0):
                outer.append(w0 if f0 < 0 else w)
            elif T.F(1, 4) <= w <= T.F(3, 4):
                blend += 1
        if not outer and blend:
            out[p] = (face, "in")
        elif len(outer) == 1 and outer[0] >= T.F(wmin).limit_denominator(100):
            out[p] = (face, "out")
    return out


def outer_texel(R, c, n, axis_i, texel, rival):
    """The dword index a tap past the face reads under an edge rival. The tap is texel `texel`
    (-1 or n) on axis axis_i (0 = s, 1 = t) of the pixel's face. H-SEAM-ADJ: the texel of the
    neighbour face adjacent across the edge, per the cube-map table, i.e. the face and texel the
    rule gives for the tap centre's direction (the face plane extended past the edge); H-SEAM-WRAP:
    the same neighbour face at the tap's own local (s, t) taken mod n."""
    face, ax = face_of(c)
    r = R[str(face)]
    mi = [i for i in range(3) if i != ax]
    sa, ta = mi[r["s_minor"]], mi[1 - r["s_minor"]]
    ma = abs(c[ax])
    face0, vs, vt, _, order = st(R, c, n)
    loc = [flo(vs), flo(vt)]
    loc[axis_i] = texel
    ctr = [T.F(loc[0]) + T.F(1, 2), T.F(loc[1]) + T.F(1, 2)]
    d = [None] * 3
    d[ax] = c[ax]
    d[sa] = (ctr[0] * 2 / n - 1) * ma / r["s_sign"]
    d[ta] = (ctr[1] * 2 / n - 1) * ma / r["t_sign"]
    nf, nax = face_of(d)
    if nf is None:
        return None
    nface, ns, nt, _, norder = st(R, d, n)
    if rival == "H-SEAM-ADJ":
        s, t = min(max(flo(ns), 0), n - 1), min(max(flo(nt), 0), n - 1)
    elif rival == "H-SEAM-WRAP":
        s, t = loc[0] % n, loc[1] % n
    else:
        raise ValueError(rival)
    return 0xD0000000 | (nface * n * n + local(s, t, norder, n, "MORTON"))


def blend(R, c, n, rival):
    """The bilinear value per byte (exact reals) of a pixel whose taps may pass the face: [(dword,
    weight)] of its taps under an edge rival, or None when a tap has no reading under it."""
    face, vs, vt, ma, order = st(R, c, n)
    out = []
    for s, ws in taps(vs, n):
        for t, wt in taps(vt, n):
            w = ws * wt
            if w == 0:
                continue
            if 0 <= s < n and 0 <= t < n:
                out.append((0xD0000000 | (face * n * n + local(s, t, order, n, "MORTON")), w))
                continue
            if (0 <= s < n) == (0 <= t < n):
                return None          # a corner tap: neither rival names it
            i, tx = (0, s) if not 0 <= s < n else (1, t)
            v = outer_texel(R, c, n, i, tx, rival)
            if v is None:
                return None
            out.append((v, w))
    return out


def blend_bytes(tapl):
    """The exact per-byte blend [b0, b1, b2, b3] (Fractions) of [(dword, weight)]."""
    return [sum(((v >> (8 * i)) & 255) * w for v, w in tapl) for i in range(4)]


TOL = 1    # bytes: E931's in pixels read the exact blend within 0.5 (1536 of 1536 in dz and dx)


# ---- r10-tex: stage cube3 ----------------------------------------------------------------------
# Ties by ramp kind (seeds q284/rows_a.py, its rows_a.json): 16 x 16 faces, point-sampled.
#   cc: both tied coordinates movs of +-0.75, the third a ramp 0.25 (1 + y / 32) + 0.21875 =
#       0.469 to 0.711 (|third| / |ma| 0.625 to 0.948); every pixel a two-axis tie
#   rr: both tied coordinates the bit-identical fmad ramp R (or its exact negation, fmad with K and
#       C negated), 0.1875 (1 + x / 64) + 0.376953125 = 0.564 to 0.749, the third the constant 0.5
# The seeds' finding 3: every lower-axis read of r8-geo and r9-geo's 599 kept tie pixels is a tie
# of two fmad ramps (7 of 34 such pixels); the 565 constant x ramp ties never miss.
_CC3 = lin("y", 0.25, 0.21875)
_RR, _NRR = lin("x", 0.1875, 0.376953125), lin("x", -0.1875, -0.376953125)


def _place(pair, a, b, third):
    c = [None] * 3
    i, j = pair
    c[i], c[j], c[3 - i - j] = a, b, third
    return tuple(c)


PAIRS3 = (((0, 1), "xy"), ((1, 2), "yz"), ((0, 2), "xz"))
CC3 = {}
RR3 = {}
for _pair, _nm in PAIRS3:
    CC3[f"cc-{_nm}-pn"] = _place(_pair, const(0.75), const(-0.75), _CC3)
    CC3[f"cc-{_nm}-pp"] = _place(_pair, const(0.75), const(0.75), _CC3)
    RR3[f"rr-{_nm}-pp"] = _place(_pair, _RR, _RR, const(0.5))
    RR3[f"rr-{_nm}-pn"] = _place(_pair, _RR, _NRR, const(0.5))
# r8-geo's a2 (cube-off-a2, E930): 78 two-axis tie pixels, 4 of the 7 kept lower-axis reads
A2 = OFF["a2"]
R8_A2 = "data:render/closing-r8-geo/out/20261113-015842/cube/cube-off-a2.txt.gz"
R8_A2_BIN = "data:render/closing-r8-geo/bins/cube-off-a2.bin"
TIE3_RIVALS = ("H-HIGHAXIS", "H-FMADNE", "H-THIRD")

# Edges: the major coordinate 0.75, the across coordinate the ramp 0.09375 (1 + x / 64) +
# 0.563232421875 (texel coordinate 15 + (x + 1/2) / 64 on the face: columns 0 to 15 in-face blends
# at weights 1/2 to 3/4, columns 48 to 63 an outer tap of weight 1/4 to 1/2: 16 out columns), the
# along coordinate off the texel centre: texel 7.75 (+z/+x) and 8.25 (-y/+x), across the 7 / 8
# Morton step (index 0x2a to 0x80), where the rivals part on 512 of 512 out pixels by more than
# 2 in a byte; the plan's 7.25 parts them on 0 of 512 at +z/+x (the along taps 6 and 7 differ by
# a few index units, tests/test_gen.py).
_RAMPE = lin("x", 0.09375, 0.563232421875)
EDGE3_ALONG = {"zx": 0.0234375, "yx": 0.0234375}
EDGE3_TEXEL = {"zx": T.F(31, 4), "yx": T.F(33, 4)}
EDGE3_RIVALS = ("H-SEAM-FLOAT", "H-SEAM-ADJ")
WMIN3 = T.F(1, 4)


def edge3_spec(R, k):
    """The coordinates of edge job k with the along constant's sign chosen so that its texel
    coordinate on the pixel's face is EDGE3_TEXEL[k]."""
    for sgn in (1, -1):
        a = sgn * EDGE3_ALONG[k]
        spec = (_RAMPE, const(a), const(0.75)) if k == "zx" else (_RAMPE, const(-0.75), const(a))
        c = tuple(T.coord(s, 0, 0) for s in spec)
        face, vs, vt, ma, order = st(R, c, 16)
        along = vs if 4 <= vs <= 12 else vt          # the across coordinate is near 0 or 16
        if along == EDGE3_TEXEL[k]:
            return spec
    raise ValueError(k)


def tie_axis_tokens(spec, rival, n=16, r8=None, R=None):
    """Per pixel (raster): `aN` (the read's axis, (index // n^2) // 2) at a two-axis tie, the
    rule's dword elsewhere (`-` at a texel tie or a three-axis tie); H-FMADNE on the a2 replay
    is r8-geo's kept image (the replay repeats it)."""
    out = []
    for y in range(T.H):
        for x in range(T.W):
            c = tuple(T.coord(s, x, y) for s in spec)
            ax = tied_axes(c)
            if rival == "H-FMADNE" and r8 is not None:
                out.append("%08x" % r8[(x, y)])
            elif len(ax) == 2:
                out.append("a%d" % max(ax))
            elif len(ax) == 3:
                out.append("-")
            else:
                s, v = predict(R, c, n)
                out.append("%08x" % v if s == "ok" else "-")
    return out


def blend_float(R, c, n):
    """H-SEAM-FLOAT (seeds finding 3, q284/edge_cands.py's cand_bil_own_along): the in-face taps
    as the rule, the outer taps of the across axis replaced by the across weight times the
    neighbour face's bilinear (clamped) at the direction of the outer tap's centre (texel
    coordinate 16.5 or -0.5 across) and the pixel's own continuous along coordinate. [(dword,
    weight)], or None at a corner."""
    face, vs, vt, ma, order = st(R, c, n)
    tapl, ow, oax, otx = [], 0, None, None
    for s, ws in taps(vs, n):
        for t, wt in taps(vt, n):
            w = ws * wt
            if w == 0:
                continue
            if 0 <= s < n and 0 <= t < n:
                tapl.append((0xD0000000 | (face * n * n + local(s, t, order, n, "MORTON")), w))
                continue
            if (0 <= s < n) == (0 <= t < n):
                return None
            i, tx = (0, s) if not 0 <= s < n else (1, t)
            if oax is not None and (oax, otx) != (i, tx):
                return None
            oax, otx = i, tx
            ow += w
    if oax is None:
        return tapl
    fc, ax = face_of(c)
    r = R[str(fc)]
    mi = [i for i in range(3) if i != ax]
    sa, ta = mi[r["s_minor"]], mi[1 - r["s_minor"]]
    tc = T.F(2 * n + 1, 2) if otx == n else T.F(-1, 2)
    cs, ct = (tc, vt) if oax == 0 else (vs, tc)
    d = [None] * 3
    d[ax] = c[ax]
    d[sa] = (cs * 2 / n - 1) * ma / r["s_sign"]
    d[ta] = (ct * 2 / n - 1) * ma / r["t_sign"]
    q = st(R, d, n)
    if q is None:
        return None
    nface, ns, nt, _, norder = q
    for s, ws in taps(ns, n):
        for t, wt in taps(nt, n):
            w = ws * wt
            if w == 0:
                continue
            s2, t2 = min(max(s, 0), n - 1), min(max(t, 0), n - 1)
            tapl.append((0xD0000000 | (nface * n * n + local(s2, t2, norder, n, "MORTON")), ow * w))
    return tapl


def edge_tokens(R, spec, rival, n=16):
    """Per pixel (raster): `i:b0,b1,b2,b3` at an in pixel (the in-face blend), `o:...` at an out
    pixel (the rival's blend), `-` elsewhere; bytes to 4 decimals."""
    cells = edge_cells(R, spec, n, WMIN3)
    out = []
    for y in range(T.H):
        for x in range(T.W):
            if (x, y) not in cells:
                out.append("-")
                continue
            c = tuple(T.coord(s, x, y) for s in spec)
            kind = cells[(x, y)][1]
            if kind == "in":
                tl = blend(R, c, n, "H-SEAM-ADJ")
            elif rival == "H-SEAM-FLOAT":
                tl = blend_float(R, c, n)
            else:
                tl = blend(R, c, n, rival)
            if tl is None:
                out.append("-")
                continue
            out.append("%s:%s" % (kind[0], ",".join("%.4f" % float(b) for b in blend_bytes(tl))))
    return out


def jobs3():
    """[(name, set, coords, N, T0, kind)] of cube3 in run order: the control first."""
    R = rule()
    out = [("cube3-ctl-xn", "control", CONTROL["ctl-xn"], 16, T0_POINT, "control")]
    out += [("cube3-" + k, "heldout", v, 16, T0_POINT, "tie") for k, v in CC3.items()]
    out += [("cube3-" + k, "heldout", v, 16, T0_POINT, "tie") for k, v in RR3.items()]
    out += [("cube3-a2-replay", "replicate", A2, 16, T0_POINT, "replay")]
    out += [("cube3-edge-" + k, "heldout", edge3_spec(R, k), 16, T0_LINEAR, "edge")
            for k in ("zx", "yx")]
    return out
