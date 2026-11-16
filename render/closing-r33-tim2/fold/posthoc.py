#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r33-tim2's post-hoc readings (not frozen).

  posthoc.py OUT_ATTEMPT_DIR [E1131_ATTEMPT_DIR]

Per t1 row of the run: the spacing (us) from the sample before the CR_CACHE_CTRL change to the
change sample and from it to the next four, CR_EVENT_STATUS in those samples, and the frozen
scorer's readings of the window (rcc, wn, wmed, as20, as120). With E1131's attempt directory
(render/closing-r33-tim out/20261116-211055 at data main), the frozen scorer's readings of its
t1 rows too: the same window readings on the earlier run, for comparison."""
import gzip
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402

KEYS = ("ccstart", "rcc", "wn", "wmed", "wmax", "as20", "as120", "d26", "w26")


def rows_of(att):
    d = os.path.join(att, "t1")
    return [(f[:-7], os.path.join(d, f)) for f in sorted(os.listdir(d))
            if f.startswith("t1-") and f.endswith(".txt.gz")]


def main(argv):
    for name, path in rows_of(argv[1]):
        text = gzip.open(path, "rt").read()
        tl = SC.timeline(text)
        rows = tl["rows"]
        c, s = tl["regs"].index(0x0804), tl["regs"].index(0x012c)
        i = next(j for j, (_, v) in enumerate(rows) if v[c] != rows[0][1][c])
        t = rows[i][0]
        after = [round((rows[i + k][0] - t) / 1000, 1) for k in (1, 2, 3, 4) if i + k < len(rows)]
        st = ["0x%08x" % rows[i + k][1][s] for k in range(4) if i + k < len(rows)]
        a = SC.analyse(text)
        print(f"{name} before={round((t - rows[i - 1][0]) / 1000, 1)} after={after} status={st} "
              + " ".join(f"{k}={a.get(k)}" for k in KEYS))
    if len(argv) > 2:
        print("# E1131's t1 rows under this scorer")
        for name, path in rows_of(argv[2]):
            a = SC.analyse(gzip.open(path, "rt").read())
            print(f"E1131 {name} " + " ".join(f"{k}={a.get(k)}" for k in KEYS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
