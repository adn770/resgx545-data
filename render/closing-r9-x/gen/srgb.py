# SPDX-License-Identifier: MIT
"""srgb.py: stage srgb (R9-B, Q282): the bilinear sample of an sRGB texel (T0 bit 27) in E723's
g-bl-st form (strided, point-free bilinear, texel bytes injected by the program's PRE, two half
channels a pixel from the texel's bytes 0 and 1), with each lerp stage alone and both.

Geometry (x = u * W - 0.5, the fraction on the 1/64 grid, E720's two-stage form):
  a1, a2  stage 1 alone: an 8 x 64 texture, v on texel row centres (fy = 0, row y), u = (3.5 +
          x / 64) / 8, so fx = x / 64 between columns 3 and 4: every weight 0 to 63/64 across a
          row, a pair of bytes per row and channel (rows 0 to 32 injected, 66 dwords)
  b1, b2  stage 2 alone: a 64 x 8 texture, u on texel column centres (fx = 0, column y), v = (3.5 +
          x / 64) / 8, so fy = x / 64 between rows 3 and 4 (columns 0 to 32 injected)
  c1, c2  both stages: a1's and a2's textures with fy = 21/64 and 43/64 (rows y and y + 1)
  eq      the equal-corner control: a1's form with columns 3 and 4 equal in every row and each
          row's decoded value no larger in exponent than the row above (so a lerp of equal halves,
          and stage 2 at fy = 0, return the half under every rival: a control that can fail)
  ctl     E723's g-bl-st-a rerun (its kept image, pinned: a control that can fail)
Frozen rivals per pixel (closing9/rank: q282_rule.json best of family 1 = H-HALF2, q282_rule3.json
first of family 3 = H-BF11; neither exact on E723's jobs, so a and b are the reading table the fold
fits a stage's arithmetic on, c held out for that fit after its freeze, stated as such)."""
import json
import math
import random
import struct

import pins
import tex

STAGE = "srgb"
E723_CASES = "data:texture/p1141/gen/cases.json"
E723_A = "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/g-bl-st-a.txt.gz"
T0 = 0x08001E00          # g-bl-st-a's T0: bit 27 sRGB, bilinear, stride from tex.strided
T3 = 0xA0800000
K = 3                    # the texel pair: columns (a) or rows (b) 3 and 4
PAIRS = [(0, 255), (43, 213), (75, 104), (201, 167)]   # the plan's corner pairs
MODELS = ("H-HALF2", "H-BF11")


def s2l(b):
    c = b / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def h2f(h):
    return struct.unpack("<e", struct.pack("<H", h))[0]


def half_rne(f):
    return struct.unpack("<H", struct.pack("<e", f))[0]


def half_rz(f):
    h = half_rne(f)
    return h - 1 if h2f(h) > f and h & 0x7FFF else h


def half2(b4, ix, iy):
    """H-HALF2 (q282_rule.json: decode to half RNE, lerp x then y in float, each lerp to half RNE,
    weights on the 1/64 grid, out RZ: q282_fit.py's model with that rule)."""
    d = [h2f(half_rne(s2l(b))) for b in b4]
    hh = lambda v: h2f(half_rne(v))
    lh = lambda p, r, w: hh(p * (1 - w) + r * w)
    return half_rz(lh(lh(d[0], d[1], ix / 64), lh(d[2], d[3], ix / 64), iy / 64))


def bf11(b4, ix, iy):
    """H-BF11 (q282_rule3.json's first tie: M 11, align RZ, lerp RN, out RZ, per pair:
    q282_fit3.py's model3 with that rule)."""
    d = [h2f(half_rne(s2l(b))) for b in b4]
    ex = lambda v: math.frexp(v)[1] if v else -100

    def st(a, b, w):
        s = 2.0 ** (11 - max(ex(a), ex(b)))
        qa, qb = int(a * s), int(b * s)
        return ((qa * (64 - w) + qb * w + 32) >> 6) / s
    return half_rz(st(st(d[0], d[1], ix), st(d[2], d[3], ix), iy))


RIVALS = {"H-HALF2": half2, "H-BF11": bf11}


def texel(sp, cx, cy):
    """The texel dword (cx, cy) of a strided spec: injected, else the named-memory dword."""
    s = ((sp["t0"] >> 9 & 7) | (sp["t0"] >> 17 & 0x3FF) << 3) + 1
    i = cy * s + cx
    return sp["inject"].get(str(i), 0xD0000000 | i)


def footprint(sp, x, y):
    """(the four corner texels (x0, y0) (x0+1, y0) (x0, y0+1) (x0+1, y0+1), ix, iy) of pixel (x, y)
    for a w x h strided spec: x = u * w - 0.5, the fractions in 1/64 (exact here: asserted)."""
    w, h = (sp["t1"] >> 12 & 0xFFF) + 1, (sp["t1"] & 0xFFF) + 1
    fx = tex.coord(sp["u"], x, y) * w - tex.F(1, 2)
    fy = tex.coord(sp["v"], x, y) * h - tex.F(1, 2)
    x0, y0 = math.floor(fx), math.floor(fy)
    ix, iy = (fx - x0) * 64, (fy - y0) * 64
    assert ix.denominator == 1 and iy.denominator == 1, (x, y)
    assert 0 <= x0 and x0 + 1 < w and 0 <= y0 and y0 + 1 < h, (x, y)
    t = [texel(sp, x0 + dx, y0 + dy) for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
    return t, int(ix), int(iy)


def predict(sp, rule):
    out = []
    for p in range(2048):
        t, ix, iy = footprint(sp, p % 64, p // 64)
        out.append(rule([v & 255 for v in t], ix, iy) | rule([v >> 8 & 255 for v in t], ix, iy) << 16)
    return out


def eq_value(sp):
    """The eq control: every pixel's four corners hold one byte per channel: its half."""
    out = []
    for p in range(2048):
        t, _, _ = footprint(sp, p % 64, p // 64)
        b0, b1 = t[0] & 255, t[0] >> 8 & 255
        out.append(half_rne(s2l(b0)) | half_rne(s2l(b1)) << 16)
    return out


def pair_rows(seed, n=33):
    """n (byte A, byte B) pairs per channel, the plan's four first in each channel, the rest from
    a seeded generator (frozen with the session)."""
    rnd = random.Random(seed)
    ch = []
    for c in range(2):
        rows = list(PAIRS[c * 2:] + PAIRS[:c * 2]) + [(rnd.randrange(256), rnd.randrange(256))
                                                      for _ in range(n - 4)]
        ch.append(rows)
    hi = [(rnd.randrange(256), rnd.randrange(256)) for _ in range(n)]
    return [(ch[0][r], ch[1][r], hi[r]) for r in range(n)]


def word(b0, b1, hi):
    return b0 | b1 << 8 | hi[0] << 16 | hi[1] << 24


def spec_a(rows, fy=0):
    """a: an 8 x 64 strided texture, rows r = 0..32 holding the pair in columns K and K + 1;
    v = (y + 0.5 + fy / 64) / 64, u = (K + 0.5 + x / 64) / 8."""
    t0, t1, _ = tex.strided(8, 64, 8, t0=T0)
    inj = {}
    for r, ((a0, b0), (a1, b1), hi) in enumerate(rows):
        inj[str(r * 8 + K)] = word(a0, a1, hi)
        inj[str(r * 8 + K + 1)] = word(b0, b1, hi[::-1])
    return dict(base=0, ins="none", t0=t0, t1=t1, t3=T3, inject=inj,
                u=tex.lin("x", tex.F(1, 512), tex.F(2 * K + 1, 16)),
                v=tex.lin("y", tex.F(1, 64), tex.F(1, 128) + tex.F(fy, 4096)))


def spec_b(rows):
    """b: a 64 x 8 strided texture (stride 64), columns c = 0..32 holding the pair in rows K and
    K + 1; u = (y + 0.5) / 64 (fx = 0, column y), v = (K + 0.5 + x / 64) / 8 (fy = x / 64)."""
    t0, t1, _ = tex.strided(64, 8, 64, t0=T0)
    inj = {}
    for c, ((a0, b0), (a1, b1), hi) in enumerate(rows):
        inj[str(K * 64 + c)] = word(a0, a1, hi)
        inj[str((K + 1) * 64 + c)] = word(b0, b1, hi[::-1])
    return dict(base=0, ins="none", t0=t0, t1=t1, t3=T3, inject=inj,
                u=tex.lin("y", tex.F(1, 64), tex.F(1, 128)),
                v=tex.lin("x", tex.F(1, 512), tex.F(2 * K + 1, 16)))


def eq_rows(seed, n=33):
    """Equal pairs, each channel's bytes in decreasing order down the rows (so a row's decoded half
    is never smaller in exponent than the row below's: stage 2 at fy = 0 aligns to the upper)."""
    rnd = random.Random(seed)
    c0 = sorted(rnd.sample(range(256), n), reverse=True)
    c1 = sorted(rnd.sample(range(256), n), reverse=True)
    hi = [(rnd.randrange(256), rnd.randrange(256)) for _ in range(n)]
    return [((c0[r], c0[r]), (c1[r], c1[r]), hi[r]) for r in range(n)]


def jobs():
    """[(name, set, knobs, spec, {model: image}, extra)]"""
    cases = {c["name"]: c for c in json.loads(pins.blob(E723_CASES))}
    out = [("srgb-ctl", "control", "reads:pixels", cases["g-bl-st-a"]["spec"],
            {"H-E723": pins.kept_pixels(E723_A)}, {})]
    sp = spec_a(eq_rows(9050))
    out.append(("srgb-eq", "control", "reads:pixels", sp, {"H-HALF": eq_value(sp)}, {}))
    ra, rb = pair_rows(9051), pair_rows(9052)
    for name, st, sp in (("srgb-a1", "fit", spec_a(ra)), ("srgb-a2", "fit", spec_a(rb)),
                         ("srgb-b1", "fit", spec_b(pair_rows(9053))),
                         ("srgb-b2", "fit", spec_b(pair_rows(9054))),
                         ("srgb-c1", "heldout", spec_a(ra, 21)),
                         ("srgb-c2", "heldout", spec_a(rb, 43))):
        out.append((name, st, "-", sp, {m: predict(sp, RIVALS[m]) for m in MODELS}, {}))
    return out
