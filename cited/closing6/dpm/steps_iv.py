#!/usr/bin/env python3
"""O1: is a step S_k one page count per (target, scene)?  For every kept timeline, each step of
the global page count in the FIRST TA run is bracketed by two samples (a, b]: the count before
the step lies in [a, b-1].  Intersect the brackets over all jobs of a (target, scene, k).
Empty intersection = the step itself moves between jobs (not a sampling matter)."""
import sys, collections
from r6lib import *
iv = collections.defaultdict(list)
for ds, stg, name, d, m in jobs():
    args = m.get('args', '')
    try: cols, rows = load(f'{d}/{name}.txt.gz')
    except Exception: continue
    if not rows or 0x72c not in rows[0][1] or 0x724 not in rows[0][1] or 0x658 not in rows[0][1]: continue
    st = stretches(rows); end = st[0][0] if st else len(rows)
    wh, sc = scene_of(args)
    pg = pp = None
    for i in range(1, end):
        g = hi(rows[i][1], 0x72c); p = hi(rows[i][1], 0x724)
        if pg is not None and g == pg + 1 and g >= 2 and p >= pp:
            iv[(wh, sc, g)].append((pp, max(pp, p - 1), f'{ds[8:]}/{stg}/{name}'))
        pg, pp = g, p
for key in sorted(iv):
    L = iv[key]; lo = max(a for a, b, _ in L); hi_ = min(b for a, b, _ in L)
    wid = collections.Counter((a, b) for a, b, _ in L)
    tag = 'ONE VALUE %#x' % lo if lo == hi_ else ('range %#x..%#x' % (lo, hi_) if lo < hi_ else 'EMPTY (lo %#x > hi %#x)' % (lo, hi_))
    print('%-10s %-22s S%d jobs %3d  %s   brackets %s' % (key[0], key[1], key[2], len(L), tag,
          ' '.join('[%x,%x]x%d' % (a, b, n) for (a, b), n in sorted(wid.items()))))
    if lo > hi_ or '-v' in sys.argv:
        for a, b, n in L:
            if a > hi_ or b < lo or '-v' in sys.argv: print('      [%x,%x] %s' % (a, b, n))
