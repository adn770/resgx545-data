# SPDX-License-Identifier: MIT
"""rows.py: the rows of stages g14 (Q261) and clipr (Q199), their vertices designed here with
guard.py's engine (seeded, deterministic; tests/test_gen.py checks every premise).

A row is a dict: name, set, knobs, W, H, unit, vt (the tool's six integers), vp (the viewport
the row's words give, window = offset + scale ndc), pokes (`--poke blk:N=V` words), side (the
far vertex's side), parts (the bound values the row was designed to part), kept (the kept output
a control or replicate must draw), kind (guard: the guard hypotheses and the side's family;
tie: the clip-made vertex's rounding; intie: a vertex inside the guard on a tie; int32: the
int32 ends with far.py's H-SAT, H-WRAP, H-CULL)."""
import os
import sys
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import far as FA  # noqa: E402
import guard as G  # noqa: E402

KEPT = {"far-ctl": "data:render/closing-r9-x/out/20261113-081821/far/far-ctl.txt.gz",
        "t128-1": "data:render/closing-r13-isp/out/20261113-215416/q261/q261-t128-1.txt.gz",
        "x30p": "data:render/closing-r13-isp/out/20261113-215416/far/far-x30p.txt.gz"}
# E979's near vertices (c6, r13-isp gen/clip.py NEAR), in pixels of a 64 x 64 target
NEAR = {"pos-x": ((F(25, 4), F(37, 4)), (F(19, 2), F(215, 4))),
        "neg-x": ((F(225, 4), F(31, 4)), (F(113, 2), F(223, 4))),
        "neg-y": ((F(27, 4), F(233, 4)), (F(229, 4), F(219, 4))),
        "pos-y": ((F(29, 4), F(25, 4)), (F(225, 4), F(31, 4)))}
FAR_X = {"pos-x": ((2 ** 22, 2 ** 24 - 1), (-2 ** 22, 2 ** 22)),
         "neg-x": ((-2 ** 24 + 1, -2 ** 22), (-2 ** 22, 2 ** 22)),
         "pos-y": ((-2 ** 22, 2 ** 22), (2 ** 22, 2 ** 24 - 1)),
         "neg-y": ((-2 ** 22, 2 ** 22), (-2 ** 24 + 1, -2 ** 22))}
VP32, VP64 = 0x42000000, 0x42800000      # 32.0 and 64.0, the viewport words of the vp rows


def near(side, W, H):
    return tuple((x * F(W, 64), y * F(H, 64)) for x, y in NEAR[side])


def others(W, H, vp, side):
    """the other bounds' values each designed image must not depend on: H-VP's and 8 pixels
    either side, and E1023's 64 x 64 values (x >= -9, -16; y in [-16, 80])"""
    b = G.boxes(W, H, vp)["H-VP"]
    out = {}
    for s, i in G.SIDES.items():
        if s == side:
            continue
        v = b[i]
        out[s] = sorted({v, v - 8, v + 8} | ({F(-9), F(-16)} if s == "neg-x" else set()))
    return out


def row(name, st, W, H, unit, pts, vp, side, kind="guard", parts=(), pokes=(), kept=None, knobs=None):
    vt = G.to_units(pts, unit, W, H, vp)
    return dict(name=name, set=st, knobs=knobs or ("expectdiff reads:job,pixels" if st == "control" else "expectdiff"),
                W=W, H=H, unit=unit, vt=vt, vp=vp, pokes=tuple(pokes), side=side, kind=kind,
                parts=tuple(parts), kept=kept)


def args(r):
    a = G.MAIN % (r["W"], r["H"], r["W"], r["H"])
    a += " --tri-unit %d --tri-v %s" % (r["unit"], ",".join(map(str, r["vt"])))
    for p in r["pokes"]:
        a += " --poke %s" % p
    return a + " --pixels"


def from_units(name, st, W, unit, vt, kept, side="pos-x"):
    vp = G.default_vp(W, W)
    pts = [(F(vt[2 * i], 1 << unit), F(vt[2 * i + 1], 1 << unit)) for i in range(3)]
    return row(name, st, W, W, unit, pts, vp, side, kept=kept)


# ---------------------------------------------------------------- g14 (Q261)
G14 = (  # name, W, H, side, n, parts (bound values), seed
    ("g14-64-nx", 64, 64, "neg-x", 2, (-9, -16), 14061),
    ("g14-128-px", 128, 128, "pos-x", 2, (147, 160, 173, 186), 14062),
    ("g14-128-nx", 128, 128, "neg-x", 2, (-32, -16, -9, -19), 14063),
    ("g14-128-ny", 128, 128, "neg-y", 1, (-32, -16), 14064),
    ("g14-128-py", 128, 128, "pos-y", 1, (160, 147, 173), 14065),
    ("g14-256-px", 256, 256, "pos-x", 1, (320, 275, 294), 14066),
    ("g14-256-nx", 256, 256, "neg-x", 1, (-64, -16, -9), 14067),
    ("g14-256-py", 256, 256, "pos-y", 1, (320, 275, 294), 14068),
    ("g14-256-ny", 256, 256, "neg-y", 1, (-64, -16), 14069),
    ("g14-128x64-px", 128, 64, "pos-x", 1, (160, 144, 147), 14070),
    ("g14-128x64-py", 128, 64, "pos-y", 1, (80, 96), 14071),
    ("g14-64x128-px", 64, 128, "pos-x", 1, (80, 96), 14072),
    ("g14-64x128-py", 64, 128, "pos-y", 1, (160, 144, 147), 14073),
)


def g14_rows(pool=40):
    """E979's far-ctl (E684's far21d0) first, the in-range held-out rows, E1023's t128-1 replicate,
    then the poked-viewport rows (last: the stage stops at the first job that is not ok)"""
    rows = [from_units("g14-ctl-far21", "control", 64, 8, list(FA.E684_CTL[1]), "far-ctl")]
    for name, W, H, side, n, parts, seed in G14:
        vp = G.default_vp(W, H)
        xr, yr = FAR_X[side]
        ch, _ = design_cached(name, W, H, vp, side, near(side, W, H), xr, yr, n, pool, seed, parts)
        for i, pts in enumerate(ch):
            rows.append(row("%s%s" % (name, "" if n == 1 else "-%d" % (i + 1)), "heldout", W, H, 5, pts, vp,
                            side, parts=parts))
    rows.append(from_units("g14-ctl-t128", "control", 128, 5, [400, 592, 608, 3440, 257450388, 31020207],
                           "t128-1"))
    rows += vp_rows(pool)
    return rows


def vp_rows(pool):
    """128 x 128 with the viewport poked to 64 x 64 at the origin (words 6 to 9 = 32.0): the far
    vertex along +x, then +y (H-VP cuts at window 80, H-TGT draws to 127); 64 x 64 with the viewport
    poked to 128 x 128 (words 6 to 9 = 64.0): along +x, band pixels part 160 (H-VP) from 80 (H-TGT)"""
    out = []
    v32 = (F(32), F(32), F(32), F(32))
    pokes = ["blk:%d=0x%08x" % (k, VP32) for k in (6, 7, 8, 9)]
    pts = NEAR["pos-x"] + ((F(2 ** 22), F(2 ** 18)),)
    out.append(row("g14-vp64-px", "heldout", 128, 128, 5, pts, v32, "pos-x", pokes=pokes, parts=(80, 160)))
    pts = NEAR["pos-y"] + ((F(2 ** 18), F(2 ** 22)),)
    out.append(row("g14-vp64-py", "heldout", 128, 128, 5, pts, v32, "pos-y", pokes=pokes, parts=(80, 160)))
    v64 = (F(64), F(64), F(64), F(64))
    pokes = ["blk:%d=0x%08x" % (k, VP64) for k in (6, 7, 8, 9)]
    xr, yr = FAR_X["pos-x"]
    ch, _ = design_cached("g14-vp128-px", 64, 64, v64, "pos-x", NEAR["pos-x"], xr, yr, 1, pool, 14074, (160, 80), grid=16)
    out.append(row("g14-vp128-px", "heldout", 64, 64, 5, ch[0], v64, "pos-x", pokes=pokes, parts=(160, 80)))
    return out


# the designs are deterministic but slow; make.py --check recomputes them all, tests read this cache
_DESIGN = {}


def design_cached(name, W, H, vp, side, nr, xr, yr, n, pool, seed, parts, grid=32):
    key = (name, W, H, vp, side, nr, xr, yr, n, pool, seed, parts, grid)
    if key not in _DESIGN:
        _DESIGN[key] = G.design(W, H, vp, side, nr, xr, yr, 5, n, pool, seed, [F(p) for p in parts],
                                others(W, H, vp, side), grid)
    return _DESIGN[key]


# ---------------------------------------------------------------- clipr (Q199)
RULES = ("HU", "HA", "RNE", "TR")
# the tie rows: (name, the near x, the far vertex's x, n's parity, sign of the clip y): the clip
# vertex on H-VP's x = 80 has y = (n + 1/2)/256 pixel; A and B with the far vertex at 16400 px
# (t = 2^-8), C (a negative y) at 144 px (t = 1/2: a far vertex past 80 inside the y guard
# cannot put a negative y on x = 80 with its edge through the target otherwise)
TIES = (("clipr-tie-a", 16, 16400, 0, 1, 15001), ("clipr-tie-b", 16, 16400, 1, 1, 15002),
        ("clipr-tie-c", 16, 144, 0, -1, 15003))
UNIT_TIE = 8


def tie_polys(V, W=64, H=64):
    vp = G.default_vp(W, H)
    b = G.boxes(W, H, vp)["H-VP"]
    out = {r: G.clip(V, b, r) for r in RULES}
    out["H-EXACT"] = G.oriented(V)
    return out


def tie_design(nx, fx, parity, sign, seed, tries=6000):
    """the tie row with the most decisive pixels: P1 = (nx, ya), P2 = (nx, y2), V = (fx, Vy) on the
    1/256 grid, the clip of P1-V on x = 80 at y = (n + 1/2)/256 (n of the parity, the sign's side),
    the clip of P2-V on the grid; the four rules part as the tie's parity and sign say. A pixel is
    decisive when HU's image and a rival's part on it and its centre lies 6.4e-4 pixel or more from
    the edges of both (E943's band); ya is drawn near a pixel centre row so that the near edge runs
    along it (many decisive pixels when the edge is nearly level)"""
    import random
    rnd = random.Random(seed)
    t = F(80 - nx, fx - nx)
    band = 6.4e-4
    best = None
    for _ in range(tries):
        if sign > 0:
            ya = 256 * rnd.randrange(3, 56) + 128 + rnd.randrange(-24, 25)
        else:
            ya = rnd.randrange(2 * 256, 13 * 256)
        n = None
        for _ in range(50):
            if sign > 0:
                m = int(50 * 256 * t)
                yc = ya + rnd.randrange(-m, m)
            else:
                yc = rnd.randrange(-14 * 256, -256 // 2)
            if yc % 2 == parity:
                n = yc
                break
        if n is None:
            continue
        # Vy from ya and the clip y (n + 1/2): Vy = ya + (n + 1/2 - ya) / t, on the grid
        Vy = ya + (F(2 * n + 1, 2) - ya) / t
        if Vy.denominator != 1 or not -15 * 256 <= Vy <= 79 * 256:
            continue
        Vy = int(Vy)
        y2 = ya + rnd.choice((1, -1)) * rnd.randrange(6 * 256, 30 * 256)
        y2 -= (y2 - Vy) % int(1 / t) if t.numerator == 1 else 0
        if not 1 * 256 <= y2 <= 62 * 256 or ((Vy - y2) * t).denominator != 1:
            continue
        V = [(nx * 256, ya), (nx * 256, y2), (fx * 256, Vy)]
        polys = tie_polys(V)
        imgs = {k: G.cover(P, 64, 64) for k, P in polys.items()}
        want = tie_classes(n, sign)
        if any((imgs[a] == imgs[b]) != (want[a] == want[b]) for a in RULES for b in RULES):
            continue
        dec, least = 0, None
        for r in RULES[1:]:
            for j in range(64 * 64):
                if imgs[r][j] != imgs["HU"][j]:
                    d = min(G.dist(polys["HU"], j % 64, j // 64), G.dist(polys[r], j % 64, j // 64))
                    dec += d >= band
                    least = d if least is None else min(least, d)
        key = (least >= 2.5e-4, min(dec, 8), least)
        if best is None or key > best[0]:
            best = (key, V, n)
    return best


def tie_classes(n, sign):
    """per rule, the integer the tie n + 1/2 (units) rounds to"""
    q = F(2 * n + 1, 2)
    return {r: G.CLIP_RULES[r](q) for r in RULES}


# the 4096-wide rows on 4096 x 16 (the nearest shape drawn without fault: r7-geo zf's 4096 x 16
# rows, 120 jobs `ok` with --pixels; 4096 x 128 never ran), H-VP's box [-1024, 5120] x [-4, 20]
W4, H4 = 4096, 16
IN_TIES = (  # name, unit, the window vertices (P1, P2, V): V's y on a 1/512 tie inside the guard
    ("clipr-w4-d", 9, ((F(2), F(9, 2) - F(6, 256)), (F(2), F(15, 2) + F(6, 256)), (F(5000), F(9, 2) + F(9, 512)))),
    ("clipr-w4-e", 9, ((F(4094), F(1) + F(2, 256)), (F(4094), F(4) + F(2, 256)), (F(-1000), -F(3, 512)))),
)
F_FAMILY = (4096, 4100, 4112, 4115, 4118, 4128, 4160, 4352, 4608, 5000, 5110, 5119, 5120, 5121, 5130, 5376, 6144)


def w4_far(seed=15004, tries=400):
    """clipr-w4-f: a far vertex at 2^24 px along +x on 4096 x 16 (--tri-unit 5), its near edge
    crossing the pixel centre row 4.5 inside the target, so that the clip vertex's rounding at the
    x bound moves the crossing by many pixels; V's y (1/32 grid) chosen for the most classes of
    F_FAMILY with H-VP's 5120 parted from 4100 (H-MIN4) and 4115 (64 + 4096 - 45: E1023's G)"""
    import random
    rnd = random.Random(seed)
    vp = G.default_vp(W4, H4)
    base = G.boxes(W4, H4, vp)["H-VP"]
    P1, P2 = (F(17, 4), F(9, 2) + F(1, 32)), (F(27, 4), F(23, 2) - F(1, 32))
    best = None
    for _ in range(tries):
        cross = rnd.uniform(1500, 3800)
        Vy = P1[1] - F(1, 32) * (2 ** 24 - P1[0]) / (F(cross) - P1[0])
        Vy = F(round(Vy * 32), 32)
        pts = (P1, P2, (F(2 ** 24), Vy))
        vt = G.to_units(pts, 5, W4, H4, vp)
        vs = G.variants(vt, 5, W4, H4, vp)
        if len(vs) != 1:
            continue
        V = vs[0]
        sig = {v: tuple(G.image(V, G.with_bound(base, "pos-x", F(v)), W4, H4)) for v in F_FAMILY}
        if sig[5120] in (sig[4100], sig[4115]):
            continue
        key = len(set(sig.values()))
        if best is None or key > best[0]:
            best = (key, pts)
    return best[1]


def int32_far(side, seed, tries=60):
    """the int32 ends at --tri-unit 0 on 64 x 64: x = 2^31 - 1 (pos-x) or y = -2^31 (neg-y), the
    near vertices E979's rounded to whole pixels (r13-isp far), the other coordinate (whole pixels
    within 2^29) the one whose merged image parts most values of the side's family"""
    import random
    rnd = random.Random(seed)
    vp = G.default_vp(64, 64)
    base = G.boxes(64, 64, vp)["H-VP"]
    nr = tuple((F(round(x)), F(round(y))) for x, y in NEAR[side])
    fam = G.family_values(64, 64, side)
    best = None
    for _ in range(tries):
        o = F(rnd.randrange(-2 ** 29, 2 ** 29))
        far = (F(2 ** 31 - 1), o) if side == "pos-x" else (o, F(-2 ** 31))
        pts = nr + (far,)
        vt = G.to_units(pts, 0, 64, 64, vp)
        sig = {v: tuple(G.predict(vt, 0, 64, 64, vp, G.with_bound(base, side, F(v)))) for v in fam}
        key = len(set(sig.values()))
        if best is None or key > best[0]:
            best = (key, pts)
    return best[1]


def clipr_rows():
    """E684's far21d0 first, the three tie rows, the 4096 x 16 rows, E1024's far-x30p replicate,
    then the int32 ends (last: the stage, the session's last, stops at the first job not ok)"""
    rows = [from_units("clipr-ctl-far21", "control", 64, 8, list(FA.E684_CTL[1]), "far-ctl")]
    for name, nx, fx, par, sg, seed in TIES:
        _, V, n = tie_design(nx, fx, par, sg, seed)
        pts = [(F(x, 256), F(y, 256)) for x, y in V]
        r = row(name, "heldout", 64, 64, UNIT_TIE, pts, G.default_vp(64, 64), "pos-x", kind="tie")
        r["tie"] = n
        rows.append(r)
    for name, unit, pts in IN_TIES:
        rows.append(row(name, "heldout", W4, H4, unit, pts, G.default_vp(W4, H4),
                        "pos-x" if pts[2][0] > 0 else "neg-x", kind="intie"))
    rows.append(row("clipr-w4-f", "heldout", W4, H4, 5, w4_far(), G.default_vp(W4, H4), "pos-x",
                    parts=(5120, 4100, 4115)))
    rows.append(from_units("clipr-ctl-x30p", "control", 64, 0, [6, 9, 10, 54, 1073741824, 132369010], "x30p"))
    rows.append(row("clipr-i32-x", "heldout", 64, 64, 0, int32_far("pos-x", 15005), G.default_vp(64, 64),
                    "pos-x", kind="int32"))
    rows.append(row("clipr-i32-y", "heldout", 64, 64, 0, int32_far("neg-y", 15006), G.default_vp(64, 64),
                    "neg-y", kind="int32"))
    return rows
