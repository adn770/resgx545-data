#!/usr/bin/env python3
"""Q230 offline: which reciprocal rule gives the stored 1/w of every clamp job and every in-band w (E736, E754)?

Data (float32 word in -> stored 1/w word), all from the records:
  in band (w itself; E754 e3i, S1 e3w): 3, 7, 0.003, 3e-5, 2, 0.5, 1
  under a clamp (the stored 1/w is the clamp's reciprocal; E736 e3k-ctl/-above, E754 e3k-i-*): clamps 1e-3, 1e-3+1ulp,
  1e-5, 3e-5, 1e-4, 3e-4
Rules tried: RZ and RN of the exact reciprocal; RZ/RN after the input's mantissa is truncated or rounded to k bits;
RZ/RN of a reciprocal computed in a reduced precision (k-bit result); one-Newton-step from a k-bit seed (RZ/RN).
"""
import sys, struct
from fractions import Fraction
sys.dont_write_bytecode = True

DATA_W = [(0x40400000, 0x3eaaaaaa), (0x40e00000, 0x3e124924), (0x3b449ba6, 0x43a6aaaa), (0x37fba882, 0x47023555),
          (0x40000000, 0x3f000000), (0x3f000000, 0x40000000), (0x3f800000, 0x3f800000)]
DATA_C = [(0x3a83126f, 0x4479ffff), (0x3a831270, 0x4479fffd), (0x3727c5ac, 0x47c35000), (0x37fba882, 0x47023555),
          (0x38d1b717, 0x461c4000), (0x399d4952, 0x45505555)]


def f32(w):
    return struct.unpack("<f", struct.pack("<I", w))[0]


def bits(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def frac_of(w):
    return Fraction(f32(w))


def rz(x: Fraction):
    """float32 toward zero of a positive rational."""
    f = float(x)                      # double, nearest
    b = bits(f)
    # correct: make sure the float32 value <= x
    while Fraction(f32(b)) > x:
        b -= 1
    while Fraction(f32(b + 1)) <= x:
        b += 1
    return b


def rn(x: Fraction):
    lo = rz(x); hi = lo + 1
    dl, dh = x - Fraction(f32(lo)), Fraction(f32(hi)) - x
    return lo if dl < dh else hi if dh < dl else (lo if lo % 2 == 0 else hi)


def trunc_mant(w, k):
    """keep k mantissa bits of a float32 word (truncate the rest)."""
    return w & ~((1 << (23 - k)) - 1) if k < 23 else w


def round_mant(w, k):
    if k >= 23:
        return w
    step = 1 << (23 - k)
    return (w + step // 2) & ~(step - 1)


def check(rule, data):
    return sum(1 for a, b in data if rule(a) == b), len(data)


def main():
    rules = {"RZ(1/x)": lambda w: rz(1 / frac_of(w)), "RN(1/x)": lambda w: rn(1 / frac_of(w))}
    for k in range(23, 7, -1):
        rules[f"RZ(1/trunc{k}(x))"] = (lambda k: lambda w: rz(1 / frac_of(trunc_mant(w, k))))(k)
        rules[f"RN(1/trunc{k}(x))"] = (lambda k: lambda w: rn(1 / frac_of(trunc_mant(w, k))))(k)
        rules[f"RZ(1/round{k}(x))"] = (lambda k: lambda w: rz(1 / frac_of(round_mant(w, k))))(k)
        rules[f"RN(1/round{k}(x))"] = (lambda k: lambda w: rn(1 / frac_of(round_mant(w, k))))(k)
        # reciprocal computed with a k-bit significand result then widened (toward zero / nearest at k bits)
        rules[f"RZk{k}(1/x)"] = (lambda k: lambda w: trunc_mant(rz(1 / frac_of(w)), k))(k)
        rules[f"RNk{k}(1/x)"] = (lambda k: lambda w: round_mant(rn(1 / frac_of(w)), k))(k)
    print("rule: in-band w hits / clamp hits")
    for name, rule in rules.items():
        hw, nw = check(rule, DATA_W)
        hc, nc = check(rule, DATA_C)
        flag = " <== all" if hw == nw and hc == nc else (" <== all clamp" if hc == nc else "")
        if hw == nw or hc == nc or name in ("RZ(1/x)", "RN(1/x)"):
            print(f"  {name:22} {hw}/{nw}  {hc}/{nc}{flag}")
    print("\nper clamp: exact 1/x, RZ, RN, stored")
    for a, b in DATA_C:
        x = frac_of(a)
        print(f"  clamp {a:#010x} = {f32(a):.9g}: 1/x = {float(1 / x):.9f}  RZ {rz(1 / x):#010x} RN {rn(1 / x):#010x}  stored {b:#010x} ({f32(b):.9g})")
    # distance of the exact reciprocal from the stored word in ulps
    print("\nstored - exact in ulps of the stored word (positive: stored above exact)")
    for a, b in DATA_W + DATA_C:
        x = 1 / frac_of(a)
        ulp = Fraction(f32(b + 1)) - Fraction(f32(b))
        print(f"  in {a:#010x} stored {b:#010x}: {float((Fraction(f32(b)) - x) / ulp):+.4f} ulp")


if __name__ == "__main__":
    main()
