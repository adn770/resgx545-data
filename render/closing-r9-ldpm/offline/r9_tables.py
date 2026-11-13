#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""r9_tables.py (round 9, S9-ldpm: the frozen tables gen/plan.py builds the rows and predictions
from; offline, read-only, standard library only, no number fitted). Run after OD-1 to OD-3 and
before the session is frozen; writes r9_tables.json (sorted keys), its sha256 then goes into
FREEZE-tables.sha256 and gen/r9_tables.json is a byte copy (tests/test_plan.py checks it).

  models  per target: E874's step replay S_k (lag 3), H-SPAN's A_k, E874's B_k and U (g3_span
          through ol7lib, hash-checked); after[b_6 + d] for d = 0 .. 4 (OD-2's family)
  m6b     four targets never run near band 6 (run 2: up to three where OD-2's frozen end parts
          from A_6, from the plan's 2304x2304, 1792x1792, 2816x2048, 2048x2560 then M6B_MORE, and
          one of the plan's where they agree; each U < 0x3f0) with the class E936's rivals use,
          and OD-2's frozen candidate's end E_6 (od2_band6.json "frozen")
  w       OD-1's four wide targets and cells (od1_wide.json, unchanged)
  f9b     three targets never run in an f9 stage (1280x1280, 1792x1792 and 2560x2048, U < 0x3f0):
          two cells off band 4 where F9's count with R-5's guard equals F9's without a raise and
          parts from E854's d = 7/4 and d = 1 (the lowest such thr0 in [U / 8, U / 3] and in
          [U / 3, U / 2]; run 2 widened the first from [U / 8, U / 4]), and one band 4 cell (S_4 < thr0 < A_4, 2 global pages left by H-SPAN)
          where F9 (raised, R-5's guard as formalized) and H-NORAISE (E938's reading of band 4:
          not raised) part, on the count if any cell parts so, else on the run peaks; the middle
          such cell

  python3 -I -B r9_tables.py > r9_tables.out
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ol7lib as L  # noqa: E402

U_MAX = 0x3F0
M6B_PLAN = [(2304, 2304), (1792, 1792), (2816, 2048), (2048, 2560)]
M6B_MORE = [(2304, 2048), (2048, 2304), (2304, 1792), (1792, 2304), (2560, 1536), (1536, 2560),
            (2816, 2304), (2304, 2816), (1280, 1280), (2048, 2816), (2816, 2560), (1280, 1792)]
REPL = {(1536, 1536): {0x109: 2, 0x10A: 2, 0x10B: 1}, (4096, 2048): {0x362: 2, 0x363: 1, 0x364: 1}}
F9B = [(1280, 1280), (1792, 1792), (2560, 2048)]
OTHER = [(2048, 2048)]


def hx(v):
    return f"0x{v:x}"


def cls(w, h):
    n = (w > 2048) + (h > 2048)
    return {0: "small", 1: "one", 2: "both"}[n]


def model_entry(w, h):
    S, A, B, U = L.model(w, h)
    _, _, after = L.F5.replay(w, h, L.ents(w, h), 3)
    b6 = L.F5.bk(6)
    return {"S": {str(k): hx(v) for k, v in sorted(S.items())}, "A": {str(k): hx(v) for k, v in sorted(A.items())},
            "B": {str(k): hx(v) for k, v in sorted(B.items())}, "U": hx(U),
            "after6": [hx(after[b6 + d]) for d in range(5)]}


def f9(w, h, t, raised):
    return L.F9.run(L.ents(w, h), t, raised, w, h)


def f9b_cells(w, h):
    S, A, B, U = L.model(w, h)
    out = []
    for lo, hi in ((U // 8, U // 3), (U // 3, U // 2)):
        for t in range(lo, hi + 1):
            band = max([k for k, v in S.items() if v <= t], default=1)
            if t in S.values() or band == 4:
                continue
            a = f9(w, h, t, L.guard_class(t, S, A) == "R")
            b = f9(w, h, t, False)
            if a is None or b is None or a[0] != b[0] or a[0] > 10:
                continue
            d74, d1 = L.dcount(t, U, 1.75), L.dcount(t, U, 1.0)
            if a[0] != d74 and a[0] != d1:
                out.append(("off4", t, a, b))
                break
    band4 = [t for t in range(S[4] + 1, A[4]) if t not in S.values()]
    parts_n = [t for t in band4 if f9(w, h, t, True)[0] != f9(w, h, t, False)[0]]
    parts_p = [t for t in band4 if f9(w, h, t, True)[1] != f9(w, h, t, False)[1]]
    pick = parts_n or parts_p
    if not pick:
        raise SystemExit(f"{w}x{h}: no band 4 cell parts F9 from H-NORAISE")
    t = pick[len(pick) // 2]
    out.append(("band4", t, f9(w, h, t, True), f9(w, h, t, False)))
    return out


def main():
    od1 = json.load(open(os.path.join(HERE, "od1_wide.json")))
    od2 = json.load(open(os.path.join(HERE, "od2_band6.json")))
    res = {"models": {}, "m6b": [], "repl": [], "w": od1["w"], "f9b": [], "od2_frozen": od2.get("frozen")}
    # run 2 (after run 1, r9_tables.run1.out, gave H-NEXT1 = H-SPAN at three of the plan's four
    # targets): m6b takes up to three targets where H-NEXT1's end parts from A_6 (the plan's, then
    # M6B_MORE in order) and one where they agree (the plan's first such), each U < 0x3f0, S_7 above
    # A_6 + 3; model numbers only, no reading of any of them exists
    cand = []
    for w, h in M6B_PLAN + M6B_MORE:
        m = model_entry(w, h)
        U, A6, S7 = int(m["U"], 16), int(m["A"]["6"], 16), int(m["S"].get("7", "0x0"), 16)
        if U < U_MAX and S7 > A6 + 3:
            cand.append(((w, h), int(m["after6"][1], 16) != A6))
    M6B = [t for t, p in cand if p][:3] + [t for t, p in cand if not p and t in M6B_PLAN][:1]
    for w, h in M6B + list(REPL) + F9B + OTHER + [(x["w"], x["h"]) for x in od1["w"]]:
        if f"{w}x{h}" not in res["models"]:
            res["models"][f"{w}x{h}"] = model_entry(w, h)
    for w, h in M6B:
        m = res["models"][f"{w}x{h}"]
        U = int(m["U"], 16)
        if U >= U_MAX:
            raise SystemExit(f"m6b {w}x{h}: U {U:#x} not below 0x3f0")
        A6 = int(m["A"]["6"], 16)
        E = None
        if od2.get("frozen"):
            name, d = od2["frozen"][:-1], int(od2["frozen"][-1])
            after = [int(x, 16) for x in m["after6"]]
            E = after[d] if name == "H-NEXT" else A6 + -(-d * (after[1] - A6) // 2)
        res["m6b"].append({"w": w, "h": h, "class": cls(w, h), "A6": hx(A6), "U": hx(U),
                           "S6": m["S"]["6"], "S7": m["S"].get("7"), "E6": hx(E) if E else None})
        print(f"m6b {w}x{h} ({cls(w, h)}): U {U:#x} S6 {m['S']['6']} A6 {A6:#x} S7 {m['S'].get('7')} "
              f"after6 {m['after6']} OD-2 end {hx(E) if E else '-'}")
    for (w, h), cells in REPL.items():
        m = res["models"][f"{w}x{h}"]
        res["repl"].append({"w": w, "h": h, "cells": {hx(t): v for t, v in cells.items()}, "A6": m["A"]["6"]})
        print(f"repl {w}x{h}: A6 {m['A']['6']} cells (E936 read) {[(hx(t), v) for t, v in cells.items()]}")
    for w, h in F9B:
        m = res["models"][f"{w}x{h}"]
        U = int(m["U"], 16)
        if U >= U_MAX:
            raise SystemExit(f"f9b {w}x{h}: U {U:#x} not below 0x3f0")
        S = {int(k): int(v, 16) for k, v in m["S"].items()}
        cells = []
        for kind, t, a, b in f9b_cells(w, h):
            cells.append({"kind": kind, "thr0": hx(t), "F9": [a[0], [hx(x) for x in a[1]]],
                          "H-NORAISE": [b[0], [hx(x) for x in b[1]]], "d=7/4": L.dcount(t, U, 1.75),
                          "d=1": L.dcount(t, U, 1.0), "E625": int(t < U), "gps_abort": L.gps_abort(t, S)})
            print(f"f9b {w}x{h} U {U:#x} {kind} thr0 {t:#x}: F9 {a[0]} {[hex(x) for x in a[1]]} "
                  f"H-NORAISE {b[0]} {[hex(x) for x in b[1]]} d7/4 {L.dcount(t, U, 1.75)} d1 {L.dcount(t, U, 1.0)}")
        res["f9b"].append({"w": w, "h": h, "U": hx(U), "cells": cells})
    with open(os.path.join(HERE, "r9_tables.json"), "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
