#!/usr/bin/env python3
"""Round 6 dpm offline stage (copied from the planner's ../r6lib.py, data root from RESGX545_DATA), read-only: shared reader over the published closing sessions
(resgx545-data/render/closing-*/out).  Pure python.  Public data only."""
import os, gzip, csv, re
ROOT = os.path.join(os.environ.get('RESGX545_DATA', '/Users/jtorra/src/resgx545-data'), 'render')
def load(path):
    cols = None; rows = []
    for l in gzip.open(path, 'rt', errors='replace'):
        if l.startswith('timeline:'):
            cols = [int(x, 16) for x in l.split('regs ')[1].split(' samples')[0].split()]
        elif l.startswith('tl ') and cols:
            p = l.split()
            if len(p) != len(cols) + 2: continue
            try: rows.append((int(p[1]), dict(zip(cols, (int(x, 16) for x in p[2:])))))
            except ValueError: continue
    return cols, rows
hi = lambda v, r: (v[r] >> 16) & 0xffff
def stretches(rows):
    out = []; a = None
    for i, (t, v) in enumerate(rows):
        on = v[0x658] & 1
        if on and a is None: a = i
        if not on and a is not None: out.append((a, i - 1)); a = None
    if a is not None: out.append((a, len(rows) - 1))
    return out
def jobs():
    """every kept job with a timeline: (session, stage dir relative, name, dir, args)"""
    for ds in sorted(os.listdir(ROOT)):
        if not ds.startswith('closing-'): continue
        base = f'{ROOT}/{ds}/out'
        if not os.path.isdir(base): continue
        for d, _, files in sorted(os.walk(base)):
            meta = {}
            if 'cases.tsv' in files:
                try:
                    for r in csv.DictReader(open(f'{d}/cases.tsv'), delimiter='\t'): meta[r.get('name')] = r
                except Exception: pass
            for f in sorted(files):
                if f.endswith('.txt.gz') and '.' not in f[:-7]:
                    yield ds, os.path.relpath(d, base), f[:-7], d, meta.get(f[:-7], {})
def scene_of(args):
    m = re.search(r'--width (\d+) --height (\d+)', args or '')
    wh = f'{m.group(1)}x{m.group(2)}' if m else '?'
    v = re.search(r'--vertices (\d+)', args or ''); mv = re.search(r'--move (\S+)', args or '')
    sc = 'full' if '--tri-full' in (args or '') else ('tri' + (v.group(1) if v else '1'))
    if mv: sc += '@' + mv.group(1)
    if '--geometry' in (args or ''): sc += '+geom'
    return wh, sc
