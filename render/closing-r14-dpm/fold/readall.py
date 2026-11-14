# SPDX-License-Identifier: MIT
"""fold/readall.py: POST HOC (r14-dpm fold, 2026-11-14), outside the freeze. The one job the stage
ran (pr3-c0-1, the first PR 0 control): its timeline's lines, distinct 0x0748 values, bit 2 and
the sampling period; and the period the plan's [check] expected, for comparison.

  python3 fold/readall.py ATTEMPT_DIR"""
import collections
import gzip
import pathlib
import sys

sys.dont_write_bytecode = True
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KP / "score"))
import read as R  # noqa: E402

d = pathlib.Path(sys.argv[1])
text = gzip.open(d / "pr3/pr3-c0-1.txt.gz", "rt", errors="replace").read()
regs, rows, start, end, samples = R.parse(text)
rd = R.reading(text)
vals = collections.Counter(v[0x748] for _, v in rows)
print(f"pr3-c0-1: regs {[hex(r) for r in regs]} samples {samples} start {start} end {end} lines {len(rows)}")
print(f"period end/samples {rd['period']} ns (frozen premise: at most {R.SHORT_NS} ns, expected 460 ns)")
print("0x0748 values: " + ", ".join(f"0x{v:x} x{n}" for v, n in sorted(vals.items())))
print(f"bit 2 clear lines {rd['clr']}, pulses {rd['pulses']} (bit 2 set in every line: "
      f"{all(v[0x748] & 4 for _, v in rows)})")
print(f"lines before the command's start {sum(1 for t, _ in rows if t < start)}, after "
      f"{sum(1 for t, _ in rows if t >= start)}; first line after start at {next(t for t, _ in rows if t >= start)} ns")
print("kept 16-register jobs (r13-dpm): 7.4 to 7.6 us; 1 register here 1682 ns: a floor near 1.3 us "
      "plus about 0.4 us a register (16 x 0.39 + 1.29 = 7.5), not 0.46 us a register")
