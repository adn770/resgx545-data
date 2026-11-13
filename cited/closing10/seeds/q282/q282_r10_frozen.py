"""Frozen Q282 round-10 rule (fit on r9-x srgb a1 a2 b1 b2 only). One lerp stage on two half values:
 k == 0 -> the first operand unchanged; else both operands floored on the grid 2^(e-11), e = the
 larger frexp exponent of the two (a shared 11-bit mantissa), the lerp (64-k)*A + k*B computed exactly
 (>= 17 bits), the result rounded to half to nearest with ties up (away from zero)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import numpy as np
from q282_r10_tab import h2f, s2l_arr
from q282_r10_rules import half_bits, expo

def decode_half(byte):
    return h2f(half_bits(s2l_arr(np.asarray(byte, dtype=np.float64)), "rne"))

def stage(a, b, k):
    """a, b float64 arrays of half values, k weight numerator of b (/64); returns half values (float64)"""
    g = 2.0 ** (np.maximum(expo(a), expo(b)) - 11)
    qa, qb = np.floor(a / g) * g, np.floor(b / g) * g
    r = qa + (k / 64.0) * (qb - qa)
    out = h2f(half_bits(r, "rhu"))
    return np.where(k == 0, a, out)

def stage_bits(a, b, k):
    g = 2.0 ** (np.maximum(expo(a), expo(b)) - 11)
    qa, qb = np.floor(a / g) * g, np.floor(b / g) * g
    r = qa + (k / 64.0) * (qb - qa)
    return np.where(k == 0, half_bits(a, "rne"), half_bits(r, "rhu"))
