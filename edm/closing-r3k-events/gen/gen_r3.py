#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen_r3.py (R3k): write everything the two kernel-batch sessions run from, in this directory's parent (closing3/r3k-events/).

R3k = laptop sessions K0 and K1 of the question-closing pass, round 3, on the NEW module (fork resgx545-r3 8fc748b0, srcversion
230E0EF50FFFD606C53AE3C; decisions R3-K1 to R3-K11 and R3-E* in plans/resgx545-question-closing.md, designs closing3/kernel/exp-kernel-r3.md
and closing3/events/exp-events-r3.md, readings closing3/events/readings/readings-r3.md, L3's results).  A copy of the framework of
closing3/r3x-events (L3).  NOT RUN.  Stages, in run order (stages.txt, one file a session):

  K0 (~/r3k0)  k0f defaults of the new debugfs files   k0t one geometry + one pixel job (pinned L1/L2 tool)   k0c alias2 C0, C1
               k0h ring_hold H0, H1 (a tick hold) and G0 (one ordinary kick)
  K1 (~/r3kev) f    the end of a pass: cont4 control, own end + cfi + phas, + cfi, + phas        t   the EVENT_TIMER str
               kb   Q290 Q0-Q3 (kicker, kick_no_bump)      e2b  Q098 mov to pa3, pa4, pa2      e3h  Q166 host CLEAR2 (kregnow)
               e3a  Q166 CLEAR2 by a task (str #69)        e3b  Q111 skip-once + CLEAR (host, then str #77), LAST

  asm/*.s, bins/*.blob, bins/blobs.json, bins/progs/*   the tasks (the landed verifier accepts them) and the tool programs
  tables/STAGE.json   the job tables;   predictions/STAGE.tsv   the frozen predictions (case quantity value model set)

Run with the scratch venv:  ../../closing/pixel-faults/.venv/bin/python gen/gen_r3.py   (then run/freeze_r3.sh freeze)
"""
import hashlib
import json
import pathlib
import re
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R3 = HERE.parent
sys.path.insert(0, str(HERE))
import r3layout as L  # noqa: E402
import r3blobs as B  # noqa: E402
import r3kblobs as K  # noqa: E402

STAGES = L.STAGES
HOLD_SHA = "fa0f79dbb5864187516febf9c96f6ceea944e5abf6ae69b5acbeb9ac8a0ac168"
N90 = L.n_for_ticks(L.K7_HOLD_TICKS)
SPEC = L.ROW_SPEC
STR_RE = re.compile(r"(?:[!]?p\d\s+)?str\s+#(\d+)\s*,")


# ---- blobs -----------------------------------------------------------------------------------------------------------------
def info_of(name, text, blob, arm):
    p = B.fwtask.parse_blob(blob)
    lines = B.instructions(text)
    writes = B.all_writes(text)
    d = {"insns": len(p.words), "bytes": len(blob), "patches": len(p.patches), "entries": p.entries,
         "sha256": hashlib.sha256(blob).hexdigest(), "arm": arm,
         "sa_writes": sorted({w for w in writes if w.startswith("sa")}), "pa_writes": sorted({w for w in writes if w.startswith("pa")}),
         "str": sorted(int(m.group(1)) for s in lines for m in [STR_RE.match(s)] if m),
         "ldr": sorted({re.sub(r"[^#0-9]", "", s.split(",")[1]) for s in lines if re.match(r"ldr\b", s)}),
         "cont4": any("@patch cont4" in ln for ln in text.splitlines())}
    if name == "alias2":
        d["cmd_sa"] = {str(k): v for k, v in B.sa_writes_by_command(text).items()}
    return d


def build_blobs():
    info = {}
    arms = {"alias2": L.ONE_ARM, "pa_write2": L.ONE_ARM}
    for name in L.GENERATED_BLOBS:
        text, blob = K.build(name)
        (R3 / "asm" / f"{name}.s").write_text(text)
        (R3 / "bins" / f"{name}.blob").write_bytes(blob)
        info[name] = info_of(name, text, blob, arms.get(name, L.RING_ARM))
    hold = (R3 / "bins" / "ring_hold.blob").read_bytes()
    assert hashlib.sha256(hold).hexdigest() == HOLD_SHA, "ring_hold.blob is not S2b's"
    hp = B.fwtask.parse_blob(hold)
    src = (R3 / "asm" / "ring_hold.s").read_text()
    info["ring_hold"] = {"insns": len(hp.words), "bytes": len(hold), "patches": len(hp.patches), "entries": hp.entries, "sha256": HOLD_SHA,
                         "arm": L.RING_ARM, "sa_writes": sorted({w for w in B.all_writes(src) if w.startswith("sa")}), "pa_writes": [],
                         "str": [], "ldr": ["#81"], "cont4": False, "note": "byte-identical to closing/s2b/bins/ring_hold.blob"}
    (R3 / "bins" / "blobs.json").write_text(json.dumps(info, indent=1, sort_keys=True) + "\n")
    return info


# ---- tables ----------------------------------------------------------------------------------------------------------------
def label_of(spec, k):
    """control and fit rows keep their label on every rep; a held-out row's first rep is held out, the others replicate."""
    lab = spec["label"]
    return lab if lab in ("control", "fit") or k == 0 else "replicate"


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


def make_defaults(row, spec, k):
    return {"op": "defaults", "files": list(L.K0F_FILES), "defaults": dict(L.K0F_DEFAULTS)}


def make_tool(row, spec, k):
    return {"op": "tooljob", "tool": spec["tool"], "args": list(spec["args"]), "frozen": spec["frozen"]}


def make_alias2(row, spec, k):
    cmd = spec["cmd"]
    j = {"op": "alias2", "cmd": cmd, "sa": L.CMD_SA2.get(cmd, []), "w65": spec.get("w65"), "npass": spec.get("npass", 0),
         "marker": 0, "ri": [0, 0, 0, 0], "w63": 0, "w64": 0, "restore63": False, "read_1200": False, "d_reads": 20}
    return j


def make_hold(row, spec, k):
    return {"op": "holdsig", "hold": spec["hold"], "n": N90 if spec["hold"] else 0, "window": 2, "sig_ms": [20, 60], "status_ms": 40,
            "open_ms": 160, "d_reads": 20, "status_reads": 20 if not spec["hold"] else 1}


def make_k0h(row, spec, k):
    return make_kicker(row, spec, k) if spec["op"] == "kicker" else make_hold(row, spec, k)


def make_act(row, spec, k):
    return {"op": "act", "kind": spec["kind"], "act": spec["act"], "count": spec["count"], "trigger": spec["trigger"], "window": 2,
            "pre_ms": 3, "open_ms": spec["open_ms"], "d_reads": 20}


def make_kicker(row, spec, k):
    return {"op": "kicker", "set_kicker": spec["set_kicker"], "no_bump": spec["no_bump"], "kick": spec["kick"], "window": 2, "pre_ms": 1,
            "ticks_ms": 5, "post_ms": 5}


def make_pa(row, spec, k):
    return {"op": "pawrite", "cmd": spec["cmd"], "marker": spec["marker"], "flags": [0, 0, 1, 1], "sa": L.PW_SA[spec["cmd"]],
            "pa": L.PW_PA[spec["cmd"]]}


def make_clear(row, spec, k):
    return {"op": spec["op"], "steps": [list(x) for x in L.E3_STEPS], "prog": L.LOOP_PROG}


def make_skip3(row, spec, k):
    return {"op": "skip3", "skip": spec["skip"], "fw_clear": bool(spec.get("fw_clear")), "watch_ms": L.E3B_WATCH_MS,
            "clear_values": list(L.CLEAR_BITS), "timer_bit": L.CLEAR_TIMER_BIT, "hold_recovery": "Y" if spec["skip"] else "N"}


MAKE = {"k0f": make_defaults, "k0t": make_tool, "k0c": make_alias2, "k0h": make_k0h, "f": make_act, "t": make_act, "kb": make_kicker,
        "e2b": make_pa, "e3h": make_clear, "e3a": make_clear, "e3b": make_skip3}


def table(stage):
    info = L.STAGE_INFO[stage]
    return {"stage": stage, "blob": info["blob"], "arm": info["arm"], "stop_budget": info["budget"], "per_job_reset": info["per_job_reset"],
            "jobs": jobs_of(stage, MAKE[stage]), "needs": info["gate"], "session": L.SESSION_OF[stage]}


# ---- predictions (frozen before the first job; `case quantity value model set`) --------------------------------------------
def add(P, n, q, v, model, s):
    P.append((n, q, str(v), model, s))


def preds_k0f(t):
    P = []
    for j in t["jobs"]:
        n = j["name"]
        m = "K0 defaults (fork 8fc748b0)"
        for q, v in (("files_present", "yes"), ("srcversion_new", "yes"), ("kick_no_bump", "N"), ("render_rgn_arrays", "0x00000001"),
                     ("render_pb_pages", "0x00000422"), ("hold_recovery", "N"), ("kicker_format", "yes"), ("kicker_w_eq_wofs", "yes"),
                     ("kregnow_rows", L.K0F_KREGNOW_ROWS), ("kregnow_no_clear_rows", "yes"), ("kregnow_bif_rows", "yes")):
            add(P, n, q, v, m, "control")
        add(P, n, "kicks_eq_wofs", "yes", "[infer] the per-load kick count equals the command count since the boot", "heldout")
    return P


def preds_k0t(t):
    P = []
    for j in t["jobs"]:
        n, row = j["name"], j["row"]
        if row == "GD":
            m = "L1 g-dd dd-p1 (closing3/r3-geo/out/g-dd/raw.sha256)"
            for q, v in (("rc", 0), ("o0_line", "yes"), ("lines_sha256", "yes"), ("class", "ok")):
                add(P, n, q, v, m, "control")
            for q in ("param_sha256", "tadata_sha256"):
                add(P, n, q, "yes", "[infer] the render buffers are as L1's with render_rgn_arrays 1", "heldout")
        else:
            m = "L2 q-t t-ctl-green-16x16"
            for q, v in (("rc", 0), ("o0_line", "yes"), ("status2_pre", "0x400"), ("status2_post", "0x400"), ("class", "ok")):
                add(P, n, q, v, m, "control")
    return P


def preds_k0c(t):
    P = []
    for j in t["jobs"]:
        n, row = j["name"], j["row"]
        if row == "C0":
            for q, v in (("pclink", "0x98"), ("p1", "1"), ("sa64", "2"), ("sa65", "K<<24"), ("sa63", "0"), ("kept", "yes")):
                add(P, n, q, v, "E791 A0", "control")
        else:
            m = "E155 no handler bit"       # L3 c C1 (= A7): kept 3 of 3
            for q, v in (("kept", "yes"), ("next_pclink", "0x98"), ("next_sa65", "K<<24"), ("read_minus_write", "0"), ("dword14", "0")):
                add(P, n, q, v, m, "control")
    return P


def preds_k0h(t):
    P = []
    for j in t["jobs"]:
        n, row = j["name"], j["row"]
        if row == "H0":
            add(P, n, "idle", "yes", "L3 h H0 (idle EDM)", "control")
        elif row == "H1":
            add(P, n, "hold_band", "yes", "S2 run 3 knob (L3 h H1: held 3 of 3)", "control")
            add(P, n, "elements", "all", "L3 h H1 (a running task's signature, 3 of 3)", "control")
        else:
            m = "E768 (ring_e1: K = 2 after the arm, +1 a kick)"
            for q, v in (("ticks_K_before", 2), ("kick_entries", 1), ("miscinfo_answered", "yes"), ("ticks_K_after", 3), ("grid", "yes")):
                add(P, n, q, v, m, "control")
    return P


def preds_act_f(t):
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "E0":
            for q, v in (("entries", "14+-2"), ("grid", "yes"), ("acted", "0")):
                add(P, n, q, v, "control (L3 e E0)", s)
            continue
        add(P, n, "acted", 1, "design", s)
        if row == "FC4":
            add(P, n, "kept", "yes", "H-EXITPATH (the closed exit alone keeps the tick: L3 X1)", s)
            add(P, n, "kept", "no", "H-BEFORE (the need is before the exit)", s)
            add(P, n, "flag_logged", 4, "design", s)
            add(P, n, "next_gap", "25000+-50", "H-EXITPATH (the closed exit alone keeps the tick: L3 X1)", s)
        else:
            want = {"FB": {"H-BOTH": "yes", "H-CFI": "yes", "H-PHAS": "yes", "H-ANY": "yes", "H-PLACE": "no"},
                    "FCF": {"H-BOTH": "no", "H-CFI": "yes", "H-PHAS": "no", "H-ANY": "yes"},
                    "FPH": {"H-BOTH": "no", "H-CFI": "no", "H-PHAS": "yes", "H-ANY": "yes"}}[row]
            for model, v in want.items():
                add(P, n, "kept", v, model, s)
            add(P, n, "flag_logged", 3, "design", s)
            add(P, n, "next_gap", "25000+-50", "kept rows (a kept pass leaves the grid)", s)
            add(P, n, "sig_busy", "yes", "E793 (a stop looks busy)", s)
        add(P, n, "p3_answered", "no", "L3 d (P3 answered 0 of 2 stops)", s)
    return P


def preds_act_t(t):
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "E0":
            for q, v in (("entries", "14+-2"), ("grid", "yes"), ("acted", "0")):
                add(P, n, q, v, "control (L3 e E0)", s)
            continue
        add(P, n, "acted", 1, "design", s)
        if row == "T1":
            m = "H-TIMERW-HARMLESS (the closed handler stores the same word)"
            add(P, n, "kept", "yes", m, s)
            add(P, n, "next_gap", "25000+-50", m, s)
            add(P, n, "flag_logged", 4, "design", s)
            add(P, n, "kept", "no", "H-TIMERW-STOPS (a str of the timer by our pass stops the tick)", s)
        else:
            add(P, n, "kept", "yes", "H-TIMER (the timer write is what an ended tick pass needs)", s)
            add(P, n, "kept", "no", "H-NOTIMER (our own end stops the tick whatever it stores: E793)", s)
            add(P, n, "flag_logged", 3, "design", s)
            add(P, n, "sig_busy", "yes", "E793 (a stop looks busy)", s)
            add(P, n, "next_gap", "25000+-50", "H-TIMER (the timer write is what an ended tick pass needs)", s)
        add(P, n, "p3_answered", "no", "L3 d (P3 answered 0 of 2 stops)", s)
    return P


def preds_kb(t):
    P = []
    def ad(P, n, q, v, model, s):               # the controls of the rows (the kicker file, ccbctl, the count of kicks, the answer) are control rows
        add(P, n, q, v, model, "control" if model.startswith("control") else s)
    H = ("H-KW", "H-LATCH", "H-HWC")
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "Q0":
            for m in H:
                ad(P, n, "ticks_K", 2, m, s)
            ad(P, n, "kicker_w_after", 2, "control", s)
            ad(P, n, "kicks_delta", 0, "control", s)
        elif row == "Q1":
            for m, v in zip(H, (L.KICKER_WORD, 2, 2)):
                ad(P, n, "ticks_K_post_set", v, m, s)
            ad(P, n, "kicker_w_after", L.KICKER_WORD, "control (the file reads what was written)", s)
            ad(P, n, "ccbctl0_after", 2, "control (no command)", s)
            ad(P, n, "kicks_delta", 0, "control (no kick)", s)
        elif row == "Q2":
            for m, v in zip(H, (L.KICKER_WORD, 2, 2)):
                ad(P, n, "ticks_K_pre_kick", v, m, s)
            for m, v in zip(H, (L.KICKER_WORD + 1, L.KICKER_WORD + 1, 3)):
                ad(P, n, "ticks_K_post_kick", v, m, s)
            ad(P, n, "kicker_w_after", L.KICKER_WORD + 1, "control (the command bumps the word)", s)
            ad(P, n, "ccbctl0_after", 3, "control", s)
            ad(P, n, "kicks_delta", 1, "control", s)
            ad(P, n, "miscinfo_answered", "yes", "control", s)
        else:
            for m, v in zip(H, (2, 2, 3)):
                ad(P, n, "ticks_K_post_kick", v, m, s)
            ad(P, n, "kicker_w_after", 2, "control (kick_no_bump leaves the word)", s)
            ad(P, n, "ccbctl0_after", 3, "control (the command is written)", s)
            ad(P, n, "kicks_delta", 1, "control (the command is kicked)", s)
            ad(P, n, "kick_no_bump_after", "N", "control (one-shot)", s)
            ad(P, n, "miscinfo_answered", "yes", "control", s)
    return P


def preds_e2b(t):
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "R":
            add(P, n, "e748_words", "yes", "E748 (pa0-pa4 = sa64-sa68 = the frozen words)", s)
            add(P, n, "next_same", "yes", "E748 (the next pass reads the same)", s)
        elif row in ("S", "Z67", "Z68"):
            reg, alias = ("pa3", "sa67") if row in ("S", "Z67") else ("pa4", "sa68")
            m = "E748 (a write to the sa is read back through the pa)"
            add(P, n, f"{reg}_same", "M", m, s)
            add(P, n, f"{reg}_next", "M", m, s)
            add(P, n, f"{alias}_next", "M", m, s)
        else:
            pa, sa = {"C4": ("pa3", "sa67"), "C5": ("pa4", "sa68"), "C6": ("pa2", "sa66")}[row]
            for m, (a, b, c, d) in (("H-D alias", ("M", "M", "M", "M")), ("H-B lost", ("old", "old", "old", "old")),
                                    ("H-P private", ("M", "old", "M", "old"))):
                add(P, n, f"{pa}_same", a, m, s)
                add(P, n, f"{sa}_same", b, m, s)
                if row != "C6":
                    add(P, n, f"{pa}_next", c, m, s)
                    add(P, n, f"{sa}_next", d, m, s)
            add(P, n, "neighbours_unchanged", "yes", "control (only the one register is written)", s)
    return P


def preds_e3(t, route):
    P = []
    models = {"s2_step1": ("0x440", "0x440", "0x440"), "s2_step2": ("0x440", "0x440", "0x440"), "s2_step3": ("0x440", "0x400", "0x440"),
              "s2_step4": ("0x400", "0x400", "0x440"), "s2_step5": ("0x440", "0x440", "0x440")}
    for j in t["jobs"]:
        n, s = j["name"], j["set"]
        add(P, n, "status2_pre", "0x400", "control (idle after the reset)", "control")
        for q, vals in models.items():
            lab = "fit" if q in ("s2_step1", "s2_step2") else s
            for m, v in zip(("H-W", "H-ALL", "H-NONE"), vals):
                add(P, n, q, v, m, lab)
        add(P, n, "bit10_always", "yes", "control (DCU_INVAL_COMPLETE is the idle level)", "control")
        if route == "fw":
            add(P, n, "task_took_commands", "yes", "control (the command word is taken once)", "control")
    return P


def preds_e3b(t):
    P = []
    for j in t["jobs"]:
        n, row, s = j["name"], j["row"], j["set"]
        if row == "B0":
            for q, v in (("tool_ok", "yes"), ("tick_alive", "yes"), ("end_render_entries", 1), ("skipped", 0)):
                add(P, n, q, v, "control (the fill without the skip)", s)
            continue
        add(P, n, "skipped", 1, "design", s)
        add(P, n, "tick_alive", "no", "H-STOP3 (a skipped end-render pass stops the tick: E793)", s)
        add(P, n, "tick_alive", "yes", "H-FREE3", s)
        add(P, n, "bit18_in_watch", "all", "H-LEVEL (bit 18 holds until acknowledged: E547's inference)", s)
        add(P, n, "bit18_in_watch", "never", "H-PULSE", s)
        add(P, n, "end_render_entries", 1, "H-ONCE (the event is not re-fired)", s)
        add(P, n, "end_render_entries", ">1", "H-REFIRE", s)
        for m, v in (("H-W", "1"), ("H-ALL", "0"), ("H-NONE", "1")):
            add(P, n, "bit18_after_bit15", v, m, s)
        for m, v in (("H-W", "0"), ("H-ALL", "0"), ("H-NONE", "1")):
            add(P, n, "bit18_after_bit18", v, m, s)
        add(P, n, "bit29_clears", "yes", "H-W (stop only: the one unacknowledged bit of a stop clears and returns within 1 ms)", s)
        if row == "B2":
            add(P, n, "route_agrees", "yes", "H-W (the firmware route agrees with the host's: B1)", s)
    return P


PREDS = {"k0f": preds_k0f, "k0t": preds_k0t, "k0c": preds_k0c, "k0h": preds_k0h, "f": preds_act_f, "t": preds_act_t, "kb": preds_kb,
         "e2b": preds_e2b, "e3h": lambda t: preds_e3(t, "host"), "e3a": lambda t: preds_e3(t, "fw"), "e3b": preds_e3b}


# ---- writing -------------------------------------------------------------------------------------------------------------
def write_preds(stage, rows):
    out = ["case\tquantity\tvalue\tmodel\tset"] + ["\t".join(r) for r in rows]
    (R3 / "predictions" / f"{stage}.tsv").write_text("\n".join(out) + "\n")


def brief(j):
    skip = {"name", "set", "row", "runid", "op", "run_if", "steps", "files", "defaults", "args", "frozen", "prog"}
    return ", ".join(f"{k}={v}" for k, v in j.items() if k not in skip and v not in (None, [], False, 0))


def tables_md(info, tabs):
    L_ = ["# R3k job tables (generated by gen/gen_r3.py; the JSON in tables/ is what runs)", "",
          f"n for the 90-tick hold = ((90 + 0.5) * 25000 - 82) / 1.5 = {N90} (S2b's e4l, hold = 1.5 n + 15 units, about 90.5 ms).",
          f"EVENT_TIMER str word (ring_timer): {L.TIMER_STR_WORD:#010x} = 0x01000000 | {L.EVT_RELOAD} (the closed tick handler's own word).", "",
          "| blob | insns | bytes | sha256 | arm | sa writes | pa writes | str | ldr | cont4 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, i in info.items():
        L_.append(f"| {n} | {i['insns']} | {i['bytes']} | {i['sha256'][:16]}... | `{i['arm']}` | {', '.join(i['sa_writes']) or 'none'} | "
                  f"{', '.join(i['pa_writes']) or 'none'} | {', '.join('#%d' % x for x in i['str']) or 'none'} | {', '.join(i['ldr']) or 'none'} | "
                  f"{'yes' if i['cont4'] else 'no'} |")
    L_ += [""]
    for st in STAGES:
        t = tabs[st]
        L_ += [f"## stage {st} (session {t['session']}): blob {t['blob']}, needs {t['needs']}, stop budget {t['stop_budget']} (stop number "
               f"{t['stop_budget'] + 1} ends the stage), reset + arm each job: {t['per_job_reset']}", "",
               "| job | set | row | op | parameters | run if |", "|---|---|---|---|---|---|"]
        for j in t["jobs"]:
            L_.append(f"| {j['name']} | {j['set']} | {j['row']} | {j['op']} | {brief(j)} | {j.get('run_if') or ''} |")
        L_.append("")
    (R3 / "TABLES.md").write_text("\n".join(L_) + "\n")


def main():
    info = build_blobs()
    tabs = {st: table(st) for st in STAGES}
    (R3 / "tables").mkdir(exist_ok=True)
    (R3 / "predictions").mkdir(exist_ok=True)
    for st in STAGES:
        (R3 / "tables" / f"{st}.json").write_text(json.dumps(tabs[st], indent=1, sort_keys=True) + "\n")
        write_preds(st, PREDS[st](tabs[st]))
    for s, sts in L.SESSIONS.items():
        (R3 / f"stages-{s}.txt").write_text("\n".join(f"{st} {L.STAGE_INFO[st]['alarm']}" for st in sts) + "\n")
    tables_md(info, tabs)
    print("wrote", ", ".join(f"{k}: {v['insns']} insns" for k, v in info.items()), "; tables", ", ".join(STAGES),
          "; jobs", {st: len(tabs[st]["jobs"]) for st in STAGES}, "total", sum(len(t["jobs"]) for t in tabs.values()))


if __name__ == "__main__":
    main()
