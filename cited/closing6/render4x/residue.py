#!/usr/bin/env python3
"""residue.py (round 6, offline, [infer]): under H-TPM, which headers of the two 4096-wide faults (E828 j4, E846 o7) and of row a3 lose
their stream offset, by macrotile, and the pixels of the macrotiles before the first lost header.  Standard library only."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from morton import lay, z
def run(w, h, mw, mh):
    t = lay(w, h); base = lay(mw, mh)["rgn"]; n = t["n"]
    X, Y = 2 * t["tx"], 2 * t["ty"]
    ent = {4 * z(x, y) for x in range(X) for y in range(Y)}
    i = 0; by_mt = collections.Counter(); first = None; inmt = collections.Counter(); before = 0
    for col in range(n):
        for row in range(n):
            for by in range(2 * t["my"] // 4):
                for bx in range(2 * t["mx"] // 4):
                    for yy in range(4):
                        for xx in range(4):
                            x, y = col * 2 * t["mx"] + bx * 4 + xx, row * 2 * t["my"] + by * 4 + yy
                            if x < X and y < Y:
                                inmt[col * n + row] += 1
                                if (base + 12 * i + 4) in ent:
                                    by_mt[col * n + row] += 1
                                    if first is None: first = (i, col * n + row, x, y, before)
                                elif first is None: before += 1
                            i += 1
    px = lambda tiles: tiles * 16 * 8
    print("%d x %d on %d x %d: doubled macrotile %d x %d tiles (%d x %d pixels); in-target tiles a macrotile %s" % (w, h, mw, mh, 2 * t["mx"], 2 * t["my"], 32 * t["mx"], 16 * t["my"], dict(sorted(inmt.items()))))
    print("   lost stream offsets by macrotile: %s" % dict(sorted(by_mt.items())))
    if first: print("   first lost header: index %d, macrotile %d, tile (%d, %d); in-target tiles before it %d = %d pixels (clipped to the target not applied)" % (first[:4] + (first[4], px(first[4]))))
    clean = [m for m in sorted(inmt) if not by_mt[m]]
    print("   macrotiles with no lost offset: %s = %d tiles" % (clean, sum(inmt[m] for m in clean)))
run(4096, 4096, 4096, 4096); run(4096, 1152, 4096, 1152); run(1040, 1280, 1040, 1280); run(1280, 1024, 1280, 1024)
