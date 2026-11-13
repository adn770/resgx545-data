#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round 10 seeds, Q177 offline: what u mode 5 reads past the texture in E565's kept 32 x 8 job
(bd-hb-ns-uv5) per (s, t), against the layout index at the clamped and the repeated s."""
import gzip
import re
import sys

DATA = sys.argv[1] if len(sys.argv) > 1 else "/Users/jtorra/src/resgx545-data"


def pixels(path):
    out = {}
    for m in re.finditer(r"row (\d+): ([0-9a-fx ]+)$", gzip.open(path, "rt").read(), re.M):
        for x, t in enumerate(m.group(2).split()):
            out[(x, int(m.group(1)))] = int(t, 16)
    return out


def morton(s, t, nb=3):
    i = 0
    for b in range(nb):
        i |= ((t >> b) & 1) << (2 * b) | ((s >> b) & 1) << (2 * b + 1)
    return i


def idx(s, t):
    return morton(s & 7, t & 7) | (s >> 3) << 6


px = pixels(f"{DATA}/texture/p1132/tx-border/bd-hb-ns-uv5.txt.gz")
cells = {}
for (x, y), v in px.items():
    s, t = 2 * x - 47, y - 12
    cells[(s, t % 8)] = v & 0x0fffffff
for side, ss in (("s < 0", range(-47, 0, 2)), ("s >= 32", range(33, 81, 2))):
    print(f"== {side}: per t, the distinct values read (and each less the clamped texel's index + 308)")
    for t in range(8):
        vals = sorted({cells[(s, t)] for s in ss if (s, t) in cells})
        cl = idx(0 if side == "s < 0" else 31, t) + 308
        print(f"  t {t}: {vals} clamped+308 = {cl}; diff {[v - cl for v in vals]}")
