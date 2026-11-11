#!/usr/bin/env python3
"""Frozen numbers for the proposal (offline, numpy for float32 only)."""
import sys, math, struct
sys.dont_write_bytecode = True
sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
import numpy as np
from fractions import Fraction
from u_model import model, default_tri, tiling
from clip_rules import sh_clip, zigzag

f32 = np.float32


def bits(x):
    return struct.unpack("<I", struct.pack("<f", float(f32(x))))[0]


def rz_frac(x: Fraction):
    f = float(x); b = bits(f)
    fb = lambda b: Fraction(struct.unpack("<f", struct.pack("<I", b))[0])
    while fb(b) > x: b -= 1
    while fb(b + 1) <= x: b += 1
    return b


print("== Q211 held-out U predictions (HU1: 128 B a stream, a page per macrotile list, + 1 global page)")
base = default_tri(1024, 768)
scenes = [
    ("1024x768 moved (32,0) [one column]", 1024, 768, [default_tri(1024, 768, 32, 0)]),
    ("1024x768 moved (0,96)", 1024, 768, [default_tri(1024, 768, 0, 96)]),
    ("1024x768 moved (-128,96) [E627's move]", 1024, 768, [default_tri(1024, 768, -128, 96)]),
    ("1024x768 moved (384,288) [E627: completes at 0x30]", 1024, 768, [default_tri(1024, 768, 384, 288)]),
    ("1024x768 two: base + (-96,0) [E627 st-two]", 1024, 768, [base, default_tri(1024, 768, -96, 0)]),
    ("1024x768 two: base + (256,192)", 1024, 768, [base, default_tri(1024, 768, 256, 192)]),
    ("1024x768 three: base + (16,0) + (0,16)", 1024, 768, [base, default_tri(1024, 768, 16, 0), default_tri(1024, 768, 0, 16)]),
    ("1024x768 four apart: (0,0) (512,0) (0,384) (512,384)", 1024, 768, [default_tri(1024, 768, dx, dy) for dx, dy in ((0, 0), (512, 0), (0, 384), (512, 384))]),
    ("640x480 default", 640, 480, [default_tri(640, 480)]),
    ("800x600 default", 800, 600, [default_tri(800, 600)]),
    ("1280x1024 default", 1280, 1024, [default_tri(1280, 1024)]),
    ("2048x2048 default", 2048, 2048, [default_tri(2048, 2048)]),
    ("2048x1536 default", 2048, 1536, [default_tri(2048, 1536)]),
    ("512x384 moved (128,0)", 512, 384, [default_tri(512, 384, 128, 0)]),
    ("4096x4096 moved (1024,0)", 4096, 4096, [default_tri(4096, 4096, 1024, 0)]),
    ("4096x4096 two: base + (0,1024)", 4096, 4096, [default_tri(4096, 4096), default_tri(4096, 4096, 0, 1024)]),
]
for name, w, h, tris in scenes:
    U, per, pg = model(w, h, tris)
    cov = len(per)
    print(f"  {name:52} tiling {str(tiling(w, h)):22} U = {U:4d}  (macrotiles {cov}, HU2 'coverage+c' would give {cov}+c)  per-mtile {' '.join(f'{m}:{per[m]}:{pg[m]}' for m in sorted(per))}")

print("\n== E625 count constant k: 4096x4096 default triangle (U 287), count 2 iff k >= 2*thr0 - 256 (spacing 0x1f)")
for P in range(0xa2, 0xab):
    thr0 = P - 0x22
    print(f"  P {P:#x} thr0 {thr0}: count 2 iff k >= {2 * thr0 - 256} (0x1f) / k >= {2 * thr0 - 257} (0x1e)")
print("  three partial renders: count 3 iff k >= 3*thr0 + 2s - 287:")
for P in range(0x5e, 0x66):
    thr0 = P - 0x22
    print(f"  P {P:#x} thr0 {thr0}: count 3 iff k >= {3 * thr0 + 2 * 0x1f - 287} (0x1f) / k >= {3 * thr0 + 2 * 0x1e - 287} (0x1e)")

print("\n== Q230 clamp ladder: clamp words where RZ and RN of 1/clamp differ (fraction of the exact in the ulp of the stored)")
for c in (2e-5, 4e-5, 5e-5, 6e-5, 7e-5, 8e-5, 1.5e-4, 2e-4, 2.5e-4, 4e-4, 5e-4, 6e-4, 7e-4, 8e-4, 9e-4, 1.2e-3, 2e-3):
    w = bits(c)
    x = 1 / Fraction(float(f32(c)))
    lo = rz_frac(x)
    flo = Fraction(struct.unpack("<f", struct.pack("<I", lo))[0]); fhi = Fraction(struct.unpack("<f", struct.pack("<I", lo + 1))[0])
    frac = float((x - flo) / (fhi - flo))
    print(f"  clamp {c:8.1e} word {w:#010x}: RZ {lo:#010x} RN {lo + (1 if frac > 0.5 else 0):#010x} frac {frac:.3f} {'<- separates' if frac > 0.5 else ''}")

print("\n== Q230 depth at w != 1: candidate formulas for the stored depth of a vertex with clip z = Z, w = W (viewport z off 0.5, scale 0.5)")
def rz32(x):  # toward zero of a double, as float32 bits
    f = f32(x)
    if abs(float(f)) > abs(x):
        b = bits(f) - 1
        return struct.unpack("<f", struct.pack("<I", b))[0]
    return float(f)
def cands(Z, W):
    Z, W = f32(Z), f32(W)
    rhw_rz = f32(rz32(1.0 / float(W)))
    out = {}
    out["D1 0.5+0.5*(Z*RZ(1/W))"] = f32(f32(0.5) + f32(f32(0.5) * f32(Z * rhw_rz)))
    out["D2 0.5+0.5*RZ(Z/W)"] = f32(f32(0.5) + f32(f32(0.5) * f32(rz32(float(Z) / float(W)))))
    out["D3 0.5+0.5*RN(Z/W)"] = f32(f32(0.5) + f32(f32(0.5) * f32(float(Z) / float(W))))
    out["D4 fma(0.5,Z*RZ(1/W),0.5) exact"] = f32(0.5 * float(f32(Z * rhw_rz)) + 0.5)
    out["D5 RZ(Z*RZ(1/W))*0.5+0.5"] = f32(f32(0.5) + f32(f32(0.5) * f32(rz32(float(Z) * float(rhw_rz)))))
    out["D6 (Z+W)/(2W) RN"] = f32((float(Z) + float(W)) / (2 * float(W)))
    return {k: bits(v) for k, v in out.items()}
pairs = [(0.3, 3), (0.7, 3), (0.9, 7), (0.1, 7), (0.5, 3), (0.37, 0.003), (0.61, 3e-5), (0.2, 7), (0.8, 0.7)]
for Z, W in pairs:
    c = cands(Z, W)
    vals = list(c.values())
    print(f"  Z {Z} W {W}: " + " ".join(f"{k.split()[0]}={v:#010x}" for k, v in c.items()) + f"  distinct {len(set(vals))}/6")

print("\n== Q230 slab cut z = 4x (inside |z| <= w: -0.25 <= x <= 0.25), SH order over the planes z<=w then z>=-w, then zigzag")
A, B, C = (-0.75, -0.75), (0.75, -0.375), (-0.375, 0.75)
win = lambda p: (round(32 + 32 * p[0], 3), round(32 + 32 * p[1], 3))
def cross_at(xc):
    return lambda a, b: (xc, a[1] + (xc - a[0]) / (b[0] - a[0]) * (b[1] - a[1]))
for order_name, planes in (("+w then -w", ((lambda p: p[0] <= 0.25, cross_at(0.25)), (lambda p: p[0] >= -0.25, cross_at(-0.25)))),
                           ("-w then +w", ((lambda p: p[0] >= -0.25, cross_at(-0.25)), (lambda p: p[0] <= 0.25, cross_at(0.25))))):
    poly = [A, B, C]
    for inside, cross in planes:
        poly = sh_clip(poly, inside, cross)
    zz = zigzag(len(poly))
    print(f"  planes {order_name}: polygon {[win(p) for p in poly]} -> stored order {[win(poly[i]) for i in zz]}")
    print(f"     depths: 0.5 + 0.5*4x -> {[round(0.5 + 0.5 * 4 * poly[i][0], 4) for i in zz]}")
print("  cut z = 2x + 0.5 (<= w: x <= 0.25):")
poly = sh_clip([A, B, C], lambda p: p[0] <= 0.25, cross_at(0.25))
print(f"     polygon {[win(p) for p in poly]} -> stored {[win(poly[i]) for i in zigzag(len(poly))]} depths {[round(0.5 + 0.5 * (2 * poly[i][0] + 0.5), 4) for i in zigzag(len(poly))]}")
