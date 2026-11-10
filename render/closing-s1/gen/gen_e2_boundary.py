#!/usr/bin/env python3
"""Generate the E2 boundary and count jobs (table g-e2b) from the page need U measured by g-e2a.

PAUSE POINT of S1: run g-e2a, score it (score/score_s1.py g-e2a ... --emit-u), then run this, then
freeze (run/freeze_s1.sh e2b) and only then run g-e2b.

usage: gen_e2_boundary.py U.json
  U.json  {"u-2a-0x422": 21, "u-2s-0x422": 17, ...}, written by `score_s1.py g-e2a --emit-u U.json`
          (the scene's U = the peak of the page status, cross-checked against the pool walk)

Rules (E625, a fit on one-triangle scenes; here HELD OUT on a second shape):
  overflow iff thr0 = P - 0x22 is below U;  boundary jobs P = U + 0x22 - 1 (overflow) and U + 0x22 (none)
  partial renders = 1 + floor((U + k - thr0) / (thr0 + s)), k in 2..13, s in {0x1e, 0x1f}; P1 and P2 are
  chosen where the (k, s) pairs still allowed by E625 predict different counts; if no P separates
  them the count jobs are skipped and the table says so.
"""
from __future__ import annotations

import itertools
import json
import re
import sys

import s1common as C
from s1common import Row, write_preds, write_table
import s1geo

PAIRS = [(k, s) for k in range(2, 14) for s in (0x1E, 0x1F)]


def count(u, thr0, k, s):
    return 1 + (u + k - thr0) // (thr0 + s)


def pick_counts(u):
    """Two thr0 values that split the (k, s) pairs best; (list of (thr0, classes))."""
    best = []
    chosen = []
    classes = {p: () for p in PAIRS}
    for _ in range(2):
        top = None
        for thr0 in range(1, u):
            if thr0 in chosen:
                continue
            groups = {}
            for p in PAIRS:
                groups.setdefault(classes[p] + (count(u, thr0, *p),), []).append(p)
            if top is None or len(groups) > top[0]:
                top = (len(groups), thr0)
        if top is None or top[0] <= len(set(classes.values())):
            break
        chosen.append(top[1])
        for p in PAIRS:
            classes[p] = classes[p] + (count(u, top[1], *p),)
    return chosen, len(set(classes.values()))


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    U = json.load(open(argv[1]))
    rows, preds, notes = [], [], []
    for name in sorted(U):
        m = re.fullmatch(r"u-(\d)([as])-0x422", name)
        if not m:
            continue
        k, lay = int(m[1]), m[2]
        u = int(U[name])
        mv = (s1geo.E2_APART if lay == "a" else s1geo.E2_STACKED)[:k - 1]
        for tag, P in (("lo", u + 0x22 - 1), ("hi", u + 0x22)):
            nm = f"b-{k}{lay}-{tag}"
            Ph = hex(P)
            rows.append(Row(nm, "heldout", "safe", Ph, "stophang expectdiff", C.RT_DPM_SHORT,
                            s1geo.e2_args(k, mv), f"boundary of {name}: U = {u}, P = U + 0x22 {'- 1' if tag == 'lo' else ''}"))
            thr0 = P - 0x22
            preds += [(nm, "knob0624_first", hex(thr0), "knob", "heldout"),
                      (nm, "outcome", "overflow" if thr0 < u else "complete", "E625 rule", "heldout")]
        if k == 4 and lay == "a":
            chosen, ncls = pick_counts(u)
            if not chosen or ncls < 2:
                notes.append(f"count jobs skipped: no P separates the (k, s) pairs for U = {u}")
            for i, thr0 in enumerate(chosen, 1):
                nm = f"k-4a-P{i}"
                P = thr0 + 0x22
                rows.append(Row(nm, "heldout", "safe", hex(P), "stophang expectdiff", C.RT_DPM_SHORT,
                                s1geo.e2_args(4, mv), f"partial-render count at thr0 = {thr0} (separates k, s)"))
                preds.append((nm, "knob0624_first", hex(thr0), "knob", "heldout"))
                for (k_, s_) in PAIRS:
                    preds.append((nm, "nparts", str(count(u, thr0, k_, s_)), f"E625 k={k_} s={hex(s_)}", "heldout"))
            notes.append(f"count jobs: thr0 {chosen} classes {ncls} of {len(PAIRS)} pairs separated")
    head = f"""E2 second part (geometry): Q211 boundary and count jobs, generated from the measured U
({argv[1]}).  Predictions frozen with sha256 before the run (run/freeze_s1.sh e2b).
Overflow iff P - 0x22 < U (E625's rule, HELD OUT here on K-triangle scenes); counts by
1 + floor((U + k - thr0) / (thr0 + s)).  {'; '.join(notes)}"""
    write_table("g-e2b", rows, [], head)
    write_preds("g-e2b", preds)
    (C.S1 / "out").mkdir(exist_ok=True)
    (C.S1 / "out" / "g-e2b.generated-from.json").write_text(json.dumps(U, indent=1, sort_keys=True) + "\n")
    print(f"g-e2b: {len(rows)} jobs; {'; '.join(notes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
