# SPDX-License-Identifier: MIT
"""fold/look.py: r9-z2 post-run look (not frozen): the format-0 references' values per ramp, and
the integer rows' values against z, by x (y = 0 row). Standard library."""
import collections, gzip, os, struct, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import z2 as Z
D = os.path.join(KP, "out/20261113-082522/z2")
def dw(n):
    b = gzip.open(os.path.join(D, n + ".depth.1.bin.gz")).read()
    return struct.unpack("<%dI" % (len(b) // 4), b)
f = lambda v: struct.unpack("<f", struct.pack("<I", v))[0]
for r in ("a", "b"):
    z0 = dw(f"z2-{r}-f0")
    zs = {}
    for x in range(256):
        i = 512 * ((0 >> 4) * 8 + (x >> 5)) + Z.in_tile_index(x, 0)
        zs[x] = z0[i]
    vals = sorted(set(f(v) for v in zs.values()))
    print(f"ramp {r}: format 0 at y=0: {len(vals)} distinct, min {vals[0]!r} max {vals[-1]!r}; "
          f"x=0 {zs[0]:#010x} x=127 {zs[127]:#010x} x=128 {zs[128]:#010x} x=255 {zs[255]:#010x}")
    neg = sum(f(v) < 0 for v in zs.values()); zero = sum(v == 0 for v in zs.values())
    print(f"  negative {neg}, zero {zero} of 256")
    for n in (f"z2-{r}-f1", f"z2-{r}-f1-b19"):
        d = dw(n)
        vs = [d[512 * (x >> 5) + Z.in_tile_index(x, 0)] for x in (0, 64, 127, 128, 129, 192, 255)]
        print(f"  {n}: x 0,64,127,128,129,192,255: " + " ".join(f"{v:#08x}" for v in vs))
    # where the format-1 rows miss: pixels whose z0 is negative or not
    if r == "a":
        d = dw(f"z2-{r}-f1")
        p = Z.predict(z0, 1, False, "H-CLAMP")
        miss = collections.Counter()
        for i, v in p.items():
            k = i % 512; t = i // 512
            if d[i] != v:
                miss["z0<0" if f(z0[i]) < 0 else "z0==0" if z0[i] == 0 else "z0>0"] += 1
        print("  f1 misses by the reference's sign:", dict(miss))
        bits = [(z0[i], d[i]) for i in list(p)[:0]]
        ex = [(f(z0[i]), d[i], v) for i, v in p.items() if d[i] != v][:5]
        print("  examples (z0, kept, H-CLAMP):", ex)
# whole dumps: the floor rule of E977 (format 1: min(floor(z * 2^24), 0xffffff); format 2: the same
# >> 8, E490's layout), bit 19 against no bit 19, and ramp b's zeros
import math
fl = lambda z: min(math.floor(z * 16777216), 0xFFFFFF)
for r in ("a", "b"):
    z0 = dw(f"z2-{r}-f0")
    zf = {}
    for ty in range(8):
        for tx in range(8):
            for k in range(512):
                x, y = Z.in_tile_pixel(k)
                zf[(32 * tx + x, 16 * ty + y)] = f(z0[512 * (ty * 8 + tx) + k])
    p1 = {512 * ((y >> 4) * 8 + (x >> 5)) + Z.in_tile_index(x, y): fl(zf[(x, y)]) for y in range(128) for x in range(256)}
    p2 = {256 * ((y >> 4) * 8 + (x >> 5)) + Z.in_tile_index16(x, y): fl(zf[(x, y)]) >> 8 | (fl(zf[(x, y + 1)]) >> 8) << 16
          for y in range(0, 128, 2) for x in range(256)}
    for n, p in ((f"z2-{r}-f1", p1), (f"z2-{r}-f1-b19", p1), (f"z2-{r}-f2", p2), (f"z2-{r}-f2-b19", p2)):
        d = dw(n)
        print(f"{n}: floor rule {sum(d[i] == v for i, v in p.items())}/{len(p)} dwords; zero dwords {sum(d[i] == 0 for i in p)}")
    for a, b in ((f"z2-{r}-f1", f"z2-{r}-f1-b19"), (f"z2-{r}-f2", f"z2-{r}-f2-b19")):
        print(f"{a} == {b} byte for byte: {dw(a) == dw(b)}")
