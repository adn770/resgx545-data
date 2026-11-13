#!/usr/bin/env python3
"""Q139 offline: every kept mtile-fields job whose first macrotile bound fx is 2 or 3 mod 4 (where
H-EVEN and R7-BLK part), its outcome (whole image or not) and the two models' wrong-tile counts.
Read only. python3 -I -B fx_status.py [DATA_REPO]"""
import os, re, sys, importlib.util
data = sys.argv[1] if len(sys.argv) > 1 else "/Users/jtorra/src/resgx545-data"
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ei", os.path.join(here, "even_images.py"))
F = None
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
F = load("q139_fit_r7", os.path.join(data, "render/closing-r7-rp/fold/q139_fit.py"))
sys.path.insert(0, os.path.join(data, "cited/closing6/fold-misc/q139"))
M = load("q139_model", os.path.join(data, "cited/closing6/fold-misc/q139/q139_model.py"))
for ds in ("ta/mtile-fields", "ta/mtile-fields-risky"):
    for line in list(open(os.path.join(data, ds, "cases.tsv")))[1:]:
        p = line.rstrip("\n").split("\t"); name, w, h = p[0], int(p[2]), int(p[3]); args = p[4] if len(p) > 4 else ""
        try:
            m1, m2, s = F.words(w, h, args); n, bx, by = F.bounds(m1, m2)
        except Exception:
            continue
        if bx[1] % 4 in (2, 3) or by[1] % 4 in (2, 3):
            W, H, job, bad = M.load(os.path.join(data, ds, "dumps", name + ".txt.gz"))
            print("%-6s %-36s fx=%2d fy=%2d bx=%s by=%s %s" % (ds[-5:], name, bx[1], by[1], bx, by,
                  "whole image, %d wrong tiles" % len(bad) if bad is not None else "NO whole image (fault or cut)"))
