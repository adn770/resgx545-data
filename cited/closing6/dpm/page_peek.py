#!/usr/bin/env python3
"""O2 helper: dwords of one PB page of a kept dump, and the offsets at which the page's first
dword pattern recurs (the period of the object blocks).  Read-only."""
import sys, gzip, struct
param = gzip.open(sys.argv[1]).read(); pg = int(sys.argv[2], 0); n = int(sys.argv[3]) if len(sys.argv) > 3 else 96
ws = struct.unpack_from('<1024I', param, (pg - 1) * 4096)
for i in range(0, n, 8): print('%4d' % i, ' '.join('%08x' % x for x in ws[i:i + 8]))
occ = [i for i, x in enumerate(ws) if x == ws[0]]
print('recurrences of dword0 %08x at' % ws[0], occ[:40])
occ1 = [i for i in range(1023) if ws[i] == ws[0] and ws[i + 1] == ws[1]]
print('recurrences of dwords 0,1 at', occ1[:40], 'diffs', sorted(set(b - a for a, b in zip(occ1, occ1[1:]))))
