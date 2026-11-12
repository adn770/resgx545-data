#!/usr/bin/env python3
"""Round 7 planner: which kept dumps are one-triangle scenes (no --vertices), by target."""
import sys, os, collections
sys.path.insert(0, '/Users/jtorra/src/scratch/resgx545/closing6/dpm/offline')
from r6lib import jobs, scene_of
c = collections.Counter(); ex = {}
for ds, stg, name, d, m in jobs():
    pre = f'{d}/{name}.p1139-green'
    has = any(f.startswith(name + '.') and f.endswith('.param.bin.gz') for f in os.listdir(d))
    if not has: continue
    args = m.get('args', '')
    wh, sc = scene_of(args)
    c[(wh, sc.split('@')[0])] += 1; ex.setdefault((wh, sc.split('@')[0]), f'{ds}/{stg}/{name} :: {args[:150]}')
for k, v in sorted(c.items()): print(k, v, ex[k])
