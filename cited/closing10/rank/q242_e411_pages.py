#!/usr/bin/env python3
"""Q242 offline (round 10): E411's stored pages per pitch G, recomputed from E465's address rule
(depth 512 dwords a tile at 512 (ty (G + 1) + tx), stencil 128 a tile, E467) for E411's 64 x 64
target (2 x 4 tiles), the depth at scratch page 12 and the stencil at page 4 of a 16-page buffer
(E411's table: control pages 12-15 and 4). Prints, per G, the pages each store would write with
dword counts, and which pass page 15. Compare with E411's table by eye (no fit)."""
from collections import Counter
rows = {"control (G 1)": 1, "bit 3 cleared (G 0)": 0, "bit 4 set (G 3)": 3, "bit 5 set (G 5)": 5,
        "bit 6 set (G 9)": 9, "bit 7 set (G 17)": 17}
for name, G in rows.items():
    t = [ty * (G + 1) + tx for ty in range(4) for tx in range(2)]
    dep = Counter(); st = Counter()
    for s in t:
        for k in range(512): dep[12 + (512 * s + k) // 1024] += 1
        for k in range(128): st[4 + (128 * s + k) // 1024] += 1
    dep = {p: n for p, n in sorted(dep.items())}; st = {p: n for p, n in sorted(st.items())}
    print(f"{name}: depth {dep} stencil {st} past page 15: {[p for p in dep if p > 15]}")
