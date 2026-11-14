# SPDX-License-Identifier: MIT
"""srgb4.py: stage srgb4 (r14-tex, Q282; closing14/plan/rank-round14.md section 2 "srgb4"): the
trilinear sRGB level lerp held out at seven LODs and chains, and texel bytes 2 and 3 (alpha) of
an sRGB texel under a bilinear sample. r13-tex's gen/srgb.py (resgx545-data
render/closing-r13-tex/gen/srgb.py, copied unchanged) gives the level sampler, the strided forms
and closing11 c2's frozen stage rule (rule_b.py, pinned, sha256 84bd4264...).

Trilinear (T0 0x0FFC1600: bit 27 sRGB, top 0x3f so the LOD is the operand, max level 14, bilinear,
bit 9 mip interpolation; smp2dreplace with the LOD in r26). The levels lo = floor(LOD) and lo + 1,
each the bilinear FTZ-OUT halves (E1025, held out), then a third stage at f / 64, f = floor(64
frac(LOD)) (Q-FLOOR; the LOD 1.2 row also Q-NEAR: f = round(64 frac), the QN- models):
  TRI-RNTU     both halves floored to 2^(e - 16) (e the larger frexp exponent), the lerp exact,
               rounded to the nearest half, ties up, the result below 2^-14 flushed to +0
               (E1025's post hoc form, fold/srgb3_tri_post.py: 4091 of 4096 halves on srgb3-tri)
  TRI-RNTU-NF  the same, the third result not flushed
  TRI-G15      the operands floored to 2^(e - 15), else TRI-RNTU (fitted here on srgb3-tri, 4096
               of 4096 halves, fit/tri_fam.py; post hoc, README.md "Deviations" 1)
  TRI-G15-NF   the same, not flushed
  TRI-RNE      TRI-RNTU-NF rounded to nearest even (3957 of 4096 post hoc)
  TRI-BF11     c2's stage rule as the third stage (2^(e - 11), ties up), not flushed (3185)
  TRI-OUT      c2's stage rule with its flush (r13-tex's frozen TRI-OUT, 1137 of 2048 pixels)
Rows: the 16 x 16 counting chain of srgb3-tri (dword i = 0xD0000000 | i, base 0) at LOD 1.125,
1.5, 1.75, 1.984375 (levels 1 and 2, f 8, 32, 48, 63), 0.25 (levels 0 and 1, f 16), 1.2 (float32
0x3f99999a: f 12 floor, 13 nearest), and a dark 4 x 4 chain injected with bytes 0 to 3 (levels 0
and 1 at LOD 0.125, f 8): its level halves are 0 or above 2^-14 after the level flush and the
third stage's results are subnormal on most pixels (the third flush parts -NF).

Alpha (bytes 2 and 3): E723's tx_map_r11.s (the published template, pinned: o0 from r11, the
sample's second dword). Post hoc on E723's kept g-st8x4-r11 and g-tw8x8-r11 (point samples, 2048
of 2048 each, fit/r11.py): the low half is half(sRGB(byte 2)), the high half half(byte 3 / 255)
[fitted]. Bilinear, frozen here:
  B2-FTZ-OUT   the low half: byte 2 by the bytes 0 / 1 rule (sRGB, FTZ-OUT), h: tokens
  A-LIN        the high half: byte 3 decoded half(b / 255), filtered by the same stage rule
               (FTZ-OUT), u: tokens
  A-SRGB       byte 3 decoded sRGB, filtered so (H-ALPHA-SRGB of the plan)
  A-BYTE       texmodel's byte blend (the bytes weighted, (s + 2048) >> 12), then half(b / 255)
Rows: the x stage alone (r10-tex's a form, kx 0 to 63), the y stage alone (b form), both stages
(a form at fy 29/64); byte 2 (0, b) pairs, b 1 to 3; byte 3 random pairs.

Controls that can fail: E723's g-bl-st-a rerun (its kept image; r10-tex's srgb2-ctl program),
srgb3-tri rerun (its kept image, r13-tex), and the r11 program on srgb3-x1's texture with byte 2
equal to byte 0 (its low half must be srgb3-x1's kept channel 0 halves, h: tokens)."""
import json
import math
import random

import pins
import srgb as S
import tex

STAGE = "srgb4"
F = tex.F
R11 = "data:texture/p1141/templates/tx_map_r11.s"
R13 = "data:render/closing-r13-tex/out/20261113-214825/srgb3/%s.txt.gz"
R13_TRI_BIN = "data:render/closing-r13-tex/bins/srgb3-tri.bin"
R10_CTL_BIN = "data:render/closing-r10-tex/bins/srgb2-ctl.bin"
TINY = F(2) ** -14

TRI = ("TRI-RNTU", "TRI-RNTU-NF", "TRI-G15", "TRI-G15-NF", "TRI-RNE", "TRI-BF11", "TRI-OUT")
ALPHA = ("A-LIN", "A-SRGB", "A-BYTE")


def r11_text(spec):
    pre, setup, smp = pins.module(tex.BUILD).case_inputs(spec)
    return (pins.blob(R11).decode().replace("{PRE}", pre).replace("{SETUP}", setup)
            .replace("{SMP}", smp))


# ---- trilinear --------------------------------------------------------------------------------
def tri_spec(lod_bits, w=16, inject=None):
    return dict(base=0, ins="replace", t0=S.TRI_T0,
                t1=0x0C000000 | (w - 1) << 12 | (w - 1), t3=S.TRI_T3,
                u=tex.lin("x", F(1, 64), F(1, 128)), v=tex.lin("y", F(1, 32), F(1, 64)),
                lod=["bits", lod_bits], inject=dict(inject or {}))


def chain_texel(sp, i):
    return sp["inject"].get(str(i), 0xD0000000 | i)


def level_halves(R, sp, u, v, lvl):
    """(channel 0, channel 1) FTZ-OUT halves of one level's bilinear sample (address mode 0)."""
    w = (sp["t1"] >> 12 & 0xFFF) + 1
    n, off = S.chain(w)[lvl]
    fx, fy = u * n - F(1, 2), v * n - F(1, 2)
    x0, y0 = math.floor(fx), math.floor(fy)
    kx, ky = 64 * (fx - x0), 64 * (fy - y0)
    assert kx.denominator == 1 and ky.denominator == 1
    t = [chain_texel(sp, off + S.tw_morton((x0 + dx) % n, (y0 + dy) % n, n))
         for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
    return [S.two_stage(R, [b >> 8 * c & 255 for b in t], int(kx), int(ky), "out")
            for c in (0, 1)]


def third(R, a, b, f, model):
    """The half of the level lerp of halves a (level lo) and b (lo + 1) at f / 64."""
    A, B = R.h2f(a), R.h2f(b)
    if model in ("TRI-BF11", "TRI-OUT"):
        return R.half_rne(R.stage(A, B, f, "out" if model == "TRI-OUT" else "none"))
    if f == 0:
        return a
    bits = 15 if model.startswith("TRI-G15") else 16
    g = F(2) ** (max(R.expo(A), R.expo(B)) - bits)
    qa, qb = math.floor(F(A) / g) * g, math.floor(F(B) / g) * g
    r = qa + F(f, 64) * (qb - qa)
    h = R.half_rne(float(r)) if model == "TRI-RNE" else R.half_rhu(r)
    if model in ("TRI-RNTU", "TRI-G15") and abs(F(R.h2f(h))) < TINY:
        h = 0
    return h


def lod_f(lod_bits, near=False):
    lod = F(tex.fbits(lod_bits))
    lo = math.floor(lod)
    q = (lod - lo) * 64
    f = math.floor(q + F(1, 2)) if near else math.floor(q)
    return lo, f


def tri_image(R, sp, model, near=False):
    lo, f = lod_f(sp["lod"][1], near)
    out = []
    for p in range(2048):
        x, y = p % 64, p // 64
        u, v = tex.coord(sp["u"], x, y), tex.coord(sp["v"], x, y)
        a, b = level_halves(R, sp, u, v, lo), level_halves(R, sp, u, v, lo + 1)
        out.append(sum(third(R, a[c], b[c], f, model) << 16 * c for c in (0, 1)))
    return out


def dark_inject(seed=14038):
    """The 4 x 4 chain's 21 dwords (levels 4 x 4 at 0 to 15, 2 x 2 at 16 to 19, 1 x 1 at 20):
    byte 1 (channel 1) from 0 to 3 on every level (the dark halves: subnormal before the level
    flush, the third stage's results subnormal); byte 0 (channel 0) from 0 to 3 on level 0 and
    from 64 to 255 above (a dark level lerped with a bright one: the operands' exponents far apart,
    where the floor's grid parts TRI-G15 from TRI-RNTU); bytes 2 and 3 0x5A, 0xA5 (not read)."""
    rnd = random.Random(seed)
    out = {}
    for i in range(21):
        b0 = rnd.randrange(4) if i < 16 else rnd.randrange(64, 256)
        out[str(i)] = b0 | rnd.randrange(4) << 8 | 0xA55A0000
    return out


TRI_ROWS = [  # name, LOD bits, chain side, inject
    ("srgb4-t1125", 0x3F900000, 16, None),
    ("srgb4-t15", 0x3FC00000, 16, None),
    ("srgb4-t175", 0x3FE00000, 16, None),
    ("srgb4-t1984", 0x3FFE0000, 16, None),
    ("srgb4-t025", 0x3E800000, 16, None),
    ("srgb4-t12", 0x3F99999A, 16, None),
    ("srgb4-tdark", 0x3E000000, 4, "dark"),
]
QN_ROW = "srgb4-t12"


def tri_models(R, sp, name):
    m = {k: tri_image(R, sp, k) for k in TRI}
    if name == QN_ROW:
        m.update({"QN-" + k: tri_image(R, sp, k, near=True) for k in TRI})
    return m


# ---- alpha (bytes 2 and 3) --------------------------------------------------------------------
def word4(b):
    return b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24


def spec_a4(rows, fy):
    """r10-tex's a form with all four bytes of each injected texel (rows: (texel K, texel K + 1)
    as byte quadruples)."""
    sp = S.spec_a([((0, 0), (0, 0), (0, 0))] * len(rows), fy)
    for r, (ta, tb) in enumerate(rows):
        sp["inject"][str(r * 8 + S.K)] = word4(ta)
        sp["inject"][str(r * 8 + S.K + 1)] = word4(tb)
    return sp


def spec_b4(cols):
    sp = S.spec_b([((0, 0), (0, 0), (0, 0))] * len(cols))
    for c, (ta, tb) in enumerate(cols):
        sp["inject"][str(S.K * 64 + c)] = word4(ta)
        sp["inject"][str((S.K + 1) * 64 + c)] = word4(tb)
    return sp


def alpha_rows(seed, n=33):
    """byte 2 (0, b) with b = 1 + r % 3 (the flush's ground, as srgb3-x2's channel 0), byte 3 a
    random pair, bytes 0 and 1 random (not read by the r11 program)."""
    rnd = random.Random(seed)
    out = []
    for r in range(n):
        a3, b3 = rnd.randrange(256), rnd.randrange(256)
        out.append(((rnd.randrange(256), rnd.randrange(256), 0, a3),
                    (rnd.randrange(256), rnd.randrange(256), 1 + r % 3, b3)))
    return out


def b2x1_rows(n=33):
    """srgb3-x1's texels (channel 0 (0, 1), channel 1 (1, 0), bytes 2 and 3 0x5A, 0xA5 and
    0xA5, 0x5A) with byte 2 set to byte 0: the r11 low half reads srgb3-x1's channel 0."""
    return [((0, 1, 0, 0xA5), (1, 0, 1, 0x5A)) for _ in range(n)]


def lin_decode(b):
    return S_R().h2f(S_R().half_rne(b / 255.0))


_R = []


def S_R():
    if not _R:
        _R.append(S.rule())
    return _R[0]


def alpha_two_stage(R, b4, kx, ky, model):
    if model == "A-SRGB":
        return R.two_stage(b4, kx, ky, "out")
    if model == "A-BYTE":
        wt = [(64 - kx) * (64 - ky), kx * (64 - ky), (64 - kx) * ky, kx * ky]
        s = (sum(b * w for b, w in zip(b4, wt)) + 2048) >> 12
        return R.half_rne(s / 255.0)
    d = [lin_decode(b) for b in b4]
    top, bot = R.stage(d[0], d[1], kx, "out"), R.stage(d[2], d[3], kx, "out")
    return R.half_rne(R.stage(top, bot, ky, "out"))


def alpha_tokens(R, sp, model):
    """h:XXXX (B2-FTZ-OUT, the low half) or u:XXXX (an alpha model, the high half) a pixel."""
    out = []
    for p in range(2048):
        t, fx, fy = S.footprint(sp, p % 64, p // 64)
        kx, ky = int(64 * fx), int(64 * fy)
        assert kx == 64 * fx and ky == 64 * fy
        if model == "B2-FTZ-OUT":
            out.append("h:%04x" % R.two_stage([b >> 16 & 255 for b in t], kx, ky, "out"))
        else:
            out.append("u:%04x" % alpha_two_stage(R, [b >> 24 & 255 for b in t], kx, ky, model))
    return out


ALPHA_ROWS = [
    ("srgb4-ax", lambda: spec_a4(alpha_rows(14381), 0)),
    ("srgb4-ay", lambda: spec_b4(alpha_rows(14382))),
    ("srgb4-axy", lambda: spec_a4(alpha_rows(14383), F(29, 64))),
]


def dwords(img):
    return ["%08x" % v for v in img]


def jobs():
    """[(name, set, template, spec or None (a published bin), bin pin or None, {model: tokens})]
    in run order."""
    R = S.rule()
    out = []
    cases = {c["name"]: c for c in json.loads(pins.blob(S.E723_CASES))}
    out.append(("srgb4-ctl", "control", "tx_map", cases["g-bl-st-a"]["spec"], R10_CTL_BIN,
                {"H-E723": dwords(pins.kept_pixels(S.E723_A))}))
    out.append(("srgb4-trir", "control", "tx_map", tri_spec(S.TRI_LOD), R13_TRI_BIN,
                {"H-R13": dwords(pins.kept_pixels(R13 % "srgb3-tri"))}))
    x1 = pins.kept_pixels(R13 % "srgb3-x1")
    out.append(("srgb4-b2x1", "control", "r11", spec_a4(b2x1_rows(), 0), None,
                {"H-X1": ["h:%04x" % (v & 0xFFFF) for v in x1]}))
    for name, lod, w, inj in TRI_ROWS:
        sp = tri_spec(lod, w, dark_inject() if inj == "dark" else None)
        out.append((name, "heldout", "tx_map", sp, None,
                    {m: dwords(im) for m, im in tri_models(R, sp, name).items()}))
    for name, mk in ALPHA_ROWS:
        sp = mk()
        out.append((name, "heldout", "r11", sp, None,
                    {m: alpha_tokens(R, sp, m) for m in ("B2-FTZ-OUT",) + ALPHA}))
    return out


def parts(models):
    """{(m1, m2): tokens that differ} over a row's models (tests and README.md)."""
    ks = sorted(models)
    return {(a, b): sum(x != y for x, y in zip(models[a], models[b]))
            for i, a in enumerate(ks) for b in ks[i + 1:]}
