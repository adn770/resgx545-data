# Q139 offline macrotile test, step 2 (score): checks the freeze (q139_FROZEN.sha256: the model,
# both scripts, the fit's output and the frozen variant), then reads the risky dataset
# (resgx545-data ta/mtile-fields-risky) for the first time and scores the frozen R-SLOT variant
# and R-CELL on its jobs with a full image. Usage:
#   python3 q139_score.py DATA/ta/mtile-fields-risky > q139_score.out
# Verdicts, fixed before the risky images were read:
#   H-SLOT (the frozen variant): held iff its predicted set of undrawn tiles equals the observed
#     wrong-tile set in every scored job (exact images included: predicted empty); FAILED otherwise.
#   R-CELL: held iff every wrong image's wrong tiles are a union of its cells; FAILED otherwise
#     (it already fails 3 of the 8 safe wrong images, q139_fit.out).
# The section "post hoc" after the verdicts scores every variant; it is not a verdict.
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for line in open(os.path.join(HERE, "q139_FROZEN.sha256")):
    h, name = line.split()
    got = hashlib.sha256(open(os.path.join(HERE, name), "rb").read()).hexdigest()
    if got != h:
        sys.exit(f"freeze broken: {name}")
print("freeze verified:", sum(1 for _ in open(os.path.join(HERE, "q139_FROZEN.sha256"))), "files")
sys.path.insert(0, HERE)
import q139_model as M  # noqa: E402

frozen = open(os.path.join(HERE, "q139_frozen.txt")).read().strip()
fv = next(v for v in M.VARIANTS if M.vname(v) == frozen)
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
print(f"risky dataset: {len(jobs)} jobs with a full image, {len(wrong)} wrong, "
      f"{len(jobs) - len(wrong)} exact")
print(f"frozen R-SLOT variant: {frozen}")
by = {}
misses = []
for name, st, w, h, (m1, m2, s), bad in jobs:
    pr = M.predict(w, h, m1, m2, s, fv)
    ok = pr == bad
    k = (st, "wrong" if bad else "exact")
    a, b = by.get(k, (0, 0))
    by[k] = (a + ok, b + 1)
    if not ok:
        misses.append((name, st, len(bad), None if pr is None else len(pr),
                       None if pr is None else len(pr & bad)))
for k in sorted(by):
    print(f"  {k[0]} {k[1]}: {by[k][0]} of {by[k][1]} predicted exactly")
tot = sum(a for a, _ in by.values())
print(f"H-SLOT: {'held' if tot == len(jobs) else 'FAILED'} ({tot} of {len(jobs)} jobs)")
for m in misses:
    print(f"  miss {m[0]} ({m[1]}): observed {m[2]} tiles, predicted {m[3]}, common {m[4]}")
cons = [j for j in wrong if M.union_of_cells(j[5], M.cells(j[2], j[3], j[4][0], j[4][1]))]
print(f"R-CELL: {'held' if len(cons) == len(wrong) else 'FAILED'} ({len(cons)} of {len(wrong)} "
      f"wrong images are unions of cells)")
print("post hoc (not a verdict): every variant on the risky jobs")
for v in M.VARIANTS:
    hit = sum(M.predict(w, h, m1, m2, s, v) == bad for _, _, w, h, (m1, m2, s), bad in jobs)
    print(f"  {M.vname(v)}: {hit} of {len(jobs)}")
