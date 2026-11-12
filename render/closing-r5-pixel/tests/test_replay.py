#!/usr/bin/env python3
"""Round 5 addition (BRIEF-BUILD): every scorer replayed before the freeze on the kept round 4 files it must hold on and on the ones it
must fail on (plan section 6).  Kept files: tests/fixtures/r4-p4-o4 (R4 p4-o4, E838, attempt 20261111-205726) and r4-g4-rw (R4 g4-rw,
E842, attempt 20261111-210423) with R4's frozen predictions and R4's kept score file.
  o4: the new reader reads class A (5:0) for R4's c-v-a4 and bits 5:4 = 3 at every tag-5 word of c-e709-x; G-o4 passes on c-e709; the
      G-o1 control passes on R4's c-u; the displaced tag-1 count is 0 in R4's 17 configurations (the d1 class is free); a reader that
      looks for a wrong file name (R4's t slip) finds nothing on the same directory and is void, never a pass.
  1/w: the new scorer's word table on R4's kept dumps and R4's predictions equals R4's kept table byte for byte (42 words read, 18 not)
      and its shape reading FAILS rw-15..rw-20 (six FAILED shapes, the rest held); the viewport check flags exactly rw-15..rw-20 on
      R4's design and nothing on R5's 48 rows.
Prints ok / FAIL; exit 1 on any FAIL."""
import collections
import pathlib
import re
import sys

sys.dont_write_bytecode = True
R5 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R5 / "gen"), str(R5 / "score")]
import r4lib as L  # noqa: E402
import rwdesign as D4  # noqa: E402
import rwdesign5 as D  # noqa: E402
import score_o5 as S5  # noqa: E402
import score_rw5 as W  # noqa: E402
import scorekit as SK  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


FX = R5 / "tests/fixtures"
# ---------------------------------------------------------------- o4 on R4's p4-o4
k = L.Kept(FX / "r4-p4-o4")
p4 = L.load_preds(FX / "r4-p4-o4.preds.tsv")
r = S5.read_cfg(k, p4, "c-v-a4")
check("R4 c-v-a4 through the new reader: 5:0 (class A, E838)", not r["void"] and r["cls"] == "5:0", str(r.get("cls") or r.get("void")))
r = S5.read_cfg(k, p4, "c-e709")
b = collections.Counter((w >> 4) & 3 for row in r["gx"] for w in row if w != L.BG and (w & 15) == 5)
check("R4 c-e709-x: bits 5:4 = 3 at every tag-5 word (39 of 39)", dict(b) == {3: 39}, str(dict(b)))
text, res = S5.score(k, {**p4, "c-e709-x": p4["c-e709-x"]})
check("G-o4 on R4's c-e709 passes in the new scorer", res["controls"]["G-o4 c-e709"] is True, str(res["controls"]))
check("G-o1 on R4's c-u passes in the new scorer", res["controls"]["G-o1 c-u"] is True)
d1s = {}
for cfg in sorted({n.rsplit("-", 1)[0] for n in k.names() if n.endswith("-x")}):
    rr = S5.read_cfg(k, p4, cfg)
    if not rr["void"]:
        d1s[cfg] = rr["d1"]
check("displaced tag-1 pairs: 0 in every R4 configuration (17), so 10..100 of them is a reading no R4 job gives",
      len(d1s) == 17 and set(d1s.values()) == {0}, str(d1s))
check("every R4 marker configuration reads a decided label (none of them d1)", all(S5.read_cfg(k, p4, c)["cls"] not in (None, "d1") for c in d1s))


class WrongName(L.Kept):
    def out(self, name):                       # R4's t slip: a reader that looks for another file name
        return self._gz(f"{name}.out.gz").decode() if self._gz(f"{name}.out.gz") else None


r = S5.read_cfg(WrongName(FX / "r4-p4-o4"), p4, "c-v-a4")
check("a reader looking for a wrong file name finds nothing on R4's directory: void (cannot tell), never a pass", r["void"] == "no output kept", str(r))
text, res = S5.score(WrongName(FX / "r4-p4-o4"), p4)
check("  and the whole scorer then cannot tell (controls not passed)", not res["answered"] and "cannot tell" in text.splitlines()[-1])
# ---------------------------------------------------------------- 1/w on R4's g4-rw
kr = L.Kept(FX / "r4-g4-rw")
pr = L.load_preds(FX / "r4-g4-rw.preds.tsv")
split = {}
for q in ("FIT", "HELD_OUT"):
    for v, m, s in pr.get("@split", {}).get(q, []):
        split[int(v, 16)] = q.replace("_", " ")
names = [n for n in sorted(pr) if re.fullmatch(r"rw-\d\d", n)]
jobs, recs = W.word_records(kr, pr, names, split)
kept = (FX / "r4-g4-rw.score.txt").read_text().split("\n\n")[1]
mine = W.word_table(recs)
check("the new scorer's word table on R4's kept dumps equals R4's kept table byte for byte", mine == kept,
      "" if mine == kept else next((f"{a!r} != {b!r}" for a, b in zip(mine.splitlines(), kept.splitlines()) if a != b), "lengths differ"))
check("42 words read, 18 not", sum(1 for r in recs if r[4] is not None) == 42 and sum(1 for r in recs if r[4] is None) == 18)
fs = sorted(n for n, j in jobs.items() if j["shape"] is False)
check("six FAILED shapes, exactly rw-15..rw-20 (must fail), the other 14 held", fs == [f"rw-{i}" for i in range(15, 21)]
      and all(jobs[n]["shape"] is True for n in names if n not in fs), str(fs))
ctl, _ = W.controls(kr, pr)
check("R4's controls rw-k0..k3 pass in the new scorer (as kept: PASS x 4)", ctl == {f"rw-k{i}": True for i in range(4)}, str(ctl))
flag = [D4.job_params(i)["name"] for i in range(20) if not D.viewport_ok(D4.job_params(i)["w"])]
check("the viewport check flags exactly rw-15..rw-20 on R4's frozen design (the fixture that must fail)", flag == [f"rw-{i}" for i in range(15, 21)], str(flag))
check("the viewport check passes all 48 R5 rows (S scaling)", all(D.viewport_ok(p["w"], p["S"]) for p in D.all_rows()) and len(D.all_rows()) == 48)
sys.exit(0 if ok else 1)
