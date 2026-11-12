#!/usr/bin/env python3
"""d_cmp.py (round 6, offline, POST HOC): what differs between two COMPLETED twins (m1, m2: the noise floor), and then the headers of
row d that differ from m1, by kind and with their words.  Standard library only."""
import gzip, os, struct, collections
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
ATT = DATA + "/render/closing-r5-render4x/out/20261112-100112"
rd = lambda p: gzip.open(p).read()
d = rd(ATT + "/d/d1-1280x1024-held.heldtadata.bin.gz")
m1 = rd(ATT + "/m/m1-1280x1024-max1280x1040.tri.tadata.bin.gz")
m2 = rd(ATT + "/m/m2-1280x1024-max2048x2048.tri.tadata.bin.gz")
N = 12288
def H(t, base): return [struct.unpack_from("<3I", t, base + 12 * i) for i in range(N)]
hd, h1, h2 = H(d, 0x7000), H(m1, 0x13000), H(m2, 0x13000)
print("m1 vs m2 headers differing:", sum(a != b for a, b in zip(h1, h2)))
c = collections.Counter()
for i, (a, b) in enumerate(zip(hd, h1)):
    if a == b: continue
    x0 = a[0] ^ b[0]
    if a[1] == b[1] and a[2] == b[2]:
        c["w0 xor 0x%08x, w1 same" % x0] += 1
    elif a[0] == b[0] and a[1] == 0:
        c["w0 same, w1 zero"] += 1
    else:
        c["other"] += 1
for k, v in sorted(c.items()): print("%6d %s" % (v, k))
print("flag bits of w0 (31:24) by count: d", collections.Counter(a[0] >> 24 for a in hd), "m1", collections.Counter(a[0] >> 24 for a in h1))
print("-- 'other' headers of d (offset, d words, m1 words), runs compressed")
prev = None
for i, (a, b) in enumerate(zip(hd, h1)):
    if a == b or (a[1] == b[1] and a[2] == b[2]) or (a[0] == b[0] and a[1] == 0): continue
    print("0x%05x i %5d  d %08x %08x %08x  m1 %08x %08x %08x" % ((0x7000 + 12 * i, i) + a + b))
