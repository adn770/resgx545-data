#!/usr/bin/env python3
"""Q141: print the background pixel pattern of each tile listed by q141_ident.py, with the range of
x + y (the triangle's hypotenuse is x + y = 192) and of 2x + y / x + 2y. Standard library."""
import gzip, re, sys
from collections import defaultdict
D = "/Users/jtorra/src/resgx545-data/isp/msaa-ident/dumps/"
for n in sys.argv[1:]:
    rows = {}
    for l in gzip.open(D + n + "-x.txt.gz", "rt"):
        m = re.search(r"row (\d+): (.*)$", l)
        if m: rows[int(m.group(1))] = m.group(2).split()
    bad = {(x, y) for y in rows for x, v in enumerate(rows[y]) if v.lower().endswith("ff203040")}
    t = defaultdict(set)
    for x, y in bad: t[(x // 16, y // 16)].add((x, y))
    for k, s in sorted(t.items()):
        print(n, "tile", k, len(s), "x+y in", min(x + y for x, y in s), max(x + y for x, y in s))
        x0, y0 = k[0] * 16, k[1] * 16
        for y in range(y0, y0 + 16):
            line = "".join("#" if (x, y) in s else "." for x in range(x0, x0 + 16))
            if "#" in line: print("   y=%3d %s" % (y, line))
