#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""q139_o2_candidates.py (round 8 planning, leftovers; offline): candidate held-out rows for the
write order of Q139.  For stride pokes inside the range that drew without a fault in the kept
datasets (256 x 256: 0..31; 640 x 480: 4..63), the wrong-tile set R7-BLK's slots give under row
order (raster), 4 x 4 block order (rowblk) and block order with the block's rows and columns by
bits (blkcol; never apart from rowblk on any kept row).  Prints the counts and where they part.
No dump or image is read.   python3 -I -B q139_o2_candidates.py DATA_REPO
"""
import os, sys
data = sys.argv[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = [sys.argv[0], data, os.devnull]
import importlib.util
spec = importlib.util.spec_from_file_location("p", os.path.join(os.path.dirname(os.path.abspath(__file__)), "q139_o1_predict.py"))
import io, contextlib
p = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(p)
done = {(256, 256): {0, 1, 2, 4, 8, 16, 24, 31}, (640, 480): {4, 16, 36, 63}}
for (w, h), lo, hi in (((256, 256), 1, 31), ((640, 480), 4, 63)):
    for s in range(lo, hi + 1):
        args = "--kpoke-render 1:ta:146=0x%x" % s
        r = {k: set(p.predict(w, h, args, p.KEYS[k])) for k in ("raster", "rowblk", "blkcol")}
        tag = "kept" if s in done[(w, h)] else "new"
        print("%dx%d stride %2d %-4s wrong raster %3d rowblk %3d blkcol %3d | raster^rowblk %3d rowblk^blkcol %3d" % (
            w, h, s, tag, len(r["raster"]), len(r["rowblk"]), len(r["blkcol"]), len(r["raster"] ^ r["rowblk"]), len(r["rowblk"] ^ r["blkcol"])))
