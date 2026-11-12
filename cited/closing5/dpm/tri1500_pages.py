#!/usr/bin/env python3
"""Round 5 dpm planning, offline, Q211 scope check: the pages the TA took over all runs less the
pages each partial render left, for the kept 1500-vertex jobs (g-c1..g-c6, g-d36), against the
one-triangle rule's d = 7/4.  Extraction only.  Read-only."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from tlc import load
from endstretch import jobs, stretches, hi
from gsteps import main as _m  # noqa (import check only)
import csv, re
for ds, stg, name, d in jobs():
    if stg in ('g-c7', 'g-u1', 'g-u2'): continue
    hdr, cols, rows = load(f'{d}/{name}.txt.gz')
    if not rows or 0x72c not in rows[0][1]: continue
    st = stretches(rows)
    if not st: continue
    bounds = [(1, st[0][0])] + [(st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(rows)) for k in range(len(st))]
    peaks = [max(hi(rows[i][1], 0x724) for i in range(a, e)) for a, e in bounds if e > a]
    kept = [hi(rows[b][1], 0x724) for a, b in st]
    meta = {r['name']: r for r in csv.DictReader(open(f'{d}/cases.tsv'), delimiter='\t')} if os.path.exists(f'{d}/cases.tsv') else {}
    args = meta.get(name, {}).get('args', ''); m = re.search(r'--width (\d+) --height (\d+)', args)
    print(f'{stg}/{name:16} {m.group(1) + "x" + m.group(2) if m else "?":10} n={len(st)} peaks {" ".join("%x" % p for p in peaks)} | kept {" ".join("%x" % k for k in kept)} | produced {sum(peaks) - sum(kept)}')
