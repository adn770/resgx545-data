#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_scorer.py: the scorers of R4-events on worlds built from REAL records (tests/fixtures/real/: E816's G0, E817's e0, fph and fcf, E813's
B3 with its stop dumps, E819's q2 and q3, E823's b0 and b1; copied from the kept stage directories of the sessions that ran them), and the
row engine on small synthetic tables.  The worlds of each hypothesis run through the runner and the mock in run_mock.py.

What this proves: the scorers read the records the runner keeps the way they were designed to (quantities, void rules, gates, family verdicts);
that the old E819 shape (the ring full before the kick) cannot be scored as G0P's control (cannot tell, the stage would stop); that a stop
read from E813's real dumps scores as KP's H-KICK-MORE shape; that E823's real watch and clears score as e3p's B1P rows.  Exit 0 when every
check holds.
"""
import copy
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R4 / "gen"))
sys.path.insert(0, str(R4 / "score"))
sys.path.insert(0, str(R4 / "run"))
sys.path.insert(0, str(R4 / "tests" / "mockfw"))     # ops_kicker2 imports fwtask_run: the mock stands in (only timing_of is used)
import r4layout as L  # noqa: E402
import scorelib as C  # noqa: E402
import r4common as R  # noqa: E402
import sc_kb2  # noqa: E402
import sc_kp  # noqa: E402
import sc_e3p  # noqa: E402
import scorekit as K  # noqa: E402
import ops_kicker2  # noqa: E402

FIX = R4 / "tests" / "fixtures" / "real"
FAIL = []
TABLES = {st: json.loads((R4 / "tables" / f"{st}.json").read_text()) for st in L.STAGES}


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def job(stage, name):
    return next(j for j in TABLES[stage]["jobs"] if j["name"] == name)


def real(name):
    return json.loads((FIX / f"{name}.json").read_text())


def stage_dir(stage, recs, extra=()):
    """A kept stage directory with the given records ({job name: record}), stage.json and the dump files in `extra`."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="r4score-"))
    for n, r in recs.items():
        r = copy.deepcopy(r)
        r["run"] = "T"
        r["name"] = n
        (d / f"{n}.json").write_text(json.dumps(r))
    (d / "stage.json").write_text(json.dumps({"stage": stage, "run": "T", "exit": 0, "why": "", "jobs_run": list(recs), "stops": 0, "classes": {}}))
    for src, dst in extra:
        shutil.copy(FIX / src, d / dst)
    return d


# ---- the row engine and the kit --------------------------------------------------------------------------------------------------
def test_engine():
    S = C.Stage("kb2", stage_dir("kb2", {}), R4)
    S.preds = [{"case": "x", "quantity": "c1", "value": "1", "model": "control (a)", "set": "control"},
               {"case": "x", "quantity": "q", "value": "2", "model": "H-A", "set": "heldout"},
               {"case": "x", "quantity": "q", "value": "3", "model": "H-B", "set": "heldout"}]
    ok_, why = R.tally_job(S, "x", {"c1": "1", "q": "2"})
    rows = {(m): ok for (_c, _q, m, _k, ok, _n) in S.t.rows}
    check(ok_ and rows["H-A"] is True and rows["H-B"] is False, "the engine: a passing control lets the rows through, H-A held, H-B FAILED")
    S.t.rows.clear()
    ok_, why = R.tally_job(S, "x", {"c1": "0", "q": "2"})
    rows = {(m): ok for (_c, _q, m, _k, ok, _n) in S.t.rows}
    check(not ok_ and rows["control (a)"] is False and rows["H-A"] is None and rows["H-B"] is None, "the engine: a FAILED control makes every other row cannot tell")
    S.t.rows.clear()
    R.tally_job(S, "x", {"q": "2"})
    rows = {(m): ok for (_c, _q, m, _k, ok, _n) in S.t.rows}
    check(rows["control (a)"] is None and rows["H-A"] is None, "the engine: a control that could not be read is cannot tell and gates the rest (scorekit.gate)")
    S.t.rows.clear()
    R.tally_job(S, "x", {"c1": "1", "q": "2"}, gate_why="the stage's gate is shut")
    check(all(ok is None for (_c, _q, m, k, ok, _n) in S.t.rows if k != "control"), "the engine: a stage-level gate makes every non-control row cannot tell")
    check(K.combine([True, False]) == "mixed" and K.combine([True, None]) == "cannot tell", "scorekit: replicates that disagree are mixed, a void one is cannot tell")
    check(R.unique([2, 2, 2]) == 2 and R.unique([2, 3]) == "mixed" and R.unique([]) is None, "unique: one value, mixed, or none")
    check(R.serv_bit16([{"regs": {"0xb14": 0x10000 | 5}}, {"regs": {"0xb14": 0x10000 | 6}}]) == "set"
          and R.serv_bit16([{"regs": {"0xb14": 5}}, {"regs": {"0xb14": 6}}]) == "clear", "serv_bit16: set / clear from USE0_SERV_EVENT")


# ---- kp: E817's real kept passes, E813's real stop ------------------------------------------------------------------------------
def test_kp_real():
    d = stage_dir("kp", {"e0": real("e817-e0"), "fk": real("e817-fph")})
    S = C.Stage("kp", d, R4)
    q, info, why = sc_kp.quantities(S, C.record(d, "e0"), job("kp", "e0"))
    check(why is None and q["entries"] == "12..16" and q["grid"] == "yes" and q["acted"] == 0, f"E0 on E817's real e0: 14 entries on the grid, nothing acted ({q})")
    q, info, why = sc_kp.quantities(S, C.record(d, "fk"), job("kp", "fk"))
    check(why is None and q["kept"] == "yes" and q["flag_logged"] == 3 and q["next_gap"] == "24950..25050" and q["next_gap_exact"] == "24994..24995"
          and q["read_minus_write"] == "0" and q["dword14"] == "0", f"FK on E817's real fph (ends idf, wdf, phas, nop.end): kept, flag 3, next +24994 ({q})")
    summary = sc_kp.score_kp(S)
    check("E0 and FK held" in summary, f"the kp scorer reads both controls from real records as held ({summary[:120]})")
    # E817's real fcf (the same pass without the phas): a stop with E817's signature
    d = stage_dir("kp", {"fcf": real("e817-fcf")})
    S = C.Stage("kp", d, R4)
    j = dict(job("kp", "fk"), act=3)
    q, info, why = sc_kp.quantities(S, C.record(d, "fcf"), j)
    check(why is None and q["kept"] == "no" and q["next_gap"] is None and q["p3_answered"] == "no", f"a real stopped tick pass reads as a stop, P3 not answered ({q})")
    # E813's real B3: a kick pass ended without the phase end stopped the tick: the H-KICK-MORE shape of KP
    b3 = real("e813-b3")
    b3["page"][L.ACT_SEEN] = 1               # ring_end.s did not record ACT_SEEN (ring_exit2.s does): the real pass was ACT 1
    b3["page2"][L.ACT_SEEN] = 1
    d = stage_dir("kp", {"kp": b3}, extra=[("e813-b3-regs.txt", "stop-kp-regs.txt"), ("e813-b3-status.txt", "stop-kp-status.txt")])
    S = C.Stage("kp", d, R4)
    j = dict(job("kp", "kp"), act=1)
    q, info, why = sc_kp.quantities(S, C.record(d, "kp"), j)
    check(why is None and q["kept"] == "no" and q["ticks_after_kick"] == "0" and q["read_minus_write"] == "-1" and q["dword14"] == "0"
          and q["sig_class"] == "busy" and q["miscinfo_answered"] == "no", f"E813's real B3 reads as KP's H-KICK-MORE shape: kept no, nothing after the kick, read - write -1, busy ({q})")
    # the same record under KP's own row: ACT_SEEN 1 is not the designed ACT 4: the hypothesis rows are cannot tell
    S2 = C.Stage("kp", d, R4)
    S2.table = copy.deepcopy(S2.table)
    S2.preds = [pr for pr in S2.preds if pr["case"] == "kp"]
    out = sc_kp.score_kp(S2)
    check(all(ok is None for (_c, _q, _m, kind, ok, _n) in S2.t.rows if kind != "control" and _q in ("kept", "ticks_after_kick", "sig_class")),
          "KP's rows on a pass that was not acted as designed (ACT_SEEN 1, not 4) are cannot tell")


# ---- kb2: E819's real q2 and q3 (the ring full before the kick), E816's real G0 ----------------------------------------------------
def test_kb2_real():
    recs = {"g0p": real("e816-g0"), "q2p": real("e819-q2"), "q3p": real("e819-q3")}
    d = stage_dir("kb2", recs)
    S = C.Stage("kb2", d, R4)
    q, info, why = sc_kb2.quantities(C.record(d, "g0p"), job("kb2", "g0p"))
    check(why is None and q["kick_entries"] == 1 and q["kick_entry_K"] == 2 and q["n_after_ge3"] == "no" and q["ticks_K_after"] is None,
          f"E816's real G0 (the kick entry is the last rung): one kick entry, K 2, 0 ticks after: the G0P timing control would FAIL ({q['n_after_ge3']})")
    es = L.slot_entries(real("e816-g0")["page"], 0)
    check([k for k, e in enumerate(es) if L.is_kick_entry(e)] == [len(es) - 1], "E816's real ring: the kick entry is the last of 16")

    class R4Ops(ops_kicker2.Kicker2Ops):
        pass
    nk, after = R4Ops().timing_of(real("e816-g0"))
    check((nk, after) == (1, 0) and not (nk == 1 and after >= L.KB2_MIN_AFTER), f"the runner's timing check on E816's G0: ({nk}, {after}): the stage would stop")
    q, info, why = sc_kb2.quantities(C.record(d, "q3p"), job("kb2", "q3p"))
    check(why is None and q["kick_entries"] == 0 and q["n_after_ge3"] == "no" and q["ticks_K_after"] is None and q["ticks_pa2_after"] is None
          and q["miscinfo_answered"] == "no" and q["kicker_file_after"] == "kicker 2 ccbctl 3 2 kicks 3", f"E819's real q3 under the new rule: no kick entry, no 3 ticks after the call's stamp + 8 ms (the old shape is cannot tell), not answered, E819's file ({q})")
    last = [e for e in C.merged(C.ring(real("e819-q3")["page"])) if C.e_tick(e)][-3:]
    check(any(e[4] == 0x01061A74 for e in last), "E819's real q3: the last ticks of the ring read pa2 0x01061a74 (round 4's note 0b)")
    q, info, why = sc_kb2.quantities(C.record(d, "q2p"), job("kb2", "q2p"))
    check(why is None and q["kick_entries"] == 0 and q["n_after_ge3"] == "no", f"E819's real q2: no kick entry in the ring, nothing after: cannot tell ({q['n_after_ge3']})")
    summary = sc_kb2.score_kb2(S)
    check("G0P NOT held" in summary, f"the kb2 scorer says G0P did not hold on the real E816 record ({summary[:100]})")
    check(all(ok is None for (c, qq, m, kind, ok, n) in S.t.rows if kind != "control" and c in ("q2p", "q3p")), "the stage gate made every Q2P and Q3P row cannot tell")
    # the families on a stage whose gate is shut: nothing is decided
    v = R.family_verdict(S, S.table, ("H-LATCH", "H-CNT", "H-HWC"))
    check(all(x == "cannot tell" for x in v.values()), f"no hypothesis is decided on a shut gate ({v})")


# ---- e3p: E823's real b0 and b1 ----------------------------------------------------------------------------------------------------
def test_e3p_real():
    b0, b1 = real("e823-b0"), real("e823-b1")
    for r in (b0, b1):
        r["slot3_seen"], r["slot3_wait_ms"] = True, 12.0           # the record of the new runner has them: E823's runner did not take the wait
        r["knobs"] = dict(r["knobs"])
        r["watch"] = r["watch"][1:]       # E823's first read came before the render's end (the very point of the new wait): dropped, as the new runner never takes it
    skipped = {"class": "skipped", "note": "row B1P stopped: a stopped row is never replicated", "op": "skip3p", "row": "B1P", "set": "replicate"}
    d = stage_dir("e3p", {"b0": b0, "b1p": b1, "b1p-r2": skipped, "b1p-r3": skipped})
    S = C.Stage("e3p", d, R4)
    q, info, why = sc_e3p.quantities(C.record(d, "b0"), job("e3p", "b0"))
    check(why is None and q["skipped"] == 0 and q["slot3_logged"] == "yes" and q["tool_ok"] == "yes" and q["tick_alive"] == "yes"
          and q["end_render_entries"] == 1 and q["bit18_in_watch"] == "never" and q["hold_recovery_after"] == "N", f"B0 on E823's real b0: as the plan froze it ({q})")
    q, info, why = sc_e3p.quantities(C.record(d, "b1p"), job("e3p", "b1p"))
    check(why is None and q["skipped"] == 1 and q["tick_alive"] == "no" and q["bit18_in_watch"] == "all" and q["fill_returned_in_watch"] == "no"
          and q["bit18_after_bit15"] == "1" and q["bit18_after_bit18"] == "0", f"B1P's quantities on E823's real b1 (stopped, bit 18 held, bit 15 does not clear it, bit 18 does) ({q})")
    summary = sc_e3p.score_e3p(S)
    check("B0 held" in summary and "H-W consistent" in summary and "H-SLOT3-MORE consistent" in summary and "H-PHAS-ANY REFUTED" in summary,
          f"the e3p scorer on E823's real jobs: B0 held, the stopped B1P is H-SLOT3-MORE's, the clears are H-W's ({summary[:220]})")
    # a world whose watch is too short or whose slot 3 entry is missing: the level and the clears are cannot tell
    b1s = copy.deepcopy(b1)
    b1s["watch"] = b1s["watch"][:3]
    d = stage_dir("e3p", {"b0": b0, "b1p": b1s})
    q, info, why = sc_e3p.quantities(C.record(d, "b1p"), job("e3p", "b1p"))
    check(q["bit18_in_watch"] is None and q["bit18_after_bit15"] is None and q["bit18_after_bit18"] is None, "a watch of 3 reads: the level and the clears are cannot tell")
    b1n = copy.deepcopy(b1)
    b1n["slot3_seen"] = False
    d = stage_dir("e3p", {"b0": b0, "b1p": b1n})
    S = C.Stage("e3p", d, R4)
    summary = sc_e3p.score_e3p(S)
    check(all(ok is None for (c, qq, m, kind, ok, n) in S.t.rows if kind != "control" and c == "b1p"), "no slot 3 entry in the page: every B1P row is cannot tell (the control slot3_logged fails)")


def main():
    test_engine()
    test_kp_real()
    test_kb2_real()
    test_e3p_real()
    print(f"{len(FAIL)} failed" if FAIL else "all scorer checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
