#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""posthoc.py ATT: r31-kreg2's k2 readings after the run (POST HOC, no verdict): why BOUND2 went
over its cap (s0's v1-v8 spread, the per-render noise within a job, drift over the stage), the
k2 controls, and every value's two medians against the controls' median. Reads the kept
.txt.gz files of ATT (out/ATTEMPT) only; prints to stdout."""
import gzip
import os
import re
import statistics as st
import sys

TIME = re.compile(r"^tri \d+x\d+ #\d+: (\d+) us$")


def renders(path):
    with gzip.open(path, "rt") as f:
        return [int(m[1]) for m in map(TIME.match, f.read().splitlines()) if m]


def med(xs):
    s, n = sorted(xs), len(xs)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2


def iqr_pct(xs):
    q = st.quantiles(xs, n=4, method="inclusive")
    return (q[2] - q[0]) / st.median(xs) * 100


def main(att):
    s0 = {f"v{i}": renders(os.path.join(att, "s0", f"v{i}.txt.gz")) for i in range(1, 9)}
    k2d = os.path.join(att, "k2")
    rows = sorted(n[:-7] for n in os.listdir(k2d)
                  if re.fullmatch(r"([ab][0-9a-f]{2}|c\d\d)\.txt\.gz", n))
    k2 = {n: renders(os.path.join(k2d, n + ".txt.gz")) for n in rows if n != "c-end"}
    print("# POST HOC readings of r31-kreg2 k2 (no verdict; the frozen rule said cannot tell)")
    v = [med(r[1:]) for r in s0.values()]
    print(f"s0 v1-v8 medians of renders 2-6: {' '.join(map(str, v))} us; median "
          f"{st.median(v)}, IQR {iqr_pct(v):.2f} % -> BOUND2 {max(1.0, 3 * iqr_pct(v)):.2f} %")
    allr = [x for r in list(s0.values()) + list(k2.values()) for x in r[1:]]
    first = [r[0] for r in list(s0.values()) + list(k2.values())]
    print(f"renders 2-6, all {len(allr)} L2 renders: median {st.median(allr)} us, min {min(allr)}, "
          f"max {max(allr)}, IQR {iqr_pct(allr):.2f} %, stdev {st.pstdev(allr) / st.mean(allr) * 100:.2f} %")
    print(f"render 1 of each job: median {st.median(first)} us (renders 2-6 {st.median(allr)})")
    within = [iqr_pct(r[1:]) for r in k2.values()]
    print(f"within one job (renders 2-6): IQR median {st.median(within):.2f} %, "
          f"max {max(within):.2f} %")
    ctl = {n: med(r[1:]) for n, r in k2.items() if re.fullmatch(r"c\d\d", n)}
    cm = st.median(ctl.values())
    print(f"k2 controls c01-c16: {' '.join(f'{n} {u}' for n, u in sorted(ctl.items()))}; "
          f"median {cm}, IQR {iqr_pct(list(ctl.values())):.2f} %")
    # drift: the controls in run order are c01..c16; compare the first and last eight
    cs = [ctl[n] for n in sorted(ctl)]
    print(f"drift: c01-c08 median {st.median(cs[:8])} us, c09-c16 median {st.median(cs[8:])} us")
    print("# per value: median of renders 2-6, fit (a) and held out (b), percent of the "
          "controls' median (readings only)")
    for i in range(64):
        a, b = k2.get(f"a{i:02x}"), k2.get(f"b{i:02x}")
        ma, mb = med(a[1:]), med(b[1:])
        print(f"0x{i:02x} a {ma:4d} us {(ma / cm - 1) * 100:+6.2f} %  b {mb:4d} us "
              f"{(mb / cm - 1) * 100:+6.2f} %")
    names = [ln.split("|")[0] for ln in open(os.path.join(os.path.dirname(__file__), "..",
                                                           "tables", "k2.txt"))
             if not ln.startswith("#") and ln.strip()]
    run = [med(k2[n][1:]) for n in names if n in k2]
    print("# drift: the median of each 18 rows in run order (c01 to b-pass end)")
    print(" ".join(f"{st.median(run[i:i + 18])}" for i in range(0, len(run), 18)))
    hist = {}
    for u in run:
        hist[u // 20 * 20] = hist.get(u // 20 * 20, 0) + 1
    print("# job medians (144 rows) by 20 us bin: " +
          ", ".join(f"{k}-{k + 19}: {hist[k]}" for k in sorted(hist)))
    vals = [med(r[1:]) for n, r in k2.items() if n[0] in "ab"]
    print(f"all 128 value rows: median {st.median(vals)} us, IQR {iqr_pct(vals):.2f} %, range "
          f"{min(vals)}-{max(vals)}; controls' range {min(cs)}-{max(cs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
