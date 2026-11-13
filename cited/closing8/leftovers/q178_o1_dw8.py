#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""q178_o1_dw8.py (round 8 planning, leftovers; offline, POST HOC: a reading of E911's kept images,
made while planning; nothing frozen before it).  H-DW8: TEXTYPE 5 returns 0x0000ffff iff bit B of
the texture dword floor(((y mod h) * w + (x mod w)) / K) is set, else 0, with the map fill's dword
i = 0xD0000000 | i (and 0 / 0xffffffff in the first 112 dwords for the two memory rows).  Scans K in
1..64 and B in 0..31 over the six kept type 5 rows of render/closing-r7-geo (2048 pixels each)
read from the kept tool outputs (TX/NAME.txt.gz, the `row N:` lines); standard library only.
  python3 -I -B q178_o1_dw8.py DATA_REPO
"""
import os, sys
data = sys.argv[1]; K_ = os.path.join(data, "render/closing-r7-geo")
import gzip, re
def read(path):
    im = {}
    for ln in gzip.open(path, "rt", errors="replace"):
        m = re.search(r": row (\d+): (.*)$", ln)
        if m: im[int(m.group(1))] = [int(v, 16) for v in m.group(2).split()]
    assert len(im) == 32 and all(len(v) == 64 for v in im.values()), path
    return [im[y] for y in range(32)]
d = os.path.join(K_, "out/20261112-211113/tx")
if not os.path.isdir(d): d = os.path.join(K_, "out/20261112-211042/tx")
rows = {"tx-ty5-8x8": (8, 8, None), "tx-ty5-16x16": (16, 16, None), "tx-ty5-32x32": (32, 32, None), "tx-ty5-64x64": (64, 64, None),
        "tx-ty5-16x16-zero": (16, 16, 0), "tx-ty5-16x16-ones": (16, 16, 0xffffffff)}
imgs = {}
for n in rows:
    imgs[n] = read(os.path.join(d, n + ".txt.gz"))
def dword(i, inj): return inj if (inj is not None and i < 112) else (0xD0000000 | i)
fits = []
for K in range(1, 65):
    for B in range(32):
        ok = {}
        for n, (w, h, inj) in rows.items():
            im = imgs[n]
            ok[n] = sum(1 for y in range(32) for x in range(64)
                        if im[y][x] == (0xffff if dword(((y % h) * w + x % w) // K, inj) >> B & 1 else 0))
        if all(v == 2048 for v in ok.values()): fits.append((K, B))
        if (K, B) in ((8, 0), (1, 3), (16, 1), (4, 0)): print("K %2d bit %2d:" % (K, B), " ".join("%s %d" % (n[6:], v) for n, v in ok.items()))
print("exact on all six rows (K, bit):", fits)
