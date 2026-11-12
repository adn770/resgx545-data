# SPDX-License-Identifier: MIT
"""sc_h.py: the scorer of stages h1, h2, h3 of R5-events (Q295's lockup check, Q166's clears).  Standard library only.  R4-events'
sc_e3p.py with the lockup marks, the count and the clock added, and a replay mode for kept records of earlier rounds.

A job's quantities (text, compared with predictions/STAGE.tsv; None = cannot tell, with the reason and, for a missing file, its path):
  skipped, slot3_logged, hold_recovery_after          the design echoed back (the page, the record)
  timer_clock_read                                    the knob read back before the job's reset
  arm_dword6, arm_marks                               HostCtl dword 6, and dwords 3 and 8 ("3 8"), in the arm's status dump (rec status_arm)
  tick_gap                                            the median gap of the slot 0 ring's consecutive ticks (CR_TIMER units):
                                                      "G+-T" when within the clock's tolerance, else the number (fewer than 3 ticks: None)
  tick_alive, end_render_entries, bit18_in_watch      as R4 (bit 18 over the watch: all, never, mixed; fewer than 5 reads: None)
  tool_ok, post_marks                                 B0: the fill's rc 0 and diff 0; dwords 3 and 8 in the status dump after the watch
  fill_returned_in_watch                              B1P / B1E
  lockups, iflags, sw_events, dword9, dword14, ccb    the STOP's status dump (stop-NAME-status.txt, taken at the signature, before any
  dword57, dword58, ta3d_dword28, status_bit6         clear): lockups = dword 3 there minus dword 3 at the arm; iflags = dword 8; ccb "w r";
                                                      dword58 "nonzero" / "0"; status_bit6 = EVENT_STATUS bit 6 "clear" / "set"
                                                      (a job that kept the tick: lockups and iflags from the dump after the watch)
  dpm_task_state                                      0x0694 in stop-NAME-regs.txt (the rgn4 kernel prints `skip` there: None)
  p3_answered, sig_event_status                       P3 after the stop; EVENT_STATUS in the first signature sample
  ticks_after_kick                                    a STOP's count (r5layout.count_after_kick on stop-NAME-own_res.json, else the job's page):
                                                      the ring's ticks after the fill's kick entry + page dword 16
  bit18_after_bit15, bit18_after_bit18                h1 (late) and h3 (early): bit 18 over the reads after each host write: 1, 0, mixed;
                                                      read only where bit 18 was set before the writes (h1: all in the watch; h3: the
                                                      read before the clears), else None
  bit18_before_clears, misc_answered, misc_kick_in_ring   h3's early clears and the miscinfo after them
The control gate: a job's control that is not a pass makes its other rows cannot tell; B0's controls gate the stage's rows (h2: the
rows of its clock).  Hypotheses (families): H-HWR / H-NOMARK, H-TICKS / H-TIME, H-STATE / H-ACK18, H-LEVEL / H-PULSE, H-W / H-ALL / H-NONE.
"""
import json
import pathlib

import r5common as R
import scorelib as C
import r5layout as L

CLASSES = {"ok", "stop"}
FAMILIES = {"h1": [("H-HWR", "H-NOMARK"), ("H-TICKS",), ("H-LEVEL", "H-PULSE"), ("H-W", "H-ALL", "H-NONE")],
            "h2": [("H-HWR", "H-NOMARK"), ("H-TICKS", "H-TIME"), ("H-LEVEL", "H-PULSE")],
            "h3": [("H-STATE", "H-ACK18"), ("H-TICKS",), ("H-LEVEL",), ("H-W", "H-ALL", "H-NONE")]}


def bit(v, b=L.BIT18):
    return None if v is None else int(bool(v & b))


def text_of(bits):
    bits = [b for b in bits if b is not None]
    if not bits:
        return None
    return "all" if all(bits) else "never" if not any(bits) else "mixed"


def read_text(p):
    try:
        return pathlib.Path(p).read_text()
    except OSError:
        return None


def stop_page(d, name, rec):
    """The stop's own_res dump (the page at the signature), else the job's page."""
    t = read_text(pathlib.Path(d) / f"stop-{name}-own_res.json")
    if t:
        try:
            pg = json.loads(t)
            if isinstance(pg, list) and len(pg) == L.PAGE_DWORDS:
                return pg, f"stop-{name}-own_res.json"
        except ValueError:
            pass
    return rec.get("page"), "the job's page"


def quantities(rec, j, d, base_lockups=None):
    """({quantity: value}, {quantity: why None}, info text, why-not-readable or None)."""
    name = rec["name"]
    why = {}
    ev, w = R.read_page(rec.get("page"), rec.get("page2"), rec.get("window_stamp"))
    if w:
        return None, {}, "", w
    pg = rec["page"]
    clock = j.get("timer_clock", 0)
    stopped = rec["class"] == "stop"
    s3 = [e for e in ev if e[0] == 3]
    er = [e for e in s3 if e[2] == 0 and (e[3] & L.LOW24) == L.SKIP3_WORD_BIT]
    watch = [x for x in (rec.get("watch") or []) if x[1] is not None]
    q = {"skipped": pg[L.SKIPPED], "slot3_logged": R.yn(bool(rec.get("slot3_seen")) and bool(s3)),
         "hold_recovery_after": (rec.get("knobs") or {}).get("hold_recovery_after"), "tick_alive": R.yn(not stopped),
         "end_render_entries": 1 if len(er) == 1 else ">1" if len(er) > 1 else 0,
         "timer_clock_read": rec.get("timer_clock_read")}
    if q["timer_clock_read"] is None:
        why["timer_clock_read"] = "no knob read-back in the record (a round before r5)"
    # the arm's dump
    ma = L.parse_marks(rec.get("status_arm")) if rec.get("status_arm") else None      # the text (a record's JSON keys are strings)
    if ma:
        q["arm_dword6"] = ma["hc"].get(L.HC_CLOCK)
        q["arm_marks"] = f"{ma['hc'].get(L.HC_LOCKUPS)} {ma['hc'].get(L.HC_IFLAGS)}"
        base = ma["hc"].get(L.HC_LOCKUPS, 0)
    else:
        why["arm_dword6"] = why["arm_marks"] = "no arm status dump in the record (a round before r5)"
        base = base_lockups
    # the clock's grid
    g = L.tick_gap(pg)
    G, tol = L.gap_units(clock), L.GAP_TOL[clock]
    if g is None:
        why["tick_gap"] = f"fewer than {L.H_MIN_TICKS} ticks in the slot 0 ring"
        q["tick_gap"] = None
    else:
        q["tick_gap"] = f"{G}+-{tol}" if abs(g - G) <= tol else str(g)
    lvl = text_of([bit(x[1]) for x in watch]) if len(watch) >= L.H_MIN_WATCH else None
    if lvl is None:
        why["bit18_in_watch"] = f"a watch of {len(watch)} reads (fewer than {L.H_MIN_WATCH})"
    q["bit18_in_watch"] = lvl
    info = (f"class {rec['class']}, clock {clock}, skipped {pg[L.SKIPPED]}, slot 3 entries {len(s3)} (end of render {len(er)}), "
            f"slot 3 seen after {rec.get('slot3_wait_ms')} ms, gap {g}, watch {len(watch)} reads bit 18 {lvl}, tool rc {rec.get('tool_rc')}")
    if not j["skip"]:
        q["tool_ok"] = R.yn(rec.get("tool_rc") == 0 and "diff: 0" in (rec.get("tool_out") or ""))
        mp = L.parse_marks(rec.get("status_post")) if rec.get("status_post") else None
        q["post_marks"] = f"{mp['hc'].get(L.HC_LOCKUPS)} {mp['hc'].get(L.HC_IFLAGS)}" if mp else None
        if not mp:
            why["post_marks"] = "no status dump after the watch in the record (a round before r5)"
        return q, why, info, None
    q["fill_returned_in_watch"] = R.yn(rec.get("tool_returned_in_watch"))
    # the marks
    sp = pathlib.Path(d) / f"stop-{name}-status.txt"
    if stopped:
        st = read_text(sp)
        m = L.parse_marks(st) if st else None
        if not m:
            for k in ("lockups", "iflags", "sw_events", "dword9", "dword14", "ccb", "dword57", "dword58", "ta3d_dword28", "status_bit6"):
                why[k] = f"no stop status dump: {sp}"
        else:
            hc, ta = m["hc"], m["ta"]
            if base is None:
                why["lockups"] = "no arm dump and no baseline given"
            else:
                q["lockups"] = hc.get(L.HC_LOCKUPS, 0) - base
            q["iflags"] = hc.get(L.HC_IFLAGS)
            q["sw_events"] = m["sw_events"]
            q["dword9"] = hc.get(L.HC_ICLEAR)
            q["dword14"] = hc.get(L.HC_ASSERT_DWORD)
            cc = L.parse_status(st)[2]
            q["ccb"] = f"{cc[0]} {cc[1]}" if cc else None
            q["dword57"] = ta.get(L.TA_COUNT3D)
            d58 = ta.get(L.TA_SIG3D)
            q["dword58"] = None if d58 is None else ("nonzero" if d58 else "0")
            q["ta3d_dword28"] = ta.get(L.TA_CTX3D)
            es = m["regs"].get(L.REG_EVENT_STATUS)
            q["status_bit6"] = None if es is None else ("set" if es & L.EVENT_BIT6 else "clear")
        rp = pathlib.Path(d) / f"stop-{name}-regs.txt"
        kind, v = L.regs_value(read_text(rp), L.REG_DPM_TASK_STATE)
        q["dpm_task_state"] = v if kind == "value" else None
        if kind != "value":
            why["dpm_task_state"] = (f"0x0694 reads `skip` in {rp.name}: the kernel's regs file never reads it (fork a2788bd8 "
                                     "sgxfive_regdump.c)" if kind == "skip" else f"no stop regs dump: {rp}")
        p3 = rec.get("p3")
        q["p3_answered"] = None if not p3 else R.yn(p3.get("answered"))
        smp = [s for s in ((rec.get("sig") or {}).get("samples") or []) if isinstance(s, dict) and "regs" in s]
        es0 = smp[0]["regs"].get(hex(L.REG_EVENT_STATUS)) if smp else None
        q["sig_event_status"] = None if es0 is None else f"0x{es0:08x}"
        spg, src = stop_page(d, name, rec)
        cnt, cinfo, cwhy = L.count_after_kick(spg) if isinstance(spg, list) else (None, {}, "no page")
        q["ticks_after_kick"] = cnt
        if cnt is None:
            why["ticks_after_kick"] = cwhy
        info += (f"; stop: lockups {q.get('lockups')} dword 8 {q.get('iflags')} sw_events {q.get('sw_events')} d57 {q.get('dword57')} "
                 f"d58 {d58 if m else None} ccb {q.get('ccb')} status 0x{(es if m and es is not None else 0):08x}; count {cnt} from {src} "
                 f"{cinfo}; {C.p3_text(rec)}")
    else:
        mp = L.parse_marks(rec.get("status_post")) if rec.get("status_post") else None
        if mp:
            q["lockups"] = mp["hc"].get(L.HC_LOCKUPS, 0) - (base or 0)
            q["iflags"] = mp["hc"].get(L.HC_IFLAGS)
        for k in ("sw_events", "dword9", "dword14", "ccb", "dword57", "dword58", "ta3d_dword28", "status_bit6", "dpm_task_state",
                  "p3_answered", "sig_event_status", "ticks_after_kick"):
            why[k] = "no stop: a stop's reading"
    # the clears
    cl = rec.get("clears") or {}
    if j.get("clears") == "early":
        sb = (rec.get("status_before_clears") or {}).get("status")
        q["bit18_before_clears"] = None if sb is None else str(bit(sb))
        held = q["bit18_before_clears"] == "1"
        m = rec.get("misc") or {}
        q["misc_answered"] = None if not m else R.yn(m.get("answered"))
        s0 = L.slot_entries(pg, 0)
        kicks = [i for i, e in enumerate(s0) if L.is_kick_entry(e)]
        q["misc_kick_in_ring"] = R.yn(len(kicks) >= 2 and any(L.is_tick_entry(e) for e in s0[kicks[1] + 1:]))
    else:
        held = lvl == "all"

    def after(key):
        rs = (cl.get(key) or {}).get("reads") or []
        if not held or not rs:
            why[f"bit18_after_{key}"] = "no reads" if not rs else "bit 18 was not set before the writes"
            return None
        t = text_of([bit(r.get("status")) for r in rs])
        return {"all": "1", "never": "0"}.get(t, t)
    if j.get("clears") in ("late", "early") or cl:
        q["bit18_after_bit15"], q["bit18_after_bit18"] = after("bit15"), after("bit18")
        info += f"; clears: after bit 15 {q['bit18_after_bit15']}, after bit 18 {q['bit18_after_bit18']}"
    return q, why, info, None


def score_stage(S):
    stage = S.stage
    S.why_none = {}
    gate = {}                        # clock group -> why the group's B0 gates its rows (None: it passed)
    ctl = {}
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        grp = L.CLOCK_GROUP.get(row, "all")
        rec = C.record(S.d, n)
        v = R.void_job(S, n, rec, CLASSES)
        if v and v.startswith("not run"):
            S.p(f"{n}: {v}")
            continue
        q, why, info, w = (None, {}, "", v) if v else quantities(rec, j, S.d)
        if w:
            S.nodata(n, w)
            if not j["skip"]:
                gate[grp] = f"the control {n} is void ({w})"
            continue
        for k, r in why.items():
            S.why_none[(n, k)] = r
        S.p(f"{n}: {info}")
        if rec["class"] == "stop":
            S.stop_names.append(n)
        if not j["skip"]:
            ok, why_c = R.tally_job(S, n, q)
            ctl[n] = ok
            if not ok:
                gate[grp] = f"the control {n} is not a pass ({why_c})"
            continue
        R.tally_job(S, n, q, gate_why=gate.get(grp))
    note = S.stage_note()
    fam = [R.family_verdict(S, S.table, f) for f in FAMILIES[stage]]
    parts = "; ".join(", ".join(f"{k} {v}" for k, v in d.items()) for d in fam)
    b0 = ("B0 held" if ctl and all(ctl.values()) else f"B0 NOT held ({[k for k, v in ctl.items() if not v]})" if ctl else "B0 not read")
    return (f"{stage}: {b0}; {parts}; stops {len(S.stop_names)} {S.stop_names}; {R.controls_line(S)}; "
            f"Q295/Q166 rows: {S.t.line()}" + (f"; {note}" if note else ""))


def replay(stage, as_job, d, name, base_lockups=0, root=None):
    """A kept record of an earlier round (d/name.json and its stop dumps) read as job `as_job` of `stage`: every frozen row of that job,
    with its verdict (True held, False FAILED, None cannot tell) and the reason.  No gate is applied (the rows are shown).  The arm
    baseline of dword 3 is `base_lockups` when the record has no arm dump (rounds before r5; E849: no kept dump before r4's b1p reads
    dword 3 non-zero).  Returns [(quantity, value, model, set, got, ok, note)]."""
    preds = [p for p in C.load_preds(stage, root) if p["case"] == as_job]
    j = next(x for x in C.load_table(stage, root)["jobs"] if x["name"] == as_job)
    rec = json.loads((pathlib.Path(d) / f"{name}.json").read_text())
    rec["name"] = name
    q, why, info, w = quantities(rec, j, d, base_lockups=base_lockups)
    out = []
    for p in preds:
        got = None if q is None else q.get(p["quantity"])
        ok = None if got is None else R.match(p["value"], got)
        note = w or ("" if got is not None else why.get(p["quantity"], "not measured"))
        out.append((p["quantity"], p["value"], p["model"], p["set"], got, ok, note))
    return out, info
