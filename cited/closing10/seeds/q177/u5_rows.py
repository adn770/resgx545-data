#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round 10 seeds, Q177 offline: bd-hb-ns-uv5 (E565, 32 x 8, u and v mode 5), per row y the
values read left (s < 0) and right (s >= 32) of the texture."""
import gzip
import re
import sys

DATA = sys.argv[1] if len(sys.argv) > 1 else "/Users/jtorra/src/resgx545-data"
px = {}
for m in re.finditer(r"row (\d+): ([0-9a-fx ]+)$", gzip.open(f"{DATA}/texture/p1132/tx-border/bd-hb-ns-uv5.txt.gz", "rt").read(), re.M):
    for x, t in enumerate(m.group(2).split()):
        px[(x, int(m.group(1)))] = int(t, 16)
for y in range(32):
    t = y - 12
    left = sorted({px[(x, y)] & 0x0fffffff for x in range(64) if 2 * x - 47 < 0})
    right = sorted({px[(x, y)] & 0x0fffffff for x in range(64) if 2 * x - 47 >= 32})
    print(f"y {y:2d} t {t:3d}: left {left} right {right}")
