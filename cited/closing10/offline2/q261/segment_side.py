#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round 10 offline (O10s, Q261, post hoc on E979's kept rows): for each band pixel of r9-x stage
far (centre within 1e-3 pixel of an edge line, E684's band, as closing10/seeds/q261/band_far.py
finds them), the edge line it is nearest to, whether that edge has the far vertex, and where the
pixel centre projects on it: t in [0, 1] on the segment from the near end (0) to the far vertex
(1), t < 0 past the near vertex. Prints the hardware against the exact coverage per pixel and the
counts. Standard library; reads only the published session (resgx545-data render/closing-r9-x).
    python3 -I -B segment_side.py > segment_side.out"""
import gzip
import math
import os
import re
import sys

S = "/Users/jtorra/src/resgx545-data/render/closing-r9-x"
sys.path.insert(0, os.path.join(S, "gen"))
import far as FA  # noqa: E402

ATT = os.path.join(S, "out/20261113-081821/far")


def drawn(name):
    t = gzip.open(f"{ATT}/{name}.txt.gz", "rt").read()
    out = {}
    for m in re.finditer(r"^row (\d+): (.*)$", t, re.M):
        for x, v in enumerate(m.group(2).split()):
            out[(x, int(m.group(1)))] = int(v, 16) == FA.TRI_COLOUR
    return out


def is_far(p):
    return max(abs(p[0]), abs(p[1])) > 1 << 20  # 4096 pixels in 1/256 units: far outside 64 x 64


rows = [(FA.E684_CTL[0], [(FA.F(a, 256), FA.F(b, 256)) for a, b in zip(FA.E684_CTL[1][::2], FA.E684_CTL[1][1::2])])] + list(FA.FAR)
tally = {}
for name, vp in rows:
    V = [(FA.grid(x), FA.grid(y)) for x, y in vp]
    d = drawn(name)
    for (x, y), (inside, near) in sorted(FA.coverage(V).items()):
        if not near:
            continue
        sx, sy = x * 256 + 128, y * 256 + 128
        best = None
        for i in range(3):
            p, q = V[i], V[(i + 1) % 3]
            if is_far(p) and not is_far(q):
                p, q = q, p  # from the near end to the far one
            dx, dy = q[0] - p[0], q[1] - p[1]
            dist = abs(dx * (sy - p[1]) - dy * (sx - p[0])) / (256 * math.hypot(dx, dy))
            t = ((sx - p[0]) * dx + (sy - p[1]) * dy) / (dx * dx + dy * dy)
            if best is None or dist < best[0]:
                best = (dist, t, is_far(q))
        dist, t, far_edge = best
        side = "segment" if 0 <= t <= 1 else ("past-near" if t < 0 else "past-far")
        ok = d[(x, y)] == inside
        key = (far_edge, side, ok)
        tally[key] = tally.get(key, 0) + 1
        print(f"{name} ({x},{y}): far edge {far_edge!s:5} {side:9} t {t:+.3e} exact {'in ' if inside else 'out'} "
              f"hw {'in ' if d[(x, y)] else 'out'} {'ok' if ok else 'WRONG'}")
for (far_edge, side, ok), n in sorted(tally.items()):
    print(f"far edge {far_edge}, {side}: {'agree' if ok else 'off the exact image'} {n}")
