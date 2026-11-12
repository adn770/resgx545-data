#!/usr/bin/env python3
"""Round 5 dpm fold (2026-11-12), offline, Q211 scope: the count rule of qf_count2.py
(n = min{n >= 1 : thr0 + n (thr0 + 0x20 - 7/4) >= U}, d = 7/4, k = 0) applied to the kept
1500-vertex jobs at 2048x2048, whose page need U = 0x213 is E785's, with thr0 the first run's
peak and the count the stretches of 0x0658, both read from tri1500_pages.out.  Pure python,
written in the fold after the planner's tri1500_pages.py; post hoc, nothing held out."""
import fractions
F = fractions.Fraction
def rule(t, U, d=F(7, 4), k=0):
    n = 1
    while t + n * (t + 0x20 - d) < U + k: n += 1
    return n
seen = {}
for l in open('tri1500_pages.out'):
    p = l.split()
    if len(p) < 5 or p[1] != '2048x2048': continue
    name = p[0].split('/')[1]
    if name in seen: continue
    n = int(p[2][2:]); thr0 = int(p[4], 16)
    seen[name] = (thr0, n, rule(thr0, 0x213))
ok = sum(n == r for t, n, r in seen.values())
print(f'2048x2048, 1500 vertices, U = 0x213: {ok} of {len(seen)} jobs give the rule\'s count')
for name, (t, n, r) in sorted(seen.items(), key=lambda x: x[1]):
    print(f'  {name:16} thr0={t:#x} read {n} rule {r}{"" if n == r else "  MISS"}')
