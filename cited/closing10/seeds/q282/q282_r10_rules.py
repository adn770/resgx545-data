"""Candidate one-stage rules for Q282 (sRGB bilinear, one lerp stage). Vectorised numpy float64
(every operation here is exact in float64 for the widths used). A rule is a dict of parameters."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, math
from q282_r10_tab import h2f, s2l_arr

def half_bits(x, mode):
    """float64 array (>=0) -> half bit patterns, mode rne/rz/ru"""
    x = np.asarray(x, dtype=np.float64)
    h = x.astype(np.float16)          # numpy rounds to nearest even
    hv = h.astype(np.float64)
    b = h.view(np.uint16).astype(np.int64)
    if mode == "rz":
        b = np.where(hv > x, b - 1, b)
    elif mode == "ru":
        b = np.where(hv < x, b + 1, b)
    elif mode == "rhu":   # round to nearest, ties up (away from zero; values are >= 0)
        lo = np.where(hv > x, b - 1, b)
        lov = h.view(np.uint16).astype(np.int64)
        lov = np.where(hv > x, lo, b).astype(np.uint16).view(np.float16).astype(np.float64)
        hiv = (lo + 1).astype(np.uint16).view(np.float16).astype(np.float64)
        b = np.where(x - lov >= hiv - x, lo + 1, lo)
    return b

def rnd(x, mode):
    if mode == "floor": return np.floor(x)
    if mode == "rne": return np.rint(x)
    if mode == "ceil": return np.ceil(x)
    if mode == "rhu": return np.floor(x + 0.5)
    if mode == "none": return x
    raise ValueError(mode)

def decode(Abyte, p):
    """decoded corner (float64) per the rule's decode: half | f32 | fixB:<bits>:<mode>"""
    d = p["dec"]
    l = s2l_arr(Abyte.astype(np.float64))
    if d == "half":
        return h2f(half_bits(l, "rne"))
    if d == "f32":
        return l.astype(np.float32).astype(np.float64)
    if d.startswith("fix"):
        _, bits, mode = d.split(":")
        s = 2.0 ** int(bits)
        return rnd(l * s, mode) / s
    raise ValueError(d)

def expo(x):
    return np.frexp(np.where(x == 0, 1e-300, x))[1]

def grid_for(a, b, p):
    sel = p.get("align", "max")
    ea, eb = expo(a), expo(b)
    e = np.maximum(ea, eb) if sel == "max" else ea if sel == "a" else eb if sel == "b" else np.minimum(ea, eb)
    return 2.0 ** (e - p["M"])

def apply_rule(A, B, k, p):
    """A,B bytes (arrays), k weight numerator /64 (arrays); returns half bit patterns"""
    a, b = decode(A, p), decode(B, p)
    wb = k / 64.0
    if p.get("wbits"):      # weight precision: nearest representable on 2^-wbits grid (k/64 exact if >=6)
        wb = np.floor(wb * 2 ** p["wbits"]) / 2 ** p["wbits"]
    wa = 1.0 - wb
    fam = p["fam"]
    if fam == "bf":         # block-float / shared-exponent grid
        g = grid_for(a, b, p)
        qa, qb = rnd(a / g, p["qin"]) * g, rnd(b / g, p["qin"]) * g
    else:
        qa, qb = a, b
        g = None
    if fam == "mant":       # float with m mantissa bits at every step
        m = p["M"]
        def R(x):
            e = expo(x)
            s = 2.0 ** (m - e)
            return rnd(x * s, p["qf"]) / s
        qa, qb = R(a), R(b)
        if p["form"] == "A":
            r = R(qa + R(wb * R(qb - qa)))
        else:
            r = R(R(wa * qa) + R(wb * qb))
        return half_bits(r, p["out"])
    if fam == "fx":         # fixed point with F fractional bits
        s = 2.0 ** p["F"]
        qa, qb = rnd(a * s, p["qin"]) / s, rnd(b * s, p["qin"]) / s
        g = 1.0 / s
        qn = g
    else:
        qn = g
    if p["form"] == "A":
        pr = rnd(wb * (qb - qa) / (qn / 2.0 ** p["X"]), p["qprod"]) * (qn / 2.0 ** p["X"])
        r = qa + pr
    else:
        pa = rnd(wa * qa / (qn / 2.0 ** p["X"]), p["qprod"]) * (qn / 2.0 ** p["X"])
        pb = rnd(wb * qb / (qn / 2.0 ** p["X"]), p["qprod"]) * (qn / 2.0 ** p["X"])
        r = pa + pb
    if p["qsum"] != "none":
        r = rnd(r / qn, p["qsum"]) * qn
    return half_bits(np.maximum(r, 0), p["out"])

def grid():
    """the declared search space: yields parameter dicts"""
    import itertools
    outs = ("rne", "rz", "ru", "rhu")
    # block float, shared exponent
    for dec in ("half", "f32"):
      for M in range(8, 17):
        for al in ("max", "a", "b"):
          for qin in ("floor", "rne"):
            for form in ("A", "B"):
              for X in (0, 1, 2, 3, 4, 6, 8):
                for qprod in ("floor", "rne"):
                  for qsum in ("none", "floor", "rne"):
                    for out in outs:
                        yield dict(fam="bf", dec=dec, M=M, align=al, qin=qin, form=form, X=X, qprod=qprod, qsum=qsum, out=out)
    # fixed point on decoded value
    for dec in ("half", "f32") + tuple(f"fix:{b}:{m}" for b in (10, 12, 14, 16, 20) for m in ("floor", "rne")):
      for F in range(8, 25):
        for qin in ("floor", "rne", "none"):
          for form in ("A", "B"):
            for X in (0, 2):
              for qprod in ("floor", "rne"):
                for qsum in ("none", "floor", "rne"):
                  for out in outs:
                    yield dict(fam="fx", dec=dec, F=F, qin=qin, form=form, X=X, qprod=qprod, qsum=qsum, out=out, M=0)
    # mantissa-limited floats at every step
    for dec in ("half", "f32"):
      for M in range(10, 24):
        for qf in ("floor", "rne"):
          for form in ("A", "B"):
            for out in outs:
                yield dict(fam="mant", dec=dec, M=M, qf=qf, form=form, out=out)
    # weight precision variants of the half baseline
    for dec in ("half",):
      for wb in (6, 7, 8):
        for form in ("A", "B"):
          for out in outs:
            yield dict(fam="mant", dec=dec, M=11, qf="rne", form=form, out=out, wbits=wb)
