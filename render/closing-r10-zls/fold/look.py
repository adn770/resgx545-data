#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/look.py (post hoc, not frozen): r10-zls's rows that held no frozen model and the readings.
1. zst2: the f5 and f6 rows that left E985 (z2y-f5, z2y-f6, z2e-f6): changed dwords per tile
   block, how many distinct depths each tile row holds in the format-0 reference, the first dwords
   of the first block; f7's changed dwords per plane and fill.
2. zw: z against t = (x + 0.5) / 512 over the whole target per word 10: the fraction at
   t + w - 0.5 (H-OFF) and at (1.6 w + 0.2) t (H-LIN), within 1e-5 relative.
Usage: python3 -I -B fold/look.py [KEPT_ATTEMPT_DIR] > fold/look.out"""
import gzip
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import zbg as B  # noqa: E402
import zst2 as Z  # noqa: E402

A = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KP, "out/20261113-102039")
FILL = 0xDEADBEEF


def dw(stage, n):
    b = gzip.open(os.path.join(A, stage, n + ".depth.1.bin.gz")).read()
    return list(struct.unpack("<%dI" % (len(b) // 4), b))


def f(v):
    return struct.unpack("<f", struct.pack("<I", v))[0]


print("## 1. zst2")
for n, blk in (("z2y-f5", 640), ("z2y-f6", 512), ("z2e-f6", 512), ("z2d-f6", 512), ("z2y-f3", 640)):
    d = dw("zst2", n)
    ref = dw("zst2", Z.ref_of(n))
    per = [sum(1 for v in d[k * blk:(k + 1) * blk] if v != FILL) for k in range(4)]
    w, h = Z.PLANES[Z.plane_of(n)][:2]
    rows = []
    for ty in range(2):
        for tx in range(2):
            rows.append([len({ref[512 * (ty * 2 + tx) + Z.in_tile_index(x, y)] for x in range(32)})
                         for y in range(16)])
    print(f"{n}: changed per block {per}; distinct depths per tile row (tile 0) {rows[0]}")
    print("   first block:", " ".join(f"{v:08x}" for v in d[:24]))
for n in ("z2x-f7-s00", "z2x-f7-sff", "z2x-f7-sa5", "z2y-f7", "z2d-f7"):
    d = dw("zst2", n)
    print(f"{n}: changed {sum(v != FILL for v in d)}; first", " ".join(f"{v:08x}" for v in d[:12]))
print("## 2. zw over the whole target")
for n, w in (("zw-0125", 0.125), ("zw-075", 0.75), ("zw-100", 1.0)):
    d = dw("zw", n)
    off = lin = tot = 0
    for y in range(B.H):
        for x in range(B.W):
            z = f(d[B.f0_index(x, y)])
            t = (x + 0.5) / 512
            tot += 1
            off += B.w10_at(z, max(0.0, t + w - 0.5))
            lin += B.w10_at(z, (1.6 * w + 0.2) * t)
    zs = [f(d[B.f0_index(x, 0)]) for x in (0, 64, 128, 255)]
    print(f"{n}: of {tot}: H-OFF {off}, H-LIN {lin}; y = 0 at x 0, 64, 128, 255: {zs}")
