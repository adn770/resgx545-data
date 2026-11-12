#!/usr/bin/env python3
"""O4 helper: page count against time in the first TA run of a kept job (is the page take
steady or in bursts?).  Prints t (us from the first non-zero count), PS_hi, GPS_hi per sample
where either changed, and the rate over each global band.  Read-only."""
import sys
from r6lib import *
cols, rows = load(sys.argv[1]); st = stretches(rows); end = st[0][0] if st else len(rows)
t0 = None; prev = None; seq = []
for i in range(end):
    t, v = rows[i]; p = hi(v, 0x724); g = hi(v, 0x72c)
    if p and t0 is None: t0 = t
    if t0 is None: continue
    if (p, g) != prev: seq.append(((t - t0) // 1000, p, g)); prev = (p, g)
step = int(sys.argv[2]) if len(sys.argv) > 2 else 1
print('samples with a change:', len(seq), 'of', end)
print(' '.join('%d:%x/%d' % s for s in seq[::step]))
# gaps: longest times without a page taken, and biggest page jumps between two changes
gaps = sorted(((b[0] - a[0], a[1], b[1]) for a, b in zip(seq, seq[1:])), reverse=True)[:12]
print('longest waits (us, from page, to page):', ' '.join('%d:%x>%x' % g for g in gaps))
