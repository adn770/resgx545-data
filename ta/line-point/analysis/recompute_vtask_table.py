#!/usr/bin/env python3
"""Q094: the table of every vertex-task case: N coordinate outputs, R output rows, field, V vertices a task, R * V,
object vertex counts and their sum, from the kept data only: python3 -B recompute_vtask_table.py DIR."""
import collections, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import recompute_p1131 as R
root = pathlib.Path(sys.argv[1])
rows = []
for sc in ("vdm-vtask", "vdm-vtask2", "vdm-vtask3", "vdm-vtask4"):
    d = root / sc
    if not (d / "cases.tsv").exists():
        continue
    for c in R.load_cases(d):
        t, p, td = R.load(d, c["name"])
        fail = R.outcome(t) == "fail"
        objs = R.all_objects(p, td) if p and td else {}
        counts = [nv for _a, (nv, _p) in sorted(objs.items())]
        n = int(re.search(r"--vtx-coords (\d+)", c["args"])[1])
        v = re.search(r"--vdm 6\^=0x([0-9a-f]+)", c["args"])
        f = 15 ^ ((int(v[1], 16) >> 28) if v else 0)
        rows.append((n, -(-(4 + n) // 4), f, f + 1, sc, c["name"], "FAIL" if fail else "ok", counts, sum(counts)))
print("N  R field V  R*V  script        case             regular(15x8+6)  sum  counts")
for r in sorted(rows, key=lambda r: (r[1] * r[3], r[0], r[2], r[5])):
    reg = r[7] == [15] * 8 + [6]
    print("%-2d %d %-5d %-2d %-4d %-13s %-16s %-7s %-5s %-3d %s" % (r[0], r[1], r[2], r[3], r[1] * r[3], r[4], r[5], "REGULAR" if reg else "irregular", r[6], r[8], r[7]))
