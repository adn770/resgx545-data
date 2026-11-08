#!/usr/bin/env python3
"""Tenth follow-up of 11.31, declared after vdm-vtask4 and before vdm-vtask5 runs.
H94-ATTR: the attribute rows of the vertex task (VDM_TASK1 bits 14:7, word 7 of the stream, default 1) do not
change which vertices reach the objects: the list of object vertex counts of a job with the rows at 2, 4 or 8 is the
list of the same job with the default rows (read from the kept data of vdm-vtask, 2, 3 and 4 by this generator and written
into the predictions). Cases: (N, field) = (8, 11) [R*V = 36, irregular], (8, 10) [33, regular], (11, 7) [32, regular],
(2, 15) [32, regular], each at rows 2, 4, 8 (the (2, 15) at 4 and 8, and (8, 11) also at 16)."""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "recompute"))
import recompute_p1131 as R
ref = {}
for sc in ("vdm-vtask", "vdm-vtask2", "vdm-vtask3", "vdm-vtask4"):
    d = ROOT / "data" / sc
    for c in R.load_cases(d):
        t, p, td = R.load(d, c["name"])
        objs = R.all_objects(p, td)
        n = int(re.search(r"--vtx-coords (\d+)", c["args"])[1])
        v = re.search(r"--vdm 6\^=0x([0-9a-f]+)", c["args"])
        f = 15 ^ ((int(v[1], 16) >> 28) if v else 0)
        ref.setdefault((n, f), [nv for _a, (nv, _p) in sorted(objs.items())])
CASES = [(8, 11, (2, 4, 8, 16)), (8, 10, (2, 4, 8)), (11, 7, (2, 4, 8)), (2, 15, (4, 8))]
cases, preds = [], []
for n, f, rows in CASES:
    for r in rows:
        name = "v5-n%d-f%d-a%d" % (n, f, r)
        a = ["probe", "--tri", "pixpds:12", "--temps", "32", "--width", "64", "--height", "64", "--vertices", "126", "--vtx-coords", str(n)]
        if f != 15:
            a += ["--vdm", "6^=0x%08x" % ((15 ^ f) << 28)]
        a += ["--vdm", "7^=0x%08x" % ((1 ^ r) << 7), '--dump-render "$W/dump"', '--slot "pixel=$S/pix_pa0.bin"', '--slot "vtxuse=$S/vtx_c%d.bin"' % n, '"$S/p1131-fmt-%d__0.bin"' % n]
        cases.append("%s|heldout|64|64|%s" % (name, " ".join(a)))
        preds.append((name, "object_vertex_counts", ",".join(map(str, ref[(n, f)])), "H94-ATTR"))
(ROOT / "declared-followup10.tsv").write_text("name\tscript\tset\tW\tH\n" + "".join("%s\tvdm-vtask5\theldout\t64\t64\n" % c.split("|")[0] for c in cases))
(ROOT / "predictions-followup10.tsv").write_text("name\tquantity\tpredicted\tmodel\n" + "".join("\t".join(p) + "\n" for p in preds))
src = (ROOT / "vdm-vtask2.sh").read_text().split("TABLE=$(cat <<'TABLE'")[0].replace("SCRIPT_NAME=vdm-vtask2", "SCRIPT_NAME=vdm-vtask5")
tail = "TABLE\n)\nrun_table \"$TABLE\"\nhealth </dev/null || true\necho \"## end\"\n"
(ROOT / "vdm-vtask5.sh").write_text(src + "TABLE=$(cat <<'TABLE'\n" + "\n".join(cases) + "\n" + tail)
(ROOT / "gen" / "table-vdm-vtask5.txt").write_text("\n".join(cases) + "\n")
print(len(cases), "cases")
