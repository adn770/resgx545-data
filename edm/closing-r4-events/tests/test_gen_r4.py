#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_gen_r4.py: the generated tables and predictions are what gen/gen_r4.py makes from gen/r4layout.py (nothing edited by hand), every
prediction names a job of its table, every job has a control row that can fail, the sets are the right labels, and the numbers the plan froze
(job counts, the kick timing constants, the allowed values) are what the layout says.  Exit 0 when every check holds."""
import json
import os
import pathlib
import sys

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R4 / "gen"))
os.environ.setdefault("RESGX545", "/Users/jtorra/src/scratch/resgx545/closing4/lead/wt")
import r4layout as L  # noqa: E402
import gen_r4 as G  # noqa: E402

FAIL = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def rows_of(stage):
    lines = (R4 / "predictions" / f"{stage}.tsv").read_text().splitlines()
    assert lines[0] == "case\tquantity\tvalue\tmodel\tset"
    return [tuple(ln.split("\t")) for ln in lines[1:] if ln.strip()]


def main():
    check([len(json.loads((R4 / "tables" / f"{s}.json").read_text())["jobs"]) for s in L.STAGES] == [10, 4, 4], "job counts: kb2 10, kp 4, e3p 4 (18 in all: the plan's 16 to 18)")
    for st in L.STAGES:
        t = json.loads((R4 / "tables" / f"{st}.json").read_text())
        check(json.loads(json.dumps(G.table(st))) == t, f"{st}: tables/{st}.json is exactly what gen_r4.py makes from r4layout.ROW_SPEC")
        want = ["\t".join(r) for r in G.PREDS[st](t)]
        got = ["\t".join(r) for r in rows_of(st)]
        check(want == got, f"{st}: predictions/{st}.tsv is exactly what gen_r4.py freezes ({len(got)} rows)")
        names = {j["name"] for j in t["jobs"]}
        sets = {}
        for case, q, v, m, s in rows_of(st):
            sets.setdefault(case, set()).add(s)
        check(set(sets) <= names and all(sets.get(n) for n in names), f"{st}: every job has predictions and every prediction names a job")
        check(all(s >= {"control"} for s in sets.values()), f"{st}: every job has at least one control row (a control that can fail)")
        check(all(s <= {"control", "fit", "heldout", "replicate"} for s in sets.values()), f"{st}: the sets are control, fit, heldout, replicate only")
        for j in t["jobs"]:
            exp = j["set"]
            heldrows = {s for s in sets[j["name"]] if s not in ("control", "fit")}
            check(heldrows <= {exp}, f"{st}/{j['name']}: its discriminating rows carry its own set ({exp})")
    kb = {j["name"]: j for j in json.loads((R4 / "tables" / "kb2.json").read_text())["jobs"]}
    check(all(j["pre_ms"] == 1 and j["ticks_ms"] == 0 and j["post_ms"] == 5 and j["window"] == 2 for j in kb.values()), "kb2: the call starts 1 ms after the window (ticks_ms 0)")
    check(kb["q2p"]["set_kicker"] == 0x42 and kb["q3p"]["no_bump"] and kb["q4"]["second_kick"] and not kb["q3p"]["second_kick"], "kb2: the writes of each row are the plan's")
    check(L.KB2_AFTER_MS == 8.0 and L.KB2_MIN_AFTER == 3 and L.KB2_SIG_N == 2, "kb2: 'after the kick' = the kick entry or the call's stamp + 8.0 ms; 3 ticks after; the signature x2")
    kp = json.loads((R4 / "tables" / "kp.json").read_text())["jobs"]
    check([(j["name"], j["kind"], j["act"], j["trigger"], j["may_stop"], j["reset_arm"]) for j in kp] ==
          [("e0", 0, 0, "none", False, False), ("fk", 1, 4, "none", False, False), ("kp", 2, 4, "miscinfo", True, True), ("kp-r2", 2, 4, "miscinfo", True, True)],
          "kp: E0, FK, KP x2 (only KP may stop; each KP resets and arms)")
    e3 = json.loads((R4 / "tables" / "e3p.json").read_text())["jobs"]
    check([(j["name"], j["skip"], j["hold_recovery"]) for j in e3] == [("b0", 0, "N"), ("b1p", 1, "Y"), ("b1p-r2", 1, "Y"), ("b1p-r3", 1, "Y")], "e3p: B0 then B1P x3 (hold_recovery Y only in B1P)")
    check(all(j["clear_values"] == [0x8000, 0x40000] for j in e3), "e3p: the host's CLEAR values are bits 15 and 18 only")
    check(L.STOP_BUDGET == {"kb2": 0, "kp": 1, "e3p": 0}, f"stop budgets: kb2 0, kp 1 (KP), e3p 0 (its first stop ends the stage) ({L.STOP_BUDGET})")
    check(L.STR_OF == {} and all(not i["str"] for i in json.loads((R4 / "bins" / "blobs.json").read_text()).values()), "no firmware str in any blob (R4-7)")
    print(f"{len(FAIL)} failed" if FAIL else "all generator checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
