#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""postrun/misses.py (r8-ldpm fold, 2026-11-13; POST HOC: written and run after the run and its
frozen scores were read): every row's reading beside the frozen tables, per stage, to read the
misses. `left` is the frozen reader's (the global pages in the last sample of the first partial
render), `next` the global pages of the first sample after it. Uses the session's own reader (score/read.py), tables (gen/plan.py) and dump reader
(score/score.py blocks); standard library only.

  python3 postrun/misses.py out/20261113-021431
"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "kit"), os.path.join(KP, "gen")]
import score as SC  # noqa: E402
import plan as PL  # noqa: E402
import kitscore as K  # noqa: E402

h = lambda v: "-" if v is None else f"0x{v:x}"  # noqa: E731


def main(att):
    for st in PL.STAGES:
        d = os.path.join(att, st)
        rds = SC.readings(st, d)
        print(f"== {st}")
        for r in K.table(KP, st):
            rd = rds[r["name"]]
            t = SC.thr0_of(r)
            w, hh = PL.target(r)
            if rd is None:
                print(f"{r['name']:22s} unread")
                continue
            S = " ".join(f"{k}:{h(v)}" for k, v in sorted(rd["S"].items()))
            extra = ""
            if " probe " in f" {r['args']} " and "--vtx-coords" not in r["args"]:
                Sm, A, B, U = PL.model(w, hh)
                k = max([k for k, v in Sm.items() if v <= t], default=1)
                extra = (f" | model band {k} A_k {h(A.get(k))} span {PL.span_left(t, Sm, A)}"
                         f" off-steps " + " ".join(f"{k2}:{h(rd['S'][k2])}/{h(v)}" for k2, v in sorted(Sm.items())
                                                    if k2 in rd["S"] and rd["S"][k2] != v))
            if st == "v" and r["set"] != "control":
                try:
                    b = SC.blocks(os.path.join(d, r["name"] + ".p1139-green."))
                    extra += f" | {len(b)} blocks, first 8 {b[:8]}"
                except Exception as e:  # noqa: BLE001
                    extra += f" | dump not read: {e}"
            gnext = None                    # the global pages of the first sample after the stretch
            if rd["nparts"]:
                import read as R
                regs, rows, _ = R.parse(K.text(d, r["name"] + ".txt"))
                st_ = R.stretches(rows)
                if st_[0][1] + 1 < len(rows):
                    gnext = R.hi(rows[st_[0][1] + 1][1][0x72C])
            print(f"{r['name']:22s} {w}x{hh} thr0 {h(t)} n {rd['nparts']} need {h(rd['need'])} "
                  f"abort {h(rd['gps_abort'])} left {h(rd['gps_left'])} next {h(gnext)} gmax {h(rd['gmax'])} "
                  f"peaks {','.join(h(x) for x in rd['runpeaks'])} | S {S}{extra}")


if __name__ == "__main__":
    main(sys.argv[1])
