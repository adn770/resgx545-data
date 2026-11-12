#!/usr/bin/env python3
"""morton.py (round 6, offline, POST HOC): H-TPM, the tail-pointer entry of tile (x, y) of the DOUBLED grid (16 x 8 pixel tiles) is the
dword at TA-data offset 4 * Z(x, y), Z the bit interleave with y on the even bits and x on the odd bits (Z-order).
Part 1 (fit, row d of E869): the dwords of the held TA data that lost their value against m1's completed twin, against the Z-order
addresses of the in-target tiles.  Part 2 (check, not used for the fit): fault iff some in-target tile's entry lies at or past a limit
of the context's layout, over the 24 four-array 4x cells below 4096 wide on record and the 4096-wide ones.
Standard library only; reads the published session render/closing-r5-render4x."""
import gzip, os, struct, sys, collections
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
ATT = DATA + "/render/closing-r5-render4x/out/20261112-100112"
rd = lambda p: gzip.open(p).read()

def rup(a, m): return (a + m - 1) // m * m
def lay(w, h):
    tx, ty = (w + 31) // 32, (h + 15) // 16
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = rup((tx + n - 1) // n, 4), rup((ty + n - 1) // n, 4)
    span = max(n * mx, n * my); side = 1
    while side < span: side <<= 1
    tail = rup(4 * side * side, 4096)
    return dict(tx=tx, ty=ty, n=n, mx=mx, my=my, side=side, tail=tail, otpm=tail + 0x1000, state=tail + 0x2000, rgn=tail + 0x3000)
def spread(v):
    r = 0
    for b in range(12):
        r |= ((v >> b) & 1) << (2 * b)
    return r
def z(x, y, yeven=True):
    return (spread(y) | spread(x) << 1) if yeven else (spread(x) | spread(y) << 1)
def unz(i, yeven=True):
    a = b = 0
    for k in range(12):
        a |= ((i >> (2 * k)) & 1) << k
        b |= ((i >> (2 * k + 1)) & 1) << k
    return (b, a) if yeven else (a, b)        # (x, y)
def zmax(w, h, yeven=True, grid="target"):
    """the largest entry index over the doubled grid's tiles: of the target (2tx x 2ty) or of the header grid (2 n mx x 2 n my)"""
    t = lay(w, h)
    X, Y = (2 * t["tx"], 2 * t["ty"]) if grid == "target" else (2 * t["n"] * t["mx"], 2 * t["n"] * t["my"])
    return max(z(x, y, yeven) for x in (X - 1, *[(X - 1) | ((1 << k) - 1) for k in range(12) if ((X - 1) | ((1 << k) - 1)) < X], *[((X - 1) >> k << k) - 1 for k in range(12) if ((X - 1) >> k << k) - 1 >= 0])
               for y in range(Y)) if False else max(z(x, y, yeven) for x in range(X) for y in range(Y))

def part1():
    d = rd(ATT + "/d/d1-1280x1024-held.heldtadata.bin.gz")
    m1 = rd(ATT + "/m/m1-1280x1024-max1280x1040.tri.tadata.bin.gz")
    N, BD, BM = 12288, 0x7000, 0x13000
    t = lay(1280, 1024)
    X, Y, GX, GY = 2 * t["tx"], 2 * t["ty"], 2 * t["n"] * t["mx"], 2 * t["n"] * t["my"]
    lost, kept_nz = set(), set()       # dword offsets of d: zero where m1's twin is non-zero / equal to m1's and non-zero
    flag = {}
    for i in range(N):
        a, b = struct.unpack_from("<3I", d, BD + 12 * i), struct.unpack_from("<3I", m1, BM + 12 * i)
        for k in range(3):
            o = BD + 12 * i + 4 * k
            if b[k] and not a[k]: lost.add(o)
            elif b[k] and a[k] == b[k]: kept_nz.add(o)
            elif a[k] != b[k]: flag[o] = (a[k], b[k])
    print("part 1: d against m1, %d headers: dwords lost (zero in d, non-zero in m1) %d, non-zero and equal %d, other differences %d" % (N, len(lost), len(kept_nz), len(flag)))
    print("  other differences by (d xor m1):", dict(collections.Counter("0x%08x" % (a ^ b) for a, b in flag.values())))
    for yeven in (True, False):
        tin = {4 * z(x, y, yeven) for x in range(X) for y in range(Y)}
        tgrid = {4 * z(x, y, yeven) for x in range(GX) for y in range(GY)}
        w1 = {o for o in lost if (o - BD) % 12 == 4}; w0 = {o for o in lost if (o - BD) % 12 == 0}
        allw1 = {BD + 12 * i + 4 for i in range(N) if struct.unpack_from("<I", m1, BM + 12 * i + 4)[0]}
        pred = allw1 & tin
        print("  interleave %s: lost word-1 dwords %d; predicted (a stream offset whose dword is an in-target tile's entry) %d; both %d, lost only %d, predicted only %d"
              % ("y even" if yeven else "x even", len(w1), len(pred), len(w1 & pred), len(w1 - pred), len(pred - w1)))
        print("     lost word-0 dwords %d: at an in-target entry %d, at an entry of the header grid outside the target %d, neither %d" % (len(w0), len(w0 & tin), len((w0 & tgrid) - tin), len(w0 - tgrid)))
        allw0 = {BD + 12 * i for i in range(N)}
        print("     word-0 dwords at an in-target entry: %d, of them lost %d; at a grid-only entry %d, lost %d" % (len(allw0 & tin), len(allw0 & tin & w0), len((allw0 & tgrid) - tin), len(((allw0 & tgrid) - tin) & w0)))
    # bit 27
    yeven = True
    b27 = [o for o, (a, b) in flag.items() if (a ^ b) == 0x08000000]
    c = collections.Counter()
    for o in b27:
        i = (o - BD) // 12
        w0 = struct.unpack_from("<I", m1, BM + 12 * i)[0]
        x, y = (w0 >> 16) & 0xff, w0 & 0xfff
        e = 4 * z(x, y)
        c["own entry " + ("in the tail room" if e < 0x4000 else "in ctl/OTPM/state" if e < 0x7000 else "in the headers")] += 1
    print("  bit 27 set in d only: %d headers; %s" % (len(b27), dict(c)))
    tot = collections.Counter()
    for x in range(X):
        for y in range(Y):
            e = 4 * z(x, y)
            tot["in the tail room" if e < 0x4000 else "in ctl/OTPM/state" if e < 0x7000 else "in the headers"] += 1
    print("  in-target tiles by where their own entry lies:", dict(tot))
    return b27

CELLS = [  # (w, h, mw, mh, fault, record)
 (64, 64, 64, 64, 0, "E824 c2"), (288, 144, 288, 144, 0, "E824 h1, E828 j1r"), (256, 288, 256, 288, 0, "E824 h2"), (384, 384, 384, 384, 0, "E824 h3"),
 (320, 160, 320, 160, 0, "E824 h4"), (512, 384, 512, 384, 0, "E824 h5"), (640, 480, 640, 480, 0, "E824 h6"), (320, 400, 320, 400, 0, "E824 h7"),
 (1024, 768, 1024, 768, 0, "E824 h8"), (1280, 1024, 1280, 1024, 1, "E845, E869 d"), (2048, 1536, 2048, 1536, 1, "E845"),
 (1024, 768, 2048, 2048, 0, "E867 m0"), (1280, 1024, 1280, 1040, 0, "E867 m1"), (1280, 1024, 2048, 2048, 0, "E867 m2"), (1280, 1024, 2048, 1024, 1, "E867 m3"),
 (2048, 1536, 4096, 4096, 0, "E867 m4"), (2048, 240, 2048, 240, 1, "E868 l1"), (256, 1536, 256, 1536, 0, "E868 l2"), (768, 2048, 768, 2048, 1, "E868 l3"),
 (1280, 768, 1280, 768, 1, "E868 l4"), (1024, 1024, 1024, 1024, 1, "E868 l5"), (1024, 512, 1024, 512, 0, "E868 x1"), (1184, 768, 1184, 768, 1, "E868 x2"),
 (1024, 800, 1024, 800, 1, "E868 x3"),
 (4096, 1152, 4096, 1152, 1, "E846 o7 (also overflows)"), (4096, 4096, 4096, 4096, 1, "E828 j4 (also overflows)")]

def part2():
    print("part 2: fault iff 4 * (largest Z over the tiles) >= limit of the maximum's layout; misses over %d cells" % len(CELLS))
    for yeven in (True, False):
        for grid in ("target", "grid"):
            for lim in ("tail", "otpm", "state", "rgn"):
                miss = []
                for w, h, mw, mh, f, rec in CELLS:
                    p = 4 * zmax(w, h, yeven, grid) >= lay(mw, mh)[lim]
                    if p != bool(f): miss.append("%dx%d on %dx%d" % (w, h, mw, mh))
                print("  %s, tiles of the %-6s, limit %-5s: %2d misses %s" % ("y even" if yeven else "x even", grid, lim, len(miss), "; ".join(miss[:6])))
    print("  the cells under (y even, target, rgn):")
    for w, h, mw, mh, f, rec in CELLS:
        m = lay(mw, mh); e = 4 * zmax(w, h) + 4
        print("    %4d x %-4d on %4d x %-4d  entries end 0x%06x  room 0x%06x rgn 0x%06x  -> %-8s measured %-8s %s" % (w, h, mw, mh, e, m["tail"], m["rgn"], "fault" if e > m["rgn"] else "complete", "fault" if f else "complete", rec))

if __name__ == "__main__":
    part1(); part2()
