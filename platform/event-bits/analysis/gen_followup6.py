#!/usr/bin/env python3
"""Sixth follow-up of 11.31: repeats of vtask cases, declared after vdm-vtask3 and before vdm-vtask4 runs.
H94-DET: a case's list of vertex counts a TA object (the order of objects by address) is the same on every
run; the reference list is that of the case's first run in vdm-vtask, vdm-vtask2 or vdm-vtask3 (read from the
kept data by this generator and written into the predictions). Cases: (N, field) = (6, 10) x3, (8, 10) x2,
(5, 11) x2, (9, 8) x2, (6, 9) x2, (11, 8) x2."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "recompute"))
import recompute_p1131 as R
ref = {}
for sc in ("vdm-vtask", "vdm-vtask2", "vdm-vtask3"):
    d = ROOT / "data" / sc
    for c in R.load_cases(d):
        t, p, td = R.load(d, c["name"])
        objs = R.all_objects(p, td)
        m = __import__("re").search(r"--vtx-coords (\d+)", c["args"]); n = int(m[1])
        v = __import__("re").search(r"--vdm 6\^=0x([0-9a-f]+)", c["args"])
        f = 15 ^ ((int(v[1], 16) >> 28) if v else 0)
        ref.setdefault((n, f), [nv for _a, (nv, _p) in sorted(objs.items())])
CASES = [(6, 10, 3), (8, 10, 2), (5, 11, 2), (9, 8, 2), (6, 9, 2), (11, 8, 2)]
cases, preds = [], []
for n, f, reps in CASES:
    for k in range(1, reps + 1):
        name = "v4-n%d-f%d-r%d" % (n, f, k)
        a = ["probe", "--tri", "pixpds:12", "--temps", "32", "--width", "64", "--height", "64", "--vertices", "126", "--vtx-coords", str(n)]
        if f != 15:
            a += ["--vdm", "6^=0x%08x" % ((15 ^ f) << 28)]
        a += ['--dump-render "$W/dump"', '--slot "pixel=$S/pix_pa0.bin"', '--slot "vtxuse=$S/vtx_c%d.bin"' % n, '"$S/p1131-fmt-%d__0.bin"' % n]
        cases.append("%s|heldout|64|64|%s" % (name, " ".join(a)))
        preds.append((name, "object_vertex_counts", ",".join(map(str, ref[(n, f)])), "H94-DET"))
(ROOT / "declared-followup6.tsv").write_text("name\tscript\tset\tW\tH\n" + "".join("%s\tvdm-vtask4\theldout\t64\t64\n" % c.split("|")[0] for c in cases))
(ROOT / "predictions-followup6.tsv").write_text("name\tquantity\tpredicted\tmodel\n" + "".join("\t".join(p) + "\n" for p in preds))
src = (ROOT / "vdm-vtask2.sh").read_text().split("TABLE=$(cat <<'TABLE'")[0].replace("SCRIPT_NAME=vdm-vtask2", "SCRIPT_NAME=vdm-vtask4")
tail = "TABLE\n)\nrun_table \"$TABLE\"\nhealth </dev/null || true\necho \"## end\"\n"
(ROOT / "vdm-vtask4.sh").write_text(src + "TABLE=$(cat <<'TABLE'\n" + "\n".join(cases) + "\n" + tail)
(ROOT / "gen" / "table-vdm-vtask4.txt").write_text("\n".join(cases) + "\n")
print(len(cases), "cases")
