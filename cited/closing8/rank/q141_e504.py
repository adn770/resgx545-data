#!/usr/bin/env python3
"""Q141: the landed region model (msaa_model.py, frozen for E727, unchanged) on E504's images
(isp/msaa-te-dumps: tri-full, colour ff00ff00, background ff203040), which no scorer has read with
it; mode 0 with bits 31/30 included (E618 refuses it: untested). Standard library."""
import importlib.util, gzip, re, csv, os
M = importlib.util.spec_from_file_location("mm", "/Users/jtorra/src/resgx545-data/texture/p1141/recompute/msaa_model.py")
mm = importlib.util.module_from_spec(M); M.loader.exec_module(mm)
D = "/Users/jtorra/src/resgx545-data/isp/msaa-te-dumps/"
for r in csv.DictReader(open(D + "cases.tsv"), delimiter="\t"):
    n, W, H, mode, te = r["name"], int(r["W"]), int(r["H"]), int(r["mode"]), int(r["te"], 16)
    rows = {}
    for l in gzip.open(f"{D}dumps/{n}.txt.gz", "rt"):
        m = re.search(r"row (\d+): (.*)$", l)
        if m: rows[int(m.group(1))] = m.group(2).split()
        if l.startswith("diff:"): diff = l.strip()
    if len(rows) != H:
        print(f"{n}: rows {len(rows)} of {H} kept ({diff})"); continue
    vals = {v for y in rows for v in rows[y]}
    hole = {(x, y) for y in rows for x, v in enumerate(rows[y]) if v.lower().endswith("ff203040")}
    for var, kw in (("halves", {}), ("halves+nogate", {"bit29_gate": False})):
        out = mm.predict(mm.tri_full(W, H), W, H, mode, te, **kw)
        miss = {(x, y) for x in range(W) for y in range(H) if (x, y) not in out}
        print(f"{n} m{mode} te {te:#010x} {var}: hw holes {len(hole)} model {len(miss)} equal {miss == hole} values {len(vals)} | {diff}")
