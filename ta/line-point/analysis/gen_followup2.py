#!/usr/bin/env python3
"""Second follow-up of 11.31, declared after vdm-vtask and vdm-vtask2 ran and before vdm-vtask3 runs.
H94-MR2: with R = ceil((4 + N) / 4) output rows (N = --vtx-coords) and V = field + 1 vertices, a task keeps
all of its vertices when R * V <= 33 and loses or duplicates some when R * V >= 36 (the data of
vdm-vtask and vdm-vtask2: R*V = 30, 32, 33 all kept; 36, 39, 42, 48, 64 not). Writes declared-followup2.tsv,
predictions-followup2.tsv and vdm-vtask3.sh."""
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = [(5, 10), (6, 10), (8, 10), (5, 11), (6, 12), (9, 6), (11, 6), (4, 15)]
rows, preds, table = [], [], []
for n, f in CASES:
    name = "v3-n%d-f%d" % (n, f) + ("-b" if (n, f) == (8, 10) else "")
    V, R = f + 1, -(-(4 + n) // 4)
    pv = "all" if R * V <= 33 else "lost" if R * V >= 36 else "?"
    a = ["probe", "--tri", "pixpds:12", "--temps", "32", "--width", "64", "--height", "64", "--vertices", "126",
         "--vtx-coords", str(n)]
    if f != 15:
        a += ["--vdm", "6^=0x%08x" % ((15 ^ f) << 28)]
    a += ['--dump-render "$W/dump"', '--slot "pixel=$S/pix_pa0.bin"', '--slot "vtxuse=$S/vtx_c%d.bin"' % n,
          '"$S/p1131-fmt-%d__0.bin"' % n]
    table.append("%s|heldout|64|64|%s" % (name, " ".join(a)))
    rows.append("%s\tvdm-vtask3\theldout\t64\t64\n" % name)
    preds.append("%s\tvertices_all_reach_objects\t%s\tH94-MR2\n" % (name, pv))
    preds.append("%s\trows_times_vertices\t%d\tH94-MR2\n" % (name, R * V))
(ROOT / "declared-followup2.tsv").write_text("name\tscript\tset\tW\tH\n" + "".join(rows))
(ROOT / "predictions-followup2.tsv").write_text("name\tquantity\tpredicted\tmodel\n" + "".join(preds))
src = (ROOT / "vdm-vtask2.sh").read_text().split("TABLE=$(cat <<'TABLE'")[0].replace("SCRIPT_NAME=vdm-vtask2", "SCRIPT_NAME=vdm-vtask3")
tail = "TABLE\n)\nrun_table \"$TABLE\"\nhealth </dev/null || true\necho \"## end\"\n"
(ROOT / "vdm-vtask3.sh").write_text(src + "TABLE=$(cat <<'TABLE'\n" + "\n".join(table) + "\n" + tail)
(ROOT / "gen" / "table-vdm-vtask3.txt").write_text("\n".join(table) + "\n")
print(len(CASES), "cases")
