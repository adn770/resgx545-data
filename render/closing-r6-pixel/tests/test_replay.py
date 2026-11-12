#!/usr/bin/env python3
"""Round 6 rule (BRIEF-BUILD): every scorer replayed before the freeze on kept files it must hold on and on ones it must fail on
(plan section 5).  Kept files: R5's published session (render/closing-r5-pixel, attempt 20261112-091752: p5-o4 = E858, g5-rwa and
g5-rw = E859) with R5's frozen predictions.
  p6-rd's reader on R5's walk: w-1..w-7 put o0's word (1:2) on the own pixel, so the readback reader must read A0 there and NOT S
      (TRI taken from R5's w-0 own tag-1 words); R5's c-e709, c-u and c-all4 pass G-o4, G-o1 and 5:1 through the new control code;
      a reader looking for a wrong file name (R4's t slip) is void, never a pass.
  p6-l3's job reader on R5's p3-pa-k0 / -k3: x 5:0 / y 5:1 and 5:1 / 5:1 (must hold), and k0 read as k3 must fail.
  p6-s's setup pattern on R5's plain c-all4 must FAIL (the plain job shows tags 2 to 4); G-o1 on R5's c-u as the restore check holds.
  g6-rw: R5's word table on R5's kept dumps and R5's predictions is reproduced byte for byte (126 words); the g6-rwa control scorer
      passes R5's rw-k0..k5 and d-01, d-02 (the same programs) on R5's kept dumps; a known word changed by one ulp must fail; the
      window reader on R5's FIT words (the dense table's half read before) gives the separability it must, and an inverted
      fixture must fail.
Prints ok / FAIL; exit 1 on any FAIL."""
import collections
import pathlib
import re
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True
R6 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R6 / "gen"), str(R6 / "score")]
import r4lib as L  # noqa: E402
import rdmodel as RM  # noqa: E402
import rwdesign6 as D  # noqa: E402
import score_rd as S  # noqa: E402
import score_rw5 as W5  # noqa: E402
import score_rw6 as W  # noqa: E402

ok = True
R5P = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r5-pixel")
O5 = R5P / "out/20261112-091752"


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


k5 = L.Kept(O5 / "p5-o4")
p5 = L.load_preds(R5P / "predictions/p5-o4.tsv")
# TRI from R5's w-0: the own tag-1 words of both jobs (marker, source the pixel)
g, why = S.grids(k5, "w-0")
m0 = S.marker_of(p5, "w-0")
tri = [(x, y) for y in range(64) for x in range(64)
       if S.own_label(g[0][y][x], x, y, "x", m0).startswith("1:") and S.own_label(g[1][y][x], x, y, "y", m0 + 1).startswith("1:")]
check("TRI from R5's w-0 (own tag-1 words in both jobs): >= 300 pixels", len(tri) >= 300, str(len(tri)))
reads = {}
for j in range(1, 8):
    pp = dict(p5)
    pp[f"w-{j}-x"] = dict(p5[f"w-{j}-x"])
    pp[f"w-{j}-x"]["labels"] = [(f"S={RM.TAG[j]}:1 A0=1:2", "", "")]
    r = S.read_rd(k5, pp, f"w-{j}", tri)
    reads[j] = r["cls"]
check("the readback reader on R5's walk w-1..w-7 (no readback in R5): A0 at every j, never S (must hold)", all(v == "A0" for v in reads.values()), str(reads))
out = []
ctl = S.r5_controls(k5, {**p5, "c-u-x": p5["c-u-x"]}, out)
check("R5's c-e709 passes G-o4 and c-u passes G-o1 through the new control code (must hold)", ctl == {"G-o4 c-e709": True, "G-o1 c-u": True}, str(ctl))
import score_o5 as S5  # noqa: E402
r = S5.read_cfg(k5, p5, "c-all4")
check("R5's c-all4 reads 5:1 (must hold: the p6-rd control's frozen value)", r["cls"] == "5:1", str(r.get("cls")))


class WrongName(L.Kept):
    def out(self, name):                       # R4's t slip: a reader that looks for another file name
        return self._gz(f"{name}.out.gz").decode() if self._gz(f"{name}.out.gz") else None


r = S.read_rd(WrongName(O5 / "p5-o4"), pp, "w-4", tri)
check("a reader looking for a wrong file name on R5's directory: void (cannot tell), never a pass", r["void"] == "no output kept", str(r))
# ---- L3
obs = {}
for kk in (0, 3):
    r = S5.read_cfg(k5, p5, f"p3-pa-k{kk}")
    obs[kk] = (S.job_label(r["cx"]), S.job_label(r["cy"]))
check("p6-l3's job reader on R5's p3-pa-k0 / k3: x 5:0 / y 5:1 and 5:1 / 5:1 (must hold)", obs == {0: ("5:0", "5:1"), 3: ("5:1", "5:1")}, str(obs))
check("  and k0 read against k3's frozen labels fails (must fail)", obs[0] != ("5:1", "5:1"))
# ---- S: the setup pattern on the plain c-all4 must fail; G-o1 on R5's c-u as the restore check
g, why = S.grids(k5, "c-all4")
m = S.marker_of(p5, "c-all4")
cs = [S.tag_counts(g[0], m), S.tag_counts(g[1], m + 1)]
patt = all(sum(c[t] for t in (2, 3, 4)) <= 2 and c[5] >= 10 for c in cs)
check("E406's setup pattern on R5's plain c-all4: FAILS (tags 2 to 4 on other pixels: the set-void rule can fire)", patt is False, str([dict(c) for c in cs]))
pr = dict(p5)
pr["r-u-x"] = p5["c-u-x"]


class Renamed(L.Kept):
    def out(self, name):
        return super().out(name.replace("r-u-", "c-u-"))

    def case(self, name):
        return super().case(name.replace("r-u-", "c-u-"))

    def void(self, name, dumps=()):
        return super().void(name.replace("r-u-", "c-u-"), dumps)


out = []
ctl = S.r5_controls(Renamed(O5 / "p5-o4"), pr, out, restore="r-u")
check("the restore check's G-o1 on R5's c-u (read as r-u): PASS (must hold)", ctl == {"G-o1 r-u": True}, str(ctl))
# ---- g6-rw on R5's kept g5-rw / g5-rwa
pw = L.load_preds(R5P / "predictions/g5-rw.tsv")
pwa = L.load_preds(R5P / "predictions/g5-rwa.tsv")
ka, kb = L.Kept(O5 / "g5-rwa"), L.Kept(O5 / "g5-rw")
both = W5.Both(ka, kb)
allp = collections.defaultdict(lambda: collections.defaultdict(list))
for pp_ in (pw, pwa):
    for c, qs in pp_.items():
        for q, v in qs.items():
            allp[c][q] += v
split = {}
for q in ("FIT", "HELD_OUT"):
    for v, mm, s in pw.get("@split", {}).get(q, []):
        split[int(v, 16)] = q.replace("_", " ")
names = [n for n in allp if not n.startswith(("rw-k", "@"))]
names.sort(key=lambda n: ({"q": 0, "m": 1, "r": 2, "d": 3}[n[0]], n))
jobs, recs = W5.word_records(both, allp, names, split)
kept = (O5 / "score-g5-rw.txt").read_text().split("\n\n")[1]
mine = W5.word_table(recs)
check("R5's word table reproduced byte for byte on R5's kept dumps (126 words, must hold)", mine == kept and sum(1 for r in recs if r[4] is not None) == 126,
      "" if mine == kept else next((f"{a!r} != {b!r}" for a, b in zip(mine.splitlines(), kept.splitlines()) if a != b), "lengths differ"))
p6a = L.load_preds(stage="g6-rwa")
ctl, _ = W.controls(both, p6a)
check("the g6-rwa control scorer passes R5's kept rw-k0..k5 and d-01, d-02 (the same programs, the same words: must hold)",
      ctl == {n: True for n in ["d-01", "d-02"] + [f"rw-k{i}" for i in range(6)]}, str(ctl))
bad = {c: dict(q) for c, q in p6a.items()}
v = bad["d-01"]["rhw_known"][0]
bad["d-01"]["rhw_known"] = [("0x407c0fc0," + v[0].split(",", 1)[1], v[1], v[2])]
ctl, _ = W.controls(both, bad)
check("  with d-01's RZ + 1 word frozen as RZ the control FAILS (must fail)", ctl["d-01"] is False)
# ---- the window reader on kept words: R5's FIT words (read before) as a window
fit = [(D.frac(D.mant(r[2])), r[4] - r[3]) for r in recs if r[0].startswith("d-") and r[5] == "FIT" and r[4] is not None]
st, txt = W.window_state(fit)
check("the window reader on R5's 30 FIT dense words: cannot tell (fewer than 30 words is the frozen floor) or a decided state, never an error",
      st in (None, True, False), txt)
fx = [(F(i, 40) + F(1, 80), int(i >= 30)) for i in range(40)]
check("a separable fixture (RZ + 1 exactly above frac 0.75) is separable: e in [0.24, 0.25)", W.window_state(fx)[0] is True, W.window_state(fx)[1])
fx2 = fx[:]
fx2[25] = (fx2[25][0], 1)
check("  one RZ + 1 word below an RZ word above 0.5: an inversion (must fail)", W.window_state(fx2)[0] is False, W.window_state(fx2)[1])
sys.exit(0 if ok else 1)
