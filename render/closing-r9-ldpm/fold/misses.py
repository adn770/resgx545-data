#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/misses.py (r9-ldpm fold, 2026-11-13; POST HOC: written and run after the run and its frozen
scores were read): every row's reading beside the frozen tables, per stage, and stage w's cells
read against their frozen predictions without the gate their calibrations closed (the calibrations
failed on H-STEPMODEL's steps, not on the need). Uses the session's own reader (score/read.py),
tables (gen/plan.py) and scorer's value/holds; standard library only.

  python3 fold/misses.py out/20261113-082650
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
            if f"{w}x{hh}" in PL.T["models"]:
                Sm, A, U, after = PL.model(w, hh)
                extra = " | off-steps " + " ".join(f"{k}:{h(rd['S'][k])}/{h(v)}" for k, v in sorted(Sm.items())
                                                    if k in rd["S"] and rd["S"][k] != v)
            print(f"{r['name']:22s} {w}x{hh} thr0 {h(t)} n {rd['nparts']} need {h(rd['need'])} abort "
                  f"{h(rd['gps_abort'])} left {h(rd['gps_left'])} next {h(rd['gps_next'])} "
                  f"peaks {','.join(h(x) for x in rd['runpeaks'])} | S {S}{extra}")
    print("== w cells without their calibration's gate (post hoc)")
    d = os.path.join(att, "w")
    rds = SC.readings("w", d)
    preds = K.predictions(KP, "w")
    tal = {}
    for r in K.table(KP, "w"):
        if r["set"] != "heldout":
            continue
        for q, by in preds.get(r["name"], {}).items():
            for mdl, v in by.items():
                if mdl == "CTL":
                    continue
                st = SC.holds(SC.value(rds[r["name"]], q), v)
                tal.setdefault(mdl, [0, 0])[0 if st else 1] += 1
                print(f"{r['name']} [{mdl}] {q} {SC.shown(SC.value(rds[r['name']], q))} (frozen {v}): "
                      f"{'held' if st else 'FAILED' if st is False else 'cannot tell'}")
    for mdl, (a, b) in sorted(tal.items()):
        print(f"post hoc {mdl}: {a} held, {b} not, of {a + b}")


if __name__ == "__main__":
    main(sys.argv[1])
