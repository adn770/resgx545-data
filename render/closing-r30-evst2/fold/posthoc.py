#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r30-evst2's post-hoc readings (NOT frozen), from the kept files of one
attempt through the frozen scorer's timeline().

  posthoc.py OUT/ATTEMPT

Per row of e2, e3, e4: CR_EVENT_STATUS's words in the job, each time in us from CR_CACHE_CTRL's
change (0x0000ffff to 0x1000ffff), the first 300 us; per row of e5: bit 26's episodes against the
render ends (bits 18 and 0)."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402


def main(att):
    print("# post hoc (not frozen): r30-evst2, attempt", os.path.basename(att.rstrip("/")))
    for st in ("e2", "e3", "e4"):
        for r in SC.K.table(KP, st):
            tl = SC.timeline(SC.K.text(os.path.join(att, st), r["name"] + ".txt"))
            regs = tl["regs"]
            c, k = regs.index(0x012c), regs.index(0x0804)
            ch = next(t for t, v in tl["rows"] if v[k] != tl["rows"][0][1][k])
            seq, prev = [], None
            for t, v in tl["rows"]:
                if t >= ch and t - ch <= 300_000 and v[c] != prev:
                    seq.append("%.1f:%08x" % ((t - ch) / 1000, v[c]))
                prev = v[c]
            print(f"{r['name']}: " + " ".join(seq))
    for r in SC.K.table(KP, "e5"):
        a = SC.analyse(SC.K.text(os.path.join(att, "e5"), r["name"] + ".txt"))
        tl, c = a["timeline"], a["timeline"]["regs"].index(0x012c)
        e26 = SC.episodes(tl["rows"], c, 26)
        ends = sorted(e[0] for b in (18, 0) for e in SC.episodes(tl["rows"], c, b))
        t0 = tl["start"]
        print(f"{r['name']}: bit 26 at " + ", ".join(
            "%.1f us (%.1f wide)" % ((s - t0) / 1000, ((f or s) - s) / 1000) for s, f, _ in e26)
            + "; render ends at " + ", ".join("%.1f" % ((t - t0) / 1000) for t in ends))


if __name__ == "__main__":
    main(sys.argv[1])
