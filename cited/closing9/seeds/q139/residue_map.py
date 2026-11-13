#!/usr/bin/env python3
"""Q139 offline: slot -> tile maps of the residue dumps. Read only. python3 residue_map.py [R8LGEO_DIR]"""
import gzip, os, sys
S = sys.argv[1] if len(sys.argv) > 1 else "/Users/jtorra/src/scratch/resgx545/closing8/r8-lgeo"
sys.path.insert(0, S + "/score"); sys.path.insert(0, S + "/kit")
import lib_dump as L  # noqa
D = S + "/out/20261113-024441/q139"
def rd(n, e):
    p = f"{D}/{n}{e}.gz"
    return gzip.open(p).read() if os.path.exists(p) else open(f"{D}/{n}{e}", "rb").read()
for n, w, h, cn in (("q139-res-256x256-m1-B2-10", 256, 256, "q139-ctl-256x256"),
                    ("q139-res-256x256-m1-B2-11", 256, 256, "q139-ctl-256x256"),
                    ("q139-res-640x480-m1-B1-23", 640, 480, "q139-ctl-640x480")):
    ok, txt, ly = L.baseline_layout(rd(cn, ".tri.tadata.bin"), rd(cn, ".tri.param.bin"), w, h)
    hs = L.headers(rd(n, ".tri.tadata.bin"), ly["base"], stop_zero=1 << 30)
    comp, bad = L.image_tiles(rd(n, ".txt").decode(), w, h)
    print(f"== {n}: {len(hs)} headers, wrong {L.tiles_text(bad)}")
    tx, ty = -(-w // 32), -(-h // 16)
    grid = {}
    for i, col, row, fl, st in hs:
        t = L.tile_of(col, row)
        grid.setdefault(t, []).append(i)
    lim = 12 if w == 256 else 24
    for r in range(ty + 2):
        print(" ".join(("%4s" % ",".join(map(str, grid.get((c, r), [])))[:9] if (c, r) in grid else "   .") for c in range(min(tx + 4, lim))))
    print("slot order:", [(i, L.tile_of(c, r)) for i, c, r, f, s in hs][:80])
