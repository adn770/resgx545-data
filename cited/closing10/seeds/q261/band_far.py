#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round 10 seeds, Q261 offline (post hoc): the band pixels of r9-x stage far (E979), each against
the exact coverage (E606: centre test, 1/256 half up, top-left ties): its signed distance to the
nearest edge line, the edge's length and the far vertex's distance, drawn or not."""
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


rows = [(FA.E684_CTL[0], [(FA.F(a, 256), FA.F(b, 256)) for a, b in zip(FA.E684_CTL[1][::2], FA.E684_CTL[1][1::2])])] + list(FA.FAR)
tot = wrong = 0
for name, vp in rows:
    V = [(FA.grid(x), FA.grid(y)) for x, y in vp]
    a, b, c = V
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if area < 0:
        b, c = c, b
    edges = [(p, q) for p, q in ((a, b), (b, c), (c, a))]
    d = drawn(name)
    cov = FA.coverage(V)
    for (x, y), (inside, near) in sorted(cov.items()):
        if not near:
            continue
        sx, sy = x * 256 + 128, y * 256 + 128
        best = None
        for p, q in edges:
            dx, dy = q[0] - p[0], q[1] - p[1]
            e = dx * (sy - p[1]) - dy * (sx - p[0])
            dist = e / (256 * math.hypot(dx, dy))
            L = math.hypot(dx, dy) / 256
            far = max(abs(p[0]), abs(p[1]), abs(q[0]), abs(q[1])) / 256
            if best is None or abs(dist) < abs(best[0]):
                best = (dist, L, far)
        tot += 1
        ok = d[(x, y)] == inside
        wrong += not ok
        print(f"{name} ({x},{y}): exact {'in ' if inside else 'out'} hw {'in ' if d[(x, y)] else 'out'} "
              f"{'ok   ' if ok else 'WRONG'} dist {best[0]:+.3e} px edge {best[1]:.3e} px far {best[2]:.3e} px")
print(f"band pixels {tot}, off the exact coverage {wrong}")
