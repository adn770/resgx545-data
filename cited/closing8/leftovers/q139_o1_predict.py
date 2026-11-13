#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""q139_o1_predict.py (round 8 planning, leftovers; offline, no run).
Step 1 of the offline held-out test of Q139's write order: for every job of resgx545-data
ta/mtile-fields and ta/mtile-fields-risky (cases.tsv only: NO dump or image is opened here) that
round 7's q139 stage did NOT re-run with a dump, the set of target tiles with no surviving region
header under R7-BLK's slot rule (render/closing-r7-rp/fold/q139_fit.py, imported from its published
copy) and five write orders (fold/q139_order_posthoc.py's keys, copied verbatim).  H-PRESENT (E907):
a tile is wrong iff no header names it.  Writes q139_o1_pred.json; its sha256 is taken before
q139_o1_score.py opens any image.

  python3 -I -B q139_o1_predict.py DATA_REPO OUT.json
"""
import json, os, re, sys
data = sys.argv[1]
sys.path.insert(0, os.path.join(data, "render/closing-r7-rp/fold"))
import q139_fit as F
KEYS = {"raster": lambda r, c, mc, mr, n: (r, c), "N": lambda r, c, mc, mr, n: (mc * n + mr, r, c),
        "rowblk": lambda r, c, mc, mr, n: (r >> 2, c >> 2, r, c),
        "blkcol": lambda r, c, mc, mr, n: (r >> 2, c >> 2, r & 3, c & 3),
        "pair": lambda r, c, mc, mr, n: (r >> 1, c, r)}
def predict(w, h, args, key):
    tx, ty = F.cdiv(w, 32), F.cdiv(h, 16); m1, m2, s = F.words(w, h, args); n, bx, by = F.bounds(m1, m2)
    fx, fy = bx[1], by[1]; ws = []
    for r in range(max(ty, by[-1] + fy)):
        for c in range(max(tx, bx[-1] + fx)):
            mcol, lx = F.place(c, bx); mrow, ly = F.place(r, by)
            sl = (mcol * n + mrow) * s + ((ly >> 2) * (fx >> 2) + (lx >> 2)) * 16 + (r & 3) * 4 + (c & 3)
            ws.append((key(r, c, mcol, mrow, n), sl, (c, r)))
    ws.sort(key=lambda t: t[0]); own = {}
    for _, sl, t in ws: own[sl] = t
    drawn = {t for t in own.values() if t[0] < tx and t[1] < ty}
    return sorted("%d.%d" % (c, r) for r in range(ty) for c in range(tx) if (c, r) not in drawn)
rerun = set()
for ln in open(os.path.join(data, "render/closing-r7-rp/tables/q139.txt")):
    if ln.startswith("#") or not ln.strip(): continue
    nm = ln.split("|")[0]
    rerun.add(re.sub(r"^q139-[a-z]-", "", nm))
out = {}; skipped = []
for ds in ("ta/mtile-fields", "ta/mtile-fields-risky"):
    with open(os.path.join(data, ds, "cases.tsv")) as f:
        hdr = next(f)
        for line in f:
            p = line.rstrip("\n").split("\t"); name, w, h = p[0], int(p[2]), int(p[3]); args = p[4] if len(p) > 4 else ""
            short = re.sub(r"^q100-", "", name)
            if short in rerun or re.sub(r"-r\d+$", "", short) in rerun: skipped.append(name); continue
            try:
                pokes = re.findall(r"ta:(\d+)=", args)
                if any(i not in ("143", "144", "146") for i in pokes): out[ds + ":" + name] = {"refused": "another poke"}; continue
                m1, m2, s = F.words(w, h, args); n, bx, by = F.bounds(m1, m2)
                if bx[1] <= 0 or by[1] <= 0: out[ds + ":" + name] = {"refused": "a first macrotile of width 0"}; continue
                if max(bx[-1] + bx[1], by[-1] + by[1]) > 1024: out[ds + ":" + name] = {"refused": "too large"}; continue
                out[ds + ":" + name] = {"w": w, "h": h, "args": args, "wrong": {k: predict(w, h, args, f) for k, f in KEYS.items()}}
            except Exception as e:
                out[ds + ":" + name] = {"refused": repr(e)}
json.dump({"model": "R7-BLK slots, five write orders, H-PRESENT", "skipped_rerun": sorted(skipped), "cases": out},
          open(sys.argv[2], "w"), indent=0, sort_keys=True)
print("cases predicted", sum(1 for v in out.values() if "wrong" in v), "refused", sum(1 for v in out.values() if "refused" in v),
      "skipped (re-run with a dump in r7-rp)", len(skipped))
