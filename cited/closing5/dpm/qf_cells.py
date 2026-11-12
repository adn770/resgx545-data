#!/usr/bin/env python3
"""Round 5 dpm planning, Q211: for a page need U, the thr0 cells where the count rule
(d = 7/4, k = 0) and its nearest refuted or untested neighbours disagree, so that held-out
cells can be frozen from a measured U.  Pure python, no data read."""
import sys, fractions
F = fractions.Fraction
def rule(t, U, d=F(7, 4), k=0):
    n = 1
    while t + n * (t + 0x20 - d) < U + k: n += 1
    return n
def e625(t, U, k, s): return max(1, 1 + (U + k - t) // (t + s))
ALTS = {'d=1': lambda t, U: rule(t, U, F(1)), 'd=5/4': lambda t, U: rule(t, U, F(5, 4)), 'd=9/4': lambda t, U: rule(t, U, F(9, 4)),
        'd=3': lambda t, U: rule(t, U, F(3)), 'E625(0,0x1e)': lambda t, U: e625(t, U, 0, 0x1e),
        'E625(-1,0x1e)': lambda t, U: e625(t, U, -1, 0x1e), 'E625(2,0x1f)': lambda t, U: e625(t, U, 2, 0x1f)}
for U in [int(x) for x in sys.argv[1:]] or [120, 200, 287, 438]:
    cells = []
    for t in range(1, U):
        r = rule(t, U); diff = [a for a, f in ALTS.items() if f(t, U) != r]
        step = rule(t - 1, U) != r if t > 1 else False
        if diff or step: cells.append((t, r, step, diff))
    print(f'U={U}: {len(cells)} cells at a step of the rule or where an alternative differs')
    for t, r, step, diff in cells:
        print(f'   thr0={t:#x} (P={t + 0x22:#x}) rule n={r}{" STEP" if step else ""} differs: {",".join(diff) or "-"}')
