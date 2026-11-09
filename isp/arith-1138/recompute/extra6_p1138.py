#!/usr/bin/env python3
"""extra6_p1138.py DIR (pairs keyed by set, size and name: the generator reuses the names pheldout-0... in each size group, so the frozen
recompute analysed only the 20 heldout pairs whose names are not shared; this reads all 70): post-hoc (after the fit data were read): shared-edge pairs with the exact geometry.  The frozen pair
criterion counts uncovered centres near the diagonal, which includes centres outside both triangles (the wedge at the ends of
the diagonal); here a gap is a centre strictly inside A or B (exact integers, vertices as given) that neither drew, a double hit
a centre that both drew, and a tie a centre exactly on the shared edge."""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recompute_p1138 import Data, load, log  # noqa: E402


def strict(t, px, py):
    ar = (t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0])
    if ar == 0:
        return np.zeros(px.shape, dtype=bool)
    s = 1 if ar > 0 else -1
    ok = np.ones(px.shape, dtype=bool)
    for i in range(3):
        p, q = t[i], t[(i + 1) % 3]
        ok &= ((q[0] - p[0]) * (py - p[1]) - (q[1] - p[1]) * (px - p[0])) * s > 0
    return ok


def main():
    cases, jobs = load(sys.argv[1])
    data = Data(sys.argv[1], cases, jobs)
    pairs = collections.defaultdict(list)
    for c in cases:
        if c.cls in ("pairA", "pairB") and data.cov(c.id) is not None:
            pairs[(c.set, "%dx%d" % (c.w, c.h), c.pair)].append(c)
    tot = collections.defaultdict(lambda: collections.Counter())
    for (sn, size, pid), cs in sorted(pairs.items()):
        if len(cs) != 2:
            continue
        a, b = sorted(cs, key=lambda c: c.cls)
        ca, cb = data.cov(a.id), data.cov(b.id)
        ys, xs = np.mgrid[0:a.h, 0:a.w]
        px, py = xs * 256 + 128, ys * 256 + 128
        ina, inb = strict(a.v, px, py), strict(b.v, px, py)
        c0, c2 = a.v[0], a.v[2]
        cross = (c2[0] - c0[0]) * (py - c0[1]) - (c2[1] - c0[1]) * (px - c0[0])
        dot = (c2[0] - c0[0]) * (px - c0[0]) + (c2[1] - c0[1]) * (py - c0[1])
        l2 = (c2[0] - c0[0]) ** 2 + (c2[1] - c0[1]) ** 2
        tie = (cross == 0) & (dot > 0) & (dot < l2)
        endp = (cross == 0) & ((dot == 0) | (dot == l2))
        t = tot[(sn, size)]
        t["pairs"] += 1
        t["gaps (strictly inside A or B, drawn by neither)"] += int(np.count_nonzero((ina | inb) & ~ca & ~cb))
        t["double hits"] += int(np.count_nonzero(ca & cb))
        for n_ in (0, 1, 2):
            t["endpoint centres drawn %d times" % n_] += int(np.count_nonzero(endp & ((ca.astype(int) + cb.astype(int)) == n_)))
        t["ties on the shared edge drawn once"] += int(np.count_nonzero(tie & (ca ^ cb)))
        t["ties on the shared edge drawn 0 or 2 times"] += int(np.count_nonzero(tie & (ca == cb)))
        t["strictly inside A drawn by A (of)"] += int(np.count_nonzero(ina))
        t["strictly inside A not drawn by A"] += int(np.count_nonzero(ina & ~ca))
        t["strictly inside B not drawn by B"] += int(np.count_nonzero(inb & ~cb))
    for k in sorted(tot):
        log("   %-8s %-8s %s" % (k + (dict(tot[k]),)))


if __name__ == "__main__":
    main()
