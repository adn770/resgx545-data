# SPDX-License-Identifier: MIT
"""fold/posthoc.py KEPT_ATTEMPT_DIR: r29-kreg's post-hoc readings (not frozen, no verdict).
Every timed row in run order with its six render times, its reading (mean of renders 2-6) and its
deviation from the median of the 15 0x2c controls other than c11; then the rows whose reading or
any single render of 2-6 lies more than 1 percent from that median."""
import gzip
import os
import re
import statistics
import sys

TIME = re.compile(r"^tri 256x256 #(\d+): (\d+) us$", re.M)


def rows(d):
    out = []
    for ln in open(os.path.join(d, "cases.tsv")).read().splitlines()[1:]:
        f = ln.split("\t")
        txt = gzip.open(os.path.join(d, f[0] + ".txt.gz"), "rt").read()
        t = [int(m[2]) for m in TIME.finditer(txt)]
        if len(t) == 6:
            v = next((w.split("=")[1] for w in f[4].split() if w.startswith("kreg:")), "reset")
            out.append((f[0], v, t, sum(t[1:]) // 5))
    return out


def main(top):
    s0, k1 = rows(os.path.join(top, "s0")), rows(os.path.join(top, "k1"))
    ctl = [r for r in k1 if re.fullmatch(r"c\d\d", r[0])]
    med = statistics.median(r[3] for r in ctl if r[0] != "c11")
    ref = statistics.median(r[3] for r in s0)
    print(f"# s0 references median {ref} us; k1 0x2c controls without c11 median {med} us")
    print("# k1 order: idx name value reading dev% renders(1-6)")
    for i, (n, v, t, m) in enumerate(k1, 1):
        dev = (m / med - 1) * 100
        far = max(abs(x / med - 1) * 100 for x in t[1:])
        flag = " <" if abs(dev) > 1 or far > 1.5 else ""
        print(f"{i:3d} {n:4s} {v:5s} {m:6d} {dev:+6.2f} {' '.join(map(str, t))}{flag}")
    for n, v, t, m in s0:
        print(f"s0 {n} {m} {(m / med - 1) * 100:+.2f} {' '.join(map(str, t))}")


if __name__ == "__main__":
    main(sys.argv[1])
