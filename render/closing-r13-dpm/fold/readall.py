# SPDX-License-Identifier: MIT
# POST HOC (written after the score was read): per row the partial renders, timeline lines, bit 2
# clear lines, global pages, and the log-loss terms of E1019's three per-job forms.
import gzip, math, pathlib, sys
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "gen")]
import read as R, plan as PL  # noqa: E402,E401
ATT = KP / "out/20261113-212348/pr2"
ll = lambda p, y: -math.log(min(.99, max(.01, p)) if y else 1 - min(.99, max(.01, p)))  # noqa: E731
tot = dict.fromkeys(("R-PR", "R-LEN", "CONST"), 0.0)
print("row PR lines clr G | -ln p(R-PR) -ln p(R-LEN) -ln p(CONST)")
for r in PL.rows():
    rd = R.reading(gzip.open(ATT / (r["name"] + ".txt.gz"), "rt").read())
    y = rd["clr"] > 0
    t = (ll(1 - math.exp(-PL.R_PR * r["pr"]), y), ll(1 - (1 - PL.Q_LEN) ** rd["n"], y), ll(PL.F_CONST, y))
    for k, v in zip(tot, t):
        tot[k] += v
    print(r["name"], rd["nparts"], rd["n"], rd["clr"], rd["gmax"], "|", " ".join(f"{v:.2f}" for v in t))
print("total", " ".join(f"{k} {v:.2f}" for k, v in tot.items()))
