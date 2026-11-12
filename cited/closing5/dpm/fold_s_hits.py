#!/usr/bin/env python3
"""Round 5 dpm fold (2026-11-12), offline, Q210: from gsteps.out, the page counts S_k at which
the global page count steps (the count read before global page k appears, k >= 2), pooled over
the kept jobs of each target and scene, and the jobs whose first threshold equals one of them or
is within 1 page of one.  Pure python, written in the fold to check the planner's statement
"c4-b3 is the only kept job whose first threshold falls on a step"; post hoc."""
import re
from collections import defaultdict
S = defaultdict(set); rows = []
for l in open('gsteps.out'):
    p = l.split()
    key = (p[0], p[1]); thr0 = int(p[2].split('=')[1], 16)
    for g, a in re.findall(r'(\d+):\(([0-9a-f]+),', l):
        if int(g) >= 2: S[key].add(int(a, 16))
    rows.append((key, thr0, p[5], 'grow=1' in l))
print('jobs', len(rows))
for key in sorted(S): print(' '.join(key), 'S_k:', ' '.join('%#x' % s for s in sorted(S[key])))
for key, thr0, name, grow in rows:
    d = min((abs(thr0 - s), s) for s in S[key]) if S[key] else None
    if grow or (d and d[0] <= 1):
        print(f'{name:24} {" ".join(key)} thr0={thr0:#x} nearest S={d[1]:#x} off {thr0 - d[1]:+d} grow={int(grow)}')
