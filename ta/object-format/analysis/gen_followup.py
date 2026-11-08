#!/usr/bin/env python3
"""Follow-up cases of 11.31, declared AFTER the first run of the safe scripts (their results shaped
the models below) and BEFORE the follow-up run. Writes declared-followup.tsv, predictions-followup.tsv
and the three scripts ta-object-format2.sh, vdm-vtask2.sh, ta-tri-corner.sh. python3 -B gen/gen_followup.py
from p1131/. The predictions are computed here with models of this file only."""
import math, pathlib, struct, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import models as M

ROOT = pathlib.Path(__file__).resolve().parent.parent
DUMP = '--dump-render "$W/dump"'
cases, preds = [], []


def add(script, name, sset, w, h, args):
    cases.append((name, script, sset, w, h, " ".join(args)))


# ---- fmt2: half-precision sets by size code. Model H70-F2: a set of size code s has c(s) components
# (1 -> 1, 2 -> 2, 3 -> 3, 4 -> 3, 5 -> 4: xy plus z for codes 3 and 5, w for 4 and 5); a set whose
# format bit is set stores ceil(c/2) dwords for its c components, the rest of the N outputs raw;
# stored = 1 + N - sum over flagged sets of (c - ceil(c/2)). Built from the first run's f1/alt cases
# (sizes 1, 2, 5 seen), so sizes 3 and 4 are not fitted: they are the held-out part.
def comps(s):
    return {0: 0, 1: 1, 2: 2, 3: 3, 4: 3, 5: 4}[s]


def stored(n, sizes, flags):
    sv = 1 + n
    for i, s in enumerate(sizes):
        if flags >> i & 1:
            c = comps(s)
            sv -= c - (c + 1) // 2
    return sv


FMT2 = [("f2-n4-s1", 4, [1], 1), ("f2-n4-s2", 4, [2], 1), ("f2-n4-s3", 4, [3], 1), ("f2-n4-s4", 4, [4], 1),
        ("f2-n4-s5", 4, [5], 1), ("f2-n8-34", 8, [3, 4], 3), ("f2-n8-55", 8, [5, 5], 3),
        ("f2-n8-15", 8, [1, 5], 3), ("f2-n8-52u", 8, [5, 2], 2), ("f2-n11-235", 11, [2, 3, 5], 7),
        ("f2-n11-111", 11, [1, 1, 1], 7), ("f2-n11-2u2", 11, [2, 2, 2], 5)]
for name, n, sizes, flags in FMT2:
    cs = sum(s << (3 * i) for i, s in enumerate(sizes))
    sset = "heldout"
    a = ["probe", "--tri", "pixpds:12", "--temps", "32", "--pixels", "--width", "64", "--height", "64",
         "--vtx-coords", str(n), "--blk", "16=%d" % cs, "--blk", "17=%d" % flags, DUMP,
         '--slot "pixel=$S/pix_pa0.bin"', '--slot "vtxuse=$S/vtx_c%d.bin"' % n, '"$S/p1131-fmt-%d__0.bin"' % n]
    add("ta-object-format2", name, sset, 64, 64, a)
    preds.append((name, "stored_dwords", str(stored(n, sizes, flags)), "H70-F2"))
    preds.append((name, "iterated_dwords", str(1 + n), "H70-F2"))

# ---- vtask2: Q094 capacity. The first run: 126 vertices all reach objects with 2 rows (n 2, 4) at every
# field to 15, with 3 rows (n 8) at fields 9 and below only, with 4 rows (n 11) at field 7 and below only;
# lost vertices at 3 rows with fields 15 and 13 (V = 16, 14) and 4 rows with fields 15, 13, 9 (V = 16, 14, 10).
# Two budget readings: MD, output dwords a task (4 + n) * V: safe up to 128, lost from 150; MR, rows
# R * V (R = ceil((4 + n) / 4)): safe up to 32, lost from 40; between them each says '?'.
def verdicts(n, field):
    v = field + 1
    d, r = (4 + n) * v, -(-(4 + n) // 4) * v
    md = "all" if d <= 128 else "lost" if d >= 150 else "?"
    mr = "all" if r <= 32 else "lost" if r >= 40 else "?"
    return md, mr


VT2 = [(5, 13), (5, 15), (5, 9), (6, 13), (6, 9), (9, 8), (9, 7), (8, 10), (8, 11), (8, 12), (11, 8), (6, 11)]
for n, f in VT2:
    name = "v2-n%d-f%d" % (n, f)
    a = ["probe", "--tri", "pixpds:12", "--temps", "32", "--width", "64", "--height", "64", "--vertices", "126",
         "--vtx-coords", str(n)]
    if f != 15:
        a += ["--vdm", "6^=0x%08x" % ((15 ^ f) << 28)]
    a += [DUMP, '--slot "pixel=$S/pix_pa0.bin"', '--slot "vtxuse=$S/vtx_c%d.bin"' % n, '"$S/p1131-fmt-%d__0.bin"' % n]
    add("vdm-vtask2", name, "heldout", 64, 64, a)
    md, mr = verdicts(n, f)
    preds.append((name, "vertices_all_reach_objects", md, "H94-MD"))
    preds.append((name, "vertices_all_reach_objects", mr, "H94-MR"))

# ---- ta-tri-corner: an edge of the first triangle exactly through a tile corner (T1: corners closed).
# 128 x 128, viewport scale 64: v0 = C - (48, 12), v1 = v0 + (96, 24): the edge v0 v1 passes through C
# (offset x = Cx, y = Cy + 36). Two triangles (--vertices 6): the second moved (1/16, 1/16), so its edge
# misses C by 0.047 px. Predictions: every tile's primitive set by H70-T1 (high sides open, low and
# the edge test closed), computed with models.py of the first batch.
def t1_tiles(verts, w, h):
    tris = [verts[i:i + 3] for i in range(0, len(verts) - 2, 3)]
    out = []
    for ty in range(0, h, 16):
        for tx in range(0, w, 16):
            ps = [p for p, t in enumerate(tris) if M._overlaps(t, tx, ty, tx + 16, ty + 16)]
            if ps:
                out.append("%d:%d:%s" % (tx, ty, "".join(map(str, ps))))
    return ";".join(out)


for cx in (16, 32, 48, 64):
    for cy in (16, 32):
        name = "tc-%d-%d" % (cx, cy)
        ox, oy, s = float(cx), float(cy + 36), 64.0
        a = ["probe", "--tri", "pixel", "--temps", "32", "--width", "128", "--height", "128", "--vertices", "6"]
        a += M.vp_args(ox, s, oy, s) + [DUMP, '"$S/p1131-green__0.bin"']
        add("ta-tri-corner", name, "heldout", 128, 128, a)
        v = M.vertices(128, 128, ox, s, oy, s, 6)
        preds.append((name, "tile_prims", t1_tiles(v, 128, 128), "H70-T1"))

# ---------------------------------------------------------------- write
by = {}
for c in cases:
    by.setdefault(c[1], []).append(c)
src = (ROOT / "ta-object-format.sh").read_text().split("TABLE=$(cat <<'TABLE'")[0]
tail = '''TABLE
)
run_table "$TABLE"
health </dev/null || true
echo "## end"
'''
for sc, cs in by.items():
    head = src.replace("SCRIPT_NAME=ta-object-format", "SCRIPT_NAME=" + sc)
    body = "\n".join("%s|%s|%d|%d|%s" % (c[0], c[2], c[3], c[4], c[5]) for c in cs)
    (ROOT / (sc + ".sh")).write_text(head + "TABLE=$(cat <<'TABLE'\n" + body + "\n" + tail)
    (ROOT / "gen" / ("table-" + sc + ".txt")).write_text(body + "\n")
(ROOT / "declared-followup.tsv").write_text("name\tscript\tset\tW\tH\n" + "".join(
    "%s\t%s\t%s\t%d\t%d\n" % c[:5] for c in cases))
(ROOT / "predictions-followup.tsv").write_text("name\tquantity\tpredicted\tmodel\n" + "".join(
    "\t".join(p) + "\n" for p in preds))
print(len(cases), "cases", len(preds), "predictions")
