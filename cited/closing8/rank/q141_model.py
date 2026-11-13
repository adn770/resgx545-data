#!/usr/bin/env python3
"""Q141 post hoc: do the landed region model's (data texture/p1141/recompute/msaa_model.py, E503's
reading written again) missing pixels equal the background holes of E502's identity jobs? tri-full
is two triangles meeting on the diagonal x / W + y / H = 1.25; the holes (q141_ident.out) lie along
it. Imports the model read-only by path; standard library."""
import importlib.util, gzip, re, csv
M = importlib.util.spec_from_file_location("mm", "/Users/jtorra/src/resgx545-data/texture/p1141/recompute/msaa_model.py")
mm = importlib.util.module_from_spec(M); M.loader.exec_module(mm)
D = "/Users/jtorra/src/resgx545-data/isp/msaa-ident/"
def img(p):
    rows = {}
    for l in gzip.open(p, "rt"):
        m = re.search(r"row (\d+): (.*)$", l)
        if m: rows[int(m.group(1))] = m.group(2).split()
    return rows
tot = {}
for r in csv.DictReader(open(D + "cases.tsv"), delimiter="\t"):
    n, W, H, mode, te = r["name"], int(r["W"]), int(r["H"]), int(r["mode"]), int(r["te"], 16)
    X = img(f"{D}dumps/{n}-x.txt.gz")
    hole = {(x, y) for y in X for x, v in enumerate(X[y]) if v.endswith("ff203040")}
    for var, kw in (("halves", {}), ("nohalves", {"halves": False})):
        out = mm.predict(mm.tri_full(W, H), W, H, mode, te, **kw)
        miss = {(x, y) for x in range(W) for y in range(H) if (x, y) not in out}
        ok = miss == hole
        tot.setdefault(var, [0, 0]); tot[var][0] += ok; tot[var][1] += 1
        if hole or miss:
            print(f"{n} {var}: hw holes {len(hole)} model holes {len(miss)} equal {ok} (hw-only {len(hole - miss)}, model-only {len(miss - hole)})")
print("jobs where the model's holes equal the hardware's:", tot)
