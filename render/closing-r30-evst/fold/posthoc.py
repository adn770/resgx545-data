#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r30-evst's post-hoc readings (NOT frozen), from the kept files of one attempt
through the frozen scorer's analyse().

  posthoc.py OUT/ATTEMPT

Per row: the register set, bit 26's episodes (widths in us), its lead to the render end, the
CR_CACHE_CTRL (0x0804) word before the job and after, the time from its first change to bit 26's
rise (cc26) and whether it holds to the end of the run, CR_USE0_SERV_EVENT's (0x0b14) counts
beyond the ticks over the job (seextra) and the samples with its bit 16 clear in the job. Then
each R4/RW stage's rows rescored with the frozen windows on everything but the controls' `cache`
key, whose frozen value 0x1000ffff was the builder's error (README "Fold")."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402


def cc_words(a):
    tl = a["timeline"]
    if 0x0804 not in tl["regs"]:
        return None
    c = tl["regs"].index(0x0804)
    vals = [v[c] for _, v in tl["rows"]]
    ch = [i for i, v in enumerate(vals) if v != vals[0]]
    back = any(v == vals[0] for v in vals[ch[0]:]) if ch else None
    return "%08x->%s%s" % (vals[0], "%08x" % vals[ch[0]] if ch else "-",
                           "" if not ch else (" back" if back else " held to the end"))


def main(att):
    print("# post hoc (not frozen): r30-evst, attempt", os.path.basename(att.rstrip("/")))
    widths = {}
    for st in SC.STAGES:
        d = os.path.join(att, st)
        kp = SC.Kept(st, d)
        for r in SC.K.table(KP, st):
            a = kp.get(r["name"])
            if a is None:
                print(r["name"], "not ok")
                continue
            regs = len(a["timeline"]["regs"])
            w = a.get("b26width") or []
            widths.setdefault((st, regs), []).extend(w)
            print(f"{r['name']} [{r['set']}] regs {regs} ivl {a['ivl']} ns b26 {a['b26n']} "
                  f"widths {SC._fmt(w)} lead {SC._fmt(a.get('b26lead'))} "
                  f"cc {cc_words(a)} cc26 {SC._fmt(a.get('cc26'))} "
                  f"seextra {a.get('seextra')} se16clr {a.get('se16clr')} "
                  f"tickrate {a.get('tickrate')} kick26 {SC._fmt(a.get('kick26'))}")
    print("# bit 26 widths (us) by stage and register count")
    for (st, n), w in widths.items():
        print(f"{st} regs {n}: {len(w)} episodes, " +
              (f"min {min(w):.1f} median {sorted(w)[len(w) // 2]:.1f} max {max(w):.1f}"
               if w else "none"))
    print("# R4/RW stages rescored without the controls' cache key (post hoc)")
    for st in ("e2", "e3", "e4"):
        controls, per_model, lines = SC.verdicts(st, os.path.join(att, st), [att])
        for ln in lines:
            if ln.startswith("CONTROL"):
                print(ln)
        ctl = {}
        for r in SC.K.table(KP, st):
            if r["set"] != "control":
                continue
            a = SC.Kept(st, os.path.join(att, st)).get(r["name"])
            want = SC.K.predictions(KP, st)[r["name"]]
            ctl[r["name"]] = all(SC.inside(a.get(q), v) for q, m in want.items()
                                 for v in m.values() if q != "cache")
        for m, sets in sorted(per_model.items()):
            rows = sets["fit"] + sets["held"]
            print(f"POSTHOC {st} {m}: " + SC.SK.headline(SC.CLAIMS.get(m, m), ctl, rows))


if __name__ == "__main__":
    main(sys.argv[1])
