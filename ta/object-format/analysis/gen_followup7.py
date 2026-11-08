#!/usr/bin/env python3
"""Seventh follow-up of 11.31, declared after ta-line-bisect and ta-points and before ta-line-width and
ta-points2 run.
H70-L5: the ISP word 1 width w (bits 15:8, sixteenths of a pixel) enters a one-line object's region test as a
half-width hw = max(w / 32, 0.5) pixel: a region is listed iff the segment is nearer than hw to it (Euclidean
distance, region rectangle closed). Fit: ta-line-bisect and ta-line-point at w = 0x10 (hw 0.5: 5 of the 27
bisect cases did not agree with a 0.5 distance, by up to 0.19 pixel in the y direction) and the w80 jobs
(listing up to 1.87 pixel away). Cases: near-vertical lines (sx 1/2, sy 32, v0 at y 56) at distances d =
1, 2, 3, 4, 5, 6, 8 from the region (0, 48), widths 0x20, 0x40, 0x80, 0xf0; a region is predicted only when
its distance differs from hw by 0.2 or more ('?' within 0.2).
H117-C: the two-output vertex program (psize2) with OUTSEL untouched completes and draws no pixel (a
control for the hang of ta-points' pp2 jobs), and the same program with OUTSEL bit 8 hangs again (repeat)."""
import pathlib, sys, math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import models as M
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_followup4 import dist_seg_rect
ROOT = pathlib.Path(__file__).resolve().parent.parent
cases, preds = [], []
for w in (0x20, 0x40, 0x80, 0xf0):
    hw = max(w / 32, 0.5)
    for d in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0):
        ox = 32.375 + d
        a = ["probe", "--tri", "pixel", "--temps", "32", "--width", "128", "--height", "128", "--blk 1=0x01d08200"] + \
            M.vp_args(ox, 0.5, 80.0, 32.0) + ["--blk 2=0x%08x" % (w << 8 | 0xf0), "--vdm", "2=0x84c00002", '--dump-render "$W/dump"', '"$S/p1131-green__0.bin"']
        name = "lw-w%02x-d%g" % (w, d)
        cases.append("%s|heldout|128|128|%s" % (name, " ".join(a)))
        v = M.vertices(128, 128, ox, 0.5, 80.0, 32.0, 3)
        out = []
        for y0 in range(0, 128, 16):
            for x0 in range(0, 128, 32):
                dd = dist_seg_rect(v[0], v[1], x0, y0, x0 + 32, y0 + 16)
                if abs(dd - hw) < 0.2: out.append("%d:%d:?" % (x0, y0))
                elif dd < hw: out.append("%d:%d:Y" % (x0, y0))
        preds.append((name, "regions", ";".join(out), "H70-L5"))
# the points controls
b = ["probe", "--tri", "vtxuse", "--temps", "32", "--pixels", "--width", "64", "--height", "64", "--vtx-coords", "2", "--blk 1=0x01d18200"]
tail = M.vp_args(22.5, 16, 22.5, 16) + ["--vdm", "2=0x88c00003", '--slot "pixel=$S/p1131-green__0.bin"', '--dump-render "$W/dump"', '"$S/p1131-psize2__0.bin"']
cases.append("pc-psize2-nobit8|heldout|64|64|" + " ".join(b + tail))
preds.append(("pc-psize2-nobit8", "outcome", "completes, 0 pixels", "H117-C"))
cases.append("pc-psize2-bit8-r2|heldout|64|64|" + " ".join(b + ["--blk 13^=0x00000100"] + tail))
preds.append(("pc-psize2-bit8-r2", "outcome", "hangs", "H117-C"))
(ROOT / "declared-followup7.tsv").write_text("name\tscript\tset\tW\tH\n" + "".join("%s\tta-line-width\theldout\t%s\t%s\n" % tuple([c.split("|")[0]] + c.split("|")[2:4]) for c in cases))
(ROOT / "predictions-followup7.tsv").write_text("name\tquantity\tpredicted\tmodel\n" + "".join("\t".join(p) + "\n" for p in preds))
src = (ROOT / "vdm-vtask2.sh").read_text().split("TABLE=$(cat <<'TABLE'")[0].replace("SCRIPT_NAME=vdm-vtask2", "SCRIPT_NAME=ta-line-width")
src = src.replace('for f in "$S"/p1131-green__0.bin "$S"/pix_pa0.bin; do', 'for f in "$S"/p1131-green__0.bin "$S"/p1131-psize2__0.bin; do')
tail_ = "TABLE\n)\nrun_table \"$TABLE\"\nhealth </dev/null || true\necho \"## end\"\n"
(ROOT / "ta-line-width.sh").write_text(src + "TABLE=$(cat <<'TABLE'\n" + "\n".join(cases) + "\n" + tail_)
(ROOT / "gen" / "table-ta-line-width.txt").write_text("\n".join(cases) + "\n")
print(len(cases), "cases")
