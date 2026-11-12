#!/usr/bin/env python3
"""Round 5 dpm planning, offline: steps of the global page count in each run of chosen jobs
(exact 'before' and 'after' page counts), to place the second-run steps.  Read-only."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from tlc import load
from endstretch import jobs, stretches, hi
want = set(sys.argv[1:])
for ds, stg, name, d in jobs():
    if want and name not in want and stg not in want: continue
    hdr, cols, rows = load(f'{d}/{name}.txt.gz')
    if not rows or 0x72c not in rows[0][1]: continue
    st = stretches(rows)
    if not st: continue
    bounds = [(1, st[0][0])] + [(st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(rows)) for k in range(len(st))]
    for k, (a, b) in enumerate(bounds[:4]):
        steps = []; pg = pp = None
        for i in range(a, b):
            v = rows[i][1]; g = hi(v, 0x72c); p = hi(v, 0x724)
            if pg is not None and g > pg: steps.append('%d:(%x,%x]' % (g, pp, p))
            pg, pp = g, p
        v0 = rows[a][1]; v1 = rows[b - 1][1]
        print(f'{stg}/{name:16} run {k + 1} thr={v1[0x624]:#x} start(ps,gps)=({hi(v0,0x724):x},{hi(v0,0x72c)}) '
              f'end=({hi(v1,0x724):x},{hi(v1,0x72c)}) steps {" ".join(steps)}')
