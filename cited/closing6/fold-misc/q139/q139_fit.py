# Q139 offline macrotile test, step 1 (fit): reads ONLY the safe dataset
# (resgx545-data ta/mtile-fields), scores R-CELL and every R-SLOT variant of q139_model.py on its
# jobs with a full image (exact and wrong), and freezes the variant with the most jobs matched
# exactly (tie: the first in VARIANTS order) into q139_frozen.txt. Usage:
#   python3 q139_fit.py DATA/ta/mtile-fields > q139_fit.out
import os
import sys

import q139_model as M

ds = sys.argv[1]
jobs = []
for name, st, w, h, args in M.cases(ds):
    p = f"{ds}/dumps/{name}.txt.gz"
    if not os.path.exists(p):
        continue
    W, H, job, bad = M.load(p)
    if bad is None:
        continue
    jobs.append((name, st, w, h, M.words(w, h, args), bad))
wrong = [j for j in jobs if j[5]]
print(f"safe dataset: {len(jobs)} jobs with a full image, {len(wrong)} wrong, "
      f"{len(jobs) - len(wrong)} exact")
cons = [j[0] for j in wrong if M.union_of_cells(j[5], M.cells(j[2], j[3], j[4][0], j[4][1]))]
print(f"R-CELL: {len(cons)} of {len(wrong)} wrong images are unions of cells; not: "
      + " ".join(j[0] for j in wrong if j[0] not in cons))
best = None
for v in M.VARIANTS:
    hit = hitw = 0
    miss = []
    for name, st, w, h, (m1, m2, s), bad in jobs:
        pr = M.predict(w, h, m1, m2, s, v)
        if pr == bad:
            hit += 1
            hitw += bool(bad)
        else:
            miss.append(name)
    print(f"R-SLOT {M.vname(v)}: {hit} of {len(jobs)} (wrong {hitw} of {len(wrong)}) "
          f"misses: {' '.join(miss[:6])}{' ...' if len(miss) > 6 else ''}")
    if best is None or hit > best[0]:
        best = (hit, v)
print(f"frozen: {M.vname(best[1])} ({best[0]} of {len(jobs)})")
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "q139_frozen.txt"), "w") as f:
    f.write(M.vname(best[1]) + "\n")
