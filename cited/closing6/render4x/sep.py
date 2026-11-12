#!/usr/bin/env python3
"""sep.py (round 6, offline): own-maximum sizes where H-TPM (target tiles) and H-TPM-grid (header-grid tiles) disagree on the rgn4
kernel, scene pages within the buffer (U4 <= 1000), both dimensions <= 2048.  Standard library only."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from morton import lay
from cells import ends, u4
out = []
for w in range(32, 2049, 16):
    for h in range(16, 2049, 16):
        if u4(w, h) > 1000: continue
        et, eg = ends(w, h); r = lay(w, h)["rgn"]
        if (et > r) != (eg > r): out.append((u4(w, h), w, h, et, eg, r))
print("%d sizes separate target from grid" % len(out))
for u, w, h, et, eg, r in sorted(out)[:12]: print("  %4d x %-4d U4 %4d target end 0x%05x grid end 0x%05x rgn 0x%05x" % (w, h, u, et, eg, r))
