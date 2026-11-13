#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round 10 seeds, Q177 offline: E565's kept 32 x 8 twiddled jobs (bd-hb-ns-uv4..7, u and v in
mode m) read against the offset rivals of E957 (8 N + 52 with N the width, the height, or the
size as a 16 x 16 equivalent). Reads only resgx545-data texture/p1132/tx-border (published)."""
import collections
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


def st(x, y):
    # u = -1.5 + (x + 1/2) / 16 on a 32-wide texture, v = -1.5 + (y + 1/2) / 8 on 8 rows
    return 2 * x - 47, y - 12


def wrap(v, m, n):
    return v % n if m in (0, 4, 5) else min(max(v, 0), n - 1)


def morton(s, t, nb):
    i = 0
    for b in range(nb):
        i |= ((t >> b) & 1) << (2 * b) | ((s >> b) & 1) << (2 * b + 1)
    return i


LAYOUTS = {
    # 8 x 8 Morton blocks (t in bit 0), the blocks along s in raster order
    "BLK8": lambda s, t: morton(s & 7, t & 7, 3) | (s >> 3) << 6,
    # Morton on the low 3 bits, then the two extra s bits interleaved above as plain bits
    "MORT-S": lambda s, t: morton(s & 7, t, 3) + 64 * (s >> 3),
}

for m in (4, 5, 6, 7):
    px = pixels(f"{DATA}/texture/p1132/tx-border/bd-hb-ns-uv{m}.txt.gz")
    raw = collections.Counter(v & 0x0fffffff for v in px.values())
    print(f"bd-hb-ns-uv{m}: {len(px)} pixels, {len(raw)} distinct, min {min(raw)} max {max(raw)}")
    for lay, f in LAYOUTS.items():
        d = collections.Counter()
        for (x, y), v in px.items():
            s, t = st(x, y)
            d[(v & 0x0fffffff) - f(wrap(s, m, 32), wrap(t, m, 8))] += 1
        print(f"  {lay}: read less layout index {dict(d.most_common(5))}")
    # the s, t -> value map on one row band, raw, for a layout-free look
    row = sorted(((st(x, y)[0], v & 0x0fffffff) for (x, y), v in px.items() if y == 12))
    print("  y = 12 (t = 0): " + " ".join(f"{s}:{v}" for s, v in row[20:44]))
