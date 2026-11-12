#!/usr/bin/env python3
"""F6 tabulation (post hoc, written after f6_pendreq.out was read): f6_pendreq.py's own tally
line tests a criterion that does not fit what its lines show (it asks for the first sample after
the stretch to equal the stretch minimum).  This counts its lines instead: per kind of cell (grow
at S_k, no grow at S_k - 1 or S_k + 1), the global count at the abort, its minimum inside the
first partial render, and its value at the first sample after the render (8 to 33 us later)."""
import collections, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
c = collections.Counter()
for l in open(os.path.join(HERE, 'f6_pendreq.out')):
    if ' | ' not in l or l.startswith('job'):
        continue
    p = l.split(' | ')
    cell = p[0].split()[3]
    a, mn, last = [int(x) for x in p[1].split(', ')]
    post = re.findall(r'\((\d+),0x[0-9a-f]+,(\d+)\)', p[2])
    kind = ('grow' if p[3].startswith('grow') else 'no grow') + (' S-1' if '-' in cell else ' S+1' if '+' in cell else ' S')
    c[(kind, int(post[0][1]) if post else None)] += 1
for (kind, g1), n in sorted(c.items()):
    print(f'{kind:12s} first sample after the render reads {g1} global pages: {n} jobs')
