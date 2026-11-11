# SPDX-License-Identifier: MIT
"""sc_e3p.py: the scorer of stage e3p (Q166, Q111: the slot 3 pass ended with the phase end, and CLEAR).  Standard library only.

A job's quantities (text, compared with predictions/e3p.tsv):
  skipped                the task's own count of skipped slot 3 passes (the page)
  slot3_logged           yes if the page shows a slot 3 entry (the watch started from it, the runner's bounded wait did not time out)
  hold_recovery_after    the knob read back after the job (N)
  tool_ok                B0: the fill's rc 0 and `diff: 0`;   fill_returned_in_watch: the fill had returned when the 50 ms watch ended
  tick_alive             the tick after the pass (a stop is signed first by the runner)
  end_render_entries     slot 3 entries with pa0 0 and pa1[23:0] 0x10 (the fill's end of render): 1 or '>1'
  bit18_in_watch         STATUS (0x012c) bit 18 over the watch reads: all, never or mixed (cannot tell below 5 reads)
  bit18_after_bit15, bit18_after_bit18   bit 18 over the reads after each host write of CLEAR (0x0134): 1 (set in all), 0 (clear in all) or
                         mixed; read only where bit 18 was held to the write (all in the watch), else cannot tell
Hypotheses: H-PHAS-ANY / H-SLOT3-MORE (tick_alive), H-LEVEL / H-PULSE (bit18_in_watch), H-ONCE / H-REFIRE (end_render_entries), H-W / H-ALL /
H-NONE (the clears).  The gate of B1P is B0's controls (the fill without the skip, E823's B0).
"""
import r4common as R
import scorelib as C
import r4layout as L

CLASSES = {"ok", "stop"}
BIT18 = 0x40000


def bit(v):
    return None if v is None else int(bool(v & BIT18))


def text_of(bits):
    bits = [b for b in bits if b is not None]
    if not bits:
        return None
    return "all" if all(bits) else "never" if not any(bits) else "mixed"


def quantities(rec, j):
    """({quantity: value}, info text, why-not-readable or None)."""
    ev, why = R.read_page(rec.get("page"), rec.get("page2"), rec.get("window_stamp"))
    if why:
        return None, "", why
    pg = rec["page"]
    stopped = rec["class"] == "stop"
    s3 = [e for e in ev if e[0] == 3]
    er = [e for e in s3 if e[2] == 0 and (e[3] & L.LOW24) == L.SKIP3_WORD_BIT]
    watch = [w for w in (rec.get("watch") or []) if w[1] is not None]
    tool_ok = rec.get("tool_rc") == 0 and "diff: 0" in (rec.get("tool_out") or "")
    q = {"skipped": pg[L.SKIPPED], "slot3_logged": R.yn(bool(rec.get("slot3_seen")) and bool(s3)),
         "hold_recovery_after": (rec.get("knobs") or {}).get("hold_recovery_after"), "tick_alive": R.yn(not stopped),
         "end_render_entries": 1 if len(er) == 1 else ">1" if len(er) > 1 else 0}
    lvl = text_of([bit(w[1]) for w in watch]) if len(watch) >= L.E3P_MIN_WATCH else None
    q["bit18_in_watch"] = lvl
    info = (f"class {rec['class']}, skipped {pg[L.SKIPPED]}, slot 3 entries {len(s3)} (end of render {len(er)}), slot 3 seen after "
            f"{rec.get('slot3_wait_ms')} ms, watch {len(watch)} reads bit 18 {lvl}, tool rc {rec.get('tool_rc')}")
    if j["skip"] == 0:
        q["tool_ok"] = R.yn(tool_ok)
        return q, info, None
    q["fill_returned_in_watch"] = R.yn(rec.get("tool_returned_in_watch"))
    cl = rec.get("clears") or {}
    held = lvl == "all"

    def after(key):
        rs = (cl.get(key) or {}).get("reads") or []
        if not held or not rs:
            return None
        t = text_of([bit(r.get("status")) for r in rs])
        return {"all": "1", "never": "0"}.get(t, t)
    q["bit18_after_bit15"], q["bit18_after_bit18"] = after("bit15"), after("bit18")
    info += (f"; after bit 15 (reads {[(r['ms_after'], bit(r['status'])) for r in (cl.get('bit15') or {}).get('reads', [])]}) {q['bit18_after_bit15']}, "
             f"after bit 18 (reads {[(r['ms_after'], bit(r['status'])) for r in (cl.get('bit18') or {}).get('reads', [])]}) {q['bit18_after_bit18']}")
    if stopped:
        info += f"; {C.sig_line(C.rec_sig(rec))}; {C.mark_text(C.marks_from_samples((rec.get('sig') or {}).get('samples')))}; {C.p3_text(rec)}"
    return q, info, None


def score_e3p(S):
    gate_why = None
    ctl = {}
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = C.record(S.d, n)
        v = R.void_job(S, n, rec, CLASSES)
        if v and v.startswith("not run"):
            S.p(f"{n}: {v}")
            continue
        q, info, why = (None, "", v) if v else quantities(rec, j)
        if why:
            S.nodata(n, why)
            if row == "B0":
                gate_why = f"the control {n} is void ({why})"
            continue
        S.p(f"{n}: {info}")
        if rec["class"] == "stop":
            S.stop_names.append(n)
        if row == "B0":
            ok, why = R.tally_job(S, n, q)
            ctl[n] = ok
            if not ok:
                gate_why = f"the control {n} is not a pass ({why})"
            continue
        R.tally_job(S, n, q, gate_why=gate_why)
    note = S.stage_note()
    fam = {"tick": R.family_verdict(S, S.table, ("H-PHAS-ANY", "H-SLOT3-MORE")), "level": R.family_verdict(S, S.table, ("H-LEVEL", "H-PULSE")),
           "clears": R.family_verdict(S, S.table, ("H-W", "H-ALL", "H-NONE"))}
    parts = "; ".join(", ".join(f"{k} {v}" for k, v in d.items()) for d in fam.values())
    b0 = "B0 held" if ctl and all(ctl.values()) else "B0 NOT held" if ctl else "B0 not read"
    return (f"e3p: {b0}; {parts}; stops {len(S.stop_names)} {S.stop_names}; {R.controls_line(S)}; "
            f"Q166/Q111 rows: {S.t.line()}" + (f"; {note}" if note else ""))
