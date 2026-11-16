#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r34-ev's kept rows as readings, by stage, job form and PB size (post hoc,
not frozen: no verdict changes). Each row: the scorer's analyse() readings, and for 0x012c the
episodes of bits 0, 1, 2, 18 (start us from the first sample, width us) and whether a bit 0
episode wider than 8 us runs together with bit 18.

  posthoc.py OUT/ATT   prints the table (fold/posthoc.txt)"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402

PB = {"0x422": "PR0", "0x2b6": "PR1", "0x1c2": "PR2", "0xe2": "PR4", "0x82": "PR7"}


def main(att):
    print("# r34-ev post hoc readings (fold/posthoc.py); widths and starts in us")
    for st in ("e0", "e1", "e2c", "e2", "d0"):
        d = os.path.join(att, st)
        cases = SC.K.rows(d, "cases.tsv")
        print(f"## {st}")
        for r in SC.K.table(SC.KP, st):
            n = r["name"]
            if n not in cases:
                print(f"{n}: not run")
                continue
            t = SC.K.text(d, n + ".txt")
            a = SC.analyse(t)
            f = SC.form(r["args"])
            kn = r["knobs"] if isinstance(r["knobs"], str) else " ".join(r["knobs"])
            pb = next((w.split("=")[1] for w in kn.split() if w.startswith("dbg:")), "")
            lab = f"{f} {pb} {PB.get(pb, '')}".strip()
            keys = ("ivl", "rc", "bits", "oom", "mt", "gbl", "e0", "e18", "w0max", "w1max",
                    "w18max", "s2words", "b0n", "b1n", "b2n", "b3n", "b3max", "b4n", "b4ms",
                    "pcn", "pcfin")
            a["rc"] = cases[n]["rc"]
            line = f"{n} [{lab}] " + " ".join(f"{k}={a[k]}" for k in keys if k in a)
            tl = SC.timeline(t)
            if tl and 0x012C in tl["regs"]:
                k = tl["regs"].index(0x012C)
                rows = tl["rows"]
                t0 = rows[0][0]
                eps = []
                for b in (0, 1, 2, 18):
                    for s, w in SC.episodes(rows, k, lambda x, b=b: x >> b & 1):
                        eps.append((s, b, w))
                eps.sort()
                line += " | " + " ".join(
                    f"b{b}@{(s - t0) / 1000:.0f}:{'-' if w is None else f'{w / 1000:.1f}'}"
                    for s, b, w in eps)
                long0 = [(s, w) for s, w in SC.episodes(rows, k, lambda x: x & 1)
                         if w and w > 8000]
                both = [any(v[k] >> 18 & 1 for tt, v in rows if s <= tt < s + w)
                        for s, w in long0]
                if long0:
                    line += f" | long bit 0 with bit 18: {sum(both)} of {len(long0)}"
            print(line)


if __name__ == "__main__":
    main(sys.argv[1])
