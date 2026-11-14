# SPDX-License-Identifier: MIT
"""fold/readall.py: POST HOC (r15-dpm fold, 2026-11-14), outside the freeze. Every kept pr4 job's
0x0748 clear runs: PR (the row's label), lines, the clear values, each run's start (ns after the
command's start) and width (ns), and the pooled counts against the partial renders.

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
tot_pr = tot_pul = 0
widths = []
for f in sorted((d / "pr4").glob("pr4-c*.txt.gz"), key=lambda p: p.name):
    n = f.name[:-7]
    pr = int(n.split("-")[1][1:])
    text = gzip.open(f, "rt", errors="replace").read()
    regs, rows, start, end, samples = R.parse(text)
    rd = R.reading(text)
    vals = collections.Counter(v[0x748] for t, v in rows if t >= start and not v[0x748] & 4)
    starts = [t - start for i, (t, v) in enumerate(rows)
              if t >= start and not v[0x748] & 4 and (i == 0 or rows[i - 1][1][0x748] & 4)]
    print(f"{n}: PR {pr} lines {len(rows)} period {rd['period']} ns pulses {rd['pulses']} "
          f"starts(ns after start) {starts} widths {rd['widths']} clear values "
          + (", ".join(f"0x{v:x} x{c}" for v, c in sorted(vals.items())) or "none"))
    tot_pr += pr
    tot_pul += rd["pulses"]
    widths += rd["widths"]
print(f"pooled: {tot_pul} pulses over {tot_pr} partial renders (0.49 a partial render; E1032 0.07, "
      f"E1019 0.17); widths {min(widths)}..{max(widths)} ns, mean {sum(widths) / len(widths):.0f} "
      f"(period about 1680 ns: 2.4 samples)")
