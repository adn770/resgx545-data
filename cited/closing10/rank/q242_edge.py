#!/usr/bin/env python3
"""Q242 offline (round 10): score the past-target dwords of r9-x's z242-c-f1/f2 (80 x 40, G 2) against
the rivals frozen in q242_edge_rule.json (sha256 in q242_edge_rule.sha256). Standard library only;
imports the session's own gen/zls.py for the ZLS layouts (in_tile_pixel, in_tile_index16)."""
import gzip, struct, sys, os, hashlib
D = "/Users/jtorra/src/resgx545-data/render/closing-r9-x"
sys.path.insert(0, D + "/gen")
import zls as Z
HERE = os.path.dirname(os.path.abspath(__file__))
rule = open(HERE + "/q242_edge_rule.json", "rb").read()
want = open(HERE + "/q242_edge_rule.sha256").read().split()[0]
assert hashlib.sha256(rule).hexdigest() == want, "rule changed after freeze"
OUT = D + "/out/20261113-081821/zls/"
def dw(n):
    b = gzip.open(OUT + n + ".depth.1.bin.gz").read()
    return struct.unpack("<%dI" % (len(b) // 4), b)
f32 = lambda u: struct.unpack("<f", struct.pack("<I", u))[0]
W, H, G = 80, 40, 2
TX, TY = Z.tiles(W, H)
z0d = dw("z242-c-f0"); f1 = dw("z242-c-f1"); f2 = dw("z242-c-f2")
z = {}
for ty in range(TY):
    for tx in range(TX):
        for k in range(512):
            x, y = Z.in_tile_pixel(k)
            z[(32 * tx + x, 16 * ty + y)] = (512 * (ty * (G + 1) + tx) + k, z0d[512 * (ty * (G + 1) + tx) + k])
fl24 = lambda v: min(int(v * 16777216), 0xFFFFFF)
rd24 = lambda v: int(v * 16777215 + 0.5)
fl16 = lambda v: min(int(v * 65536), 0xFFFF)
past = [(x, y) for (x, y) in z if x >= W or y >= H]
print("past-target pixels", len(past))
vals = sorted(set(f32(z[p][1]) for p in past))
print("format-0 floats past target: %d distinct, min %r max %r; 0xdeadbeef left: %d" % (
    len(vals), vals[0], vals[-1], sum(z[p][1] == 0xDEADBEEF for p in past)))
res = {"H-EXT": 0, "H-FILL": 0, "H-ROUND": 0}
for p in past:
    i, u = z[p]; v = f32(u)
    res["H-EXT"] += f1[i] == fl24(v); res["H-FILL"] += f1[i] == 0xDEADBEEF; res["H-ROUND"] += f1[i] == rd24(v)
print("format 1:", {k: f"{n}/{len(past)}" for k, n in res.items()})
pairs = [(x, y) for (x, y) in past if y % 2 == 0]
res = {"H-EXT": 0, "H-FILL": 0, "H-ROUND": 0}
miss = []
for x, y in pairs:
    i = 256 * ((y >> 4) * (G + 1) + (x >> 5)) + Z.in_tile_index16(x, y)
    a, b = f32(z[(x, y)][1]), f32(z[(x, y + 1)][1])
    e = fl16(a) | fl16(b) << 16
    res["H-EXT"] += f2[i] == e; res["H-FILL"] += f2[i] == 0xDEADBEEF
    res["H-ROUND"] += f2[i] == ((rd24(a) >> 8) | (rd24(b) >> 8) << 16)
    if f2[i] != e and len(miss) < 8: miss.append((x, y, hex(f2[i]), hex(e)))
print("format 2:", {k: f"{n}/{len(pairs)}" for k, n in res.items()}, "first misses", miss)
