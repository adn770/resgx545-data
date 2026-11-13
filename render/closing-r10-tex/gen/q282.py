# SPDX-License-Identifier: MIT
"""q282.py: the frozen R10-BF11 rule (closing10/seeds/q282/q282_r10_rule.json, sha256
e9623e35337b7a2b1a0ee28f03241e18bd3f6d0858a0133de997919512514104; q282_r10_frozen.py) in the
standard library, exact.

decode: sRGB byte -> linear (the piecewise IEC curve, in float64) -> half, round to nearest even.
stage(A, B, k): k == 0 returns A (the bypass); else e = the larger frexp exponent of A and B
(0 counts as 1e-300's), grid g = 2^(e - 11), A' = floor(A / g) g, B' = floor(B / g) g, the lerp
A' + (k / 64)(B' - A') exactly, rounded to half to nearest with ties up.
two_stage: x stage on (00, 10) and (01, 11) with kx, then the y stage on the two halves with ky
(XY, the rule's headline order).
bypass=False is H-K0FLOOR [infer]: no k == 0 bypass (A floored on the shared grid)."""
import fractions
import math
import struct

F = fractions.Fraction


def s2l(b):
    c = b / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def h2f(h):
    return struct.unpack("<e", struct.pack("<H", h))[0]


def half_rne(f):
    return struct.unpack("<H", struct.pack("<e", f))[0]


def half_rhu(x):
    """x >= 0 (an exact value, a Fraction or float) to half bits, nearest, ties up."""
    h = half_rne(float(x))
    lo = h - 1 if F(h2f(h)) > x else h
    lov, hiv = F(h2f(lo)), F(h2f(lo + 1))
    return lo + 1 if x - lov >= hiv - x else lo


def expo(v):
    return math.frexp(v if v != 0 else 1e-300)[1]


def stage(a, b, k, bypass=True):
    """a, b half values (floats); k the weight of b in 64ths (an int or an exact Fraction)."""
    if k == 0 and bypass:
        return a
    g = F(2) ** (max(expo(a), expo(b)) - 11)
    qa, qb = math.floor(F(a) / g) * g, math.floor(F(b) / g) * g
    r = qa + F(k) / 64 * (qb - qa)
    return h2f(half_rhu(r))


def decode(b):
    return h2f(half_rne(s2l(b)))


def two_stage(b4, kx, ky, bypass=True):
    """The half bits of one channel: b4 the corner bytes 00, 10, 01, 11."""
    d = [decode(b) for b in b4]
    top = stage(d[0], d[1], kx, bypass)
    bot = stage(d[2], d[3], kx, bypass)
    return half_rne(stage(top, bot, ky, bypass))
