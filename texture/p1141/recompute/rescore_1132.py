#!/usr/bin/env python3
"""Goal 1a: re-score every declared 11.32 hypothesis on the stored dumps, plain Morton (as
declared) against the tile law, per case. Prints the cases whose best hypothesis count or
exactness changes, and a group table. Written fresh; shares only p1132's texmodel and specs."""
import collections, sys
from lib import *

dec = declared()
rows = []
for name, (script, st, rk) in dec.items():
    sp = SPECS.get(name)
    pix = load_pix(script, name)
    if not sp or pix is None:
        continue
    res = {}
    for law in ("plain", "tile"):
        use_tile_law(law == "tile")
        for h, rl in zip(sp["hyps"], sp["rules"]):
            px = tm.render(sp["spec"], rl)
            if px is None:
                continue
            res[(law, h)] = sum(a == b for a, b in zip(px, pix))
    if res:
        rows.append((name, sp["group"], st, res))
use_tile_law(False)
tab = collections.defaultdict(lambda: [0, 0, 0, 0])
chg = []
for name, g, st, res in rows:
    for h in sorted({k[1] for k in res}):
        a, b = res[("plain", h)], res[("tile", h)]
        t = tab[(g, st, h)]
        t[0] += 1; t[1] += a == 2048; t[2] += b == 2048
        if (a == 2048) != (b == 2048):
            chg.append((name, g, st, h, a, b))
        elif a != b:
            t[3] += 1
print("== per group, set, hypothesis: cases, exact plain, exact tile, cases whose count moved (not exact)")
for (g, st, h), (n, a, b, m) in sorted(tab.items()):
    flag = "  <-- changes" if a != b else ""
    print(f"  {g:14s} {st:8s} {h:18s} n={n:3d} plain={a:3d} tile={b:3d} moved={m:3d}{flag}")
print("\n== cases that go from not exact to exact (or back) under the tile law")
for c in chg:
    print("  %-22s %-12s %-8s %-18s plain %4d tile %4d" % c)
print(f"\ncases scored {len(rows)} ; flips {len(chg)}")
# the best hypothesis per case, plain vs tile
best = collections.Counter()
for name, g, st, res in rows:
    bp = max(v for k, v in res.items() if k[0] == "plain")
    bt = max(v for k, v in res.items() if k[0] == "tile")
    best[(bp == 2048, bt == 2048)] += 1
print("cases with an exact hypothesis (plain, tile):", dict(best))
