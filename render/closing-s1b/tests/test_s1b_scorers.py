#!/usr/bin/env python3
"""The S1b scorers with the S1b frozen predictions, run on S1's kept data where the job names overlap (a dry run of the
readers: S1's data is the FIT of every '(S1 post hoc)' hypothesis, so agreement here shows only that the scorer reads
the data as S1's analysis did; it is no evidence).  Plus unit cases of the exact-render reader.  Prints ok/FAIL."""
import sys
sys.dont_write_bytecode = True     # the data repo's modules are imported: no __pycache__ there

import pathlib  # noqa: E402

S1B = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(S1B / "score"), str(S1B / "gen")]
import score_s1  # noqa: E402
import score_pix as P  # noqa: E402

OUT = pathlib.Path.home() / "src/scratch/resgx545/closing/s1/out"
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def summ(stage, d):
    t = score_s1.run_stage(stage, OUT / d)
    return t, next(ln for ln in t.splitlines() if ln.startswith("SUMMARY:"))


t, s = summ("p-d", "p-d")
check("p-d: S1's d-ok-64 is A4 at 64 pages pixel for pixel (the control and the A4 file's pixel order)",
      "d-ok-64" in t and "controls pass" in s, s[:120])
check("p-d: S1's 64- and 21-page images fit HB-A4 (post hoc fit, as the analysis read it: repeat only)",
      "repeat only: consistent ['HB-A4" in s, s[:200])
from s1lib import Kept, load_preds  # noqa: E402
pc = load_preds(None, "p-c")
for n in ("c-u-r2-x", "c-u-r2-y", "c-u-r3-x", "c-u-r3-y"):        # S1 ran c-u once
    pc.pop(n, None)
t = P.score_c(Kept(OUT / "p-c"), pc)[0]
s = next(ln for ln in t.splitlines() if ln.startswith("SUMMARY:"))
check("p-c: HQ consistent on S1 (its fit data: repeat only), the c-u cluster named, the replicate compared",
      "repeat only: consistent" in s and "HQ" in s.split("repeat only:")[1] and "the cluster of HCL" in t
      and "replicates c-k7-x-rep same" in s, s[:200])
t, s = summ("g-e3", "g-e3")
check("g-e3: S1's e3k-ctl passes the S1b control (HREP as measured) and e3z reads HC-poly (repeat only)",
      "e3k: held out" in s and "e3z: held out: consistent none, refuted none; repeat only: consistent ['HC-poly" in s, s[:300])
t, s = summ("g-e5", "g-e5")
check("g-e5: S1's a8 reads HL70 in 2 of 3, a12 HS1 2 of 2 (the S1 values the hypotheses came from)",
      "HL70 (S1 post hoc) in 2 of 3" in s and "r-n8-a12: HS1" in s, s[:300])
t, s = summ("g-e8b", "g-e8b")
check("g-e8b: S1 lacks the always control: cannot tell", "cannot tell" in s and "o-2-alw-far" in s, s[:160])
t, s = summ("p-f", "p-f")
check("p-f: S1 lacks f-dpm-0: cannot tell (controls come from the frozen rows)", "cannot tell" in s and "f-dpm-0" in s, s[:160])
# the exact-render reader
two_ovf = "diff: 0 of 786432 pixels\ndiff: 0 of 786432 pixels\ntri: 0 of 2 renders ok, 2 overflowed\n"
check("renders_exact: two exact partial renders under --keep-overflow", P.renders_exact(two_ovf, "tri -n 2 --keep-overflow"))
check("renders_exact: the same without --keep-overflow is not exact", not P.renders_exact(two_ovf, "tri -n 2"))
check("renders_exact: a non-zero diff is not exact",
      not P.renders_exact(two_ovf.replace("diff: 0", "diff: 5", 1), "tri -n 2 --keep-overflow"))
check("renders_exact: one diff line for two renders is not exact",
      not P.renders_exact("diff: 0 of 4096 pixels\ntri: 2 renders ok\n", "tri -n 2"))
check("renders_exact: `tri: 2 renders ok` with two diff 0", P.renders_exact("diff: 0 of 1\ndiff: 0 of 1\ntri: 2 renders ok\n", "tri -n 2"))
sys.exit(0 if ok else 1)
