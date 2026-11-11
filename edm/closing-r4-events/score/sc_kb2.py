# SPDX-License-Identifier: MIT
"""sc_kb2.py: the scorer of stage kb2 (Q290: the count byte of an event and what an unbumped kick does, with the ring over the kick).
Standard library only.

A job's quantities (text, compared with the frozen rows of predictions/kb2.tsv):
  kick_entries, kick_entry_K      the kick entries of the ring (pa0 0, pa1[23:0] 0x100) and the count byte of the first
  ticks_K_before, ticks_K_after   the count byte K = pa1[31:24] of the plain ticks before and after the kick.  "After the kick" is frozen as:
                                  the ticks stamped later than the kick entry (G0P, Q2P), or, in a `kick_no_bump` row (Q3P, Q4: a kick entry
                                  may or may not come, H-LATE), later than the call's start stamp + 8.0 ms (r4layout.KB2_AFTER_MS); "before" as
                                  the ticks earlier than the kick entry, or in those rows earlier than the call's start stamp + 5.0 ms
                                  (KB2_BEFORE_MS: the write comes 6.7 ms after that stamp, E816).  One value, or cannot tell (mixed K, or
                                  fewer than 3 ticks after)
  ticks_pa2_after                 pa2 of the ticks after: 0x01061a70 (all), 0x01061a74 (all) or mixed (G0P skips the first tick after its
                                  kick entry: a tick that arrives while the kick is served is E751's latched mark by design)
  n_after_ge3                     at least 3 ticks after (the timing control: the ring covers what the rows read)
  miscinfo_answered, kicker_file_after, kick_no_bump_after, tick_alive   as E819
  serv_bit16_after                USE0_SERV_EVENT (0x0b14) bit 16 over the two signature samples after the call that timed out
  q4_kick_entries, q4_ccbctl, q4_kicker_w   Q4's second window: kick entries, `write read` offsets, the kicker word after
Hypotheses (families): the count byte H-LATCH, H-CNT, H-HWC; what an unbumped kick does H-PEND, H-NOEVENT, H-LATE.  A family verdict is
printed per hypothesis: consistent / REFUTED / mixed / cannot tell.  G0P is the timing control of the stage: if a G0P job is not a pass the
rows of Q2P, Q3P and Q4 are cannot tell (the stage stops at the first one in the runner).
"""
import r4common as R
import scorelib as C
import r4layout as L

CLASSES = {"ok", "kick-timeout", "stop"}


def hx(v):
    return None if v is None else f"{v:#010x}"


def pa2_text(vals):
    if not vals:
        return None
    u = R.unique(hx(v) for v in vals)
    return u


def k_of(e):
    return e[3] >> 24


def quantities(rec, j):
    """({quantity: value}, info text, why-not-readable or None)."""
    ev, why = R.read_page(rec.get("page"), rec.get("page2"), rec.get("window_stamp"))
    if why:
        return None, "", why
    s0 = [e for e in ev if e[0] == 0]
    ticks = [e for e in s0 if C.e_tick(e)]
    kicks = [e for e in s0 if C.e_kick(e)]
    if kicks and not j["no_bump"]:
        ref_b = ref = kicks[0][5]
        mode = "the kick entry"
    elif rec.get("stamp_before_kick") is not None:
        ref = (rec["stamp_before_kick"] + int(L.KB2_AFTER_MS * L.UNITS_PER_MS)) & 0xFFFFFFFF
        ref_b = (rec["stamp_before_kick"] + int(L.KB2_BEFORE_MS * L.UNITS_PER_MS)) & 0xFFFFFFFF
        mode = f"the call's stamp + {L.KB2_AFTER_MS} ms after, + {L.KB2_BEFORE_MS} ms before"
    else:
        return None, "", "no kick stamp recorded"
    before = [e for e in ticks if C.rel(e[5], ref_b) < 0]
    after = [e for e in ticks if C.rel(e[5], ref) > 0]
    skip_first = bool(kicks) and not j["no_bump"]  # a tick right after a served kick may be latched while the kick is served
    kb, ka = rec.get("kicker_before") or {}, rec.get("kicker_after") or {}
    q = {"kick_entries": len(kicks), "kick_entry_K": k_of(kicks[0]) if kicks else None,
         "n_after_ge3": R.yn(len(after) >= L.KB2_MIN_AFTER),
         "ticks_K_before": (R.unique(k_of(e) for e in before) if before else None),
         "miscinfo_answered": R.yn((rec.get("kick") or {}).get("answered")),
         "kicker_file_after": ka.get("raw"), "kick_no_bump_after": rec.get("no_bump_after"),
         "tick_alive": R.yn(rec.get("class") != "stop")}
    if len(after) >= L.KB2_MIN_AFTER:
        ku = R.unique(k_of(e) for e in after)
        q["ticks_K_after"] = None if ku == "mixed" else ku
        q["ticks_pa2_after"] = pa2_text([e[4] for e in (after[1:] if skip_first else after)])
    else:
        q["ticks_K_after"] = q["ticks_pa2_after"] = None
    if j["no_bump"]:
        q["serv_bit16_after"] = R.serv_bit16(rec.get("sig_after_timeout"))
    if j["second_kick"]:
        qq = rec.get("q4") or {}
        pev, pwhy = R.read_page(qq.get("page"), qq.get("page2"), qq.get("window_stamp"))
        if pwhy is None:
            q["q4_kick_entries"] = sum(1 for e in pev if C.e_kick(e))
        qa = qq.get("kicker_after") or {}
        if qa.get("wofs") is not None:
            q["q4_ccbctl"] = f"{qa['wofs']} {qa['rofs']}"
            q["q4_kicker_w"] = qa["w"]
    info = (f"class {rec['class']}, {len(ticks)} ticks, {len(kicks)} kick entries, {len(before)} ticks before and {len(after)} after "
            f"({mode}); kicker file before {kb.get('raw')!r}, after {ka.get('raw')!r}; "
            + ", ".join(f"{k} {v}" for k, v in q.items() if k not in ("kicker_file_after", "kick_no_bump_after")))
    return q, info, None


def score_kb2(S):
    gate_why = None
    ctl_jobs = {}
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
            if row == "G0P":
                gate_why = f"the timing control {n} is void ({why})"
            continue
        if rec["class"] == "stop":
            S.stop_names.append(n)
            S.p(f"{n}: {info}; a TICK STOP (a surprise: none in 13 kicker jobs); {C.sig_line(C.rec_sig(rec))}; {C.p3_text(rec)}")
        else:
            S.p(f"{n}: {info}")
        if row != "G0P" and gate_why:
            R.tally_job(S, n, q, gate_why=gate_why)
            continue
        ok, why = R.tally_job(S, n, q)
        if row == "G0P":
            ctl_jobs[n] = ok
            if not ok:
                gate_why = f"the timing control {n} is not a pass ({why})"
    note = S.stage_note()
    cnt = R.family_verdict(S, S.table, ("H-LATCH", "H-CNT", "H-HWC"))
    evt = R.family_verdict(S, S.table, ("H-PEND", "H-NOEVENT", "H-LATE"))
    fmt = lambda d: ", ".join(f"{k} {v}" for k, v in d.items())  # noqa: E731
    g0 = "G0P timing held" if ctl_jobs and all(ctl_jobs.values()) else "G0P NOT held" if ctl_jobs else "G0P not read"
    return (f"kb2: {g0}; count byte: {fmt(cnt)}; unbumped kick: {fmt(evt)}; stops {len(S.stop_names)} {S.stop_names}; "
            f"{R.controls_line(S)}; Q290 rows: {S.t.line()}" + (f"; {note}" if note else ""))
