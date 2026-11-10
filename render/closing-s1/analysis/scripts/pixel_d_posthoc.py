"""POST HOC: p-d observed image hashes against every hypothesis hash in E722's cases.json; images compared between
jobs of the same program; the dword-index range read (0xD0000000 | i fill).  Not frozen."""
import json, pathlib, sys
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score"))
from s1lib import Kept, rows_of, pixel_sha
k = Kept(S1 / "out" / "p-d")
cj = {c["name"]: c for c in json.load(open(pathlib.Path.home() / "src/resgx545-data/texture/p1141/gen/cases.json"))}
lab = {"d-ok-64": "ad-tw128x32-L0e2", "d-L2e2-64": "ad-tw64x64-L2e2", "d-L3e3-64": "ad-tw64x64-L3e3",
       "d-st-L3e2-64": "ad-st128x32-L3e2", "d-L2e2-21": "ad-tw64x64-L2e2", "d-L2e2-20": "ad-tw64x64-L2e2"}
imgs = {}
for n, l in lab.items():
    r = rows_of(k.out(n))
    a = np.array(r, dtype=np.int64)
    imgs[n] = a
    sha = pixel_sha(r)
    hit = [h for h, v in cj[l]["preds"].items() if v == sha]
    tagged = a[(a >> 28) == 0xD]
    idx = tagged & 0x0FFFFFFF
    print(f"{n}: {a.shape} sha {sha[:12]} matches {hit or 'no hypothesis'}; tagged {len(tagged)}/{a.size}; "
          f"index range {idx.min() if len(idx) else '-'}..{idx.max() if len(idx) else '-'} (dwords) = bytes "
          f"{(idx.min() * 4) if len(idx) else '-'}..{(idx.max() * 4 + 3) if len(idx) else '-'}")
    print(f"   distinct {len(np.unique(a))}; A4 hash {cj[l]['preds']['A4'][:12]}")
print("d-L2e2-64 == d-L2e2-21:", np.array_equal(imgs["d-L2e2-64"], imgs["d-L2e2-21"]))
d = imgs["d-L2e2-20"]; e = imgs["d-L2e2-64"]
print("d-L2e2-20 low 28 bits == d-L2e2-64 index - 0x5000:", np.array_equal(d & 0x0FFFFFFF, (e & 0x0FFFFFFF) - 0x5000),
      "; d-L2e2-20 high nibble values", np.unique(d >> 28))
