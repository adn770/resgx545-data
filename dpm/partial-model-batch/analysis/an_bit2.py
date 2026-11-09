#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39 P7: 0x0748 bit 2 in every job whose timeline kept 0x0748: lines with the bit clear, the number of
stretches, the gap between lines (median), by job, and by (cell, reset before the job or not)."""
import collections, os, re, statistics, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "recompute-b"))
import recompute_p1139b as r

cs = r.load_cases(sys.argv[1])
rows = []
for n, c in cs.items():
    k = r.Case(n, c)
    if not k.tl:
        continue
    m = re.search(r"^timeline: regs (.*?) samples", k.tl, re.M)
    regs = m.group(1).split()
    if "0x0748" not in regs:
        continue
    ix = regs.index("0x0748")
    ts, vs = [], []
    for l in k.tl.splitlines():
        if l.startswith("tl "):
            f = l.split()
            ts.append(int(f[1])); vs.append(int(f[2 + ix], 16))
    clr = [i for i, v in enumerate(vs) if v & 4 == 0]
    st = sum(1 for i in clr if i == 0 or (vs[i - 1] & 4))
    gaps = [b - a for a, b in zip(ts, ts[1:]) if b - a < 100000]
    dur = []
    for i in clr:
        if i + 1 < len(ts):
            dur.append(ts[i + 1] - ts[i])
    reset = "noreset" not in c["knobs"]
    rows.append((n, c["P"], len(vs), len(clr), st, statistics.median(gaps) if gaps else 0, max(dur) if dur else 0, reset, sorted({v for v in vs}) ))
print("case\tP\tlines\tclear_lines\tstretches\tmedian_gap_ns\tmax_clear_ns\treset_before\tvalues")
for x in rows:
    print("\t".join(str(y) if not isinstance(y, list) else " ".join("%x" % z for z in y) for y in x))
agg = collections.defaultdict(lambda: [0, 0])
for n, P, ln, cl, st, g, d, rs, v in rows:
    key = (re.sub(r"-\d+$", "", n) if n.startswith("wd-bit2") else n.split("-")[0] + "-" + P, rs)
    agg[key][0] += 1
    agg[key][1] += cl > 0
print()
for k, (a, b) in sorted(agg.items(), key=str):
    print(f"{k[0]}\treset={k[1]}\t{b} of {a} jobs with a clear line")
