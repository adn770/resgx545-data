# SPDX-License-Identifier: MIT
"""sc_e3.py: the scorers of the clear-register stages: e3h / e3a (Q166 for CLEAR2: the latch STATUS2 bit 6, by the host and by a task) and
e3b (Q111: CLEAR against a held end-of-render event, level or pulse).  Standard library only."""
import json
import pathlib

import scorelib as C
import r3layout as L

T = L.TICK_UNITS


def yn(b):
    return "yes" if b else "no"


def hx(v):
    return None if v is None else f"{v:#x}"


def score_e3(S):
    verdicts = []
    for j in S.table["jobs"]:
        n = j["name"]
        rec = C.record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        if rec is None or rec.get("class") != "ok":
            S.nodata(n, f"class {None if rec is None else rec.get('class')}")
            continue
        steps = rec.get("steps") or []
        if len(steps) != 5:
            S.nodata(n, "the five steps were not all read")
            continue
        s2 = [s.get("status2") for s in steps]
        C.Stage.tally_value(S, n, "status2_pre", hx(rec.get("status2_pre")))
        step1_ok = s2[0] == L.S2_LATCH
        for i, v in enumerate(s2, 1):
            q = f"s2_step{i}"
            if i > 2 and not step1_ok:        # step 1 is the control of the round: a heldout step is read only if the latch set
                for pr in S.preds:
                    if pr["case"] == n and pr["quantity"] == q:
                        S.t.add(n, q, pr["model"], pr["set"], None, "step 1 did not set the latch")
            else:
                C.Stage.tally_value(S, n, q, hx(v))
        C.Stage.tally_value(S, n, "bit10_always", yn(all(v is not None and v & 0x400 for v in s2)))
        if S.stage == "e3a":
            C.Stage.tally_value(S, n, "task_took_commands", yn(all(s["ok"] for s in steps if s["what"] == "clear2")))
        if not step1_ok:
            verdicts.append("cannot tell (step 1 did not read 0x440)")
        elif s2[2] == L.S2_LATCH and s2[3] == L.S2_IDLE:
            verdicts.append("H-W")
        elif s2[2] == L.S2_IDLE and s2[3] == L.S2_IDLE:
            verdicts.append("H-ALL")
        elif s2[2] == L.S2_LATCH and s2[3] == L.S2_LATCH:
            verdicts.append("H-NONE")
        else:
            verdicts.append(f"none of the three ({[hex(v) if v is not None else None for v in s2]})")
        S.p(f"{n}: class ok; STATUS2 after the steps {[hex(v) if v is not None else None for v in s2]} (pre {hx(rec.get('status2_pre'))}); "
            f"route {rec.get('route')}; {verdicts[-1]}")
    note = S.stage_note()
    uniq = sorted(set(verdicts))
    extra = ""
    if S.stage == "e3a":
        try:
            host = json.loads((pathlib.Path(S.d).parent / "e3h" / "stage.json").read_text())
            extra = f"; the host route (e3h) ran: exit {host.get('exit')}"
        except (OSError, ValueError):
            extra = "; the host route (e3h) is not kept next to this stage"
    return (f"{S.stage}: CLEAR2 reads {uniq or 'not read'} in {len(verdicts)} rounds" + extra + f"; Q166 rows: {S.t.line()}"
            + (f"; {note}" if note else ""))


# ---- e3b -----------------------------------------------------------------------------------------------------------------
BIT18, BIT29 = 0x40000, 0x20000000


def bit_of(v, bit):
    return None if v is None else int(bool(v & bit))


def score_e3b(S):
    stops, b1, ref_obs = [], [], {}
    b1n = []
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = C.record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        v = C.void_ring(rec, {"ok", "stop"})
        r = None
        if v is None:
            try:
                r = C.ring(rec["page"])
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v:
            S.nodata(n, v)
            continue
        pg = rec["page"]
        cls = rec["class"]
        stopped = cls == "stop"
        ev = C.from_stamp(C.merged(r), rec.get("window_stamp"))
        end_render = [e for e in ev if e[0] == 3 and e[2] == 0 and (e[3] & L.LOW24) == L.SKIP3_WORD_BIT]
        n_er = len(end_render)
        watch = rec.get("watch") or []
        bits = [bit_of(w[1], BIT18) for w in watch if w[1] is not None]
        level = "all" if bits and all(bits) else "never" if bits and not any(bits) else "mixed" if bits else None
        tool_ok = rec.get("tool_rc") == 0 and "diff: 0" in (rec.get("tool_out") or "")
        info = (f"{n}: class {cls}, skipped {pg[L.SKIPPED]}, slot-3 end-of-render entries {n_er}, watch {len(watch)} reads bit 18 {level}, "
                f"tool rc {rec.get('tool_rc')}")
        C.Stage.tally_value(S, n, "skipped", pg[L.SKIPPED])
        if row == "B0":
            C.Stage.tally_value(S, n, "tool_ok", yn(tool_ok))
            C.Stage.tally_value(S, n, "tick_alive", yn(not stopped))
            C.Stage.tally_value(S, n, "end_render_entries", n_er)
            S.p(info)
            continue
        b1.append((row, stopped))
        b1n.append(n)
        obs = None
        C.Stage.tally_value(S, n, "tick_alive", yn(not stopped))
        # held-out readings that need the event to have been held: level or pulse first
        C.Stage.tally_value(S, n, "bit18_in_watch", level)
        er = "1" if n_er == 1 else ">1" if n_er > 1 else "0"
        C.Stage.tally_value(S, n, "end_render_entries", er if er != "1" else 1)
        cl = rec.get("clears") or {}

        def after(key, bit, ix=-1):
            rs = (cl.get(key) or {}).get("reads") or []
            return None if not rs else bit_of(rs[ix].get("status"), bit)
        a15, a18 = after("bit15", BIT18), after("bit18", BIT18)
        held = level == "all"          # H-W / H-ALL / H-NONE are read only where bit 18 was held to the write
        for q, got in (("bit18_after_bit15", a15), ("bit18_after_bit18", a18)):
            C.Stage.tally_value(S, n, q, None if not held or got is None else str(got), "" if held else "bit 18 was not held: cannot tell")
        if stopped:
            rs = (cl.get("bit29") or {}).get("reads") or []
            c29 = None if not rs else any(not (x.get("status") or 0) & BIT29 for x in rs)
            C.Stage.tally_value(S, n, "bit29_clears", None if c29 is None else yn(c29))
        if row == "B1" and "B1" not in ref_obs:
            ref_obs["B1"] = (a15, a18)
        if row == "B2":
            C.Stage.tally_value(S, n, "route_agrees", None if "B1" not in ref_obs or held is False or None in (a15, a18) else yn(ref_obs["B1"] == (a15, a18)))
        sg = C.rec_sig(rec) if stopped else None
        if stopped:
            S.stop_names.append(n)
            stops.append(n)
        S.p(info + f"; bit 18 after bit 15 {a15}, after bit 18 {a18}; clears {sorted(cl)}" + (f"; {C.sig_line(sg)}; {C.mark_text(C.marks_of(S, rec))}; {C.p3_text(rec)}" if stopped else ""))
    note = S.stage_note()
    if not b1:
        h = "B1 not read"
    else:
        st = [x[1] for x in b1]
        h = "H-STOP3 (a skipped end-of-render handler stops the tick)" if all(st) else "H-FREE3 (the tick goes on)" if not any(st) else "B1 mixed"
        # the number of runs the verdict rests on (post-run fix C9, POSTRUN-FIX.md)
        h += f" in {len(b1n)} run{'s' if len(b1n) != 1 else ''} ({', '.join(b1n)}{'; one run, no replicate' if len(b1n) == 1 else ''})"
    return (f"e3b: {h}; stops {len(stops)} {stops}; Q111 rows: {S.t.line()}" + (f"; {note}" if note else ""))
