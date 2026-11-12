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
    check([len(tabs[s]["jobs"]) for s in L.STAGES] == [3], "job count: p1 3 (B0, B1P x2)")
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
        check(all(s <= {"control", "heldout"} for s in sets.values()), f"{st}: the sets are control and heldout only (every B1P row is held out)")
        hyps = {m.split(" ")[0] for _c, _q, _v, m, s in rows_of(st) if s == "heldout"}
        fam = {h for f in G.FAMILIES[st] for h in f}
        check(fam <= hyps, f"{st}: every hypothesis of the stage's families has rows ({sorted(fam - hyps)} missing)")
        for j in t["jobs"]:
            ctl = {q for c, q, v, m, s in rows_of(st) if c == j["name"] and s == "control"}
            check({"timer_clock_read", "arm_dword6", "arm_marks", "tick_gap", "skipped"} <= ctl,
                  f"{st}/{j['name']}: the applied design is a control (knob read back, dword 6 at the arm, the gap, the skip flag)")
    p1 = tabs["p1"]["jobs"]
    check([(j["name"], j["skip"], j["timer_clock"], j["clears"], j["hold_recovery"], j["watch_ms"]) for j in p1] ==
          [("b0", 0, 0, "none", "N", 50), ("b1p", 1, 0, "late", "Y", 50), ("b1p-r2", 1, 0, "late", "Y", 50)],
          "p1: B0 + B1P x2 at timer_clock 0, the clears after the watch (E855's h1 job; the parent's plan: 3 jobs)")
    check(all(j["clear_values"] == [0x8000, 0x40000] for j in p1), "the host's CLEAR values are bits 15 and 18 only")
    check(all(j["read_ms"] == {"bit15": [1, 3], "bit18": [1, 3, 20]} for j in p1), "read times: R4's 1, 3 (and 20) ms")
    check(L.STOP_BUDGET == {"p1": 2}, f"stop budget = the B1P jobs: 2 ({L.STOP_BUDGET})")
    check(all(j["may_stop"] == bool(j["skip"]) for j in p1), "only a skipped job may stop (a B0 stop ends the stage)")
    check(L.CLOCKS == (0,) and L.knob_text(0) == "0x00000000", "part P writes timer_clock 0 only")
    check(L.EXPECT_SRCV == "41E2F5C756F96D20F7109A4" and "99CD90DA26E3AFF9C450517" in L.OLD_SRCVS, "the module is the r6-kernel build (41E2F5C7...), rgn4 refused")
    check(L.STR_OF == {} and not json.loads((R5 / "bins" / "blobs.json").read_text())["ring_skip3p"]["str"], "no firmware str in the blob")
    check(hashlib.sha256((R5 / "bins" / "ring_skip3p.blob").read_bytes()).hexdigest() == L.SKIP3P_SHA ==
          "3b35d3af206b9b21302cf4b70f7bd64af7d840ebd744f6c067f8b2819e406b49", "ring_skip3p.blob is R4's bytes (3b35d3af...)")
    rp = rows_of("p1")
    check(all(v == "20" for c, q, v, m, s in rp if q == "ticks_after_kick" and m.startswith("H-TICKS")), "H-TICKS: 20")
    pk = {(c, q, v, m.split(" ")[0]) for c, q, v, m, s in rp if q.startswith("peek_")}
    want = set()
    for n in ("b1p", "b1p-r2"):
        want |= {(n, "peek_format", "ok", "control"), (n, "peek_stop", "0x00000002", "H-R6"), (n, "peek_stop_eq_arm", "no", "H-R6"),
                 (n, "peek_stop_eq_arm", "yes", "H-IDLE"), (n, "peek_recovered_eq_arm", "yes", "H-RESET")}
    want.add(("b0", "peek_format", "ok", "control"))
    check(pk == want, f"the peek rows: H-R6 0x00000002 against H-IDLE (the arm's read), H-RESET, the format control in every job ({sorted(pk ^ want)})")
    check(not any(q == "dpm_task_state" for c, q, v, m, s in rp), "the rgn4 kernel's cannot-tell row (R6-DPM) is gone")
    check(not any("cited/closing5/r6" in m or "data-private" in m for c, q, v, m, s in rp), "no prediction cites a data-private file (E855 only)")
    print(f"{len(FAIL)} failed" if FAIL else "all generator checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
