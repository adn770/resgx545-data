"""c2-texture check B (Q282 / E1004), frozen rule. Standard library only.

Bilinear sRGB sample (T0 bit 27), two half channels a pixel from texel bytes 0 and 1. Per pixel
and channel, the four corner bytes 00, 10, 01, 11 and the weights kx, ky (1/64 units, floor):
  R10-BF11   (rival)   E982's rule: decode byte -> half (sRGB curve in double, nearest even); stage
                       k = 0 returns A, else g = 2^(e - 11), e the larger frexp exponent, A' and
                       B' floored to g, A' + (k/64)(B' - A') exact, to half nearest ties up; x stage
                       on (00, 10) and (01, 11), then the y stage; result half_rne (copied from
                       render/closing-r10-tex/gen/q282.py).
  FTZ-OUT    (tested)  R10-BF11 with every stage output (both x stages, the y stage) below 2^-14
                       flushed to +0 (copied from out/fold/post_srgb_ftz.py mode "out").
  FTZ-IN     (rival)   R10-BF11 with the operands of every stage below 2^-14 flushed to +0 and the
                       stage results NOT flushed (the pure input-flush reading; E1004's post hoc
                       script's "in" mode also flushed the results, which is FTZ-INOUT).
  FTZ-INOUT  (rival)   operands and results both flushed (post_srgb_ftz.py mode "in").
Pass criterion per job: every pixel (both halves) equal to the kept dword. Per job we count, for
each rule, pixels exact and halves exact; and PART halves = halves where R10-BF11 and FTZ-OUT
differ, SUB halves = halves with a stage output in (0, 2^-14) before any flush (a subnormal stage
output), so the number of halves on which a flush can matter. A job DECIDES the flush only where
PART > 0 (the rules part and the kept half equals one of them). If every held-out job has
PART = 0 the check cannot decide the flush.
"""
import fractions
import math
import struct

F = fractions.Fraction
TINY = 2.0 ** -14


def s2l(b):
    c = b / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def h2f(h):
    return struct.unpack("<e", struct.pack("<H", h))[0]


def half_rne(f):
    return struct.unpack("<H", struct.pack("<e", f))[0]


def half_rhu(x):
    h = half_rne(float(x))
    lo = h - 1 if F(h2f(h)) > x else h
    lov, hiv = F(h2f(lo)), F(h2f(lo + 1))
    return lo + 1 if x - lov >= hiv - x else lo


def expo(v):
    return math.frexp(v if v != 0 else 1e-300)[1]


def stage_bf11(a, b, k):
    if k == 0:
        return a
    g = F(2) ** (max(expo(a), expo(b)) - 11)
    qa, qb = math.floor(F(a) / g) * g, math.floor(F(b) / g) * g
    return h2f(half_rhu(qa + F(k) / 64 * (qb - qa)))


def decode(b):
    return h2f(half_rne(s2l(b)))


def stage(a, b, k, mode, log=None):
    if mode in ("in", "inout"):
        a = 0.0 if abs(a) < TINY else a
        b = 0.0 if abs(b) < TINY else b
    r = stage_bf11(a, b, k)
    if log is not None and 0 < abs(r) < TINY:
        log.append(r)
    return 0.0 if mode in ("out", "inout") and abs(r) < TINY else r


def two_stage(b4, kx, ky, mode, log=None):
    """The half bits of one channel; mode: none (R10-BF11), out (FTZ-OUT), in (FTZ-IN),
    inout (FTZ-INOUT); log collects the subnormal (unflushed) stage outputs."""
    d = [decode(b) for b in b4]
    top = stage(d[0], d[1], kx, mode, log)
    bot = stage(d[2], d[3], kx, mode, log)
    return half_rne(stage(top, bot, ky, mode, log))
