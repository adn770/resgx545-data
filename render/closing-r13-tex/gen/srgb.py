# SPDX-License-Identifier: MIT
"""srgb.py: stage srgb3 (r13-tex, Q282; closing13/plan/rank-round13.md section 2 "srgb3"): the
bilinear sample of an sRGB texel (T0 bit 27), r10-tex's gen/srgb.py forms (resgx545-data
render/closing-r10-tex/gen/srgb.py: E723's g-bl-st form, strided, texel bytes injected by the
program's PRE, two half channels a pixel from the texel's bytes 0 and 1).

The frozen rules are closing11 c2's rule_b.py (resgx545-data cited/closing11/plan/c2-texture/
rule_b.py, sha256 84bd4264..., frozen 2026-11-13 before any held-out pixel was read; pinned and
loaded from its frozen bytes), each channel's corner bytes 00, 10, 01, 11 and the weights kx, ky
(64ths, floor):
  FTZ-OUT   R10-BF11 with every stage output below 2^-14 flushed to +0 (E1016; tested)
  FTZ-IN    the operands of every stage below 2^-14 flushed, the results not (c2's pure input
            flush: the y stage's own subnormal result is kept)
  R10-BF11  no flush (E982's rule; E1004 refuted it on subnormal stage results)
  FTZ-T64   FTZ-OUT with the threshold at 6.4e-5, the kept data's upper bound (c2 NOTE.md: the
            threshold lies between 5.7e-5 and 6.4e-5) [infer: the rival the x row parts at the
            one half 6.16e-5]

Rows (2048 pixels each; nothing below was fitted on them):
  srgb3-ctl    E723's g-bl-st-a rerun (its kept image; the srgb2-ctl replicate): a control
  srgb3-an27   p1132 tx-lod an-t0b27 rerun (its kept image, E1016's held-out job; twiddled 64 x 64,
               gradient LOD): a control
  srgb3-x1     the x stage alone (fy = 0: ky = 0, the y stage returns its A), kx = x (0 to 63)
               on every pixel row: channel 0 corners (0, 1), channel 1 (1, 0) (next_row_b.out:
               kx 11 and 12 give 5.2e-5 and 5.7e-5, predicted flushed, 13 and 14 6.16e-5 and
               6.6e-5, kept: the threshold pinned at 2^-14)
  srgb3-x2     the x stage alone, channel 0 (0, b), channel 1 (b', 0), b and b' 1 to 3 by row
  srgb3-y1     the y stage alone (fx = 0: kx = 0, the x stage returns its A), ky = x: channel 0
               corners top 0, bottom 1, channel 1 top 1, bottom 0 (FTZ-IN keeps the y stage's
               subnormal result, FTZ-OUT flushes it: the plan's separation)
  srgb3-y2     the y stage alone, channel 0 (0, b), channel 1 (b', 0), b and b' 1 to 3 by column
  srgb3-sub2   both stages, corner bytes 0 to 3 (r10-tex's srgb2-sub form, a new seed, fy 29/64)
  srgb3-tri    trilinear: a twiddled 16 x 16 sRGB chain on the counting fill (bytes 0 and 1 of
               dword i are i's), smp2dreplace at LOD 1.25 (f = 16), T0 bit 9 (mip interpolation),
               bilinear in both levels: TRI-OUT (each level's FTZ-OUT result, then a third stage of
               the same rule between the levels with weight f, flushed), TRI-NOFLUSH (R10-BF11 in
               all three stages), TRI-LO (level 1 alone: bit 9 ignored for sRGB) [infer: the third
               stage is the level lerp of E441 on halves]
  srgb3-x1r    srgb3-x1 again, the end replicate"""
import json
import math
import random

import pins
import tex

STAGE = "srgb3"
RULE_B = "data:cited/closing11/plan/c2-texture/rule_b.py"
RULE_B_SHA = "84bd426400514091ae58c75c4fac6f6f3fca1d12dd3d4b30660e1af6551a2237"
E723_CASES = "data:texture/p1141/gen/cases.json"
E723_A = "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/g-bl-st-a.txt.gz"
AN27 = "data:texture/p1132/tx-lod/an-t0b27.txt.gz"
T0 = 0x08001E00          # g-bl-st-a's T0: bit 27 sRGB, bilinear, stride from tex.strided
T3 = 0xA0800000
K = 3                    # the texel pair: columns (a) or rows (b) 3 and 4
F = tex.F
MODES = {"FTZ-OUT": "out", "FTZ-IN": "in", "R10-BF11": "none", "FTZ-T64": "t64"}
T64 = 6.4e-5


def rule():
    R = pins.module(RULE_B, "r13t_rule_b")
    assert pins.sha(pins.blob(RULE_B)) == RULE_B_SHA
    return R


def stage(R, a, b, k, mode):
    """One stage of the frozen rule (rule_b.stage) and FTZ-T64 (its "out" with the threshold
    6.4e-5)."""
    if mode != "t64":
        return R.stage(a, b, k, mode)
    r = R.stage_bf11(a, b, k)
    return 0.0 if abs(r) < T64 else r


def two_stage(R, b4, kx, ky, mode):
    """The half bits of one channel (rule_b.two_stage, with FTZ-T64 added)."""
    if mode != "t64":
        return R.two_stage(b4, kx, ky, mode)
    d = [R.decode(b) for b in b4]
    top, bot = stage(R, d[0], d[1], kx, mode), stage(R, d[2], d[3], kx, mode)
    return R.half_rne(stage(R, top, bot, ky, mode))


def texel(sp, cx, cy):
    s = ((sp["t0"] >> 9 & 7) | (sp["t0"] >> 17 & 0x3FF) << 3) + 1
    i = cy * s + cx
    return sp["inject"].get(str(i), 0xD0000000 | i)


def footprint(sp, x, y):
    """(the four corner texels 00, 10, 01, 11, fx, fy) of pixel (x, y) of a strided spec."""
    w, h = (sp["t1"] >> 12 & 0xFFF) + 1, (sp["t1"] & 0xFFF) + 1
    fx = tex.coord(sp["u"], x, y) * w - F(1, 2)
    fy = tex.coord(sp["v"], x, y) * h - F(1, 2)
    x0, y0 = math.floor(fx), math.floor(fy)
    assert 0 <= x0 and x0 + 1 < w and 0 <= y0 and y0 + 1 < h, (x, y)
    t = [texel(sp, x0 + dx, y0 + dy) for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
    return t, fx - x0, fy - y0


def predict(R, sp, model):
    out = []
    for p in range(2048):
        t, fx, fy = footprint(sp, p % 64, p // 64)
        kx, ky = math.floor(64 * fx), math.floor(64 * fy)
        assert kx == 64 * fx and ky == 64 * fy, "every weight on the 1/64 grid"
        v = 0
        for c in (0, 1):
            v |= two_stage(R, [b >> 8 * c & 255 for b in t], kx, ky, MODES[model]) << 16 * c
        out.append(v)
    return out


def word(b0, b1, hi):
    return b0 | b1 << 8 | hi[0] << 16 | hi[1] << 24


def spec_a(rows, fy):
    """r10-tex's a form: an 8 x 64 strided texture, rows r = 0..32 holding the pair in columns K
    and K + 1; v = (y + 0.5 + fy) / 64, u = (K + 0.5 + x / 64) / 8 (kx = x)."""
    t0, t1, _ = tex.strided(8, 64, 8, t0=T0)
    inj = {}
    for r, ((a0, b0), (a1, b1), hi) in enumerate(rows):
        inj[str(r * 8 + K)] = word(a0, a1, hi)
        inj[str(r * 8 + K + 1)] = word(b0, b1, hi[::-1])
    return dict(base=0, ins="none", t0=t0, t1=t1, t3=T3, inject=inj,
                u=tex.lin("x", F(1, 512), F(2 * K + 1, 16)),
                v=tex.lin("y", F(1, 64), F(1, 128) + F(fy, 64)))


def spec_b(cols, fx=0):
    """r10-tex's b form: a 64 x 8 strided texture, columns c = 0..32 holding the pair in rows K
    and K + 1; u = (y + 0.5 + fx) / 64, v = (K + 0.5 + x / 64) / 8 (ky = x)."""
    t0, t1, _ = tex.strided(64, 8, 64, t0=T0)
    inj = {}
    for c, ((a0, b0), (a1, b1), hi) in enumerate(cols):
        inj[str(K * 64 + c)] = word(a0, a1, hi)
        inj[str((K + 1) * 64 + c)] = word(b0, b1, hi[::-1])
    return dict(base=0, ins="none", t0=t0, t1=t1, t3=T3, inject=inj,
                u=tex.lin("y", F(1, 64), F(1, 128) + F(fx, 64)),
                v=tex.lin("x", F(1, 512), F(2 * K + 1, 16)))


HI = (0x5A, 0xA5)        # bytes 2 and 3 of every injected word (not read by this format)


def pure_rows(n=33):
    """channel 0 (0, 1), channel 1 (1, 0): next_row_b.out's pattern."""
    return [((0, 1), (1, 0), HI) for _ in range(n)]


def mixed_rows(n=33):
    """channel 0 (0, b), channel 1 (b', 0), b = 1 + r % 3, b' = 1 + (r // 3) % 3."""
    return [((0, 1 + r % 3), (1 + (r // 3) % 3, 0), HI) for r in range(n)]


def sub_rows(seed, n=33):
    """r10-tex's srgb2-sub pairs: channel 0 (0, b), channel 1 (b', 0), b and b' 1 to 3."""
    rnd = random.Random(seed)
    return [((0, rnd.randint(1, 3)), (rnd.randint(1, 3), 0), (rnd.randrange(256), rnd.randrange(256)))
            for _ in range(n)]


# ---- trilinear on a twiddled chain -----------------------------------------------------------
TRI_W = 16
TRI_LOD = 0x3FA00000                       # 1.25: level 1, f = int(0.25 * 64) = 16
TRI_T0 = 0x0FFC1600                        # bit 27 sRGB, top 0x3f, max level 14, bilinear
                                           # (bits 12, 10), bit 9 (mip interpolation)
TRI_T1 = 0x0C000000 | (TRI_W - 1) << 12 | (TRI_W - 1)
TRI_T3 = 0x00800800                        # E564's control T3 (bits 11 set, 12 clear)


def tri_spec():
    # u = (x + 0.5) / 64, v = (y + 0.5) / 32: level 0 (16) x / 4 - 3/8, level 1 (8) x / 8 - 7/16:
    # every weight on the 1/64 grid at both levels
    return dict(base=0, ins="replace", t0=TRI_T0, t1=TRI_T1, t3=TRI_T3,
                u=tex.lin("x", F(1, 64), F(1, 128)), v=tex.lin("y", F(1, 32), F(1, 64)),
                lod=["bits", TRI_LOD])


def chain(w):
    out, off = [], 0
    while w >= 1:
        out.append((w, off))
        off += w * w
        w //= 2
    return out


def tw_morton(x, y, n):
    i = 0
    for b in range(max(n, 1).bit_length() - 1):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i


def level_bilinear(R, u, v, lvl, mode):
    """(channel 0, channel 1) halves of one level's bilinear sRGB sample, address mode 0."""
    n, off = chain(TRI_W)[lvl]
    fx, fy = u * n - F(1, 2), v * n - F(1, 2)
    x0, y0 = math.floor(fx), math.floor(fy)
    kx, ky = 64 * (fx - x0), 64 * (fy - y0)
    assert kx.denominator == 1 and ky.denominator == 1
    t = [0xD0000000 | (off + tw_morton((x0 + dx) % n, (y0 + dy) % n, n))
         for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
    return [two_stage(R, [b >> 8 * c & 255 for b in t], int(kx), int(ky), mode) for c in (0, 1)]


TRI_MODELS = ("TRI-OUT", "TRI-NOFLUSH", "TRI-LO")


def tri_predict(R, sp, model):
    out = []
    lod = F(tex.fbits(TRI_LOD))
    lo, f = math.floor(lod), int((lod - math.floor(lod)) * 64)
    for p in range(2048):
        x, y = p % 64, p // 64
        u, v = tex.coord(sp["u"], x, y), tex.coord(sp["v"], x, y)
        mode = "none" if model == "TRI-NOFLUSH" else "out"
        a = level_bilinear(R, u, v, lo, mode)
        if model == "TRI-LO":
            out.append(a[0] | a[1] << 16)
            continue
        b = level_bilinear(R, u, v, lo + 1, mode)
        val = 0
        for c in (0, 1):
            r = stage(R, R.h2f(a[c]), R.h2f(b[c]), f, mode)
            val |= R.half_rne(r) << 16 * c
        out.append(val)
    return out


ROWS = [
    ("srgb3-x1", lambda: spec_a(pure_rows(), 0)),
    ("srgb3-x2", lambda: spec_a(mixed_rows(), 0)),
    ("srgb3-y1", lambda: spec_b(pure_rows())),
    ("srgb3-y2", lambda: spec_b(mixed_rows())),
    ("srgb3-sub2", lambda: spec_a(sub_rows(13053), F(29, 64))),
]


def jobs():
    """[(name, set, knobs, spec, {model: image})] in run order."""
    R = rule()
    cases = {c["name"]: c for c in json.loads(pins.blob(E723_CASES))}
    specs = json.loads(pins.blob(tex.SPECS))
    out = [("srgb3-ctl", "control", "reads:pixels", cases["g-bl-st-a"]["spec"],
            {"H-E723": pins.kept_pixels(E723_A)}),
           ("srgb3-an27", "control", "reads:pixels", specs["an-t0b27"]["spec"],
            {"H-KEPT": pins.kept_pixels(AN27)})]
    for name, mk in ROWS:
        sp = mk()
        out.append((name, "heldout", "-", sp, {m: predict(R, sp, m) for m in MODES}))
    sp = tri_spec()
    out.append(("srgb3-tri", "heldout", "-", sp, {m: tri_predict(R, sp, m) for m in TRI_MODELS}))
    sp = spec_a(pure_rows(), 0)
    out.append(("srgb3-x1r", "replicate", "-", sp, {m: predict(R, sp, m) for m in MODES}))
    return out
