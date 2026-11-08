#!/usr/bin/env python3
"""Fifth follow-up of 11.31, declared after vdm-state-risky and before vdm-state-grid runs. The grid of
vdm-state-risky (the second state block's word 9 set to the base with bits 11:9 = v and bits 7:0 = rows,
rows 1, 2, 3 and 8, v 0 to 7, one run each) showed: v = 0 removes the object, v = 1 hangs, 2 to 5 and 7 draw
all marks, v = 6 hangs; while v = 6 with the base's rows (5, the xor jobs st-b2-b119-6) drew all marks in
2 of 2 runs. H47-G1: v = 6 completes only with rows = 5. H47-G2: v = 6 completes for 4 <= rows <= 7. H47-N: v = 1
hangs at every rows. Cases: v = 6 at rows 0, 4, 5 (three runs), 6, 7, 9, 16, 255; v = 1 at rows 4 to 7; v =
7 at rows 4, 5, 6, 9 (exploration)."""
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = 0x0a022405
base = "probe --tri pixel --temps 32 --pixels --width 64 --height 64 --vertices 12 --obj2 6 --obj2-blk 6=0x42400000 --obj2-blk 2=0x000020f0 --obj2-pixel \"$S/p1131-green__0.bin\" --dump-render \"$W/dump\""
cases, preds = [], []
def add(name, v, rows, g1, g2):
    w = (BASE & ~0xe00 & ~0xff) | (v << 9) | rows
    cases.append("%s|heldout|64|64|%s --vdm 9=0x%08x \"$S/p1131-blue__0.bin\"" % (name, base, w))
    if g1 is not None:
        preds.append((name, "completes", g1, "H47-G1"))
    if g2 is not None:
        preds.append((name, "completes", g2, "H47-G2"))
for rows in (0, 4, 6, 7, 9, 16, 255):
    add("sg-v6-r%d" % rows, 6, rows, "no", "yes" if 4 <= rows <= 7 else "no")
for k in (1, 2, 3):
    add("sg-v6-r5-%d" % k, 6, 5, "yes", "yes")
for rows in (4, 5, 6, 7):
    add("sg-v1-r%d" % rows, 1, rows, "no", "no")
    preds.append(("sg-v1-r%d" % rows, "completes", "no", "H47-N"))
add("sg-v2-r5", 2, 5, "yes", "yes")   # the base word itself: must equal the control
for rows in (4, 5, 6, 9):
    add("sg-v7-r%d" % rows, 7, rows, None, None)
(ROOT / "declared-followup5.tsv").write_text("name\tscript\tset\tW\tH\n" + "".join("%s\tvdm-state-grid\theldout\t64\t64\n" % c.split("|")[0] for c in cases))
(ROOT / "predictions-followup5.tsv").write_text("name\tquantity\tpredicted\tmodel\n" + "".join("\t".join(p) + "\n" for p in preds))
src = (ROOT / "vdm-vtask2.sh").read_text().split("TABLE=$(cat <<'TABLE'")[0].replace("SCRIPT_NAME=vdm-vtask2", "SCRIPT_NAME=vdm-state-grid")
tail = "TABLE\n)\nrun_table \"$TABLE\"\nhealth </dev/null || true\necho \"## end\"\n"
(ROOT / "vdm-state-grid.sh").write_text(src + "TABLE=$(cat <<'TABLE'\n" + "\n".join(cases) + "\n" + tail)
(ROOT / "gen" / "table-vdm-state-grid.txt").write_text("\n".join(cases) + "\n")
print(len(cases), "cases")
