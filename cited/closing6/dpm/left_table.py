#!/usr/bin/env python3
"""O3: per kept 1500-vertex job with a partial render: thr0, the global pages at the abort,
at the last in-stretch sample of the first partial render (and the minimum over the stretch),
the grow flag, the raise (dword 38), and the peaks of the later runs.  Read-only."""
import sys, struct, gzip, os
from r6lib import *
out = []
for ds, stg, name, d, m in jobs():
    args = m.get('args', ''); wh, sc = scene_of(args)
    if not sc.startswith('tri1500') and not sc.startswith('tri1350') and sc != 'full': continue
    try: cols, rows = load(f'{d}/{name}.txt.gz')
    except Exception: continue
    if not rows or 0x72c not in rows[0][1] or 0x658 not in rows[0][1]: continue
    st = stretches(rows)
    if not st: continue
    a, e = st[0]; thr = rows[a][1][0x624]
    gA = hi(rows[a - 1][1], 0x72c); pA = hi(rows[a - 1][1], 0x724)
    gl = hi(rows[e][1], 0x72c); pl = hi(rows[e][1], 0x724)
    gmin = min(hi(rows[i][1], 0x72c) for i in range(a, e + 1))
    grow = any((rows[i][1][0x628] & 0xffff) < 0x10 for i in range(1, a + 1))
    d38 = None
    bp = f'{d}/{name}.after.buf09.bin.gz'
    if os.path.exists(bp):
        b = gzip.open(bp).read()
        if len(b) >= 156: d38 = struct.unpack_from('<I', b, 152)[0]
    # second run: pages and global pages at the second abort (or the end)
    e2 = st[1][0] if len(st) > 1 else len(rows)
    g2 = max(hi(rows[i][1], 0x72c) for i in range(e + 1, e2)) if e2 > e + 1 else -1
    p2 = max(hi(rows[i][1], 0x724) for i in range(e + 1, e2)) if e2 > e + 1 else -1
    mt = rows[a][1].get(0x720, 0)
    out.append((wh, sc, thr, f'{ds[8:]}/{stg}/{name}', gA, pA, gl, gmin, pl, int(grow), d38, len(st), p2, g2, mt))
out.sort()
print('target scene thr0 gpsA psA gps_left gps_min ps_left grow d38 nparts run2peak run2gps abort_mtile job')
for r in out:
    print('%-10s %-8s %#06x %d %#05x %d %d %d %d %s %2d %#05x %d %08x %s' % (r[0], r[1], r[2], r[4], r[5], r[6], r[7], r[8], r[9],
          'R' if r[10] == 0x20 else ('N' if r[10] == 0 else '?'), r[11], r[12], r[13], r[14], r[3]))
