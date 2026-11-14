# SPDX-License-Identifier: MIT
"""pivot.py: stage pivot (round 10 seeds plan section 9, S10-geo, Q261): E979's far-x23p, far-x24p
and far-x25n triangles (r9-x's gen/far.py, a byte copy: one vertex at 2^23, 2^24 and -2^25 pixels,
tool t4 `tri --tri-v` at --tri-unit 5, 64 x 64), with the far vertex's y moved by d whole pixels.

E979's band (the seeds plan's finding 4, closing10/seeds/q261/band_far.out, post hoc): of the
pixels within 1e-3 pixel of an edge line, 26 differ from the exact coverage, all exact-out but
drawn, along the far edge that starts at the near vertex N; moving the far vertex F by a y
displacement of at least 43, 52 and 42 pixels (and up to the search's 400) fits every band pixel
(pivot.out). In-span (between N and the target's border) the band pixels' centres lie on one
lattice line through N, so as F moves along y the edge pivots on N and every such pixel of a
triangle flips at ONE displacement t*: 42.6, 51.4 and 41.6 pixels (pixel_intervals() below,
exact in rationals; tests/test_gen.py). The seeds plan's d from -128 to +640 is mostly on the
wrong side: under H-PIVOT (the hardware draws the exact coverage of F + (0, d + D)) a row with d
> t* - D draws as E979 did whatever D is, so the informative rows have d <= 0: the row at d draws
the in-span band pixels iff d + D > t*. d runs 0 (E979's replicate), then -16 .. -544, so the
rows bracket D in steps of 16 up to t* + 64, 32 up to t* + 160, 64 up to t* + 288 and 128 up to
t* + 544 (README.md "Deviations").

Frozen per row (predictions/pivot/NAME.MODEL.txt, 64 lines of 64 characters):
  H-EXACT       the exact coverage at the row's own vertices (E606/E607: 1/256 grid, half up,
                centre test, owning edges), no band: '1' drawn, '0' not
  H-EXACT-BAND  as E979 froze it: the same, '?' within 1e-3 pixel of an edge line
and per row the pixel intervals of H-PIVOT (NAME.ivals.txt: for every pixel whose coverage
changes at a finite displacement s of F's y within +-2^20 pixels, `x y lo hi`, lo and hi the
open interval of s where it is inside, '-' unbounded; every other pixel keeps its H-EXACT state
for every such s). The scorer finds, per row, the set of D with the row's image = the coverage
at s = d + D on all 4096 pixels, and per triangle the intersection over its 12 rows.
Control (can fail): E684's far21d0 (E979's far-ctl, exact outside the band there)."""
import fractions
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import far as FA  # noqa: E402

F = fractions.Fraction
STAGE = "pivot"
TRIS = ("far-x23p", "far-x24p", "far-x25n")
DLIST = (0, -16, -32, -48, -64, -96, -128, -160, -224, -288, -416, -544)
SMAX = F(1 << 20)         # displacements beyond +-2^20 pixels are not modelled (the rows reach 544)
MODELS = ("H-EXACT", "H-EXACT-BAND")


def verts_px(name):
    return dict(FA.FAR)[name]


def far_index(vp):
    return max(range(3), key=lambda i: abs(vp[i][0]) + abs(vp[i][1]))


def moved(vp, d):
    fi = far_index(vp)
    out = list(vp)
    out[fi] = (vp[fi][0], vp[fi][1] + d)
    return tuple(out)


def row_name(tri, d):
    return "piv-%s-%s" % (tri[4:], "d0" if d == 0 else "m%d" % -d)


def pixel_intervals(vp):
    """{(x, y): (lo, hi)} for the pixels whose inside-ness changes at a finite displacement s
    of the far vertex's y (|endpoint| <= SMAX), the vertices on E607's 1/256 grid (the far one
    at s = 0; s moves it in whole 1/256 steps only if s is a multiple of 1/256, as every row's
    is), the centre test with owning edges at a tie (inside when lo < s < hi; at s = lo or hi the
    tie rule decides, which no row's whole d reaches unless D is a breakpoint)."""
    V = [(F(FA.grid(x), 256), F(FA.grid(y), 256)) for x, y in vp]
    fi = far_index(vp)
    a, b, c = V
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    order = [0, 1, 2] if area > 0 else [0, 2, 1]
    W = [V[i] for i in order]
    fr = [1 if i == fi else 0 for i in order]
    out = {}
    for y in range(64):
        for x in range(64):
            P = (F(2 * x + 1, 2), F(2 * y + 1, 2))
            lo = hi = None
            empty = False
            for k in range(3):
                p, q = W[k], W[(k + 1) % 3]
                dp, dq = fr[k], fr[(k + 1) % 3]
                e0 = (q[0] - p[0]) * (P[1] - p[1]) - (q[1] - p[1]) * (P[0] - p[0])
                e1 = -(q[0] - p[0]) * dp - (dq - dp) * (P[0] - p[0])
                if e1 == 0:
                    empty |= e0 <= 0
                    continue
                t = -e0 / e1
                if abs(t) > SMAX:
                    if (e1 > 0 and t > 0) or (e1 < 0 and t < 0):
                        empty = True        # inside only beyond the modelled range
                    continue
                if e1 > 0:
                    lo = t if lo is None else max(lo, t)
                else:
                    hi = t if hi is None else min(hi, t)
            if empty or (lo is None and hi is None):
                continue
            out[(x, y)] = (lo, hi)
    return out


def ivals_text(iv):
    def f(v):
        return "-" if v is None else "%d/%d" % (v.numerator, v.denominator)
    return "".join("%d %d %s %s\n" % (x, y, f(lo), f(hi))
                   for (x, y), (lo, hi) in sorted(iv.items(), key=lambda kv: (kv[0][1], kv[0][0])))


def ivals_parse(text):
    def f(v):
        return None if v == "-" else F(v)
    out = {}
    for ln in text.splitlines():
        x, y, lo, hi = ln.split()
        out[(int(x), int(y))] = (f(lo), f(hi))
    return out


def cov_text(c):
    return "".join("".join("?" if v is None else "1" if v else "0" for v in c[y * 64:(y + 1) * 64])
                   + "\n" for y in range(64))


def predictions(vp):
    """{model: [drawn (True/False) or None per pixel, raster order]}"""
    v = [(FA.grid(x), FA.grid(y)) for x, y in vp]
    cov = FA.coverage(v)
    ex = [cov[(i % 64, i // 64)][0] for i in range(4096)]
    band = [None if cov[(i % 64, i // 64)][1] else ex[i] for i in range(4096)]
    return {"H-EXACT": ex, "H-EXACT-BAND": band}


def jobs():
    """[(name, set, knobs, args, {model: coverage}, ivals text or None)]"""
    out = []
    n, v = FA.E684_CTL
    pv = [(F(v[2 * i], 256), F(v[2 * i + 1], 256)) for i in range(3)]
    out.append(("piv-ctl", "control", "expectdiff reads:job,pixels",
                f"{FA.MAIN} --tri-v {','.join(map(str, v))} --pixels",
                {"H-EXACT-BAND": FA.predictions(pv)["H-EXACT"]}, None))
    for tri in TRIS:
        for d in DLIST:
            vp = moved(verts_px(tri), d)
            tv = ",".join(str(FA.u(c)) for p in vp for c in p)
            out.append((row_name(tri, d), "replicate" if d == 0 else "heldout", "expectdiff",
                        f"{FA.MAIN} --tri-unit {FA.UNIT} --tri-v {tv} --pixels",
                        predictions(vp), ivals_text(pixel_intervals(vp))))
    return out
