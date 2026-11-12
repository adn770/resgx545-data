#!/usr/bin/env python3
"""d_cmp2.py (round 6, offline, POST HOC): row d's headers against m1's, three classes: A w1 zeroed (w0 same), B w0 differs only in
the flag byte (w1 same), C w0's low 24 bits differ.  Runs in memory order with byte ranges.  Standard library only."""
import gzip, os, struct, collections
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
ATT = DATA + "/render/closing-r5-render4x/out/20261112-100112"
rd = lambda p: gzip.open(p).read()
d = rd(ATT + "/d/d1-1280x1024-held.heldtadata.bin.gz")
m1 = rd(ATT + "/m/m1-1280x1024-max1280x1040.tri.tadata.bin.gz")
N = 12288
def H(t, base): return [struct.unpack_from("<3I", t, base + 12 * i) for i in range(N)]
hd, h1 = H(d, 0x7000), H(m1, 0x13000)
def cls(a, b):
    if a == b: return "."
    if a[0] == b[0]: return "A" if a[1] == 0 else "a"
    if (a[0] ^ b[0]) & 0xffffff == 0: return "B" if a[1] == b[1] else "b"
    return "C" if a[1] == b[1] else "c"
cl = [cls(a, b) for a, b in zip(hd, h1)]
print(collections.Counter(cl))
runs, s = [], 0
for i in range(1, N + 1):
    if i == N or cl[i] != cl[s]:
        runs.append((s, i, cl[s])); s = i
for s, e, k in runs:
    if k == ".": continue
    a, b = hd[s], h1[s]
    print("%s 0x%05x-0x%05x %4d hdr  first d %08x %08x m1 %08x %08x  flagxor %s" % (k, 0x7000 + 12 * s, 0x7000 + 12 * e, e - s, a[0], a[1], b[0], b[1],
          sorted({"%02x" % ((hd[i][0] ^ h1[i][0]) >> 24) for i in range(s, e)})))
