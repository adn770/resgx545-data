#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/look.py: r15-zls's post hoc reads (written after the run, not frozen) of the kept attempt
out/20261114-073826. Run from the session directory: python3 fold/look.py > fold/look.out

1. zpass zp-z125: the stored floats of the triangle at 0.125 (not one value): their spread in
   ulps of 0.125, against the loaded 0.25 / 0.75 (the test's verdict) and by pixel.
2. zflat2 zl2-f6-0p9375 and zl2-f6-0p0625: which blocks are FL-REC0's, and the twins' spread at
   0.1 and 0.3 (the planes at those depths are not one float)."""
import gzip
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402
import z15 as Z  # noqa: E402

D = os.path.join(KP, "out/20261114-073826")


def rd(stage, name):
    return gzip.open(os.path.join(D, stage, name + ".gz")).read()


def f(u):
    return struct.unpack("<f", struct.pack("<I", u))[0]


print("== 1. zpass zp-z125")
st = Z.dwords(rd("zpass", "zp-z125.depth-store.1.bin"))
want = Z.f32_bits("0.125")
vals = {}
for y in range(32):
    for x in range(64):
        vals[(x, y)] = st[Z.store_dword(x, y, 1)]
d = sorted({v - want for v in vals.values()})
print(f"stored at 2048 pixels; distinct {len(set(vals.values()))}; ulps from 0.125 (0x{want:08x}): "
      f"{d[0]} to {d[-1]}; every stored float below the loaded 0.25: "
      f"{all(f(v) < 0.25 for v in vals.values())}")
print("ulps by x at y = 0:", [vals[(x, 0)] - want for x in range(0, 64, 8)])
print("ulps by y at x = 0:", [vals[(0, y)] - want for y in range(0, 32, 4)])
print("outside the tiles the store's fill:", all(v == Z.FILL_DEAD for v in st[2048:]))

print("== 2. zflat2")
ref = SC.kept("zl2-c-flat")[:176]
for n in ("zl2-f6-0p375", "zl2-f6-0p625", "zl2-f6-0p9375", "zl2-f6-0p0625"):
    b = rd("zflat2", n + ".depth.1.bin")
    v = Z.f32_bits(Z.REC0_DEPTHS[n])
    blk = Z.rec0_block(ref, v)
    per = [b[2048 * k:2048 * k + 176] == blk for k in range(4)]
    ch = [sum(1 for x in Z.dwords(b)[512 * k:512 * k + 512] if x != Z.FILL_DEAD) for k in range(4)]
    print(f"{n}: v 0x{v:08x}; blocks FL-REC0 {per}; changed per block {ch}")
for k in ("0p1", "0p3", "0p5e20"):
    dw = Z.dwords(rd("zflat2", f"zl2-f0-{k}.depth.1.bin"))[:2048]
    v = Z.f32_bits(Z.TWIN_DEPTHS[k])
    d = sorted({x - v for x in dw})
    print(f"zl2-f0-{k}: {len(set(dw))} values, ulps from 0x{v:08x} {d}")
