#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen_r4.py (R4-events): write everything the session runs from, in this directory's parent (closing4/r4-events/).

Stages, in run order (stages.txt): kb2 (Q290: the ring over the kick), kp (Q152: a kick pass ended with the phase end), e3p (Q166,
Q111: the slot 3 pass ended with the phase end, and HOST_CLEAR).  See gen/r4layout.py for the rows and the plan section 4 of
closing4/events/exp-events-r4.md.  The notes the plan wanted before the freeze (0a to 0e) are landed in the integration tree (E818 and
E819 Correction sections, hw_spec 12.2) and the predictions below start from them: E819's Q3 ring ended at the kick (0a), the last ticks
of an unbumped kick carry the 0x...74 mark (0b), the tick is periodic by itself (0d), a kick pass or the slot 3 pass ended without the
phase end stops (E813 B3, E823) and the phase end is what a tick pass needs (P1, E817, E830).

  asm/*.s, bins/*.blob, bins/blobs.json   the tasks (the landed verifier accepts them; ring_hold is S2b's bytes)
  tables/STAGE.json                       the job tables;   predictions/STAGE.tsv   the frozen predictions (case quantity value model set)

Run with the scratch venv:  RESGX545=<integration tree> .../pixel-faults/.venv/bin/python gen/gen_r4.py   (then run/freeze_r4e.sh freeze)
"""
import hashlib
import json
import pathlib
import re
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R4 = HERE.parent
sys.path.insert(0, str(HERE))
import r4layout as L  # noqa: E402
import r3blobs as B  # noqa: E402
import r4blobs as K  # noqa: E402

STAGES = L.STAGES
SPEC = L.ROW_SPEC
STR_RE = K.STR_RE
H_COUNT = ("H-LATCH", "H-CNT", "H-HWC")          # Q290's three readings of the count byte (H-KW is refuted by E819 Q1)
H_EVENT = ("H-PEND", "H-NOEVENT", "H-LATE")     # what an unbumped kick does
H_KP = ("H-PHAS-ANY", "H-KICK-MORE")
H_E3P = ("H-PHAS-ANY", "H-SLOT3-MORE")


# ---- blobs ------------------------------------------------------------------------------------------------------------------
def info_of(text, blob, arm):
    p = B.fwtask.parse_blob(blob)
    lines = K_instructions(text)
    writes = B.writes_of(lines)
    return {"insns": len(p.words), "bytes": len(blob), "patches": len(p.patches), "entries": p.entries,
            "sha256": hashlib.sha256(blob).hexdigest(), "arm": arm, "sa_writes": sorted({w for w in writes if w.startswith("sa")}),
            "pa_writes": sorted({w for w in writes if w.startswith("pa")}),
            "str": sorted(int(m.group(1)) for s in lines for m in [STR_RE.match(s)] if m),
            "ldr": sorted({re.sub(r"[^#0-9]", "", s.split(",")[1]) for s in lines if re.match(r"ldr\b", s)}),
            "cont4": any("@patch cont4" in ln for ln in text.splitlines())}


def K_instructions(text):
    """The instruction lines in word order with the landed `own_end` macro expanded (two words), labels and @entry dropped."""
    out = []
    for s in B.instructions(text):
        out += B.fwtask.OWN_END if s == "own_end" else [s]
    return out


def build_blobs():
    info = {}
    for name in L.GENERATED_BLOBS:
        text, blob = K.build(name)
        (R4 / "asm" / f"{name}.s").write_text(text)
        (R4 / "bins" / f"{name}.blob").write_bytes(blob)
        info[name] = info_of(text, blob, L.RING_ARM)
    hold = (R4 / "bins" / "ring_hold.blob").read_bytes()
    assert hashlib.sha256(hold).hexdigest() == L.HOLD_SHA, "ring_hold.blob is not S2b's"
    hp = B.fwtask.parse_blob(hold)
    src = (R4 / "asm" / "ring_hold.s").read_text()
    info["ring_hold"] = {"insns": len(hp.words), "bytes": len(hold), "patches": len(hp.patches), "entries": hp.entries, "sha256": L.HOLD_SHA,
                         "arm": L.RING_ARM, "sa_writes": sorted({w for w in B.all_writes(src) if w.startswith("sa")}), "pa_writes": [],
                         "str": [], "ldr": ["#81"], "cont4": False, "note": "byte-identical to closing/s2b/bins/ring_hold.blob"}
    (R4 / "bins" / "blobs.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    return info


# ---- tables ----------------------------------------------------------------------------------------------------------------
def label_of(spec, k):
    """control keeps its label on every rep; a held-out row's first rep is held out, the others replicate."""
    lab = spec["label"]
    return lab if lab == "control" or k == 0 else "replicate"


def jobs_of(stage, make):
    jobs = []
    for row in L.ROW_ORDER[stage]:
        spec = SPEC[stage][row]
        for k in range(spec["reps"]):
            j = {"name": L.rep_name(row, k), "set": label_of(spec, k), "row": row, "runid": 0x6400 + 0x100 * STAGES.index(stage) + len(jobs) + 1}
            j.update(make(row, spec, k))
            if spec.get("run_if"):
                j["run_if"] = spec["run_if"]
            jobs.append(j)
    return jobs


def make_kicker2(row, spec, k):
    return {"op": "kicker2", "set_kicker": spec["set_kicker"], "no_bump": spec["no_bump"], "kick": True, "second_kick": spec["second_kick"],
            "window": 2, "pre_ms": L.KB2_PRE_MS, "ticks_ms": 0, "post_ms": L.KB2_POST_MS, "q4_pre_ms": L.KB2_Q4_PRE_MS}


def make_act(row, spec, k):
    return {"op": "act", "kind": spec["kind"], "act": spec["act"], "count": spec["count"], "trigger": spec["trigger"], "window": 2,
            "pre_ms": spec["pre_ms"], "open_ms": spec["open_ms"], "d_reads": 20, "may_stop": spec["may_stop"], "reset_arm": spec["reset_arm"]}


def make_skip3p(row, spec, k):
    return {"op": "skip3p", "skip": spec["skip"], "watch_ms": L.E3P_WATCH_MS, "clear_values": list(L.E3P_CLEAR_VALUES),
            "read_ms": {kk: list(v) for kk, v in L.E3P_READ_MS.items()}, "slot3_wait_s": L.E3P_SLOT3_WAIT_S,
            "hold_recovery": "Y" if spec["skip"] else "N"}


MAKE = {"kb2": make_kicker2, "kp": make_act, "e3p": make_skip3p}


def table(stage):
    info = L.STAGE_INFO[stage]
    return {"stage": stage, "blob": info["blob"], "arm": info["arm"], "stop_budget": info["budget"], "per_job_reset": info["per_job_reset"],
            "jobs": jobs_of(stage, MAKE[stage]), "needs": info["gate"], "session": L.SESSION}


# ---- predictions (frozen before the first job; `case quantity value model set`) --------------------------------------------
def add(P, n, q, v, model, s):
    P.append((n, q, str(v), model, s))


KICK_FILE = "kicker {w} ccbctl {wo} {ro} kicks {kk}"


def preds_kb2(t):
    """kb2.  Readings: [data] E816 G0 (a kick is one entry, K 2, the ticks after carry 3), E768, E746; E819 Q1 (H-KW refuted), Q3 (an unbumped
    kick: not answered, file `kicker 2 ccbctl 3 2 kicks 3`, the tick goes on); notes 0a and 0b of E819's correction (the Q3 ring ended at the
    kick; the last 2, 1 and 0 ticks of q3, q3-r2, q3-r3 read pa2 0x01061a74, E751's latched-while-busy mark) [infer, post hoc]."""
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        add(P, n, "tick_alive", "yes", "control (the tick goes on after a kick or an unanswered one: 13 kicker jobs, E816, E819)", "control")
        add(P, n, "kick_no_bump_after", "N", "control (one-shot, read back)", "control")
        if row == "G0P":
            m = "control (E768, E816 G0: one ordinary kick, K 2, the ticks after carry 3)"
            for q, v in (("kick_entries", 1), ("kick_entry_K", 2), ("ticks_K_before", 2), ("ticks_K_after", 3), ("miscinfo_answered", "yes"),
                         ("kicker_file_after", KICK_FILE.format(w=3, wo=3, ro=3, kk=3)), ("n_after_ge3", "yes")):
                add(P, n, q, v, m, "control")
            add(P, n, "ticks_pa2_after", "0x01061a70", "control (E751, e5c kick90: a tick served after a served kick reads the plain word)", "control")
        elif row == "Q2P":
            m = "control (every reading: W alone changes nothing before the kick, the kick is served)"
            for q, v in (("kick_entries", 1), ("kick_entry_K", 2), ("ticks_K_before", 2), ("miscinfo_answered", "yes"),
                         ("kicker_file_after", KICK_FILE.format(w=0x43, wo=3, ro=3, kk=3)), ("n_after_ge3", "yes")):
                add(P, n, q, v, m, "control")
            for mm, v in zip(H_COUNT, (0x43, 3, 3)):
                add(P, n, "ticks_K_after", v, mm + (" (the count is W as latched at the served kick)" if mm == "H-LATCH" else
                   " (a count of served kicks or consumed commands)" if mm == "H-CNT" else " (a count of CR_EVENT_KICK writes)"), s)
        else:                                   # Q3P, Q4: the first part is the same (Q4 is Q3P plus a second window)
            fit = "E819 Q3 (3 of 3)"
            add(P, n, "miscinfo_answered", "no", fit, "fit")
            add(P, n, "kicker_file_after", KICK_FILE.format(w=2, wo=3, ro=2, kk=3), fit, "fit")
            add(P, n, "ticks_K_before", 2, "control (before the write the count is 2)", "control")
            add(P, n, "n_after_ge3", "yes", "control (the ring covers the 3 ticks after the write)", "control")
            for mm, v in zip(H_EVENT, (0, 0, 1)):
                add(P, n, "kick_entries", v, mm + (" (the event is pending and never reaches our task)" if mm == "H-PEND" else
                    " (nothing is raised)" if mm == "H-NOEVENT" else " (the kick is delivered late, inside the ring)"), s)
            for mm, v in zip(H_COUNT, (2, 2, 3)):
                add(P, n, "ticks_K_after", v, mm + (" (the count is W as latched at the served kick)" if mm == "H-LATCH" else
                   " (a count of served kicks or consumed commands)" if mm == "H-CNT" else " (a count of CR_EVENT_KICK writes)"), s)
            add(P, n, "ticks_pa2_after", "0x01061a74", "H-PEND (the ticks after the write are latched while the EDM is busy, E751's mark)", s)
            add(P, n, "ticks_pa2_after", "0x01061a70", "H-NOEVENT (the EDM stays idle: the plain word)", s)
            add(P, n, "serv_bit16_after", "clear", "H-PEND (USE0_SERV_EVENT bit 16 clear: an event in service or queued)", s)
            add(P, n, "serv_bit16_after", "set", "H-NOEVENT (USE0_SERV_EVENT bit 16 set: empty)", s)
            if row == "Q4":
                add(P, n, "q4_kick_entries", 2, "H-PEND (the pending kick is delivered with the next one)", s)
                add(P, n, "q4_kick_entries", 1, "H-NOEVENT (only the ordinary kick raises an event)", s)
                add(P, n, "q4_ccbctl", "4 4", "H-PEND (both commands are read)", s)
                add(P, n, "q4_ccbctl", "4 3", "H-NOEVENT (one command a kick is read)", s)
                add(P, n, "q4_kicker_w", 3, "control (the ordinary kick bumps W from 2 to 3)", "control")
    return P


def preds_kp(t):
    """kp.  [data] E817 and E830: a plain tick pass ended with the phase end keeps the tick, 13 of 13 (FK = E830's fk, next entry +24994 or
    +24995 then the grid); E813 B3: a kick pass ended with `idf, wdf, nop.end` stopped it with read = write - 1.  KP is the one new pass."""
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "E0":
            for q, v in (("entries", "12..16"), ("grid", "yes"), ("acted", 0)):
                add(P, n, q, v, "control (E817 e0, E830: 14 +-2 entries on the grid)", "control")
            continue
        add(P, n, "acted", 1, "control (the task's own record: ACTED 1 and ACT_SEEN 4 in the page)", "control")
        if row == "FK":
            m = "control (E830 fk 3 of 3, E817 fph 2 of 2: a plain tick pass ended with the phase end keeps the tick)"
            add(P, n, "kept", "yes", m, "control")
            add(P, n, "flag_logged", 3, m, "control")
            add(P, n, "next_gap", "24950..25050", m, "control")
            add(P, n, "next_gap_exact", "24994..24995", m, "fit")
            add(P, n, "read_minus_write", 0, m, "control")
            add(P, n, "dword14", 0, m, "control")
            continue
        add(P, n, "flag_logged", 3, "control (the kick pass is logged first with flag 3)", "control")
        add(P, n, "kept", "yes", "H-PHAS-ANY (any pass ended with the phase end is finished for the EDM)", s)
        add(P, n, "kept", "no", "H-KICK-MORE (a kick pass needs more than the phase end: E813 B3's stop)", s)
        add(P, n, "ticks_after_kick", ">=4", "H-PHAS-ANY (at least 4 ticks on the grid after the kick entry)", s)
        add(P, n, "ticks_after_kick", "0", "H-KICK-MORE (nothing after the kick entry)", s)
        add(P, n, "sig_class", "idle", "H-PHAS-ANY (an idle EDM after the pass)", s)
        add(P, n, "sig_class", "busy", "H-KICK-MORE (a stop: E537's busy signature)", s)
        fit = "E813 B3 (the closed reader never ran: the command stays unread)"
        add(P, n, "miscinfo_answered", "no", fit, "fit")
        add(P, n, "read_minus_write", -1, fit, "fit")
        add(P, n, "dword14", 0, fit, "fit")
        add(P, n, "p3_answered", "no", "H-KICK-MORE (stop only: P3 not answered, 0 of 8 in the records)", s)
    return P


def preds_e3p(t):
    """e3p.  [data] E823: B0 3 of 3 (the fill completes, one slot 3 end-of-render entry, bit 18 never read in a poll, the tick alive); the
    slot 3 pass skipped with `idf, wdf, nop.end` stopped the tick, held the fill, left STATUS bit 18 set for 48 ms and a host write of bit 18
    to CLEAR cleared it, of bit 15 did not (1 job, post hoc: the fit rows).  B1P ends the pass with the phase end instead."""
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        add(P, n, "skipped", j["skip"], "control (the design: the host's flag, the task's count)", "control")
        add(P, n, "slot3_logged", "yes", "control (the slot 3 end-of-render entry is in the page before the watch starts)", "control")
        add(P, n, "hold_recovery_after", "N", "control (put back and read back)", "control")
        if row == "B0":
            m = "control (E823 B0, 3 of 3: the fill without the skip)"
            for q, v in (("tool_ok", "yes"), ("tick_alive", "yes"), ("end_render_entries", 1), ("bit18_in_watch", "never")):
                add(P, n, q, v, m, "control")
            continue
        add(P, n, "tick_alive", "yes", "H-PHAS-ANY (the slot 3 pass ended with the phase end is finished for the EDM)", s)
        add(P, n, "tick_alive", "no", "H-SLOT3-MORE (the slot 3 pass needs more than the phase end: E823's stop)", s)
        add(P, n, "fill_returned_in_watch", "no", "both (the closed slot 3 handler is not called: the job is held)", s)
        add(P, n, "end_render_entries", 1, "H-ONCE (the event is not re-fired)", s)
        add(P, n, "bit18_in_watch", "all", "H-LEVEL (bit 18 holds until acknowledged: E823 held it 48 ms)", s)
        add(P, n, "bit18_in_watch", "never", "H-PULSE", s)
        lab = "fit" if k_of(j) == 0 else s            # E823's one job: the first B1P is the fit for the clears, the others test them
        for mm, v in (("H-W", "1"), ("H-ALL", "0"), ("H-NONE", "1")):
            add(P, n, "bit18_after_bit15", v, mm + " (the bits written are the bits cleared)" if mm == "H-W" else mm, lab)
        for mm, v in (("H-W", "0"), ("H-ALL", "0"), ("H-NONE", "1")):
            add(P, n, "bit18_after_bit18", v, mm + " (the bits written are the bits cleared)" if mm == "H-W" else mm, lab)
    return P


def k_of(j):
    return 0 if not j["name"].endswith(("-r2", "-r3")) else 1


PREDS = {"kb2": preds_kb2, "kp": preds_kp, "e3p": preds_e3p}


# ---- writing -------------------------------------------------------------------------------------------------------------
def write_preds(stage, rows):
    out = ["case\tquantity\tvalue\tmodel\tset"] + ["\t".join(r) for r in rows]
    (R4 / "predictions" / f"{stage}.tsv").write_text("\n".join(out) + "\n")


def brief(j):
    skip = {"name", "set", "row", "runid", "op", "run_if", "steps", "files", "defaults", "args", "frozen", "prog", "read_ms", "clear_values"}
    return ", ".join(f"{k}={v}" for k, v in j.items() if k not in skip and v not in (None, [], False, 0))


def tables_md(info, tabs):
    L_ = ["# R4-events job tables (generated by gen/gen_r4.py; the JSON in tables/ is what runs)", "",
          "| blob | insns | bytes | sha256 | arm | sa writes | pa writes | str | ldr | cont4 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, i in info.items():
        L_.append(f"| {n} | {i['insns']} | {i['bytes']} | {i['sha256'][:16]}... | `{i['arm']}` | {', '.join(i['sa_writes']) or 'none'} | "
                  f"{', '.join(i['pa_writes']) or 'none'} | {', '.join('#%d' % x for x in i['str']) or 'none'} | {', '.join(i['ldr']) or 'none'} | "
                  f"{'yes' if i['cont4'] else 'no'} |")
    L_ += [""]
    for st in STAGES:
        t = tabs[st]
        L_ += [f"## stage {st}: blob {t['blob']}, needs {t['needs']}, stop budget {t['stop_budget']} (stop number {t['stop_budget'] + 1} ends "
               f"the stage), reset + arm each job: {t['per_job_reset']}", "",
               "| job | set | row | op | parameters | run if |", "|---|---|---|---|---|---|"]
        for j in t["jobs"]:
            L_.append(f"| {j['name']} | {j['set']} | {j['row']} | {j['op']} | {brief(j)} | {j.get('run_if') or ''} |")
        L_.append("")
    (R4 / "TABLES.md").write_text("\n".join(L_) + "\n")


def main():
    info = build_blobs()
    tabs = {st: table(st) for st in STAGES}
    (R4 / "tables").mkdir(exist_ok=True)
    (R4 / "predictions").mkdir(exist_ok=True)
    for st in STAGES:
        (R4 / "tables" / f"{st}.json").write_text(json.dumps(tabs[st], indent=1, sort_keys=True) + "\n")
        write_preds(st, PREDS[st](tabs[st]))
    (R4 / "stages.txt").write_text("\n".join(f"{st} {L.STAGE_INFO[st]['alarm']}" for st in STAGES) + "\n")
    tables_md(info, tabs)
    print("wrote", ", ".join(f"{k}: {v['insns']} insns" for k, v in info.items()), "; tables", ", ".join(STAGES),
          "; jobs", {st: len(tabs[st]["jobs"]) for st in STAGES}, "total", sum(len(t["jobs"]) for t in tabs.values()))


if __name__ == "__main__":
    main()
