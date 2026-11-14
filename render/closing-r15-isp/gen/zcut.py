# SPDX-License-Identifier: MIT
"""zcut.py: stage zcut (Q241; E1045, E287, E606, E1037, E065), round 15 plan section 2.

E1045's form (E977's ramp setting: 80 x 40, CR_ISP_ZLSCTL 0x00171014, the depth buffer pre-filled
0xdeadbeef and dumped, ISP word 0 0x01c00200 = compare always with the depth written, every row
also `--pixels`), on triangles with one vertex depth at 1.25 (cut at z = 1) or -0.25 (cut at z = 0).

Three frozen forms of the cut, as images of the target and as the dwords of the 96 x 48 store band
(E465's layout at G 2, E730):
- H-PIXCUT: the plane is drawn unchanged (the triangle's coverage, E606) and a pixel is removed
  iff its depth at the centre lies past [0, 1] (E1045 per pixel). A pixel whose depth is within
  2^-18 of 0 or 1 is undetermined ('?': the hardware iterates the plane in float).
- H-POLYCLIP: the MTE clips the polygon at z = 1 (or 0; E287), each made vertex the exact
  intersection rounded half away from zero to 1/256 pixel on both coordinates (E1037's CLIP-HA),
  the pixels the clipped polygon covers by E606's rule (the centre inside every edge, left and top
  edges owning a tie: gen/q261_rule2.py's own, as gen/guard.py's cover).
- H-POLYCLIP-NR: the same with the made vertices unrounded (exact).
Dwords: a pixel the form draws holds the plane's float within 2^-10 (the clipped polygon's plane
passes the rounded made vertices: a reading of the deviation, not a verdict), every other dword
of the band the background 1.0 (E1045: 0x3f800000 past [0, 1]; E998: every tile dword).

Rows: the cut line is built on the pixel-centre lattice. A line of direction (q, p) through the
centres Lp + k (q, p) (in 1/256 units a centre is (256 X + 128, 256 Y + 128)); the vertices v1 =
m1 Lp1 - (m1 - 1) v0 + r1 and v2 = m2 Lp2 - (m2 - 1) v0 + r2 with the vertex depths a_i = 1.25 -
m_i / 4 (cut at 1) or (m_i - 1) / 4 (cut at 0, apex -0.25) put the crossings at Lp_i + r_i / m_i
(1/256 units, off the grid by up to 1/2): the exact cut line passes within 1/2 unit (1/512 px) of
every centre on the lattice line between them, the rounded one through the (now on-lattice) made
vertices makes those centres exact ties, so H-POLYCLIP parts from H-PIXCUT and H-POLYCLIP-NR on
the pixels where the tie's owner differs from the exact side. H-PIXCUT and H-POLYCLIP-NR are one
image except on an exact tie (undetermined for H-PIXCUT): no row can part them."""
import fractions
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import guard as G  # noqa: E402
import q261_rule2 as R2  # noqa: E402

F = fractions.Fraction
W, H, TW, TH, GP = 80, 40, 96, 48, 2
ALWAYS = 0x01C00200
ONE, BG_FILL = 0x3F800000, 0xDEADBEEF
NEAR = 2.0 ** -10               # the drawn dword's tolerance to the plane
EPS_PIX = F(1, 1 << 18)         # H-PIXCUT undetermined within this depth of 0 or 1
MODELS = ("H-PIXCUT", "H-POLYCLIP", "H-POLYCLIP-NR")
MAIN = ("tri --keep-going --wait-ms 20000 --width 80 --height 40 --max-width 80 --max-height 40 "
        "--tri-v %s --tri-z %s --depth --depth-ctl 0x00171014 --depth-fill 0xdeadbeef "
        '--depth-dump "$W" --poke blk:1=0x%08x --pixels')
GUARD = (-20, 100, -10, 50)     # H-VP's box on 80 x 40 (a vertex inside it is not guard-clipped)
VP = G.default_vp(W, H)
E1045 = "data:render/closing-r14-isp/out/20261114-060059/wind/"
E065 = "data:isp/pass-counters/tri-isp-timeline/raw.txt"
# E1045's two depth rows, the controls (replicated byte for byte): name, kept, tri-v, tri-z
CTL_Z = (("zcut-ctl-zhi", "wind-zhi", "0,0,40960,0,0,20480", "1.25,0.25,1.25"),
         ("zcut-ctl-zlo", "wind-zlo", "0,0,40960,0,0,20480", "0.25,-0.75,0.25"))
HASH_ZHI, HASH_ZLO = "0x1ae0dc9078287f25", None   # zlo's from the kept file (make.py)
E065_ROWS = (("zcut-ctl-b15", "control", 0x8000, "H-EQUIV", "blk:1^=0x8000"),
             ("zcut-b16", "heldout", 0x10000, None, "blk:1^=0x10000"),
             ("zcut-b17", "heldout", 0x20000, None, "blk:1^=0x20000"))
E065_KEPT = {0x8000: (48, "0x7e7562918f5b5125"), 0x10000: (0, "0xfc5ff15e0434a325"),
             0x20000: (0, "0xfc5ff15e0434a325")}


def f32(x):
    return F(struct.unpack("<f", struct.pack("<f", float(x)))[0])


def bits_of(f):
    return struct.unpack("<I", struct.pack("<f", float(f)))[0]


def in_tile_index(x, y):
    x, y, i = x & 31, y & 15, 0
    for b in range(4):
        i |= ((y >> b) & 1) << (2 * b) | ((x >> b) & 1) << (2 * b + 1)
    return i | ((x >> 4) & 1) << 8


def store_dword(x, y, g=GP):
    """sgx-pipe zls.rs store_dword (E465): 512 (ty (G + 1) + tx) + the in-tile index"""
    return 512 * ((y >> 4) * (g + 1) + (x >> 5)) + in_tile_index(x, y)


# ---------------------------------------------------------------- the rows
def tri_args(vt, depths, order="fwd"):
    """the tool's --tri-v and --tri-z text of a row, vertices (v0, v1, v2) of ints in 1/256 px"""
    idx = (0, 1, 2) if order == "fwd" else (0, 2, 1)
    v = ",".join("%d,%d" % tuple(vt[i]) for i in idx)
    z = ",".join(("%g" % depths[i]) for i in idx)
    return v, z


def window_variants(flat):
    """the vertices (1/256 integers) the hardware may see for the six tool integers (guard.variants)"""
    return G.variants(list(flat), 8, W, H, VP)


# ---------------------------------------------------------------- the geometry
def plane_fn(V, Z):
    (x0, y0), (x1, y1), (x2, y2) = V
    det = F((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0))
    gx = ((Z[1] - Z[0]) * (y2 - y0) - (Z[2] - Z[0]) * (y1 - y0)) / det
    gy = ((Z[2] - Z[0]) * (x1 - x0) - (Z[1] - Z[0]) * (x2 - x0)) / det
    return lambda X, Y: Z[0] + gx * (X - x0) + gy * (Y - y0)


def centre(x, y):
    return 256 * x + 128, 256 * y + 128


def cover_exact(P, w, h):
    """[bool] raster w x h: the centre inside every edge of the CCW polygon P (Fractions, 1/256),
    left and top edges owning a tie (R2.own); G.cover's test at any rational vertices"""
    out = [False] * (w * h)
    if len(P) < 3:
        return out
    n = len(P)
    edges = [(P[i], P[(i + 1) % n][0] - P[i][0], P[(i + 1) % n][1] - P[i][1]) for i in range(n)]
    for y in range(h):
        for x in range(w):
            X, Y = centre(x, y)
            ok = True
            for p, dx, dy in edges:
                e = dx * (Y - p[1]) - dy * (X - p[0])
                if not (e > 0 or (e == 0 and R2.own(dx, dy))):
                    ok = False
                    break
            out[y * w + x] = ok
    return out


def clip_z(V, Z, rule):
    """the oriented triangle (CCW, V ints with depths Z) clipped to 0 <= z <= 1: the vertices
    (x, y) of the polygon, made ones rounded by rule (HA, or None: exact)"""
    poly = [(F(v[0]), F(v[1]), z) for v, z in zip(V, Z)]
    for bound, keep_ge in ((F(1), False), (F(0), True)):
        out, n = [], len(poly)
        for i in range(n):
            p, q = poly[i], poly[(i + 1) % n]
            pi = (p[2] >= bound) if keep_ge else (p[2] <= bound)
            qi = (q[2] >= bound) if keep_ge else (q[2] <= bound)
            if pi:
                out.append(p)
            if pi != qi:
                t = (bound - p[2]) / (q[2] - p[2])
                x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
                if rule:
                    x, y = G.CLIP_RULES[rule](x), G.CLIP_RULES[rule](y)
                out.append((F(x), F(y), bound))
        poly = out
        if not poly:
            return []
    return [(p[0], p[1]) for p in poly]


def oriented_z(V, Z):
    """V, Z reordered to G.oriented's winding"""
    O = G.oriented(V)
    if O is None:
        return None, None
    zs = {tuple(v): z for v, z in zip(V, Z)}
    return O, [zs[tuple(v)] for v in O]


def images(flat, depths):
    """{model: [True | False | None] over the TW x TH band} for the row: the vertices the tool
    gets as six integers `flat` and the three depths (a pixel the hardware's float32 window
    vertices part is None)"""
    per = []
    for V in window_variants(flat):
        Z = [f32(z) for z in depths]
        O, OZ = oriented_z(V, Z)
        plane = plane_fn(V, Z)
        tri = G.cover(O, TW, TH)
        ims = {"H-PIXCUT": [None] * (TW * TH)}
        for j in range(TW * TH):
            if not tri[j]:
                ims["H-PIXCUT"][j] = False
                continue
            z = plane(*centre(j % TW, j // TW))
            if min(abs(z), abs(z - 1)) < EPS_PIX:
                ims["H-PIXCUT"][j] = None
            else:
                ims["H-PIXCUT"][j] = 0 <= z <= 1
        ims["H-POLYCLIP"] = cover_exact(clip_z(O, OZ, "HA"), TW, TH)
        ims["H-POLYCLIP-NR"] = cover_exact(clip_z(O, OZ, None), TW, TH)
        per.append(ims)
    out = {}
    for m in MODELS:
        out[m] = G.merged([p[m] for p in per])
    return out


def planes(flat, depths):
    """[(plane function, (min x, max x)...)] per variant: the plane of the original triangle"""
    return [plane_fn(V, [f32(z) for z in depths]) for V in window_variants(flat)]


def model_of(flat, depths, label):
    """{"drawn": [True | False | None] over W x H, "dwords": {index: (kind, value)}} of one form"""
    img = images(flat, depths)[label]
    pl = planes(flat, depths)
    dw = {}
    for y in range(TH):
        for x in range(TW):
            s = img[y * TW + x]
            if s is None:
                continue
            if s:
                zs = [float(p(*centre(x, y))) for p in pl]
                dw[store_dword(x, y)] = ("near", sum(zs) / len(zs))
            else:
                dw[store_dword(x, y)] = ("eq", ONE)
    drawn = [img[y * TW + x] for y in range(H) for x in range(W)]
    return {"drawn": drawn, "dwords": dw}


def ztext(m):
    out = ["".join("?" if v is None else "1" if v else "0" for v in m["drawn"][y * W:(y + 1) * W])
           for y in range(H)]
    for i in sorted(m["dwords"]):
        k, v = m["dwords"][i]
        out.append("%d %s %s" % (i, k, "0x%08x" % v if k == "eq" else repr(v)))
    return "\n".join(out) + "\n"


def zparse(text):
    ln = text.splitlines()
    drawn = [None if c == "?" else c == "1" for c in "".join(ln[:H])]
    dw = {}
    for t in ln[H:]:
        i, k, v = t.split()
        dw[int(i)] = (k, int(v, 16) if k == "eq" else float(v))
    return {"drawn": drawn, "dwords": dw}


def ones_range(m):
    """(least, most) dwords of the band holding the background 1.0 under the form: the dwords it
    says are 1.0, and those plus the pixels it does not claim"""
    lo = sum(1 for k, v in m["dwords"].values() if k == "eq")
    return lo, lo + TW * TH - len(m["dwords"])


def parse_ones(text):
    """the count of 0x3f800000 in the `depth #1:` line's list of the commonest words, or None"""
    m = re.search(r"^depth #1: .*?; (.*)$", text or "", re.M)
    if not m:
        return None
    mm = re.search(r"0x3f800000 x (\d+)", m.group(1))
    return int(mm.group(1)) if mm else None


def zcheck(m, text, drawn):
    """True when the target image and the count of background dwords in the output's depth line
    are the form's wherever it claims (None: no data); a '?' pixel claims nothing"""
    ones = parse_ones(text)
    if drawn is None or ones is None:
        return None
    for a, b in zip(drawn, m["drawn"]):
        if b is not None and a != b:
            return False
    lo, hi = ones_range(m)
    return lo <= ones <= hi


# name, apex, tool vertex order, (v0, v1, v2) in 1/256 px, depths (v0, v1, v2): found by seeded
# search (the construction in the header; every row: 6+ pixels where H-POLYCLIP parts from
# H-POLYCLIP-NR and H-PIXCUT, none undetermined, all vertices inside H-VP's guard: tests)
ROWS = (
    ("zcut-hi1", "hi", "fwd", ((16256, 4480), (-1407, -1665), (19329, 12160)), (1.25, 0.5, 0.5)),
    ("zcut-hi2", "hi", "rev", ((10880, 7808), (18560, 1665), (-3455, 7808)), (1.25, 0.5, 0.25)),
    ("zcut-hi3", "hi", "fwd", ((9344, 7808), (20865, 897), (-3969, 5761)), (1.25, 0.5, 0.25)),
    ("zcut-lo1", "lo", "rev", ((3456, 2176), (24960, 1153), (4481, 11393)), (-0.25, 0.75, 0.75)),
    ("zcut-lo2", "lo", "fwd", ((4992, 1152), (22913, 2433), (-1152, 10369)), (-0.25, 1.0, 0.5)),
    ("zcut-lo3", "lo", "rev", ((15488, 6528), (-2943, 7295), (17024, 11647)), (-0.25, 0.5, 0.25)),
)


def row_args(r):
    name, apex, order, V, d = r
    vt, zt = tri_args(V, d, order)
    return MAIN % (vt, zt, ALWAYS)


def row_flat(r):
    vt, _ = tri_args(r[3], r[4], r[2])
    return [int(t) for t in vt.split(",")]


def row_depths(r):
    _, zt = tri_args(r[3], r[4], r[2])
    return [float(t) for t in zt.split(",")]
