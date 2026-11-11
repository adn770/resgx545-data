# SPDX-License-Identifier: MIT
"""rwfam.py: the families of reciprocal algorithms g4-rw's analysis may fit (Q230), DECLARED BEFORE ANY RUN and frozen with the
scorer.  A model maps the mantissa m in [1, 2) of w = m 2^e to a float32 value q ~ 1/m; the word of 1/w is that of q 2^-e (a power
of two scales exactly).  Exact rational arithmetic with an explicit float32 rounding (rz toward zero, rn to nearest even, ru up) at
every operation named.  Families (letters are the unit of the stop condition):
  a  table of the top t mantissa bits (entry: the reciprocal at the interval's left edge or midpoint, rounded rz or rn) and ONE
     Newton-Raphson step x (2 - m x) with every operation rounded rz or rn            t 3..10, 2 x 2 x 2         64 models
  b  table of the top t bits with linear interpolation by the next bits (entries and slope rounded rz or rn, the product and the sum
     rounded the same way)                                                             t 3..10, 2 x 2             32 models
  c  a seed correct to s bits (the exact reciprocal cut to s mantissa bits by rz or rn), then k Newton-Raphson steps with rz or rn
     operations                                                                        s 4..12, k 1..3, 2 x 2    108 models
  d  restoring division, the quotient cut after b bits (b 22..26) and read as a float32 by rz or rn; and the non-restoring
     (digits +-1) quotient of b bits (b 24..27) read the same way                      5 x 2 + 4 x 2              18 models
  e  the exact reciprocal rounded rz, rn or ru (up)                                    3 models
E783's lesson (4 of 257 models fit six words by chance): a model counts only after 30 of 30 on the FIT half, and is adopted only if it
then holds 30 of 30 on the HELD OUT half; the scorer also prints how many models fit 30 of 30 on FIT words whose pairing with w was
shuffled (fixed seeds), the chance rate of this family set.  Stop condition: more than one FAMILY fits 30 of 30 held out, or none:
the words are recorded and no rule is adopted."""
from __future__ import annotations

import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True


def _quant(x: F) -> F:
    ax = abs(x)
    e = ax.numerator.bit_length() - ax.denominator.bit_length()
    if F(2) ** e > ax:
        e -= 1
    return F(2) ** (e - 23)


def rz(x: F) -> F:
    if x == 0:
        return F(0)
    q = _quant(x)
    n = abs(x) / q
    return (1 if x > 0 else -1) * (n.numerator // n.denominator) * q


def ru(x: F) -> F:
    if x == 0:
        return F(0)
    q = _quant(x)
    n = abs(x) / q
    f = -((-n.numerator) // n.denominator)
    return (1 if x > 0 else -1) * f * q


def rn(x: F) -> F:
    if x == 0:
        return F(0)
    q = _quant(x)
    n = abs(x) / q
    f = n.numerator // n.denominator
    r = n - f
    if r > F(1, 2) or (r == F(1, 2) and f % 2):
        f += 1
    return (1 if x > 0 else -1) * f * q


RND = {"rz": rz, "rn": rn, "ru": ru}


def cut_bits(x: F, s: int, mode: str) -> F:
    """x to s mantissa bits (s significant bits after the leading one)."""
    ax = abs(x)
    e = ax.numerator.bit_length() - ax.denominator.bit_length()
    if F(2) ** e > ax:
        e -= 1
    q = F(2) ** (e - s)
    n = ax / q
    f = n.numerator // n.denominator
    if mode == "rn":
        r = n - f
        if r > F(1, 2) or (r == F(1, 2) and f % 2):
            f += 1
    return f * q


def _nr(m: F, x: F, r) -> F:
    t = r(m * x)
    s = r(2 - t)
    return r(x * s)


def model_a(t, edge, tr, mode):
    r, rt = RND[mode], RND[tr]

    def f(m: F) -> F:
        i = int((m - 1) * (1 << t))
        left = 1 + F(i, 1 << t)
        pt = left if edge == "left" else left + F(1, 1 << (t + 1))
        return _nr(m, rt(1 / pt), r)
    return f


def model_b(t, tr, mode):
    r, rt = RND[mode], RND[tr]

    def f(m: F) -> F:
        i = int((m - 1) * (1 << t))
        left = 1 + F(i, 1 << t)
        right = left + F(1, 1 << t)
        y0, y1 = rt(1 / left), rt(1 / right)
        slope = r(y1 - y0)
        frac = (m - left) * (1 << t)
        return r(y0 + r(slope * frac))
    return f


def model_c(s, k, tr, mode):
    r = RND[mode]

    def f(m: F) -> F:
        x = cut_bits(1 / m, s, tr)
        for _ in range(k):
            x = _nr(m, x, r)
        return x
    return f


def model_d(b, rd):
    r = RND[rd]

    def f(m: F) -> F:
        q = F(int((1 / m) * (1 << b)), 1 << b)
        return r(q)
    return f


def model_dn(b, rd):
    r = RND[rd]

    def f(m: F) -> F:
        rem, q = F(1), F(0)
        for i in range(1, b + 1):
            if rem >= 0:
                q += F(1, 1 << i)
                rem = 2 * rem - m
            else:
                q -= F(1, 1 << i)
                rem = 2 * rem + m
        # q approximates 1/m from the digits +-1 over b places, the first digit taken at weight 2^-1 (rem starts at 1)
        return r(q)
    return f


def model_e(mode):
    r = RND[mode]
    return lambda m: r(1 / m)


def models():
    """{name: (family letter, function)} in a fixed order."""
    out = {}
    for t in range(3, 11):
        for edge in ("left", "mid"):
            for tr in ("rz", "rn"):
                for mode in ("rz", "rn"):
                    out[f"a:t{t}:{edge}:{tr}:{mode}"] = ("a", model_a(t, edge, tr, mode))
    for t in range(3, 11):
        for tr in ("rz", "rn"):
            for mode in ("rz", "rn"):
                out[f"b:t{t}:{tr}:{mode}"] = ("b", model_b(t, tr, mode))
    for s in range(4, 13):
        for k in (1, 2, 3):
            for tr in ("rz", "rn"):
                for mode in ("rz", "rn"):
                    out[f"c:s{s}:k{k}:{tr}:{mode}"] = ("c", model_c(s, k, tr, mode))
    for b in range(22, 27):
        for rd in ("rz", "rn"):
            out[f"d:rest:b{b}:{rd}"] = ("d", model_d(b, rd))
    for b in range(24, 28):
        for rd in ("rz", "rn"):
            out[f"d:nonrest:b{b}:{rd}"] = ("d", model_dn(b, rd))
    for mode in ("rz", "rn", "ru"):
        out[f"e:{mode}"] = ("e", model_e(mode))
    return out


def split_word(wb: int):
    """(m, e): the mantissa in [1, 2) and the exponent of a positive normal float32 word."""
    return 1 + F(wb & 0x7fffff, 1 << 23), ((wb >> 23) & 0xff) - 127


def word_of(q: F, e: int) -> int:
    import struct
    v = float(q / F(2) ** e)
    return struct.unpack("<I", struct.pack("<f", v))[0]


def predict(model, wb: int) -> int:
    m, e = split_word(wb)
    return word_of(model(m), e)


def fits(fn, pairs) -> int:
    """How many (w word, got word) pairs the model function reproduces exactly."""
    return sum(1 for w, g in pairs if predict(fn, w) == g)
