#!/usr/bin/env python3
"""extra_p1138.py DIR: analyses added AFTER the freeze (not in manifest-1138.sha256, written before any dump was
read): the model-free reading of the edge sweeps.  Same inputs as recompute_p1138.py, which it imports for loading."""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1138lib as L  # noqa: E402
from recompute_p1138 import Data, load, log  # noqa: E402


def sweep_section(cases, data, out):
    """Model-free reading of the edge sweeps: the edge is moved 4 or 8 (1/256 pixel) at a time; the first (or last)
    covered pixel of a row or column through the middle of the edge changes at the f where the edge crosses the
    sample point of that pixel.  Prints those f (the sample point and the snap grid are in them)."""
    log("\n## 1c edge sweeps, where the first covered pixel of a middle row (or column) changes")
    groups = collections.defaultdict(list)
    for c in cases:
        if c.cls.startswith("sweep") and data.cov(c.id) is not None:
            groups[(c.set, c.cls, c.w)].append(c)
    flips_all = {}
    for key in sorted(groups):
        cs = groups[key]
        vals = []
        for c in cs:
            cov = data.cov(c.id)
            yb, xb = (c.h // 2 - 12), (c.w // 2 - 12)
            if c.cls.startswith("sweepV"):
                row = cov[c.h // 2]
                idx = np.flatnonzero(row)
                v = int(idx.min()) if c.cls == "sweepV+" and idx.size else int(idx.max()) if idx.size else -1
            elif c.cls.startswith("sweepH"):
                col = cov[:, c.w // 2]
                idx = np.flatnonzero(col)
                v = int(idx.min()) if c.cls == "sweepH+" and idx.size else int(idx.max()) if idx.size else -1
            else:
                row = cov[yb + 10]
                idx = np.flatnonzero(row)
                v = int(idx.min()) if c.cls == "sweepD+" and idx.size else int(idx.max()) if idx.size else -1
            vals.append(v)
        fs = [int(round((c.v[0][0] - ((c.w // 2 - 12) * 256)) if c.cls.startswith("sweepV") else
                       (c.v[0][1] - ((c.h // 2 - 12) * 256)) if c.cls.startswith("sweepH") else
                       (c.v[0][0] - ((c.w // 2 - 12) * 256)))) for c in cs]
        flips = [(fs[i], vals[i - 1], vals[i]) for i in range(1, len(cs)) if vals[i] != vals[i - 1]]
        flips_all[key] = flips
        log("   %-8s %-8s w=%-3d f in 0..256: %d cases; changes at f = %s" % (key[0], key[1], key[2], len(cs),
                                                                         ", ".join("%d(%d->%d)" % t for t in flips[:12])))
    out["sweeps"] = flips_all



def main():
    cases, jobs = load(sys.argv[1])
    data = Data(sys.argv[1], cases, jobs)
    sweep_section(cases, data, {})


if __name__ == "__main__":
    main()
