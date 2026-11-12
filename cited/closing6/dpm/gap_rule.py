#!/usr/bin/env python3
"""O5 (post hoc, a FIT): does the time the refused page request would have waited decide how
many global pages the first partial render leaves?  Per target the reference is the kept job
with the highest first threshold (the longest first run); gap(T) = time from the first sample
with PS >= T to the first with PS >= T + 1 in that reference.  Each kept 1500-vertex job with a
partial render (left_table.out) is listed with gap(thr0), sorted by gap."""
import sys, collections
from r6lib import *
rows_ = [l.split() for l in open('left_table.out').read().splitlines()[1:]]
ref = {}
for r in rows_:
    if r[1] != 'tri1500': continue
    pass
# reference: per target, the job (any, also without a partial render) whose first run goes highest
best = {}
for ds, stg, name, d, m in jobs():
    wh, sc = scene_of(m.get('args', ''))
    if sc != 'tri1500': continue
    try: cols, rows = load(f'{d}/{name}.txt.gz')
    except Exception: continue
    if not rows or 0x724 not in rows[0][1] or 0x658 not in rows[0][1] or 0x72c not in rows[0][1]: continue
    st = stretches(rows); end = st[0][0] if st else len(rows)
    seq = []; mx = 0
    for i in range(end):
        p = hi(rows[i][1], 0x724)
        if p < mx: break
        if p > mx: seq.append((rows[i][0], p, hi(rows[i][1], 0x72c))); mx = p
    if wh not in best or mx > best[wh][0]: best[wh] = (mx, seq, f'{ds[8:]}/{stg}/{name}')
def gap(seq, T):
    a = next((t for t, p, g in seq if p >= T), None); b = next((t for t, p, g in seq if p >= T + 1), None)
    return None if a is None or b is None else (b - a) // 1000
for wh in sorted(best):
    mx, seq, nm = best[wh]
    print(f'== {wh} reference {nm} (first run to {mx:#x})')
    L = []
    for r in rows_:
        if r[0] != wh or r[1] != 'tri1500': continue
        T = int(r[2], 16); L.append((gap(seq, T), T, r[3], r[5], r[8], r[9]))
    seen = set()
    for g, T, gA, gl, grow, cls in sorted(L, key=lambda x: (x[0] is None, x[0] or 0, x[1])):
        key = (T, gA, gl, grow, cls)
        if key in seen: continue
        seen.add(key)
        print(f'   gap {g} us  thr0 {T:#x}  gps at abort {gA} left {gl} grow {grow} {cls}')
