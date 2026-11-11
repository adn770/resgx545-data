#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_r3.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...: score one R3k stage (k0f k0t k0c k0h of K0; f t kb e2b e3h e3a e3b of K1) from what the
runner kept (out/STAGE/: NAME.json, cases.tsv, stage.json, env.json, stop-*.txt).  Written before the run and frozen (run/freeze_r3.sh); refuses
unless `run/freeze_r3.sh verify` passes (skipped under R3_NO_FREEZE_CHECK=1, set by the tests only).  Prints a line a job and one `SUMMARY:`
line.  Exit 9 when a CONTROL of a K0 stage read differently from its frozen outcome (the driver stops: K0 failing stops everything).
Standard library only.  The shared readers are score/scorelib.py; the stage families are sc_ring.py (f, t, kb, G0), sc_e2b.py, sc_e3.py (e3h,
e3a, e3b); the controls of k0c and k0h are L3's (c: C0, C1; h: H0, H1) and E768's (G0).

STOP SIGNATURE (as L3): every tick stop is classed from the registers the runner dumped BEFORE the reset (two samples 30 ms apart): busy (the
clock status is not idle), idle-pending, idle-empty; `matches E537` needs busy, EMPTY clear, the count frozen and EVENT_TIMER counting; 0x012c is
recorded, not matched.  The stop's marks: the CCB read offset minus the write offset and HostCtl dword 14.

`gate STAGE ROOT` exits 0 when the previous stage's own kept stage.json (ROOT/PREV/stage.json) says it finished (exit 0, or 8: a stop budget
ended it, reset and gate exact) - derived from kept output only, so restaging never closes it.
"""
import json
import os
import pathlib
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R3 = HERE.parent
sys.path.insert(0, str(R3 / "gen"))
sys.path.insert(0, str(HERE))
import r3layout as L  # noqa: E402
import scorelib as C  # noqa: E402
from scorelib import *  # noqa: E402,F401,F403
import sc_ring  # noqa: E402
import sc_e2b  # noqa: E402
import sc_e3  # noqa: E402

T = L.TICK_UNITS
CONTROL_STAGES = ("k0f", "k0t", "k0c", "k0h")


def yn(b):
    return "yes" if b else "no"


def hold_band(rec, n):
    pg = rec["page"]
    h = rel(pg[L.HOLD_EXIT], pg[L.HOLD_ENTRY])
    want = L.hold_units_of(n)
    return abs(h - want) <= 0.002 * want + 50, h, want



def score_hold(S):
    """k0h's H0 (idle, a control) and H1 (a signature inside the 90-tick hold, a control with L3's frozen outcome)."""
    out = []
    for j in S.table["jobs"]:
        if j["op"] != "holdsig":
            continue
        n, row = j["name"], j["row"]
        rec = C.record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        v = C.void_ring(rec, C.RESULT_CLASSES_H)
        if v:
            S.nodata(n, v)
            out.append(f"{row} void")
            continue
        ins = rec.get("inside") or []
        if rec["class"] == "stop":
            S.stop_names.append(n)
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "the tick stopped")
            S.p(f"{n}: class stop (the tick stopped in a stage-k0h job: a surprise); {C.sig_line(C.rec_sig(rec))}; {C.p3_text(rec)}")
            out.append(f"{row} STOPPED")
            continue
        sigs = [C.score_sig(i["samples"]) for i in ins]
        if row == "H0":
            idle = bool(sigs) and all(sg["class"] == "idle-empty" and sg["values"]["clkstat"] in C.CLK_IDLE_VALUES for sg in sigs if sg["class"] != "unreadable") \
                and all(sg["class"] != "unreadable" for sg in sigs)
            C.Stage.tally_value(S, n, "idle", yn(idle))
            S.p(f"{n}: class ok; signatures {[sg['class'] for sg in sigs]}; idle {idle}")
            out.append("H0 idle" if idle else "H0 DIFFERS")
            continue
        band, hu, hw = hold_band(rec, j["n"])
        C.Stage.tally_value(S, n, "hold_band", yn(band))
        inside = [bool(i["state"]) and all(x == L.STATE_BUSY for x in i["state"]) for i in ins]
        if len(ins) < 2 or not all(inside) or any(sg["class"] == "unreadable" for sg in sigs):
            S.p(f"{n}: class ok; hold {hu} units (want {hw:.0f}, band {band}); a signature fell outside the hold or is unreadable: cannot tell")
            C.Stage.tally_value(S, n, "elements", None)
            out.append("H1 cannot tell")
            continue
        allm = all(sg["matches_e537"] and sg["values"]["clkstat"] == C.CLK_BUSY for sg in sigs)
        C.Stage.tally_value(S, n, "elements", "all" if allm else "some_differ")
        S.p(f"{n}: class ok, hold {hu} units (want {hw:.0f}, band {band}); signatures {[sg['class'] for sg in sigs]}, all elements as a running task {allm}")
        out.append("H1 as L3's" if allm and band else "H1 DIFFERS")
    return out


def score_k0h(S):
    hold = score_hold(S)
    kick = sc_ring.score_kicker(S)
    return f"k0h: {'; '.join(hold)}; {kick}"


def failed_controls(S):
    return [r for r in S.t.rows if r[3] == "control" and r[4] is False]


def k0_cannot_tell(S):
    """Why a K0 headline may not be printed although no control FAILED (post-run fix C3, POSTRUN-FIX.md): no row decided,
    or a control row that cannot tell (a job without data); None when the headline may stand."""
    ctl = [r for r in S.t.rows if r[3] == "control"]
    ct = [r for r in ctl if r[4] is None]
    if not any(r[4] is not None for r in S.t.rows):
        return "no row decided"
    if not ctl or ct:
        return f"{len(ct)} of {len(ctl)} control rows cannot tell ({', '.join(sorted({r[0] for r in ct}))})"
    return None


# ---- stage k0f -------------------------------------------------------------------------------------------------------------
def score_defaults(S):
    for j in S.table["jobs"]:
        n = j["name"]
        rec = C.record(S.d, n)
        if rec is None or rec.get("class") != "ok":
            S.nodata(n, f"class {None if rec is None else rec.get('class')}")
            continue
        sv = rec.get("srcversion") or {}
        kk = rec.get("kicker") or {}
        rows = [tuple(x) for x in (rec.get("kregnow") or {}).get("rows", [])]
        offs = [x[0] for x in rows]
        got = {"files_present": yn(all((rec.get("files") or {}).values())), "srcversion_new": yn(sv.get("loaded") == sv.get("installed") == os.environ.get("R3_SRCV_EXPECT", L.EXPECT_SRCV)),
               "kicker_format": yn(kk.get("w") is not None),
               "kicker_w_eq_wofs": None if kk.get("w") is None else yn((kk["w"] & 0xFF) == (kk["wofs"] & 0xFF)),
               "kregnow_rows": len(rows), "kregnow_no_clear_rows": yn(not any(o in L.K0F_KREGNOW_ABSENT for o in offs)),
               "kregnow_bif_rows": yn(all(o in offs for o in L.K0F_KREGNOW_PRESENT)),
               "kicks_eq_wofs": None if kk.get("w") is None else yn(kk["kicks"] == kk["wofs"])}
        got.update({k: (rec.get("defaults") or {}).get(k) for k in L.K0F_DEFAULTS})
        for q, v in got.items():
            C.Stage.tally_value(S, n, q, v)
        S.p(f"{n}: class ok; files {rec.get('files')}; defaults {rec.get('defaults')}; kicker {kk.get('raw')!r}; kregnow rows {[hex(o) for o in offs]}; "
            f"srcversion {sv.get('loaded')}")
    note = S.stage_note()
    f = failed_controls(S)
    ct = k0_cannot_tell(S)
    head = 'DEFAULTS DIFFER: ' + ', '.join(sorted({r[1] for r in f})) if f else f"cannot tell: {ct}" if ct else 'defaults as designed'
    return f"k0f: {head}; K0 rows: {S.t.line()}" + (f"; {note}" if note else "")


# ---- stage k0t -------------------------------------------------------------------------------------------------------------
def score_tool(S):
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = C.record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        if rec is None or rec.get("class") != "ok":
            S.nodata(n, f"class {None if rec is None else rec.get('class')}")
            continue
        fz = j["frozen"]
        got = {"rc": rec.get("tool_rc"), "class": rec.get("class"), "o0_line": yn(fz["o0_line"] in (rec.get("o0_lines") or []))}
        if row == "GD":
            got["lines_sha256"] = yn(rec.get("lines_sha256") == fz["lines_sha256"])
            ds = rec.get("dump_sha256") or {}
            got["param_sha256"] = yn(ds.get("dd-p1__0.param.bin") == fz["param_sha256"])
            got["tadata_sha256"] = yn(ds.get("dd-p1__0.tadata.bin") == fz["tadata_sha256"])
        else:
            got["status2_pre"] = f"{rec['status2_pre']:#x}" if rec.get("status2_pre") is not None else None
            got["status2_post"] = f"{rec['status2_post']:#x}" if rec.get("status2_post") is not None else None
        for q, v in got.items():
            C.Stage.tally_value(S, n, q, v)
        S.p(f"{n}: class ok; tool rc {rec.get('tool_rc')}; o0 lines {rec.get('o0_lines')}; " + ", ".join(f"{k} {v}" for k, v in got.items() if k not in ("rc", "class")))
    note = S.stage_note()
    f = failed_controls(S)
    ct = k0_cannot_tell(S)
    head = ('CONTROL DIFFERS: ' + ', '.join(sorted({r[0] + ' ' + r[1] for r in f})) if f else f"cannot tell: {ct}" if ct
            else 'both jobs as L1 and L2 kept them')
    return f"k0t: {head}; K0 rows: {S.t.line()}" + (f"; {note}" if note else "")


# ---- stages c and d ------------------------------------------------------------------------------------------------------
RESULT_CLASSES_ALIAS = RESULT_CLASSES_C


def rd_of(r):
    return dict(zip(L.RD_FIELDS, r)) if isinstance(r, list) and len(r) >= len(L.RD_FIELDS) else None


def void_alias2(rec, j):
    if rec is None:
        return "no record kept"
    if rec.get("class") == "skipped":
        return "not run (" + rec.get("note", "").strip() + ")"
    if rec.get("class") not in RESULT_CLASSES_ALIAS:
        return f"class {rec.get('class')}"
    cmd = j["cmd"]
    wr = rec.get("writer") or {}
    if cmd and not wr.get("done"):
        return "the writer's flag was not set (it did not run)"
    if not cmd:
        return None
    if not isinstance(wr.get("wr"), list):
        return "no writer record"
    w = dict(zip(L.WR_FIELDS, wr["wr"]))
    K = (rec.get("ccbctl_pre") or [None])[0]
    if cmd in (L.CMD_WORD65, L.CMD_E537, L.CMD_RUN64):
        if w["written"] != w["readback"]:
            return f"the read-back ({w['readback']:#x}) is not what the writer wrote ({w['written']:#x}): the write did not take"
        if K is not None and (w["sa65_before"] >> 24) != (K & 0xFF):
            return f"the task's own record of sa65 at entry has count byte {w['sa65_before'] >> 24:#x}, not K = {K & 0xFF:#x}"
    if cmd in (L.CMD_WORD65, L.CMD_E537) and rec.get("w65_word") is not None and w["written"] != rec["w65_word"] & 0xFFFFFFFF:
        return f"the word written ({w['written']:#x}) is not the row's ({rec['w65_word']:#x})"
    if cmd == L.CMD_E537:
        x = dict(zip(L.WR_X_FIELDS, wr["wr"][L.WR_X - L.WR:L.WR_X - L.WR + 4]))
        if x["sa63_w"] != x["sa63_rb"] or x["sa64_w"] != x["sa64_rb"]:
            return "D4: an sa read-back is not what the writer wrote"
    if cmd == L.CMD_RUN64 and rec.get("class") == "ok":
        br = rec.get("bracket") or {}
        try:
            passes = br["after"][0] - br["before"][2]
        except (KeyError, TypeError, IndexError):
            passes = None
        if passes is None or passes < j["npass"]:
            return f"C5's own pass counter advanced {passes}, not the {j['npass']} passes of the row"
    return None


def score_alias2(S):
    stage = S.stage
    ctl_ok = None
    kept, stops, results = {}, [], {}
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = record(S.d, n)
        v = void_alias2(rec, j)
        if v and rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        if v:
            S.nodata(n, v)
            continue
        cls = rec["class"]
        rd1 = rd_of((rec.get("reader") or {}).get("rd")) if (rec.get("reader") or {}).get("ran") else None
        K = (rec.get("ccbctl_pre") or [None])[0]
        K = None if K is None else K & 0xFF
        kept_obs = True if cls == "ok" else False if cls == "stop" else None
        kept.setdefault(row, []).append(kept_obs)
        info = f"{n}: class {cls}"
        for pr in S.preds:
            if pr["case"] == n and pr["quantity"] == "kept":
                S.t.add(n, "kept", pr["model"], pr["set"], None if kept_obs is None else (kept_obs == (pr["value"] == "yes")),
                        "reader not run" if kept_obs is None else "")
        if cls == "stop":
            sg = rec_sig(rec)
            mk = marks_of(S, rec)
            stops.append((n, sg, mk))
            S.stop_names.append(n)
            score_marks_and_p3(S, n, rec, mk, sg, kept=False)
            S.p(info + f" (tick stopped after the writer's pass); {sig_line(sg)}; {mark_text(mk)}; {p3_text(rec)}; {d_text(rec)}")
            continue
        if cls == "noreader":
            S.p(info + " (tick kept, the reader did not run: cannot tell)")
            continue
        if rd1 is None:
            S.p(info + " (kept but no reader record: cannot tell)")
            continue
        got = {"pclink": rd1["pclink"], "p1": rd1["p1"], "sa64": rd1["sa64"], "sa65": rd1["sa65"], "sa63": rd1["sa63"]}
        results[n] = got
        mk = marks_of(S, rec)
        if row in ("C0", "D0"):
            want = {"pclink": 0x98, "p1": 1, "sa64": 2, "sa65": (K << 24) if K is not None else None, "sa63": 0}
            diff = {k: (got[k], want[k]) for k in want if want[k] is None or got[k] != want[k]}
            ok_c = not diff
            ctl_ok = ok_c if ctl_ok is None else (ctl_ok and ok_c)
            for q in want:
                S.tally_preds(n, q, {"E791 A0": None if want[q] is None else got[q] == want[q]})
            S.p(info + f"; reader pclink {got['pclink']:#x} p1 {got['p1']} sa64 {got['sa64']:#x} sa65 {got['sa65']:#x} sa63 {got['sa63']:#x}; "
                + mark_text(mk) + ("" if ok_c else f"; {row} DIFFERS {diff}"))
            continue
        dn = ""
        if row in ("C1", "C2", "C3", "C4"):
            S.tally_preds(n, "next_pclink", {"E15": None if not ctl_ok else got["pclink"] == 0x98})
            S.tally_preds(n, "next_sa65", {"E15": None if not ctl_ok or K is None else got["sa65"] == K << 24})
            dn = f"; next entry pclink {got['pclink']:#x}, sa65 {got['sa65']:#x} (K << 24 = {(K or 0) << 24:#x})"
        if row == "C5":
            iv = d12_minus_passes(rec)
            S.tally_preds(n, "pclink", {"E792": None if not ctl_ok else got["pclink"] == 6})
            S.tally_preds(n, "d12_delta", {"E792": interval_near(iv, -j["npass"], 8)})
            d0 = d0_of(rec)
            dp = d_mode(d_vals(rec.get("d_post")))[0]
            shift = None if d0 is None or dp is None else dp - d0
            S.tally_preds(n, "d_shift", {"E792": None if shift is None else abs(shift - j["npass"]) <= 1})
            dn = f"; pclink {got['pclink']:#x} (want 0x6), d12 - passes in {iv} (want {-j['npass']} +-8), D shift {shift} (want {j['npass']} +-1)"
        score_marks_and_p3(S, n, rec, mk, None, kept=True)
        S.p(info + dn + "; " + mark_text(mk))
    note = S.stage_note()
    if ctl_ok is None:
        S.p("control: no readable control")
    nk = sum(1 for v in kept.values() for k in v if k is True)
    nt = sum(len(v) for v in kept.values())
    p3s = f"; P3 answered in {sum(1 for _, a in S.p3 if a)} of {len(S.p3)} stops" if S.p3 else ""
    if True:
        verdict = "C0 held" if ctl_ok else ("C0 DIFFERS" if ctl_ok is False else "C0 not read")
        rd = "; ".join(f"{r} kept {sum(1 for k in v if k is True)} of {len(v)}" for r, v in kept.items() if r != "C0")
        return (f"{stage}: {verdict}; {rd}; stops {len(S.stop_names)} {S.stop_names}{p3s}; Q152 rows: {S.t.line()}" + (f"; {note}" if note else ""))



SCORERS = {"k0f": score_defaults, "k0t": score_tool, "k0c": score_alias2, "k0h": score_k0h, "f": sc_ring.score_act, "t": sc_ring.score_act,
           "kb": sc_ring.score_kicker, "e2b": sc_e2b.score_e2b, "e3h": sc_e3.score_e3, "e3a": sc_e3.score_e3, "e3b": sc_e3.score_e3b}


# ---- gate, freeze, main ---------------------------------------------------------------------------------------------------
def gate(stage, root):
    """0 when the previous stage finished according to its own kept stage.json (derived from kept output only)."""
    prev = C.GATE_OF.get(stage)
    if not prev:
        print(f"GATE {stage} OPEN (no previous stage)")
        return 0
    try:
        st = json.loads((pathlib.Path(root) / prev / "stage.json").read_text())
    except (OSError, ValueError):
        print(f"GATE {stage} CLOSED: no kept stage.json of {prev} under {root}")
        return 1
    if st.get("exit") in C.GATE_EXITS:
        print(f"GATE {stage} OPEN: {prev} finished (exit {st.get('exit')}, run {st.get('run')})")
        return 0
    print(f"GATE {stage} CLOSED: {prev} exit {st.get('exit')} ({st.get('why', '')[:80]})")
    return 1


def freeze_problem():
    if os.environ.get("R3_NO_FREEZE_CHECK") == "1":
        return None
    r = subprocess.run([str(R3 / "run" / "freeze_r3.sh"), "verify"], capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stdout + r.stderr).strip().splitlines()[-1:]


def score(stage, d, base=None):
    S = C.Stage(stage, d, base)
    summary = SCORERS[stage](S)
    return S, summary


def main(argv):
    if len(argv) >= 4 and argv[1] == "gate":
        return gate(argv[2], argv[3])
    if len(argv) >= 3 and argv[1] == "sig":
        for f in argv[2:]:
            text = pathlib.Path(f).read_text()
            sm = []
            for part in text.split("\n===\n"):
                r, hc = C.parse_regs_text(part)
                sm.append({"regs": {hex(k): v for k, v in r.items()}, "hc12": hc.get(12)})
            print(f, C.sig_line(C.score_sig(sm)))
        return 0
    if len(argv) < 3 or argv[1] not in SCORERS:
        print("usage: score_r3.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...")
        return 2
    prob = freeze_problem()
    if prob:
        print(f"REFUSING: the frozen files changed ({prob})")
        return 3
    S, summary = score(argv[1], argv[2])
    for ln in S.lines:
        print(ln)
    print("SUMMARY: " + summary)
    if argv[1] in CONTROL_STAGES and failed_controls(S):
        print("CONTROL FAILED: " + "; ".join(f"{r[0]} {r[1]}" for r in failed_controls(S)))
        return 9
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
