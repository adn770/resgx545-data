#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""posthoc.py ATT: r32-kreg3's readings after the run (POST HOC, no verdict): per s0 form the
eight references' medians, their spread, the within-job spread of renders 2-N and the images;
kl10's controls, value range and drift. Reads the kept .txt.gz files of ATT (out/ATTEMPT) only;
prints to stdout."""
import gzip
import os
import re
import statistics as st
import sys

TIME = re.compile(r"^tri \d+x\d+ #\d+: (\d+) us$")
O0 = re.compile(r"^probe \S+: (o0 .*)$")
FORMS = ["10", "20", "40", "l10", "l20", "l40"]


def lines(path):
    with gzip.open(path, "rt") as f:
        return f.read().splitlines()


def renders(path):
    return [int(m[1]) for m in map(TIME.match, lines(path)) if m]


def images(path):
    return sorted({m[1] for m in map(O0.match, lines(path)) if m})


def med(xs):
    s, n = sorted(xs), len(xs)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2


def iqr_pct(xs):
    q = st.quantiles(xs, n=4, method="inclusive")
    return (q[2] - q[0]) / st.median(xs) * 100


def main(att):
    print("# POST HOC readings of r32-kreg3 (no verdict; the frozen verdicts are score-*.txt)")
    s0 = os.path.join(att, "s0")
    for f in FORMS:
        ref = {i: renders(os.path.join(s0, f"v{f}-{i}.txt.gz")) for i in range(1, 9)}
        meds = [med(r[1:]) for r in ref.values()]
        within = [iqr_pct(r[1:]) for r in ref.values()]
        first = [r[0] for r in ref.values()]
        imgs = sorted({i for k in range(1, 9) for i in images(os.path.join(s0, f"v{f}-{k}.txt.gz"))})
        allr = [x for r in ref.values() for x in r[1:]]
        print(f"form {f}: medians {' '.join(map(str, meds))} us; median {st.median(meds)}, IQR "
              f"{iqr_pct(meds):.3f} %, range {min(meds)}-{max(meds)}; renders 2-N all {len(allr)}: "
              f"{min(allr)}-{max(allr)} us; within-job IQR median {st.median(within):.2f} % "
              f"(max {max(within):.2f}); render 1 median {st.median(first)}; images: "
              + " | ".join(imgs))
    k = os.path.join(att, "kl10")
    rows = sorted(n[:-7] for n in os.listdir(k) if re.fullmatch(r"([ab][0-9a-f]{2}|c\d\d)\.txt\.gz", n))
    got = {n: renders(os.path.join(k, n + ".txt.gz")) for n in rows}
    ctl = {n: med(r[1:]) for n, r in got.items() if n.startswith("c")}
    cs = [ctl[n] for n in sorted(ctl)]
    print(f"kl10 controls c01-c16: {' '.join(map(str, cs))} us; median {st.median(cs)}, IQR "
          f"{iqr_pct(cs):.3f} %; c01-c08 median {st.median(cs[:8])}, c09-c16 {st.median(cs[8:])}")
    vals = [med(r[1:]) for n, r in got.items() if not n.startswith("c")]
    cm = st.median(cs)
    print(f"kl10 128 value rows: median {st.median(vals)} us, range {min(vals)}-{max(vals)} "
          f"({(min(vals) / cm - 1) * 100:+.2f} to {(max(vals) / cm - 1) * 100:+.2f} % of the "
          f"controls' median), IQR {iqr_pct(vals):.3f} %")
    within = [iqr_pct(r[1:]) for r in got.values()]
    print(f"kl10 within-job IQR of renders 2-10: median {st.median(within):.2f} %, "
          f"max {max(within):.2f} %")
    imgs = sorted({i for n in rows for i in images(os.path.join(k, n + ".txt.gz"))})
    print("kl10 images: " + " | ".join(imgs))


if __name__ == "__main__":
    main(sys.argv[1])
