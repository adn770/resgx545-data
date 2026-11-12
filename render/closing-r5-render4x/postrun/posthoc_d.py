#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""postrun/posthoc_d.py: a reading of row d's held TA-data dump made at the fold (2026-11-12), after the run (POST HOC).

The frozen scorer (score/score_r.py d) counts the region headers off the doubled-grid rule (gen/rlib.py headers()) and their span. This
script reads the same headers with the same rule and says HOW each one is off: word 0 as the rule gives it with word 1 (the stream offset)
zero where the tile is inside the target, or word 0 itself off; by macrotile; and whether any dword below td.rgn (the tail pointers,
control, OTPM and state pages) is non-zero.  Standard library only; run from the session directory:
    python3 postrun/posthoc_d.py > postrun/posthoc_d.out
"""
import collections
import gzip
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import rlib as L  # noqa: E402

ATT = "out/20261112-100112/d"
t = gzip.open(os.path.join(KP, ATT, "d1-1280x1024-held.heldtadata.bin.gz")).read()
tx, ty, n, mx, my, base = L._lay(1280, 1024)
print("held TA data: %d bytes; td.rgn 0x%x; target tiles %d x %d, n %d, macrotile %d x %d tiles" % (len(t), base, tx, ty, n, mx, my))
nz = [o for o in range(0, base, 4) if t[o:o + 4] != b"\0\0\0\0"]
print("non-zero dwords below td.rgn: %d" % len(nz))
kinds, by_mt, i, inside_n, off = collections.Counter(), collections.Counter(), 0, 0, []
for col in range(n):
    for row in range(n):
        mt = col * n + row
        for by in range(2 * my // 4):
            for bx in range(2 * mx // 4):
                for yy in range(4):
                    for xx in range(4):
                        x, y = col * 2 * mx + bx * 4 + xx, row * 2 * my + by * 4 + yy
                        o = base + 12 * i
                        i += 1
                        w0, w1, w2 = struct.unpack_from("<3I", t, o)
                        inside = x < 2 * tx and y < 2 * ty
                        inside_n += inside
                        w0ok = (((w0 >> 16) & 0xff) == x and (w0 & 0xfff) == y and ((w0 >> 12) & 0xf) == mt
                                and bool(w0 & (1 << 25)) == (not inside))
                        if w0ok and bool(w1) == inside and w2 == 0:
                            continue
                        off.append(o)
                        by_mt[mt] += 1
                        if w0ok and inside and w1 == 0 and w2 == 0:
                            kinds["word 0 on the rule, inside the target, word 1 (stream offset) zero"] += 1
                        elif not w0ok:
                            kinds["word 0 off the rule (word 1 %s)" % ("zero" if w1 == 0 else "non-zero")] += 1
                        else:
                            kinds["other"] += 1
print("headers: %d, inside the target %d, off the rule %d" % (i, inside_n, len(off)))
for k, v in sorted(kinds.items()):
    print("  %5d  %s" % (v, k))
print("off by macrotile: %s" % ", ".join("%d: %d" % kv for kv in sorted(by_mt.items())))
runs, s, p = [], off[0], off[0]
for o in off[1:]:
    if o != p + 12:
        runs.append((s, p + 12))
        s = o
    p = o
runs.append((s, p + 12))
print("runs of consecutive off headers: %d" % len(runs))
for a, b in runs:
    print("  0x%05x to 0x%05x  %4d headers" % (a, b, (b - a) // 12))
