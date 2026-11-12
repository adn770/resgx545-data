#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_gen_r5.py: the generated tables and predictions are what gen/gen_r5.py makes from gen/r5layout.py (nothing edited by hand), every
prediction names a job of its table, every job has a control row that can fail, the sets are the right labels, and the numbers the plan
froze (job counts, clocks, watches, budgets, clear values, the blob's bytes) are what the layout says.  Exit 0 when every check holds."""
import hashlib
import json
import pathlib
import sys

sys.dont_write_bytecode = True
R5 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R5 / "gen"))
import r5layout as L  # noqa: E402
import gen_r5 as G  # noqa: E402

FAIL = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def rows_of(stage):
    lines = (R5 / "predictions" / f"{stage}.tsv").read_text().splitlines()
    assert lines[0] == "case\tquantity\tvalue\tmodel\tset"
    return [tuple(ln.split("\t")) for ln in lines[1:] if ln.strip()]


def main():
    tabs = {s: json.loads((R5 / "tables" / f"{s}.json").read_text()) for s in L.STAGES}
    check([len(tabs[s]["jobs"]) for s in L.STAGES] == [4, 6, 4], "job counts: h1 4, h2 6, h3 4 (14 in all: the plan's 14)")
    for st in L.STAGES:
        t = tabs[st]
        check(json.loads(json.dumps(G.table(st))) == t, f"{st}: tables/{st}.json is exactly what gen_r5.py makes from r5layout.ROW_SPEC")
        want = ["\t".join(r) for r in G.preds_stage(st, t)]
        got = ["\t".join(r) for r in rows_of(st)]
        check(want == got, f"{st}: predictions/{st}.tsv is exactly what gen_r5.py freezes ({len(got)} rows)")
        names = {j["name"] for j in t["jobs"]}
        sets = {}
        for case, q, v, m, s in rows_of(st):
            sets.setdefault(case, set()).add(s)
        check(set(sets) <= names and all(sets.get(n) for n in names), f"{st}: every job has predictions and every prediction names a job")
        check(all(s >= {"control"} for s in sets.values()), f"{st}: every job has at least one control row (a control that can fail)")
        check(all(s <= {"control", "heldout"} for s in sets.values()), f"{st}: the sets are control and heldout only (every B1P / B1E row of round 5 is held out)")
        hyps = {m.split(" ")[0] for _c, _q, _v, m, s in rows_of(st) if s == "heldout"}
        fam = {h for f in G.FAMILIES[st] for h in f}
        check(fam <= hyps, f"{st}: every hypothesis of the stage's families has rows ({sorted(fam - hyps)} missing)")
        for j in t["jobs"]:
            ctl = {q for c, q, v, m, s in rows_of(st) if c == j["name"] and s == "control"}
            check({"timer_clock_read", "arm_dword6", "arm_marks", "tick_gap", "skipped"} <= ctl,
                  f"{st}/{j['name']}: the applied design is a control (knob read back, dword 6 at the arm, the gap, the skip flag)")
    h1, h2, h3 = (tabs[s]["jobs"] for s in L.STAGES)
    check([(j["name"], j["skip"], j["timer_clock"], j["clears"], j["hold_recovery"], j["watch_ms"]) for j in h1] ==
          [("b0", 0, 0, "none", "N", 50), ("b1p", 1, 0, "late", "Y", 50), ("b1p-r2", 1, 0, "late", "Y", 50), ("b1p-r3", 1, 0, "late", "Y", 50)],
          "h1: B0 + B1P x3 at timer_clock 0, the clears after the watch (R4's e3p job)")
    check([(j["name"], j["skip"], j["timer_clock"], j["clears"], j["watch_ms"]) for j in h2] ==
          [("b0a", 0, 800000, "none", 100), ("b1pa", 1, 800000, "none", 100), ("b1pa-r2", 1, 800000, "none", 100),
           ("b0b", 0, 1600000, "none", 150), ("b1pb", 1, 1600000, "none", 150), ("b1pb-r2", 1, 1600000, "none", 150)],
          "h2: per clock (800000, 1600000) B0 + B1P x2, no host write before the watch ends")
    check([(j["name"], j["skip"], j["timer_clock"], j["clears"], j["miscinfo_after_clears"], j["watch_ms"]) for j in h3] ==
          [("b0", 0, 1600000, "none", False, 150), ("b1e", 1, 1600000, "early", True, 150), ("b1e-r2", 1, 1600000, "early", True, 150),
           ("b1e-r3", 1, 1600000, "early", True, 150)], "h3: B0 + B1E x3 at 1600000, the clears at the slot 3 entry, one miscinfo after them")
    check(all(j["clear_values"] == [0x8000, 0x40000] for s in L.STAGES for j in tabs[s]["jobs"]), "the host's CLEAR values are bits 15 and 18 only")
    check(all(j["read_ms"] == ({"bit15": [1, 3], "bit18": [1, 3]} if j["clears"] == "early" else {"bit15": [1, 3], "bit18": [1, 3, 20]})
              for s in L.STAGES for j in tabs[s]["jobs"]), "read times: h3 1 and 3 ms after each write; elsewhere R4's 1, 3 (and 20) ms")
    check(L.STOP_BUDGET == {"h1": 3, "h2": 4, "h3": 3}, f"stop budgets = the B1P / B1E jobs: h1 3, h2 4, h3 3, 10 predicted stops ({L.STOP_BUDGET})")
    check(all(j["may_stop"] == bool(j["skip"]) for s in L.STAGES for j in tabs[s]["jobs"]), "only a skipped job may stop (a B0 stop ends the stage)")
    check(L.STR_OF == {} and not json.loads((R5 / "bins" / "blobs.json").read_text())["ring_skip3p"]["str"], "no firmware str in the blob")
    check(hashlib.sha256((R5 / "bins" / "ring_skip3p.blob").read_bytes()).hexdigest() == L.SKIP3P_SHA ==
          "3b35d3af206b9b21302cf4b70f7bd64af7d840ebd744f6c067f8b2819e406b49", "ring_skip3p.blob is R4's bytes (3b35d3af...)")
    check([L.gap_units(c) for c in L.CLOCKS] == [25000, 50000, 100000] and [L.knob_text(c) for c in L.CLOCKS] == ["0x00000000", "0x000c3500", "0x00186a00"],
          "the gaps (dword 6 / 16) and the knob's read-back text of the three clocks")
    h2p = rows_of("h2")
    check({(c, v) for c, q, v, m, s in h2p if q == "ticks_after_kick" and m.startswith("H-TIME")} ==
          {("b1pa", "9..11"), ("b1pa-r2", "9..11"), ("b1pb", "4..6"), ("b1pb-r2", "4..6")}, "h2: H-TIME's counts 10 +-1 at 800000, 5 +-1 at 1600000")
    check(all(v == "20" for c, q, v, m, s in h2p + rows_of("h1") + rows_of("h3") if q == "ticks_after_kick" and m.startswith("H-TICKS")),
          "H-TICKS: 20 in every stage")
    print(f"{len(FAIL)} failed" if FAIL else "all generator checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
