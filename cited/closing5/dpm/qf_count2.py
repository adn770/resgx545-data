#!/usr/bin/env python3
"""Round 5 dpm planning, offline, Q211 (scratch; pure python).  The family of qf_count.py in its
two effective constants:  n = min{ n >= 1 : thr0 + n * (thr0 + 0x20 - d) >= U + k },
d in sixteenths from 0 to 6, k an integer from -12 to 15.  FIT: E832's 22 g-qf cells (U 287).
HELD OUT (Q211's note of 2026-11-11): the 6 s275 cells (U 275).  Older kept cells, not used in
the fit: E625's ten 4096x4096 cells and E779's (those not already in g-qf) and 1024x768 (U 19)."""
import fractions
F = fractions.Fraction
rows = [l.split() for l in open('qf_pages.out') if l.startswith('q')]
qf = [(int(r[2], 16), int(r[3])) for r in rows if r[0].startswith('qf-')]
s275 = [(int(r[2], 16), int(r[3])) for r in rows if 's275' in r[0]]
e625 = [(p - 0x22, n) for p, n in ((0x23, 10), (0x40, 5), (0x60, 3), (0x80, 2), (0x90, 2), (0xa0, 2),
                                   (0xb0, 1), (0xb8, 1), (0xc0, 1), (0x100, 1))]
e779 = [(p - 0x22, 1) for p in (0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8, 0xa9, 0xb0)] + [(0xa0 - 0x22, 2)]
u19 = [(p - 0x22, 1) for p in range(0x23, 0x35)]
def pred(thr0, U, d, k):
    n = 1
    while thr0 + n * (thr0 + 0x20 - d) < U + k: n += 1
    return n
grid = [(F(i, 16), k) for i in range(0, 97) for k in range(-12, 16)]
fits = [(d, k) for d, k in grid if all(pred(t, 287, d, k) == n for t, n in qf)]
print('members', len(grid), 'fit all 22 g-qf cells:', len(fits))
ds = sorted({d for d, k in fits}); ks = sorted({k for d, k in fits})
print('  d from', float(ds[0]), 'to', float(ds[-1]), 'k in', ks)
for name, cells, U in (('s275 held out', s275, 275), ('E625 4096x4096', e625, 287), ('E779', e779, 287), ('1024x768 U=19', u19, 19)):
    allok = sum(all(pred(t, U, d, k) == n for t, n in cells) for d, k in fits)
    base = sum(all(pred(t, U, d, k) == n for t, n in cells) for d, k in grid)
    print(f'  {name}: {len(cells)} cells; fitting members that also give all of them: {allok}/{len(fits)}; '
          f'members of the whole grid that give all of them: {base}/{len(grid)}')
# E625's own form for comparison: 1 + floor((U + k - thr0) / (thr0 + s)), integer s
old = [(s, k) for s in range(0x18, 0x22) for k in range(-12, 16)
       if all(1 + (287 + k - t) // (t + s) == n for t, n in qf)]
print('E625 form with integer s 0x18..0x21, k -12..15, fitting all 22:', old)
d, k = F(7, 4), 0
print('table (thr0, observed, predicted) with d=7/4, k=0:')
print('  g-qf ', [(hex(t), n, pred(t, 287, d, k)) for t, n in qf])
print('  s275 ', [(hex(t), n, pred(t, 275, d, k)) for t, n in s275])
# cells that would split the surviving members: thr0 values (U 287) where they disagree
split = [t for t in range(1, 0x120) if len({pred(t, 287, d, k) for d, k in fits}) > 1]
print('thr0 values at U=287 where the fitting members disagree:', [hex(t) for t in split])
split2 = [t for t in range(1, 0x110) if len({pred(t, 275, d, k) for d, k in fits}) > 1]
print('thr0 values at U=275 where they disagree:', [hex(t) for t in split2])
