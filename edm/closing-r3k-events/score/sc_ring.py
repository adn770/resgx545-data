# SPDX-License-Identifier: MIT
"""sc_ring.py: the scorers of the ring stages of R3k: f and t (the acted tick pass: how it ends), kb and the G0 row of k0h (Q290: the count
byte K of the events and the kicker word).  Standard library only."""
import json
import pathlib

from scorelib import *  # noqa: F401,F403
import scorelib as C
import r3layout as L

T = L.TICK_UNITS


def yn(b):
    return "yes" if b else "no"


def tally(S, n, q, got, note=""):
    """Every frozen row of (n, q) against the measured text `got` (None: cannot tell)."""
    S.tally_value(n, q, got, note)


# ---- stages f and t -------------------------------------------------------------------------------------------------------
def score_act(S):
    kept_by_row, stops, ctl_ok = {}, [], []
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = C.record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        v = C.void_ring(rec, C.RESULT_CLASSES_E)
        r = None
        if v is None:
            try:
                r = C.ring(rec["page"])
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v is None and j["count"] and rec["page"][L.ACTED] not in (0, j["count"]) and rec.get("class") == "ok":
            v = f"the acted count was not taken as designed (ACTED {rec['page'][L.ACTED]}, want {j['count']})"
        if v:
            S.nodata(n, v)
            continue
        pg = rec["page"]
        drops = pg[L.DROP:L.DROP + 4]
        ev = C.from_stamp(C.merged(r), rec.get("window_stamp"))
        s0 = [e for e in ev if e[0] == 0]
        acted = [e for e in s0 if e[1] in (L.SKIP_FLAG, L.TAIL_FLAG)]
        cls = rec["class"]
        kept_obs = cls in ("ok", "kick-timeout")
        kept_by_row.setdefault(row, []).append(kept_obs)
        info = (f"{n}: class {cls}, {len(s0)} entries (acted {len(acted)}, flags {sorted({e[1] for e in s0})}), ACTED {pg[L.ACTED]} of "
                f"{j['count']}, ACT_SEEN {pg[L.ACT_SEEN]}, drops {drops}")
        if j["count"] and (pg[L.ACTED] == 0 or (not acted and drops[0] == 0) or (not acted and drops[0])):
            why = ("the KIND of pass never came in the window (ACTED 0)" if pg[L.ACTED] == 0 else
                   "the acted pass is not in the ring (not logged first)" if drops[0] == 0 else "ring full before the acted pass")
            S.p(info + f"; {why}: cannot tell")
            for pr in S.preds:
                if pr["case"] == n and pr["quantity"] not in ("p3_answered", "acted"):
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, why)
            continue
        tally(S, n, "acted", pg[L.ACTED] if j["count"] else 0)
        for pr in S.preds:
            if pr["case"] == n and pr["quantity"] == "kept":
                S.t.add(n, "kept", pr["model"], pr["set"], kept_obs == (pr["value"] == "yes"))
        stopped = cls == "stop"
        sg = C.rec_sig(rec) if stopped else None
        mk = C.marks_of(S, rec)
        if stopped:
            stops.append((n, sg, mk))
            S.stop_names.append(n)
        if row == "E0":
            grid = len(s0) >= 4 and all(C.on_grid(x) for x in C.gaps(s0))
            ok = abs(len(s0) - 14) <= 2
            ctl_ok.append(ok and grid and not acted)
            tally(S, n, "entries", "14+-2" if ok else str(len(s0)))
            tally(S, n, "grid", yn(grid))
            S.p(info + f"; entries 14 +-2: {ok}, gaps on the 25000 grid: {grid}")
            continue
        last = acted[-1] if acted else None
        after = [e for e in s0 if last is not None and C.rel(e[5], last[5]) > 0]
        nxt = C.rel(after[0][5], last[5]) if after else None
        tally(S, n, "flag_logged", acted[0][1] if acted else None)
        if not stopped:
            tally(S, n, "next_gap", None if nxt is None else ("25000+-50" if abs(nxt - T) <= C.NEXT_GAP_TOL else str(nxt)),
                  "" if nxt is not None else "no entry after the acted pass")
        else:
            tally(S, n, "sig_busy", yn(sg["class"] == "busy") if sg["class"] != "unreadable" else None)
            p3 = C.p3_of(rec)
            tally(S, n, "p3_answered", None if p3 is None else yn(p3))
            if p3 is not None:
                S.p3.append((n, p3))
        S.p(info + f"; next entry after the acted pass +{nxt} (want {T} +-{C.NEXT_GAP_TOL}); {C.mark_text(mk)}"
            + (f"; {C.sig_line(sg)}; {C.p3_text(rec)}; {C.d_text(rec)}" if stopped else ""))
    note = S.stage_note()
    h = verdict_f(kept_by_row) if S.stage == "f" else verdict_t(kept_by_row)
    p3s = f"; P3 answered in {sum(1 for _, a in S.p3 if a)} of {len(S.p3)} stops" if S.p3 else ""
    stop_sig = "; ".join(f"{x}: {sg['class']}{' (E537)' if sg['matches_e537'] else ''}, read-write {mk['rmw'] if mk else '?'}, "
                         f"dword 14 {hex(mk['hc14']) if mk else '?'}" for x, sg, mk in stops)
    ctl = "E0 held" if ctl_ok and all(ctl_ok) else ("E0 DIFFERS" if ctl_ok else "E0 not read")
    return (f"{S.stage}: {ctl}; {h}; stops {len(stops)}" + (f" [{stop_sig}]" if stops else "") + f"{p3s}; Q152 rows: {S.t.line()}"
            + (f"; {note}" if note else ""))


def _kept(kb, row):
    v = kb.get(row)
    if not v:
        return None
    return True if all(v) else False if not any(v) else "mixed"


def verdict_f(kb):
    c4, fb, cf, ph = (_kept(kb, r) for r in ("FC4", "FB", "FCF", "FPH"))
    if c4 is None:
        return "FC4 (the cont4 control) not read: nothing to conclude"
    if c4 is not True:
        return "the cont4 control did NOT keep the tick" + (" (stopped)" if c4 is False else " (mixed)") + ": H-BEFORE (the need is before the exit); the replicas are not run"
    if fb is None:
        return "FC4 kept; FB not read"
    if fb is False:
        return "FC4 kept, FB (the exact replica of the exit in our page) STOPPED: H-PLACE (what runs in our page differs from the closed exit); the single rows are not read"
    if fb == "mixed":
        return "FC4 kept, FB mixed: no hypothesis fits"
    if cf is None and ph is None:
        return "FC4 and FB kept; FCF and FPH not read"
    names = {(True, True): "H-ANY (either word alone is enough)", (True, False): "H-CFI (the cache flush is what the EDM needs)",
             (False, True): "H-PHAS (the phase end is what the EDM needs)", (False, False): "H-BOTH (it needs both)"}
    if cf in (True, False) and ph in (True, False):
        return "FC4 and FB kept; " + names[(cf, ph)]
    return f"FC4 and FB kept; FCF {cf}, FPH {ph}: not both decided"


def verdict_t(kb):
    t1, t2 = _kept(kb, "T1"), _kept(kb, "T2")
    if t1 is None:
        return "T1 not read"
    if t1 is not True:
        return "T1 (str of the timer, then the closed task) did not keep the tick: H-TIMERW-STOPS; T2 not run"
    if t2 is None:
        return "T1 kept (the timer write is harmless); T2 not read"
    return ("T1 kept; T2 kept: H-TIMER (the timer write is what an ended tick pass needs)" if t2 is True else
            "T1 kept; T2 stopped: H-NOTIMER (the timer write does not make our own end enough)" if t2 is False else "T1 kept; T2 mixed")


# ---- the kicker rows (kb Q0-Q3, k0h G0) -------------------------------------------------------------------------------------
def k_mode(es):
    """(modal K of entries, all one value) of a list of ring entries."""
    ks = [e[3] >> 24 for e in es]
    if not ks:
        return None, False
    m = max(set(ks), key=lambda v: (ks.count(v), -v))
    return m, len(set(ks)) == 1


def score_kicker(S):
    verdict = {}
    ctl = []
    for j in S.table["jobs"]:
        if j["op"] != "kicker":
            continue
        n, row = j["name"], j["row"]
        rec = C.record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        v = C.void_ring(rec, C.RESULT_CLASSES_E)
        r = None
        if v is None:
            try:
                r = C.ring(rec["page"])
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v is None and rec.get("class") == "ok" and j["set_kicker"] is not None and not rec.get("set_ok"):
            v = "the kicker write was refused"
        if v:
            S.nodata(n, v)
            continue
        cls = rec["class"]
        ev = C.from_stamp(C.merged(r), rec.get("window_stamp"))
        ticks = [e for e in ev if C.e_tick(e)]
        kicks = [e for e in ev if C.e_kick(e)]
        kb, ka = rec.get("kicker_before") or {}, rec.get("kicker_after") or {}
        info = f"{n}: class {cls}, {len(ticks)} ticks, {len(kicks)} kick entries; kicker file before {kb.get('raw')!r}, after {ka.get('raw')!r}"
        if cls == "stop":
            sg = C.rec_sig(rec)
            mk = C.marks_of(S, rec)
            S.stop_names.append(n)
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "the tick stopped")
            S.p(info + f"; a TICK STOP (a surprise); {C.sig_line(sg)}; {C.mark_text(mk)}; {C.p3_text(rec)}")
            continue
        k_set = rec.get("stamp_after_set")
        k_kick = kicks[0][5] if kicks else None
        q = {}
        if row == "Q0":
            q["ticks_K"] = k_mode(ticks)[0]
        elif row == "Q1":
            q["ticks_K_post_set"] = k_mode([e for e in ticks if k_set is not None and C.rel(e[5], k_set) > 0])[0]
        elif row == "Q2":
            q["ticks_K_pre_kick"] = k_mode([e for e in ticks if k_set is not None and k_kick is not None and C.rel(e[5], k_set) > 0
                                            and C.rel(e[5], k_kick) < 0])[0]
            q["ticks_K_post_kick"] = k_mode([e for e in ticks if k_kick is not None and C.rel(e[5], k_kick) > 0])[0]
        elif row == "Q3":
            q["ticks_K_post_kick"] = k_mode([e for e in ticks if k_kick is not None and C.rel(e[5], k_kick) > 0])[0]
        else:        # G0 (E768's ring: K = 2 after the arm, the kick, +1)
            q["ticks_K_before"] = k_mode([e for e in ticks if k_kick is not None and C.rel(e[5], k_kick) < 0])[0]
            q["ticks_K_after"] = k_mode([e for e in ticks if k_kick is not None and C.rel(e[5], k_kick) > 0])[0]
            q["kick_entries"] = len(kicks)
            q["grid"] = yn(len(ticks) >= 4 and all(C.on_grid(x) for x in C.gaps(ticks)))
        if ka.get("w") is not None and kb.get("w") is not None:
            q["kicker_w_after"] = ka["w"]
            q["ccbctl0_after"] = ka["wofs"]
            q["kicks_delta"] = ka["kicks"] - kb["kicks"]
        q["kick_no_bump_after"] = rec.get("no_bump_after")
        if j["kick"]:
            q["miscinfo_answered"] = yn((rec.get("kick") or {}).get("answered"))
        for quantity, got in q.items():
            if any(pr["case"] == n and pr["quantity"] == quantity for pr in S.preds):
                tally(S, n, quantity, got, "" if got is not None else "no entries in the interval")
        S.p(info + "; " + ", ".join(f"{k} {v}" for k, v in q.items()))
        # which of the three hypotheses each discriminating quantity leaves standing
        for pr in S.preds:
            if pr["case"] == n and pr["model"] in ("H-KW", "H-LATCH", "H-HWC"):
                got = q.get(pr["quantity"])
                if got is not None:
                    verdict.setdefault(pr["model"], []).append(str(got) == pr["value"])
        if row == "Q0":
            ctl.append(q.get("ticks_K") == 2)
    note = S.stage_note()
    if S.stage == "k0h":
        return f"k0h G0: {S.t.line()}" + (f"; {note}" if note else "")
    alive = [m for m in ("H-KW", "H-LATCH", "H-HWC") if verdict.get(m) and all(verdict[m])]
    dead = [m for m in ("H-KW", "H-LATCH", "H-HWC") if verdict.get(m) and not all(verdict[m])]
    ctls = "Q0 held (ticks K = 2)" if ctl and all(ctl) else "Q0 DIFFERS" if ctl else "Q0 not read"
    return (f"kb: {ctls}; consistent with {alive or 'none'}, refuted {dead or 'none'}; stops {len(S.stop_names)} {S.stop_names}; Q290 rows: "
            f"{S.t.line()}" + (f"; {note}" if note else ""))
