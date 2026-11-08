#!/usr/bin/env python3
"""Fourth follow-up of 11.31, declared after ta-line-point (24 line jobs: 20 one-line jobs, 4 multi-line)
and before ta-line-bisect runs. H70-L3: a one-line object's region list is the 32 x 16 regions within
e = 0.5 pixel of the segment (distance from the segment to the region's closed rectangle <= 0.5);
fitted post hoc on the one-line jobs of ta-line-point (feasible e from 0.499 to 1.94), so e is what
this script tests: single lines whose nearest region is at distances 0.3125 to 2.0 from the line,
vertical-ish (sx 1/2, sy 32, v0 in the band y 48-64, region (0, 48) to its left) and horizontal-ish (sx 32,
sy 1/2, line below the region (32, 0)). Cases whose distance is within 0.02 of 0.5 predict nothing
('?'). ISP word 1 width: 0x10 (default) and, in three jobs, 0x80."""
import math, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import models as M
ROOT = pathlib.Path(__file__).resolve().parent.parent
def dist_seg_rect(a, b, x0, y0, x1, y1):
    # exact: 0 if the segment meets the rectangle, else min over the segment's end points to the rectangle
    # and the rectangle's corners to the segment
    def p2r(p):
        dx = max(x0 - p[0], 0, p[0] - x1); dy = max(y0 - p[1], 0, p[1] - y1); return math.hypot(dx, dy)
    def p2s(p):
        vx, vy = b[0] - a[0], b[1] - a[1]; L = vx * vx + vy * vy
        t = max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L)); return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)
    if M.seg_rect(a, b, x0, y0, x1, y1): return 0.0
    return min([p2r(a), p2r(b)] + [p2s(c) for c in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))])
D = [0.3125, 0.375, 0.4375, 0.5, 0.5625, 0.625, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
cases, preds = [], []
def job(name, ox, sx, oy, sy, width=None):
    a = ["probe", "--tri", "pixel", "--temps", "32", "--width", "128", "--height", "128", "--blk 1=0x01d08200"] + \
        M.vp_args(ox, sx, oy, sy) + (["--blk 2=0x%08x" % (width << 8 | 0xf0)] if width else []) + \
        ["--vdm", "2=0x84c00002", '--dump-render "$W/dump"', '"$S/p1131-green__0.bin"']
    cases.append("%s|heldout|128|128|%s" % (name, " ".join(a)))
    v = M.vertices(128, 128, ox, sx, oy, sy, 3)
    out = []
    for y0 in range(0, 128, 16):
        for x0 in range(0, 128, 32):
            d = dist_seg_rect(v[0], v[1], x0, y0, x0 + 32, y0 + 16)
            if abs(d - 0.5) < 0.02: out.append("%d:%d:?" % (x0, y0))
            elif d <= 0.5: out.append("%d:%d:Y" % (x0, y0))
    preds.append((name, "regions", ";".join(out), "H70-L3"))
for d in D:
    job("lb-v-d%g" % d, 32.375 + d, 0.5, 80.0, 32.0)
for d in D:
    job("lb-h-d%g" % d, 48.0, 32.0, 16.34375 + d, 0.5)
for nm, args in (("lb-v-d0.5-w80", (32.875, 0.5, 80.0, 32.0)), ("lb-v-d1-w80", (33.375, 0.5, 80.0, 32.0)), ("lb-h-d0.5-w80", (48.0, 32.0, 16.84375, 0.5))):
    job(nm, *args, width=0x80)
body = "\n".join(cases)
(ROOT / "declared-followup4.tsv").write_text("name\tscript\tset\tW\tH\n" + "".join("%s\tta-line-bisect\theldout\t128\t128\n" % c.split("|")[0] for c in cases))
(ROOT / "predictions-followup4.tsv").write_text("name\tquantity\tpredicted\tmodel\n" + "".join("\t".join(p) + "\n" for p in preds))
src = (ROOT / "vdm-vtask2.sh").read_text().split("TABLE=$(cat <<'TABLE'")[0].replace("SCRIPT_NAME=vdm-vtask2", "SCRIPT_NAME=ta-line-bisect")
tail = "TABLE\n)\nrun_table \"$TABLE\"\nhealth </dev/null || true\necho \"## end\"\n"
(ROOT / "ta-line-bisect.sh").write_text(src + "TABLE=$(cat <<'TABLE'\n" + body + "\n" + tail)
(ROOT / "gen" / "table-ta-line-bisect.txt").write_text(body + "\n")
print(len(cases), "cases")
