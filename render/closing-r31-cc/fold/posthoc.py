#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r31-cc's post-hoc readings (NOT frozen), from the kept files of one attempt
through the frozen scorer's timeline().

  posthoc.py OUT/ATTEMPT

Per row of c3, c4, c5 (the rows that sample CR_BIF_CTRL, 0x0c00): every sample run whose
0x0c00 differs from its first word, as times in us from CR_CACHE_CTRL's change (0x0000ffff to
0x1000ffff): the first sample showing it, the first sample after it showing the first word again,
the bounds on how long it stayed (from the sample before it to the sample that cleared it, and
between the two printed samples), the job's end, and the CR_USE0_SERV_EVENT counts in the 30 us
after the run, where 0x0b14 is sampled. A sample run is printed only when something changes, so
the bounds use the stage's mean sample interval (the row's `ivl`)."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402


def main(att):
    print("# post hoc (not frozen): r31-cc, attempt", os.path.basename(att.rstrip("/")))
    for st in ("c3", "c4", "c5"):
        for r in SC.K.table(KP, st):
            text = SC.K.text(os.path.join(att, st), r["name"] + ".txt")
            tl, a = SC.timeline(text), SC.analyse(text)
            regs, rows = tl["regs"], tl["rows"]
            b, k = regs.index(0x0c00), regs.index(0x0804)
            s = regs.index(0x0b14) if 0x0b14 in regs else None
            b0 = rows[0][1][b]
            ch = next(t for t, v in rows if v[k] != rows[0][1][k])
            ivl = a["ivl"] / 1000
            us = lambda t: round((t - ch) / 1000, 1)  # noqa: E731
            runs, cur = [], None
            for t, v in rows:
                if v[b] != b0 and cur is None:
                    cur = [t, None, v[b]]
                    runs.append(cur)
                elif v[b] == b0 and cur is not None:
                    cur[1] = t
                    cur = None
            for t0, t1, w in runs:
                cnt = []
                if s is not None and t1 is not None:
                    prev = None
                    for t, v in rows:
                        if prev is not None and t1 <= t <= t1 + 30_000 and \
                                (v[s] & 0xffff) != (prev & 0xffff):
                            cnt.append(us(t))
                        prev = v[s]
                hi = None if t1 is None else round((t1 - t0) / 1000 + ivl, 1)
                lo = None if t1 is None else round(max((t1 - t0) / 1000 - ivl, 0), 1)
                print(f"{r['name']}: 0x{w:08x} from {us(t0)} to {None if t1 is None else us(t1)} us"
                      f" (set {lo} to {hi} us at ivl {ivl:.2f}); 0x0804 changed at 0; job end "
                      f"{us(tl['end'])} us; counts after it at {cnt}")
    print("# rows with no CR_BIF_CTRL word other than their first are not listed")


if __name__ == "__main__":
    main(sys.argv[1])
