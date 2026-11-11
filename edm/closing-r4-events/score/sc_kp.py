# SPDX-License-Identifier: MIT
"""sc_kp.py: the scorer of stage kp (Q152: a kick pass ended with the phase end).  Standard library only.

Rows: E0 (nothing acted: 12 to 16 entries on the grid), FK (a plain tick pass ended `idf, wdf, phas end, nop.end`: the control of E830's fk), KP (a
kick pass ended the same way, one `miscinfo` into the pass).  A job's quantities (text, compared with predictions/kp.tsv):
  acted, flag_logged, kept, next_gap, next_gap_exact   as the earlier stage f: ACTED in the page, the acted entry's flag, the tick kept, the
                                                       next entry after the acted pass (a window and the exact 24994 or 24995)
  entries, grid                                        E0: the entries of slot 0 and whether every gap is on the 25000 grid
  ticks_after_kick                                     KP: plain ticks on the grid after the kick entry: '>=4' or the count (cannot tell if the
                                                       ring was full before the kick entry or the kick pass was not acted as designed)
  sig_class                                            KP: the signature read twice right after the unanswered call: idle or busy
  miscinfo_answered, read_minus_write, dword14, p3_answered   as E813 B3: the unread command (read = write - 1), HostCtl dword 14, P3
Hypotheses: H-PHAS-ANY (any pass ended with the phase end is finished for the EDM: KP keeps the tick) and H-KICK-MORE (a kick pass needs more:
KP stops, E813 B3's shape).  The gate of KP is E0 and FK (controls): either not a pass makes the KP rows cannot tell.
"""
import r4common as R
import scorelib as C
import r4layout as L

CLASSES = {"ok", "kick-timeout", "stop"}
T = L.TICK_UNITS


def quantities(S, rec, j):
    """({quantity: value}, info text, why-not-readable or None)."""
    ev, why = R.read_page(rec.get("page"), rec.get("page2"), rec.get("window_stamp"))
    if why:
        return None, "", why
    pg = rec["page"]
    s0 = [e for e in ev if e[0] == 0]
    acted = [e for e in s0 if e[1] in (L.SKIP_FLAG, L.TAIL_FLAG)]
    drops = pg[L.DROP:L.DROP + 4]
    cls = rec["class"]
    kept = cls in ("ok", "kick-timeout")
    stopped = cls == "stop"
    q = {"tick_alive": R.yn(kept)}
    if j["row"] == "E0":
        grid = len(s0) >= 4 and all(C.on_grid(x) for x in C.gaps(s0))
        q.update({"entries": "12..16" if 12 <= len(s0) <= 16 else str(len(s0)), "grid": R.yn(grid), "acted": pg[L.ACTED]})
        return q, f"class {cls}, {len(s0)} entries, on the grid {grid}, ACTED {pg[L.ACTED]}", None
    last = acted[0] if acted else None
    info = (f"class {cls}, {len(s0)} entries (acted {len(acted)}, flags {sorted({e[1] for e in s0})}), ACTED {pg[L.ACTED]} of {j['count']}, "
            f"ACT_SEEN {pg[L.ACT_SEEN]}, drops {drops}")
    designed = pg[L.ACTED] == j["count"] and pg[L.ACT_SEEN] == j["act"] and bool(acted)
    q["acted"] = pg[L.ACTED]
    q["flag_logged"] = last[1] if last else None
    q["kept"] = R.yn(kept)
    after = [e for e in s0 if last is not None and C.rel(e[5], last[5]) > 0]
    nxt = C.rel(after[0][5], last[5]) if after else None
    if j["row"] == "FK":
        q["next_gap"] = None if nxt is None else ("24950..25050" if abs(nxt - T) <= C.NEXT_GAP_TOL else str(nxt))
        q["next_gap_exact"] = None if nxt is None else ("24994..24995" if 24994 <= nxt <= 24995 else str(nxt))
        info += f"; next entry after the acted pass +{nxt}"
    else:                                          # KP
        tick_after = [e for e in after if C.e_tick(e)]
        gaps_ok = all(C.on_grid(x) for x in C.gaps([last] + tick_after[:6])[1:]) if len(tick_after) >= 2 else True
        n_t = len(tick_after)
        if not designed or (not acted and drops[0]):
            q["ticks_after_kick"] = None
        elif drops[0] and n_t < L.KP_MIN_AFTER and kept:
            q["ticks_after_kick"] = None           # the ring was full: fewer than 4 ticks fit after the kick entry
        else:
            q["ticks_after_kick"] = ">=4" if n_t >= L.KP_MIN_AFTER and gaps_ok else str(n_t)
        q["miscinfo_answered"] = R.yn((rec.get("kick") or {}).get("answered"))
        q["sig_class"] = R.sig_class_of(rec.get("sig_after_kick") or (rec.get("sig") or {}).get("samples"))
        info += f"; {n_t} ticks after the kick entry (on the grid {gaps_ok}), signature {q['sig_class']}, answered {q['miscinfo_answered']}"
    mk = C.marks_of(S, rec)
    q["read_minus_write"] = None if mk is None else str(mk["rmw"])
    q["dword14"] = None if mk is None else (f"{mk['hc14']:#x}" if mk["hc14"] else "0")
    if mk is not None:
        info += f"; {C.mark_text(mk)}"
    if stopped:
        p3 = C.p3_of(rec)
        q["p3_answered"] = None if p3 is None else R.yn(p3)
        info += f"; {C.sig_line(C.rec_sig(rec))}; {C.p3_text(rec)}"
    if not designed and j["count"]:
        info += "; the pass was not acted as designed"
    return q, info, None


def score_kp(S):
    gate_why = None
    ctl = {}
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = C.record(S.d, n)
        v = R.void_job(S, n, rec, CLASSES)
        if v and v.startswith("not run"):
            S.p(f"{n}: {v}")
            continue
        q, info, why = (None, "", v) if v else quantities(S, rec, j)
        if why:
            S.nodata(n, why)
            if row in ("E0", "FK"):
                gate_why = f"the control {n} is void ({why})"
            continue
        S.p(f"{n}: {info}")
        if rec["class"] == "stop":
            S.stop_names.append(n)
            if rec.get("p3") is not None:
                S.p3.append((n, bool((rec.get("p3") or {}).get("answered"))))
        if row in ("E0", "FK"):
            ok, why = R.tally_job(S, n, q)
            ctl[n] = ok
            if not ok:
                gate_why = f"the control {n} is not a pass ({why})"
            continue
        designed = rec["page"][L.ACTED] == j["count"] and rec["page"][L.ACT_SEEN] == j["act"]
        # KP: a pass that was not acted as designed decides nothing (its hypothesis rows are cannot tell)
        R.tally_job(S, n, q, gate_why=gate_why or (None if designed else "the kick pass was not acted as designed"))
    note = S.stage_note()
    hyp = R.family_verdict(S, S.table, ("H-PHAS-ANY", "H-KICK-MORE"))
    ctls = "E0 and FK held" if ctl and all(ctl.values()) and len(ctl) == 2 else "E0/FK NOT held" if ctl else "E0 and FK not read"
    p3s = f"; P3 answered in {sum(1 for _, a in S.p3 if a)} of {len(S.p3)} stops" if S.p3 else ""
    return (f"kp: {ctls}; " + ", ".join(f"{k} {v}" for k, v in hyp.items()) + f"; stops {len(S.stop_names)} {S.stop_names}{p3s}; "
            f"{R.controls_line(S)}; Q152 rows: {S.t.line()}" + (f"; {note}" if note else ""))
