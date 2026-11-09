#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39: the dl-* jobs: what the store buffer holds, by tile row band (rows < 12 and >= 12), against the load
buffer's index fill: stored dwords, equal to their index (sign ignored), signed, zero, other."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "recompute-b"))
import recompute_p1139b as r

cs = r.load_cases(sys.argv[1])
print("case\tstored\tidx<12\tidx>=12\tzero\tsigned\tother_rows>=12\tfirst_other")
for n, c in cs.items():
    if not n.startswith("dl-"):
        continue
    k = r.Case(n, c)
    d = k.depth()
    g = (int(r.arg(c, "--depth-ctl", "0x0017100c"), 0) >> 3) & 0x1ff
    st = r.stored(d, r.fill_of(c))
    a = b = z = s = o = 0
    first = None
    for i, v in st:
        row = (i // 512) // (g + 1)
        eq = (v & 0x7fffffff) == i
        if v == 0: z += 1
        if v >> 31: s += 1
        if eq and row < 12: a += 1
        elif eq: b += 1
        elif row >= 12 and v != 0:
            o += 1
            first = first or (i, hex(v))
    print(f"{n}\t{len(st)}\t{a}\t{b}\t{z}\t{s}\t{o}\t{first}")
