# SPDX-License-Identifier: MIT
"""cube.py: stage cube (R8-2, Q284): the cube-map (s, t) rule frozen offline before this session
(closing8/rank/q284_st.py fit on E726's eight jobs, frozen by sha256 52162471..., held out on
E844's two jobs 4090 of 4096, the 6 misses exact texel ties at a |ma| that is no power of two;
gen/q284_rule.json is that file byte for byte) and the jobs that test it. Standard library only.

The rule [infer, fitted on E726, held out on E844]: the face is the coordinate of largest magnitude
and its sign (face = 2 axis + (c < 0), +x, -x, +y, -y, +z, -z = 0 to 5); per face the minor axis
to s, the signs and the Morton order of q284_rule.json; texel = floor((q + 1) / 2 * N) with
q = sign * c / |ma|; index = face * N * N + Morton(s, t) (log2 N bits each); value = 0xD0000000 |
index (the probe's scratch fill). Two kinds of pixel are no prediction ("cannot tell"):
  face tie   the two largest magnitudes equal (the face select is not frozen there)
  texel tie  (q + 1) / 2 * N exactly an integer while |ma| is no power of two (E844's 6 misses
             and E726's 8 were all such; at a power-of-two |ma| the upper texel was read 3043 of
             3043 times, so those stay predicted)."""
import hashlib
import json
import os

import texprog as T

HERE = os.path.dirname(os.path.abspath(__file__))
RULE_SHA = "52162471d1c80fd1d17a969b2de3216dfcab6fd76b34f824af9a23f81631bd61"
SMP = "smp3d r10, r24, r20, drc0"
T0_POINT = 0x07fe0000          # E726's: no LOD bias, level 0 only, nearest, repeat
T0_LINEAR = 0x07fe1400         # the same with T0.MAGFILTER (13:12) and T0.MINFILTER (11:10) 1
T1 = {8: 0x4c007007, 16: 0x4c00f00f, 32: 0x4c01f01f}   # TEXTYPE 2, width - 1, height - 1
T23 = (0x5caf0000, 0x00800800)  # the scratch buffer's address (SCRATCH_IMM), E726's T3


def rule():
    blob = open(os.path.join(HERE, "q284_rule.json"), "rb").read()
    if hashlib.sha256(blob).hexdigest() != RULE_SHA:
        raise SystemExit("gen/q284_rule.json is not the frozen rule")
    return json.loads(blob)


def twid(s, t, order, nb):
    i = 0
    for b in range(nb):
        lo, hi = (t, s) if order == "ty" else (s, t)
        i |= ((lo >> b) & 1) << (2 * b) | ((hi >> b) & 1) << (2 * b + 1)
    return i


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


def st(R, c, N):
    """(face, s texel coordinate, t texel coordinate) as exact fractions of texels, or None."""
    face, ax = face_of(c)
    if face is None:
        return None
    r = R[str(face)]
    mi = [i for i in range(3) if i != ax]
    sa, ta = mi[r["s_minor"]], mi[1 - r["s_minor"]]
    ma = abs(c[ax])
    vs = (r["s_sign"] * c[sa] / ma + 1) / 2 * N
    vt = (r["t_sign"] * c[ta] / ma + 1) / 2 * N
    return face, vs, vt, ma, r["order"]


def predict(R, c, N):
    """("ok", value) | ("face-tie", None) | ("texel-tie", None)."""
    p = st(R, c, N)
    if p is None:
        return "face-tie", None
    face, vs, vt, ma, order = p
    if not pow2(ma) and (vs.denominator == 1 or vt.denominator == 1):
        return "texel-tie", None
    s = min(max(vs.numerator // vs.denominator, 0), N - 1)
    t = min(max(vt.numerator // vt.denominator, 0), N - 1)
    nb = N.bit_length() - 1
    return "ok", 0xD0000000 | (face * N * N + twid(s, t, order, nb))


def lin(ax, k, c):
    return ("lin", ax, T.bits(k), T.bits(c))


def const(v):
    return ("bits", T.bits(v))


ONE, NEG = const(1.0), const(-1.0)
RX, RY = lin("x", 1.5, -2.25), lin("y", 1.5, -2.25)
# (a) four new off-axis programs at 16 x 16, all three coordinates non-zero in every pixel, the
# dominant axis changing inside each image, all six faces between them (tests/test_gen.py)
OFF = {
    "a1": (lin("x", 1.5, -2.25), lin("y", 1.5, -2.25), const(-0.625)),
    "a2": (const(0.625), lin("x", 1.5, -2.5), lin("y", 1.5, -2.0)),
    "a3": (lin("y", 2.0, -3.0), const(0.6875), lin("x", 1.5, -2.25)),
    "a4": (lin("x", 1.5, -2.0), const(-0.6875), lin("y", 1.5, -2.5)),
}
# (b) the same rule at 8 x 8 and 32 x 32 faces, three directions each
SIZED = {"b1": OFF["a1"], "b2": OFF["a2"], "b3": OFF["a4"]}
# (c) face ties: |w| crosses |u| at 1/1024 a column, the tie in column x = 32 (32 pixels a job)
FTIE = {
    "fu": (const(0.75), lin("y", 0.25, -0.5), lin("x", 0.0625, 0.65625)),     # +x against +z
    "fn": (const(-0.75), lin("y", 0.25, -0.5), lin("x", 0.0625, 0.65625)),    # -x against +z
}
# (c) texel ties: w = |ma| constant (face +z), u = ma (x / 64 - 1/2), v = ma (y / 32 - 1/2): the
# s texel boundary at every 8th column, the t boundary at every 4th row, |ma| of the pairs that
# went both ways offline (q284_tievar.out)
TTIE = {"t%04d" % int(m * 1000): (lin("x", m, -1.5 * m), lin("y", m, -1.5 * m), const(m))
        for m in (1.75, 1.625, 1.875, 0.90625)}
# (d) bilinear at a face's edge: +x with v, +z with -u, running from 0.56 of the major coordinate
# (2 texels a 64-pixel row) to |c| = 0.749 < 0.75 of the major one, the other minor a sixteenth
# of |ma| off the face's centre line (no blend on that axis)
EDGE = {
    "dx": (const(0.75), lin("x", 0.1875, 0.376953125), const(0.046875)),
    "dz": (lin("y", -0.1875, -0.37890625), const(0.046875), const(0.75)),
}
# the control: E726's cu-xn program (byte for byte the published p1141-cube__4.bin)
CONTROL = {"ctl-xn": (NEG, RX, RY)}


def jobs():
    """[(name, set, coords, N, T0, kind)] in run order: the control first."""
    out = [("cube-ctl-xn", "control", CONTROL["ctl-xn"], 16, T0_POINT, "control")]
    out += [("cube-off-" + k, "heldout", v, 16, T0_POINT, "rule") for k, v in OFF.items()]
    for n in (8, 32):
        out += [("cube-n%d-%s" % (n, k), "heldout", v, n, T0_POINT, "rule")
                for k, v in SIZED.items()]
    out += [("cube-ftie-" + k, "explore", v, 16, T0_POINT, "facetie") for k, v in FTIE.items()]
    out += [("cube-ttie-" + k, "explore", v, 16, T0_POINT, "texeltie") for k, v in TTIE.items()]
    out += [("cube-edge-" + k, "heldout", v, 16, T0_LINEAR, "edge") for k, v in EDGE.items()]
    return out


def twords(n, t0):
    return (t0, T1[n]) + T23


def coords_of(spec):
    return {(x, y): tuple(T.coord(s, x, y) for s in spec) for y in range(T.H) for x in range(T.W)}


def pixel_predictions(R, spec, n):
    """{(x, y): (state, value)} for every pixel under the rule."""
    return {p: predict(R, c, n) for p, c in coords_of(spec).items()}


# ---- (d): bilinear at a face edge ----------------------------------------------------------
def edge_cells(R, spec, n=16, wmin=0.4):
    """{(x, y): (face, kind)} of the pixels the edge rivals call: kind "out" when the bilinear
    footprint (texel coordinate - 1/2, taps floor and floor + 1) has its outer tap past the face
    on exactly one axis with a weight of at least wmin, "in" when every tap of non-zero weight is
    inside the face and one axis has a weight in [1/4, 3/4] (the filter must blend those). H-CLAMP: an "out" pixel's G
    byte (the face of a 16 x 16 tap) is its own face; H-SEAM: it is not (taps from the
    neighbour face [infer: by the GL cube table], faces differ by at least 1, weight >= 0.4).
    """
    out = {}
    for p, c in coords_of(spec).items():
        q = st(R, c, n)
        if q is None:
            continue
        face, vs, vt, ma, order = q
        outer, blend = [], 0
        for v in (vs, vt):
            u = v - T.F(1, 2)
            f0 = u.numerator // u.denominator
            w = u - f0
            if (f0 < 0 and w < 1) or (f0 + 1 > n - 1 and w > 0):
                outer.append(1 - w if f0 < 0 else w)
            elif T.F(1, 4) <= w <= T.F(3, 4):
                blend += 1
        if not outer and blend:
            out[p] = (face, "in")
        elif len(outer) == 1 and outer[0] >= T.F(wmin).limit_denominator(100):
            out[p] = (face, "out")
    return out
