# SPDX-License-Identifier: MIT
"""srgb.py: stage srgb2 (S10-tex, Q282, seeds plan closing10/seeds/exp-seeds-r10.md section 1):
the bilinear sample of an sRGB texel (T0 bit 27) in E723's g-bl-st form (strided, texel bytes
injected by the program's PRE, two half channels a pixel from the texel's bytes 0 and 1), r9-x's
gen/srgb.py (resgx545-data render/closing-r9-x) copied and cut to what srgb2 needs.

The frozen rule (seeds q282/q282_r10_rule.json, sha256 e9623e35..., fitted on r9-x's a1, a2, b1,
b2 only and held out offline on c1, c2 and E723's g-bl-st-b; record E982), here in the standard
library (gen/q282.py; tests/test_gen.py replays it on r9-x's six kept rows, 2048 of 2048 each).
Per stage on two halves A (weight 64 - k) and B (weight k): k = 0 returns A; else both floored on
the grid 2^(e - 11), e the larger frexp exponent, lerped exactly, rounded to half to nearest, ties
up. x stage then y stage (XY).

Rows (each 2048 pixels, nothing fitted on them):
  srgb2-ctl      E723's g-bl-st-a rerun (its kept image: a control that can fail)
  srgb2-offgrid  fx = x / 64 + 3 / 256, fy = 21 / 64 + 3 / 256: 64 f off the grid by 3/4, so
                 k = floor(64 f) (R10-BF11) and k = round(64 f) (R10-BF11-ROUND) part on every
                 pixel; H-WEXACT the rule with the exact weight f [infer]
  srgb2-k0b      fx = 0 (the x stage at k = 0), fy = x / 64; the x neighbour B larger than A in
                 even columns, smaller in odd ones: R10-BF11 (A returned) against H-K0FLOOR (no
                 bypass: A floored on the shared grid at k = 0) [infer]; with B the smaller both
                 return A, so the plan's "B the smaller" alone could not part them
  srgb2-sub      corner bytes 0 to 3, each pair a 0 and a byte 1 to 3 (channel 0 from 0, channel
                 1 to 0), fy = 5 / 64: lerps from or to 0 give subnormal halves near the 0 corner
                 (bytes 1 to 3 alone decode to normal halves, 3.0e-4 and up)
  srgb2-rand1    random bytes, a1's form at fy = 13 / 64
  srgb2-rand2    random bytes, b's form with fx = 37 / 64 (the y stage over x, the x stage fixed)"""
import json
import math
import random
import struct

import pins
import q282 as Q
import tex

STAGE = "srgb2"
E723_CASES = "data:texture/p1141/gen/cases.json"
E723_A = "data:texture/p1141/out-hw/p1141tex-dumps/tex-d-t0b27/g-bl-st-a.txt.gz"
T0 = 0x08001E00          # g-bl-st-a's T0: bit 27 sRGB, bilinear, stride from tex.strided
T3 = 0xA0800000
K = 3                    # the texel pair: columns (a) or rows (b) 3 and 4
F = tex.F


def texel(sp, cx, cy):
    """The texel dword (cx, cy) of a strided spec: injected, else the named-memory dword."""
    s = ((sp["t0"] >> 9 & 7) | (sp["t0"] >> 17 & 0x3FF) << 3) + 1
    i = cy * s + cx
    return sp["inject"].get(str(i), 0xD0000000 | i)


def footprint(sp, x, y):
    """(the four corner texels 00, 10, 01, 11, fx, fy) of pixel (x, y), fx and fy exact
    fractions (x = u * w - 0.5)."""
    w, h = (sp["t1"] >> 12 & 0xFFF) + 1, (sp["t1"] & 0xFFF) + 1
    fx = tex.coord(sp["u"], x, y) * w - F(1, 2)
    fy = tex.coord(sp["v"], x, y) * h - F(1, 2)
    x0, y0 = math.floor(fx), math.floor(fy)
    assert 0 <= x0 and x0 + 1 < w and 0 <= y0 and y0 + 1 < h, (x, y)
    t = [texel(sp, x0 + dx, y0 + dy) for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
    return t, fx - x0, fy - y0


WEIGHTS = {
    "R10-BF11": lambda f: math.floor(64 * f),
    "R10-BF11-ROUND": lambda f: math.floor(64 * f + F(1, 2)),
    "H-WEXACT": lambda f: 64 * f,
    "H-K0FLOOR": lambda f: math.floor(64 * f),
}


def predict(sp, model):
    out = []
    k0 = model == "H-K0FLOOR"
    for p in range(2048):
        t, fx, fy = footprint(sp, p % 64, p // 64)
        kx, ky = WEIGHTS[model](fx), WEIGHTS[model](fy)
        v = 0
        for c in (0, 1):
            v |= Q.two_stage([b >> 8 * c & 255 for b in t], kx, ky, bypass=not k0) << 16 * c
        out.append(v)
    return out


def word(b0, b1, hi):
    return b0 | b1 << 8 | hi[0] << 16 | hi[1] << 24


def pair_rows(seed, n=33):
    rnd = random.Random(seed)
    return [((rnd.randrange(256), rnd.randrange(256)), (rnd.randrange(256), rnd.randrange(256)),
             (rnd.randrange(256), rnd.randrange(256))) for _ in range(n)]


def sub_rows(seed, n=33):
    """Channel 0 (0, b) and channel 1 (b', 0) with b, b' in 1 to 3: a lerp from or to 0 gives
    halves below 2^-14 (subnormal) at the weights near the 0 corner."""
    rnd = random.Random(seed)
    return [((0, rnd.randint(1, 3)), (rnd.randint(1, 3), 0), (rnd.randrange(256), rnd.randrange(256)))
            for _ in range(n)]


def k0b_rows(seed, n=33):
    """Row K's byte (A of the x stage in column c, B of column c - 1) small in even columns and
    large in odd ones, per channel; row K + 1 random."""
    rnd = random.Random(seed)
    out = []
    for c in range(n):
        a = [rnd.randint(1, 60) if c % 2 == 0 else rnd.randint(150, 255) for _ in range(2)]
        b = [rnd.randrange(256) for _ in range(2)]
        out.append(((a[0], b[0]), (a[1], b[1]), (rnd.randrange(256), rnd.randrange(256))))
    return out


def spec_a(rows, fy, du=0):
    """r9-x's a form: an 8 x 64 strided texture, rows r = 0..32 holding the pair in columns K and
    K + 1; v = (y + 0.5 + fy) / 64, u = (K + 0.5 + x / 64 + du) / 8."""
    t0, t1, _ = tex.strided(8, 64, 8, t0=T0)
    inj = {}
    for r, ((a0, b0), (a1, b1), hi) in enumerate(rows):
        inj[str(r * 8 + K)] = word(a0, a1, hi)
        inj[str(r * 8 + K + 1)] = word(b0, b1, hi[::-1])
    return dict(base=0, ins="none", t0=t0, t1=t1, t3=T3, inject=inj,
                u=tex.lin("x", F(1, 512), F(2 * K + 1, 16) + F(du, 8)),
                v=tex.lin("y", F(1, 64), F(1, 128) + F(fy, 64)))


def spec_b(rows, fx=0):
    """r9-x's b form: a 64 x 8 strided texture (stride 64), columns c = 0..32 holding the pair in
    rows K and K + 1; u = (y + 0.5 + fx) / 64, v = (K + 0.5 + x / 64) / 8 (fy = x / 64)."""
    t0, t1, _ = tex.strided(64, 8, 64, t0=T0)
    inj = {}
    for c, ((a0, b0), (a1, b1), hi) in enumerate(rows):
        inj[str(K * 64 + c)] = word(a0, a1, hi)
        inj[str((K + 1) * 64 + c)] = word(b0, b1, hi[::-1])
    return dict(base=0, ins="none", t0=t0, t1=t1, t3=T3, inject=inj,
                u=tex.lin("y", F(1, 64), F(1, 128) + F(fx, 64)),
                v=tex.lin("x", F(1, 512), F(2 * K + 1, 16)))


ROWS = [
    ("srgb2-offgrid", lambda: spec_a(pair_rows(10051), F(21, 64) + F(3, 256), F(3, 256)),
     ("R10-BF11", "R10-BF11-ROUND", "H-WEXACT")),
    ("srgb2-k0b", lambda: spec_b(k0b_rows(10052)), ("R10-BF11", "H-K0FLOOR")),
    ("srgb2-sub", lambda: spec_a(sub_rows(10053), F(5, 64)), ("R10-BF11",)),
    ("srgb2-rand1", lambda: spec_a(pair_rows(10054), F(13, 64)), ("R10-BF11",)),
    ("srgb2-rand2", lambda: spec_b(pair_rows(10055), F(37, 64)), ("R10-BF11",)),
]


def jobs():
    """[(name, set, knobs, spec, {model: image})]"""
    cases = {c["name"]: c for c in json.loads(pins.blob(E723_CASES))}
    out = [("srgb2-ctl", "control", "reads:pixels", cases["g-bl-st-a"]["spec"],
            {"H-E723": pins.kept_pixels(E723_A)})]
    for name, mk, models in ROWS:
        sp = mk()
        out.append((name, "heldout", "-", sp, {m: predict(sp, m) for m in models}))
    return out


def h2f(h):
    return struct.unpack("<e", struct.pack("<H", h))[0]
