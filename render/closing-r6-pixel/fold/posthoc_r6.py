# SPDX-License-Identifier: MIT
"""R6-pixel fold, 2026-11-12: post hoc readings of the kept files (added at the fold, not by the run; nothing here is held out).

A. p6-rd (frozen verdict cannot tell: no rd entry reached the frozen 90 percent of TRI in both jobs).  For every readback
   configuration: each job's own-pixel labels over TRI (the frozen scorer's reader, score_rd.job_labels), the share of the top
   label, the name the frozen labels give it (S, A0, A4 of rdmodel.labels) and the share of the top label among the TRI pixels
   whose word decodes to the pixel itself (the "D" words, the job's marker from another source, left out), and the D words by
   tag and bits.
B. p6-rd's predicate rows (scored by design only if rd-j read S): the top label of each lane in each job and its share.
C. g6-rw: every word of score-g6-rw.txt by set, the 24-bit mantissa M of w, frac(M) = the fraction of 2^47 / M and the delta;
   the new mantissas (L and B) with frac >= 0.5 and their delta, the table sgx-pipe takes beside H-FRAC.
Run from the session directory (the frozen scorer's modules are imported from score/, unchanged):
  RESGX545_MAIN=<resgx545 at d9b2969> python -I fold/posthoc_r6.py > fold/posthoc_r6.txt"""
import collections
import pathlib
import re
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
SESSION = HERE.parent
sys.path.insert(0, str(SESSION / "score"))
import r4lib as L  # noqa: E402
import rdmodel as RM  # noqa: E402
import score_rd as SR  # noqa: E402

ATT = SESSION / "out/20261112-142113"

# ---------------------------------------------------------------- A
print("A. p6-rd readback configurations: own-pixel labels over TRI (post hoc)")
k = L.Kept(ATT / "p6-rd")
preds = L.load_preds(stage="p6-rd")
tri, why = SR.tri_of(k, preds)
n = len(tri)
print(f"TRI: {n} pixels")
cfgs = [f"rd-{j}" for j in RM.RD_J] + ["n-rd-1", "n-rd-4", "x-rd-4", "x-rd-5", "rd-4 (replicate)"]
vec = []
for cfg in cfgs:
    base = cfg.split()[0]
    xn, yn = (f"{base}-x-rep", f"{base}-y-rep") if "replicate" in cfg else (f"{base}-x", f"{base}-y")
    g, why = SR.grids(k, base, xn, yn)
    names = {v: c for c, v in RM.labels(base).items()}
    m = SR.marker_of(preds, base)
    cs = SR.job_labels(g, tri, m)
    row = []
    for ax, c in zip("xy", cs):
        top, v = c.most_common(1)[0]
        own = sum(x for lab, x in c.items() if ":" in lab and not lab.startswith("O:"))
        row.append(f"{ax} {top} ({names.get(top, 'none of S/A0/A4')}) {v}/{n} = {v / n:.3f}, of own-source {v}/{own} = {(v / own if own else 0):.3f}, "
                   f"D {c.get('D', 0)}, top four {dict(c.most_common(4))}")
    tops = {c.most_common(1)[0][0] for c in cs}
    lab = tops.pop() if len(tops) == 1 else None
    if base.startswith("rd-") and "replicate" not in cfg:
        vec.append(names.get(lab, lab))
    print(f"{cfg:18s} " + "; ".join(row))
    dt = []
    for gg, ax, mm in ((g[0], "x", m), (g[1], "y", m + 1)):
        c = collections.Counter()
        for x, y in tri:
            v = gg[y][x]
            if SR.own_label(v, x, y, ax, mm) == "D":
                c[f"{v & 15}:{(v >> 4) & 3}"] += 1
        dt.append(f"{ax} {dict(c.most_common(5))}")
    print(f"{'':18s} D words by tag:bits: " + "; ".join(dt))
print("labels of the rd-j configurations (rdmodel.labels): " + "; ".join(f"rd-{j} " + ", ".join(f"{c}={v}" for c, v in RM.labels(f'rd-{j}').items())
                                                                   for j in RM.RD_J))
print("post hoc vector of the top labels, j = 1..7: " + " ".join(str(v) for v in vec))
for mdl in RM.MODELS:
    fv = RM.rd_vector(mdl)
    print(f"  {mdl:8s} frozen {' '.join(fv)}: {'matches' if all(RM.matches(f, r) for f, r in zip(fv, vec)) else 'differs'}")

# ---------------------------------------------------------------- B
print()
print("B. p6-rd predicate rows and c-prd-0: top label of each lane (lane = (x & 1) | (y & 1) << 1), share in the x / y job (post hoc)")
for cfg in [f"c-prd-0-k{kk}" for kk in RM.CPRD_K] + [f"prd-{j}-k{kk}" for j in RM.PRD_J for kk in RM.PRD_K]:
    g, why = SR.grids(k, cfg)
    m = SR.marker_of(preds, cfg)
    cells = []
    for lane in range(4):
        px = [(x, y) for x, y in tri if RM.lane_of(x, y) == lane]
        cs = SR.job_labels(g, px, m)
        t = [c.most_common(1)[0] for c in cs]
        cells.append(f"{t[0][0]} {t[0][1] / len(px):.2f} / {t[1][0]} {t[1][1] / len(px):.2f}")
    fz = SR.frozen(preds, f"{cfg}-x", "lanes") if cfg.startswith("prd") else {}
    print(f"{cfg:12s} " + " | ".join(cells) + ("   frozen " + "; ".join(f"{a} {b}" for a, b in fz.items()) if fz else ""))

# ---------------------------------------------------------------- C
print()
print("C. g6-rw: the 1/w words by set and by frac(M) (post hoc)")
ROW = re.compile(r"(\S+)\s+(\d)\s+\S+\s+(0x[0-9a-f]{8})\s+(0x[0-9a-f]{8})\s+(0x[0-9a-f]{8})\s+(-?\d+)\s")
rows = [ROW.match(ln) for ln in (ATT / "score-g6-rw.txt").read_text().splitlines()]
rows = [r for r in rows if r]


def setof(name):
    return {"l": "L", "b": "B", "r": "replicate", "e": "E"}[name[0]]


tally = collections.defaultdict(collections.Counter)
newm = {}
for r in rows:
    M = (int(r[3], 16) & 0x7fffff) | 0x800000
    d = int(r[6])
    tally[setof(r[1])][d] += 1
    if setof(r[1]) in ("L", "B"):
        if M in newm and newm[M] != d:
            print(f"  mantissa {M:#08x} read with both deltas")
        newm[M] = d
for s, c in tally.items():
    print(f"{s}: {sum(c.values())} words, RZ {c[0]}, RZ + 1 {c[1]}")
print(f"all: {len(rows)} words, RZ + 1 {sum(c[1] for c in tally.values())}")
lo = [M for M in newm if F((1 << 47) % M, M) < F(1, 2)]
hi = sorted(M for M in newm if M not in lo)
print(f"new mantissas (L and B): {len(newm)}; frac < 0.5: {len(lo)}, RZ + 1 at {sum(newm[M] for M in lo)}; "
      f"frac >= 0.5: {len(hi)}, RZ + 1 at {sum(newm[M] for M in hi)}")
print("table for sgx-pipe (L and B, frac >= 0.5): 23-bit mantissa, delta, frac")
for M in hi:
    print(f"  {M & 0x7fffff:#08x} {newm[M]} {float(F((1 << 47) % M, M)):.4f}")
