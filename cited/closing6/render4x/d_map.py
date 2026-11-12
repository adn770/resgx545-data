#!/usr/bin/env python3
"""d_map.py (round 6, offline, POST HOC): row d's held TA data (E869) against m1's completed twin (E867), header by header.
Standard library only.  Reads the published session render/closing-r5-render4x."""
import gzip, os, struct, sys, collections
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
ATT = DATA + "/render/closing-r5-render4x/out/20261112-100112"
def rd(p): return gzip.open(p).read()
d = rd(ATT + "/d/d1-1280x1024-held.heldtadata.bin.gz")
m1 = rd(ATT + "/m/m1-1280x1024-max1280x1040.tri.tadata.bin.gz")
tx, ty, n, mx, my = 40, 64, 4, 12, 16
BD, BM = 0x7000, 0x13000
def hdrs(t, base):
    out, i = [], 0
    for col in range(n):
        for row in range(n):
            mt = col * n + row
            for by in range(2 * my // 4):
                for bx in range(2 * mx // 4):
                    for yy in range(4):
                        for xx in range(4):
                            x, y = col * 2 * mx + bx * 4 + xx, row * 2 * my + by * 4 + yy
                            w = struct.unpack_from("<3I", t, base + 12 * i)
                            out.append((i, mt, x, y, w)); i += 1
    return out
hd, hm = hdrs(d, BD), hdrs(m1, BM)
print("len d %d m1 %d" % (len(d), len(m1)))
same = diffw0 = diffw1 = 0
kinds = collections.Counter()
rows = []
for (i, mt, x, y, wd), (_, _, _, _, wm) in zip(hd, hm):
    k = (wd[0] == wm[0], wd[1] == wm[1], wd[2] == wm[2])
    kinds[k] += 1
    if k != (True, True, True):
        rows.append((i, mt, x, y, wd, wm))
print("d vs m1 (w0 same, w1 same, w2 same):", dict(kinds))
if "-v" in sys.argv:
    for i, mt, x, y, wd, wm in rows:
        print("%5d off 0x%05x mt %2d x %3d y %3d  d %08x %08x %08x  m1 %08x %08x %08x" % ((i, BD + 12 * i, mt, x, y) + wd + wm))
# map per macrotile of differing headers
for mt in sorted({r[1] for r in rows}):
    col, row = mt // n, mt % n
    S = {(r[2], r[3]): r for r in rows if r[1] == mt}
    print("macrotile %d (x %d.., y %d..): %d differing; . same, o w1 zero only, X w0 differs" % (mt, col * 2 * mx, row * 2 * my, len(S)))
    for y in range(row * 2 * my, (row + 1) * 2 * my):
        print("  y%3d " % y + "".join(("." if (x, y) not in S else ("o" if S[(x, y)][4][0] == S[(x, y)][5][0] else "X")) for x in range(col * 2 * mx, (col + 1) * 2 * mx)))
# what is beyond the header arrays in d
end = BD + 12 * len(hd)
print("d: header array ends 0x%x; file %#x" % (end, len(d)))
