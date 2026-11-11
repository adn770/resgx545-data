#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_r4b.py fr OUTDIR: the scorer of R4b's stage fr (Q152: does FCF's stop of E817 repeat).  Standard library only.

The kept records are read with R3k-events' scorelib (byte for byte: the ring, the stop signature, the CCB marks, P3); every verdict
(control states, the gate, replicates, headlines) comes from scorekit (resgx545 6421c1c tools/closing/scorekit.py, byte for byte).
The frozen values are read from predictions/fr.tsv, never written here.

An FCF replicate is one of:
  REPRO       it stopped the tick with E817's exact signature: the acted pass logged (flag 3, ACT_SEEN 3) and no entry after it;
              both signature samples busy with CR_CLKGATESTATUS 0x000ccfa0, USE0_SERV_EVENT empty bit clear and frozen,
              EVENT_TIMER counting, EVENT_STATUS 0x20000000; CCB read - write 0, HostCtl dword 14 0; P3 not answered
  STOP-OTHER  it stopped the tick, and one of those differs (named)
  KEPT        it kept the tick: the next entry 25000 +- 50 after the acted pass
  None        cannot tell (no record, not run, void, the pass not acted as designed, a signature or mark that cannot be read)
H-REP: every replicate REPRO.  H-NOREP: every replicate KEPT.  A replicate is a held / FAILED / cannot tell row of each.
Controls (each PASS, FAILED or NODATA), by block: bNe0, bNfc4, bNfc4-r2, bNfb, bNfb-r2 (E817's jobs from its arm to fcf) and armN
(block N's arm resolved exit 0x1974); fkN (E817's fph, after the recovery) and rearmN (the re-arm after a stopped fcfN; PASS when
fcfN did not stop and there is none).  The gate of fcfN is block N's controls and armN, and for N > 1 fk(N-1) and rearm(N-1): any of
them that is not PASS makes fcfN cannot tell.  fk3 and rearm3 gate no replicate (no block follows them); they are reported, and with
every other control they decide the headline, which is printed only when every control passed.
"""
import json
import pathlib
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R4 = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(R4 / "gen"))
import scorekit as K  # noqa: E402
import scorelib as C  # noqa: E402
import r4blayout as L  # noqa: E402

STAGE = "fr"
SIG_ELEMENTS = ("busy", "serv_event_empty_clear", "serv_event_frozen", "timer_counting")
CLAIM_REP = "H-REP: FCF's stop reproduces with E817's exact signature"
CLAIM_NOREP = "H-NOREP: FCF keeps the tick (E817's stop does not repeat)"


def window(text):
    a, b = text.split("..")
    return int(a), int(b)


def pv(S, n, q, model=None):
    return S.pred_value(n, q, model)


def read_ring(S, n, j):
    """(rec, info, why): the record and its ring reading, or why it cannot be read."""
    rec = C.record(S.d, n)
    if rec is None:
        return None, None, "no record kept"
    if rec.get("class") == "skipped":
        return rec, None, f"not run ({rec.get('note', '').strip()})"
    v = C.void_ring(rec, C.RESULT_CLASSES_E)
    if v:
        return rec, None, v
    try:
        r = C.ring(rec["page"])
    except ValueError as e:
        return rec, None, f"corrupt ring: {e}"
    pg = rec["page"]
    ev = C.from_stamp(C.merged(r), rec.get("window_stamp"))
    s0 = [e for e in ev if e[0] == 0]
    acted = [e for e in s0 if e[1] in (L.SKIP_FLAG, L.TAIL_FLAG)]
    last = acted[-1] if acted else None
    after = [e for e in s0 if last is not None and C.rel(e[5], last[5]) > 0]
    nxt = C.rel(after[0][5], last[5]) if after else None
    info = {"entries": len(s0), "acted": len(acted), "flags": sorted({e[1] for e in s0}), "ACTED": pg[L.ACTED],
            "act_seen": pg[L.ACT_SEEN], "next": nxt, "grid": len(s0) >= 4 and all(C.on_grid(x) for x in C.gaps(s0)),
            "flag": acted[0][1] if acted else None, "drops": pg[L.DROP:L.DROP + 4]}
    if j["count"] and (pg[L.ACTED] != j["count"] or not acted or pg[L.ACT_SEEN] != j["act"]):
        return rec, info, f"the pass was not acted as designed (ACTED {pg[L.ACTED]}, logged {len(acted)}, ACT_SEEN {pg[L.ACT_SEEN]})"
    return rec, info, None


def control_state(S, j):
    """PASS, FAILED or NODATA for a control job, and its line."""
    n = j["name"]
    rec, info, why = read_ring(S, n, j)
    if why:
        return "NODATA", f"{n}: NODATA ({why})"
    line = (f"{n}: class {rec['class']}, {info['entries']} entries (acted {info['acted']}, flags {info['flags']}), ACT_SEEN "
            f"{info['act_seen']}, next entry +{info['next']}")
    if j["row"].endswith("E0"):
        lo, hi = window(pv(S, n, "entries"))
        good = rec["class"] == "ok" and lo <= info["entries"] <= hi and info["grid"] and info["acted"] == 0
        return ("PASS" if good else "FAILED"), line + f"; entries {lo}..{hi} and on the grid: {good}"
    if rec["class"] != "ok":
        return "FAILED", line + f"; {rec['class']}: the control did not keep the tick"
    mk = C.marks_of(S, rec)
    lo, hi = window(pv(S, n, "next_gap"))
    want_flag = int(pv(S, n, "flag_logged"))
    checks = {"next gap": info["next"] is not None and lo <= info["next"] <= hi, "flag": info["flag"] == want_flag,
              "read - write": mk is not None and str(mk["rmw"]) == pv(S, n, "read_minus_write"),
              "dword 14": mk is not None and (f"{mk['hc14']:#x}" if mk["hc14"] else "0") == pv(S, n, "dword14")}
    bad = [k for k, v in checks.items() if not v]
    return ("FAILED" if bad else "PASS"), line + f"; {C.mark_text(mk)}" + (f"; differs: {', '.join(bad)}" if bad else "; as E817")


def arm_file_state(S, label, stem, want, needed):
    """PASS / FAILED / NODATA of one arm record (stem.json); `needed` False and no file: PASS (no arm was due)."""
    try:
        a = json.loads((S.d / f"{stem}.json").read_text())
    except (OSError, ValueError):
        return ("NODATA" if needed else "PASS"), f"{label}: " + (f"NODATA (no {stem}.json)" if needed else "no re-arm was due")
    v = a.get("exit_index")
    return ("PASS" if v == want else "FAILED"), f"{label}: exit index {v if v is None else hex(v)} (want {want:#x})"


def replicate_state(S, j):
    """(REPRO / STOP-OTHER / KEPT / None, line)."""
    n = j["name"]
    rec, info, why = read_ring(S, n, j)
    if why:
        return None, f"{n}: cannot tell ({why})"
    base = f"{n}: class {rec['class']}, {info['entries']} entries (flags {info['flags']}), ACT_SEEN {info['act_seen']}"
    if rec["class"] in ("ok", "kick-timeout"):
        lo, hi = window(pv(S, n, "next_gap", "H-NOREP"))
        if info["next"] is None:
            return None, base + "; kept, but no entry after the acted pass: cannot tell"
        if lo <= info["next"] <= hi:
            return "KEPT", base + f"; KEPT (next entry +{info['next']})"
        return None, base + f"; kept, next entry +{info['next']} off the grid: cannot tell"
    sg = C.rec_sig(rec)
    mk = C.marks_of(S, rec)
    p3 = C.p3_of(rec)
    if sg["class"] == "unreadable" or mk is None or p3 is None:
        return None, base + f"; stop, but {'the signature' if sg['class'] == 'unreadable' else 'the marks' if mk is None else 'P3'} cannot be read"
    v = sg["values"]
    diffs = [e for e in SIG_ELEMENTS if not sg["elements"].get(e)]
    if f"{v['clkstat']:#010x}" != pv(S, n, "clkstat", "H-REP"):
        diffs.append(f"clkstat {v['clkstat']:#x}")
    if v["event_status"] is None or f"{v['event_status']:#010x}" != pv(S, n, "event_status", "H-REP"):
        diffs.append(f"event_status {v['event_status']}")
    if str(mk["rmw"]) != pv(S, n, "read_minus_write", "H-REP"):
        diffs.append(f"read - write {mk['rmw']:+d}")
    if (f"{mk['hc14']:#x}" if mk["hc14"] else "0") != pv(S, n, "dword14", "H-REP"):
        diffs.append(f"dword 14 {mk['hc14']:#x}")
    if ("yes" if p3 else "no") != pv(S, n, "p3_answered", "H-REP"):
        diffs.append("P3 answered")
    if info["next"] is not None:
        diffs.append(f"an entry {info['next']:+d} after the acted pass")
    line = base + f"; {C.sig_line(sg)}; {C.mark_text(mk)}; {C.p3_text(rec)}"
    return ("STOP-OTHER", line + "; STOP-OTHER: " + ", ".join(diffs)) if diffs else ("REPRO", line + "; REPRO (E817's signature)")


def score(d, base=None):
    S = C.Stage(STAGE, d, base or R4)
    jobs = S.table["jobs"]
    controls, reps, lines, members = {}, {}, [], {}
    want = int(S.pred_value(jobs[0]["name"], "arm_exit"), 16)
    for j in jobs:
        b = j["block"]
        if j["row"].startswith("FCF"):
            st, ln = replicate_state(S, j)
            reps[j["name"]] = st
            lines.append(ln)
            rec = C.record(S.d, j["name"])
            stopped = bool(rec) and rec.get("class") == "stop"
            st2, ln2 = arm_file_state(S, f"rearm{b}", f"rearm-{j['name']}", want, stopped)
            controls[f"rearm{b}"] = st2
            members.setdefault(b + 1, []).append(f"rearm{b}")
            lines.append(ln2)
            continue
        st, ln = control_state(S, j)
        controls[j["name"]] = st
        lines.append(ln)
        if j["row"].startswith("FK"):
            members.setdefault(b + 1, []).append(j["name"])
        else:
            members.setdefault(b, []).append(j["name"])
        if j.get("block_start"):
            rec = C.record(S.d, j["name"])
            ran = bool(rec) and rec.get("class") != "skipped"
            st2, ln2 = arm_file_state(S, f"arm{b}", f"{j['name']}.arm", want, True) if ran else ("NODATA", f"arm{b}: NODATA (not run)")
            controls[f"arm{b}"] = st2
            members.setdefault(b, []).append(f"arm{b}")
            lines.append(ln2)
    gates, rows_rep, rows_norep = {}, {}, {}
    for j in jobs:
        if not j["row"].startswith("FCF"):
            continue
        n, b = j["name"], j["block"]
        g = K.gate({k: controls[k] for k in members.get(b, [])})
        gates[n] = g.ok
        st = reps[n]
        rows_rep[n] = K.gated(g, None if st is None else st == "REPRO")
        rows_norep[n] = K.gated(g, None if st is None else st == "KEPT")
    raw_rep = [None if s_ is None else s_ == "REPRO" for s_ in reps.values()]
    raw_norep = [None if s_ is None else s_ == "KEPT" for s_ in reps.values()]
    h_rep = K.combine(rows_rep.values())
    h_norep = K.combine(rows_norep.values())
    head_rep = K.headline(CLAIM_REP, controls, raw_rep)
    head_norep = K.headline(CLAIM_NOREP, controls, raw_norep)
    gall = K.gate(controls)
    note = S.stage_note()
    ctl = "every control PASS" if gall.ok else "controls: " + "; ".join(gall.problems)
    shut = [n for n, ok_ in gates.items() if not ok_]
    summary = (f"SUMMARY: fr: {ctl}; FCF replicates {reps}; block gates shut: {shut or 'none'}; "
               f"H-REP {h_rep} ({K.tally(rows_rep.values())}); H-NOREP {h_norep} ({K.tally(rows_norep.values())}); "
               f"{head_rep} | {head_norep}" + (f"; {note}" if note else ""))
    return {"controls": controls, "controls_gate": gall.ok, "gates": gates, "reps": reps, "rows_rep": rows_rep,
            "rows_norep": rows_norep, "h_rep": h_rep, "h_norep": h_norep, "headline_rep": head_rep, "headline_norep": head_norep,
            "lines": lines, "summary": summary}


def main(argv):
    if len(argv) != 3 or argv[1] != STAGE:
        print("usage: score_r4b.py fr OUTDIR")
        return 2
    r = score(argv[2])
    for ln in r["lines"]:
        print(ln)
    print(r["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
