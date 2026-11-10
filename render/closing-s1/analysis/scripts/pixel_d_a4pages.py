"""POST HOC: E722's A4 model (recompute/tex2.py, options of cat1141.py's A4) re-rendered with the scratch pages of
each S1 job (spec['pages'] = 64, 21, 20) instead of the 16 that cases.json assumed; compared with the observed image.
Not frozen.  Runs the data repo's own model read-only."""
import json, pathlib, sys
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
P1141 = pathlib.Path.home() / "src/resgx545-data/texture/p1141"
sys.path.insert(0, str(P1141 / "recompute")); sys.path.insert(0, str(P1141 / "support"))
sys.path.insert(0, str(S1 / "score"))
import tex2
from s1lib import Kept, rows_of
k = Kept(S1 / "out" / "p-d")
cj = {c["name"]: c for c in json.load(open(P1141 / "gen/cases.json"))}
jobs = [("d-ok-64", "ad-tw128x32-L0e2", 64), ("d-L2e2-64", "ad-tw64x64-L2e2", 64), ("d-L3e3-64", "ad-tw64x64-L3e3", 64),
        ("d-st-L3e2-64", "ad-st128x32-L3e2", 64), ("d-L2e2-21", "ad-tw64x64-L2e2", 21), ("d-L2e2-20", "ad-tw64x64-L2e2", 20)]
for n, lab, pages in jobs:
    obs = np.array(rows_of(k.out(n)), dtype=np.int64).ravel()
    for hn, opt in (("A4", {}), ("A4 stride chain", {"t3chain": "stride"}), ("A4 shift idx only", {"t3e": "idx"})):
        spec = dict(cj[lab]["spec"]); spec["pages"] = pages
        px = tex2.predict(spec, {"t3off": "pre"}, t3model=True, **opt)
        px = np.array(px, dtype=np.int64)
        oob = int((px == 0xDEADBEEF).sum())
        print(f"{n:13s} {hn:18s} pages {pages}: equal {int((px == obs).sum())}/2048, model OOB {oob}")
