#!/usr/bin/env python3
"""Recompute E466's formats from the stored depth dumps of the 11.24 rerun (store-format dumps),
independently of the run script: 1024 x 768 target, G = 33, a depth ramp across x (rampx) and across y
(rampy), the ramps' pixel decode from the geometry only (z = 0.25 + 0.5 * (p + 0.5) / (3 * size)).

usage: recompute_e466.py DUMPDIR
"""
import array, gzip, math, os, struct, sys
from collections import Counter

W, H, G, FILL = 1024, 768, 33, 0xDEADBEEF
ORDER = [("y", 0), ("x", 0), ("y", 1), ("x", 1), ("y", 2), ("x", 2), ("y", 3), ("x", 3), ("x", 4)]


def load(d, name):
    a = array.array("I")
    with gzip.open(os.path.join(d, name + ".bin.gz"), "rb") as fh:
        a.frombytes(fh.read())
    return a


def flt(v):
    return struct.unpack("<f", struct.pack("<I", v))[0]


def tile_index(lx, ly):
    v = 0
    for pos, (axis, bit) in enumerate(ORDER):
        v += (((lx if axis == "x" else ly) >> bit) & 1) << pos
    return v


def main():
    d = sys.argv[1]
    x0, y0 = load(d, "f0-rampx"), load(d, "f0-rampy")
    # format 0: the float z of the pixel at the 512-dword tile rule's address
    z = {}
    near = 0
    for y in range(H):
        for x in range(W):
            i = 512 * ((y >> 4) * (G + 1) + (x >> 5)) + tile_index(x & 31, y & 15)
            zx, zy = flt(x0[i]), flt(y0[i])
            z[(x, y)] = zx
            ex, ey = 0.25 + 0.5 * (x + 0.5) / (3 * W), 0.25 + 0.5 * (y + 0.5) / (3 * H)
            near += abs(zx - ex) < 1e-5 and abs(zy - ey) < 1e-5
    print("format 0: x-ramp and y-ramp floats within 1e-5 of the geometry's z at %d of %d pixels"
          % (near, W * H))
    # format 1: 24-bit integer at the same address
    x1 = load(d, "f1-rampx")
    c_round, c_floor = Counter(), Counter()
    for (x, y), zz in z.items():
        i = 512 * ((y >> 4) * (G + 1) + (x >> 5)) + tile_index(x & 31, y & 15)
        c_round[x1[i] - round(zz * 0xFFFFFF)] += 1
        c_floor[x1[i] - math.floor(zz * 0xFFFFFF)] += 1
    print("format 1: stored minus round(z * 0xffffff): %s; minus floor: %s" % (
        sorted(c_round.items()), sorted(c_floor.items())))
    print("format 1: changed dwords %d" % sum(1 for v in x1 if v != FILL))
    # format 2: derive the packing from the two ramps
    xa, ya = load(d, "f2-rampx"), load(d, "f2-rampy")
    print("format 2: changed dwords %d" % sum(1 for v in xa if v != FILL))
    seen = {}
    bad = 0
    cnt = 0
    for i, vx in enumerate(xa):
        if vx == FILL:
            continue
        for half in (0, 1):
            hx = (vx >> (16 * half)) & 0xFFFF
            hy = (ya[i] >> (16 * half)) & 0xFFFF
            px = round(((hx / 65536.0) - 0.25) * 6 * W - 0.5)
            py = round(((hy / 65536.0) - 0.25) * 6 * H - 0.5)
            if not (0 <= px < W and 0 <= py < H):
                bad += 1
                continue
            tile = (py >> 4) * (G + 1) + (px >> 5)
            k = i - 256 * tile
            cnt += 1
            seen.setdefault((k, half), set()).add((px & 31, py & 15))
    amb = sum(1 for s in seen.values() if len(s) > 1)
    print("format 2: %d halves decoded to a pixel, %d outside the target; %d distinct (dword in tile, "
          "half) slots, %d of them with more than one in-tile pixel over the tiles" % (
              cnt, bad, len(seen), amb))
    # the bit permutation
    cols = {}
    for (k, half), s in seen.items():
        (lx, ly), = s
        cols[(k, half)] = (lx, ly)
    out = []
    for b in range(8):
        # which pixel bits change when only bit b of k is set (from k = 0): report where bit b goes
        pass
    ok = True
    for (k, half), (lx, ly) in sorted(cols.items()):
        want_ly_low = half
        e = (lx & 1) | (((ly >> 1) & 1) << 1) | (((lx >> 1) & 1) << 2) | (((ly >> 2) & 1) << 3) | \
            (((lx >> 2) & 1) << 4) | (((ly >> 3) & 1) << 5) | (((lx >> 3) & 1) << 6) | (((lx >> 4) & 1) << 7)
        if e != k or (ly & 1) != half:
            ok = False
    print("format 2: dword in tile k = lx0 ly1 lx1 ly2 lx2 ly3 lx3 lx4 (bit 0 first), half = ly0: %s over %d slots"
          % ("all slots agree" if ok else "DISAGREES", len(cols)))
    # formats 4 and 7 store nothing; 3, 5, 6 other layouts: counts only
    for f in (3, 4, 5, 6, 7):
        a = load(d, "f%d-rampx" % f)
        print("format %d: changed dwords %d, slots of 512 dwords %d" % (
            f, sum(1 for v in a if v != FILL), len({i >> 9 for i, v in enumerate(a) if v != FILL})))
    # bit 19: the depth negated? compare with format 0 values
    for tag in ("b19_0", "b19_1", "b19_2"):
        a = load(d, tag + "-rampx")
        ch = [i for i, v in enumerate(a) if v != FILL]
        print("%s: changed dwords %d, distinct values %d" % (tag, len(ch), len({a[i] for i in ch})))
    a = load(d, "b19_0-rampx")
    neg = same = 0
    for (x, y), zz in z.items():
        i = 512 * ((y >> 4) * (G + 1) + (x >> 5)) + tile_index(x & 31, y & 15)
        v = flt(a[i])
        neg += abs(v + zz) < 1e-6 * max(1, abs(zz))
        same += abs(v - zz) < 1e-6 * max(1, abs(zz))
    print("bit 19, float: stored = -z at %d of %d pixels, = +z at %d" % (neg, W * H, same))


if __name__ == "__main__":
    main()
