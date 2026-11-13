#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""q139_o3_rivals.py (round 8 planning; offline, POST HOC: written after q139_o1_score.out was read).
Rival block orders against the kept 256 x 256 and 640 x 480 stride images (wrong-tile sets, E877's
loader) and on the candidate strides: blkrow = blocks row by row over the target (q139_o1's
rowblk), blkdown = blocks column by column, mtblk = macrotile by macrotile then its blocks,
revblk = block rows bottom up.   python3 -I -B q139_o3_rivals.py DATA_REPO
"""
import os, sys, io, contextlib, importlib.util
data = sys.argv[1]; here = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], data, os.devnull]
spec = importlib.util.spec_from_file_location("p", os.path.join(here, "q139_o1_predict.py")); p = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(p)
sys.path.insert(0, os.path.join(data, "cited/closing6/fold-misc/q139"))
import q139_model as M
K = {"raster": p.KEYS["raster"], "blkrow": p.KEYS["rowblk"], "blkdown": lambda r, c, mc, mr, n: (c >> 2, r >> 2, r, c),
     "mtblk": lambda r, c, mc, mr, n: (mc * n + mr, r >> 2, c >> 2, r, c), "mtrow": lambda r, c, mc, mr, n: (mr, mc, r >> 2, c >> 2, r, c),
     "revblk": lambda r, c, mc, mr, n: (-(r >> 2), c >> 2, r, c)}
kept = {(256, 256): (0, 1, 2, 4, 8, 16, 24, 31), (640, 480): (4, 16, 36, 63)}
for (w, h), ss in kept.items():
    for s in ss:
        W, H, job, bad = M.load("%s/ta/mtile-fields-risky/dumps/q100-%dx%d-stride-%d.txt.gz" % (data, w, h, s))
        obs = sorted("%d.%d" % t for t in bad); args = "--kpoke-render 1:ta:146=0x%x" % s
        print("kept %dx%d stride %2d obs %3d: %s" % (w, h, s, len(obs), " ".join("%s:%s" % (k, "ok" if p.predict(w, h, args, f) == obs else "NO") for k, f in K.items())))
for (w, h), ss in (((256, 256), (3, 5, 6, 7, 12, 20)), ((640, 480), (5, 6, 7, 8, 12, 24, 48))):
    for s in ss:
        args = "--kpoke-render 1:ta:146=0x%x" % s; r = {k: set(p.predict(w, h, args, f)) for k, f in K.items()}
        print("new  %dx%d stride %2d blkrow %3d wrong; differs from it in tiles: %s" % (w, h, s, len(r["blkrow"]), " ".join("%s:%d" % (k, len(r[k] ^ r["blkrow"])) for k in K if k != "blkrow")))
