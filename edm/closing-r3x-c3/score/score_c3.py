#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_c3.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...: score C3's one stage (c3) from what the runner kept (out/c3/: NAME.json,
cases.tsv, stage.json, env.json, stop-*.json).  Written before the run and frozen (run/freeze_c3.sh); refuses unless
`run/freeze_c3.sh verify` passes (the check is skipped under C3_NO_FREEZE_CHECK=1, set by the tests only).  Prints a line a job, the
verdict lines (Q124's p2/p3, Q158's rows, the start state) and one `SUMMARY:` line.  Standard library only.

A job has up to three readings of the registers at a task's entry: rd0 (the host's reader, before the writer), rdA (the reader the
writer armed, at the next event) and rdB (the host's reader after the row's perturbation: 1200 ms, a client fill, a firmware reload,
a debugfs reset and reload).  States a row can end in: held / FAILED (a prediction against a measurement), cannot tell (the
measurement does not decide: the reader did not run, the job's own control failed) and void (the job must not be read: no record, a
class that is not a result, a writer that did not run, an sa63 read-back that is not what the writer wrote).  Void and cannot-tell
rows never count as a pass.  The tally keeps fit rows, held-out rows, replicates and controls apart.

STOP SIGNATURE.  A tick stop is classed from the registers the runner dumped BEFORE the reset (two samples 30 ms apart):
  busy          the clock status (reg 0x0008) is not idle (0x20): a task or a unit is running
  idle-pending  idle, but USE0_SERV_EVENT (reg 0x0B14) bit 16 (EMPTY) is clear: events queued, none served
  idle-empty    idle and EMPTY set: nothing queued, nothing running
It is scored against E537's: busy (0x000ccfa0), USE0_SERV_EVENT 0x9e0 (EMPTY clear, count frozen), EVENT_TIMER counting,
EVENT_STATUS 0x20000000; `matches E537` needs all four.  C3's stop budget is 0: the first stop ends the stage.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R3 = HERE.parent
sys.path.insert(0, str(R3 / "gen"))
import c3layout as L  # noqa: E402

RESULT_CLASSES = {"ok", "stop", "noreader"}
GATE_OF = {}
GATE_EXITS = (0, 8)
MARK_REGS = ("sa63", "r20", "r21", "i0", "i1")
CARRY_REGS = ("sa63", "r20", "r21", "i0", "i1", "sa100", "sa127", "sa20", "sa24", "p2", "p3")
SA_PLAIN = ("sa100", "sa127", "sa20", "sa24")


def load_table(stage, base=None):
    return json.loads(((base or R3) / "tables" / f"{stage}.json").read_text())


def load_preds(stage, base=None):
    rows = ((base or R3) / "predictions" / f"{stage}.tsv").read_text().splitlines()[1:]
    return [dict(zip(("case", "quantity", "value", "model", "set"), r.split("\t"))) for r in rows if r.strip()]


def record(d, name):
    """The job's record, only if this stage's last run (stage.json) wrote it (nothing is ever deleted: an older file of the
    same stage is not read)."""
    try:
        st = json.loads((pathlib.Path(d) / "stage.json").read_text())
        rec = json.loads((pathlib.Path(d) / f"{name}.json").read_text())
    except (OSError, ValueError):
        return None
    if name not in st.get("jobs_run", []) or rec.get("run") != st.get("run"):
        return None
    return rec


class Tally:
    """Rows by label kind; ok True / False / None (cannot tell)."""
    KINDS = ("fit", "held out", "replicate", "control")

    def __init__(self):
        self.rows = []

    def add(self, case, quantity, model, label, ok, note=""):
        kind = ("fit" if label.startswith("fit") else "held out" if label == "heldout" else
                "replicate" if label.startswith("replicate") else "control" if label == "control" else "alt")
        self.rows.append((case, quantity, model, kind, ok, note))

    def line(self):
        parts = []
        for k in self.KINDS:
            rs = [r for r in self.rows if r[3] == k]
            if not rs:
                continue
            by = {}
            for r in rs:
                by.setdefault(r[2], []).append(r[4])
            ref = [m for m, v in by.items() if any(x is False for x in v)]
            ct = [m for m, v in by.items() if any(x is None for x in v) and not any(x is False for x in v)]
            n_ok = sum(1 for r in rs if r[4] is True)
            n_bad = sum(1 for r in rs if r[4] is False)
            n_ct = sum(1 for r in rs if r[4] is None)
            parts.append(f"{k}: {n_ok} held, {n_bad} FAILED, {n_ct} cannot tell/void"
                         + (f"; refuted {sorted(ref)}" if ref else "") + (f"; cannot tell {sorted(ct)}" if ct else ""))
        return "; ".join(parts) if parts else "no rows"


class Stage:
    def __init__(self, stage, d, base=None):
        self.stage, self.d = stage, pathlib.Path(d)
        self.table = load_table(stage, base)
        self.preds = load_preds(stage, base)
        self.lines = []
        self.t = Tally()
        try:
            self.stagerec = json.loads((self.d / "stage.json").read_text())
        except (OSError, ValueError):
            self.stagerec = None

    def p(self, s):
        self.lines.append(s)

    def stage_note(self):
        if self.stagerec is None:
            return "no stage.json (the stage did not finish writing)"
        if self.stagerec.get("exit") != 0:
            return f"stage exit {self.stagerec.get('exit')}: {self.stagerec.get('why', '')}"
        return None

    def void_rows_except(self, case, keep_q):
        for pr in self.preds:
            if pr["case"] == case and pr["quantity"] != keep_q:
                self.t.add(case, pr["quantity"], pr["model"], pr["set"], None, "not read")

    def tally_preds(self, case, quantity, ok_by_model, note=""):
        """One measurement against every frozen row of (case, quantity): ok_by_model maps a model-name prefix to the verdict
        (True, False, None); a row whose model matches no prefix is not scored."""
        for pr in self.preds:
            if pr["case"] != case or pr["quantity"] != quantity:
                continue
            for pref, ok in ok_by_model.items():
                if pr["model"].startswith(pref):
                    self.t.add(case, quantity, pr["model"], pr["set"], ok, note)

    def pred_value(self, case, quantity, model=None):
        for pr in self.preds:
            if pr["case"] == case and pr["quantity"] == quantity and (model is None or pr["model"].startswith(model)):
                return pr["value"]
        return None


# ---- the stop signature ---------------------------------------------------------------------------------------------------


def parse_regs_text(text):
    """({offset: value}, {hostctl dword: value}) from a `regs` file (as the runner and the landed fwtask_run read it); a
    `skip` value is left out."""
    out, hc = {}, {}
    for line in text.splitlines():
        m = re.match(r"reg (0x[0-9a-f]+) (0x[0-9a-f]+)$", line)
        if m:
            out[int(m.group(1), 16)] = int(m.group(2), 16)
        m = re.match(r"hostctl (0x[0-9a-f]+) (0x[0-9a-f]+)$", line)
        if m:
            hc[int(m.group(1), 16) // 4] = int(m.group(2), 16)
    return out, hc


def sample_of(sm):
    """A kept sample {"regs": {"0x0008": v, ...}, "hc12": v} as ({int: v}, hc12)."""
    return {int(k, 0): v for k, v in (sm.get("regs") or {}).items()}, sm.get("hc12")


def score_sig(samples):
    """Score a stop from its register samples (two or more, in time order).  Returns a dict: class (busy / idle-pending /
    idle-empty / unreadable), the four elements of E537's signature, matches_e537, note."""
    if not samples or len(samples) < 2:
        return {"class": "unreadable", "matches_e537": None, "elements": {}, "note": "fewer than two samples"}
    (r1, h1), (r2, h2) = sample_of(samples[0]), sample_of(samples[-1])
    need = (L.REG_CLKSTAT, L.REG_SERV_EVENT, L.REG_EVENT_TIMER, L.REG_EVENT_STATUS)
    if any(k not in r1 or k not in r2 for k in need):
        return {"class": "unreadable", "matches_e537": None, "elements": {}, "note": "a signature register is missing"}
    clk, sv, tm, es = r2[L.REG_CLKSTAT], r2[L.REG_SERV_EVENT], r2[L.REG_EVENT_TIMER], r2[L.REG_EVENT_STATUS]
    idle = (clk & ~L.CLK_IDLE) == 0
    empty = bool(sv >> L.SERV_EMPTY_BIT & 1)
    klass = "busy" if not idle else ("idle-empty" if empty else "idle-pending")
    el = {"busy": not idle, "serv_event_empty_clear": not empty, "serv_event_frozen": r1[L.REG_SERV_EVENT] == sv,
          "timer_counting": r1[L.REG_EVENT_TIMER] != tm, "event_status_0x20000000": es == L.E537_SIG["event_status"]}
    match = el["busy"] and el["serv_event_empty_clear"] and el["serv_event_frozen"] and el["timer_counting"] \
        and el["event_status_0x20000000"]
    return {"class": klass, "matches_e537": match, "elements": el, "hostctl12_moved": (h1 != h2) if h1 is not None and h2 is not None else None,
            "values": {"clkstat": clk, "serv_event": sv, "event_timer": tm, "event_status": es},
            "exact_e537_values": {"clkstat": clk == L.E537_SIG["clkstat"], "serv_event": sv == L.E537_SIG["serv_event"]},
            "note": ""}


def sig_line(sg):
    if sg["class"] == "unreadable":
        return f"signature unreadable ({sg['note']})"
    el = sg["elements"]
    miss = [k for k, v in el.items() if not v]
    return (f"signature {sg['class']}, " + ("matches E537" if sg["matches_e537"] else "differs from E537 in " + ", ".join(miss))
            + f" (clk {sg['values']['clkstat']:#x}, serv_event {sg['values']['serv_event']:#x}, timer {sg['values']['event_timer']:#x},"
              f" status {sg['values']['event_status']:#x})")


def rec_sig(rec):
    sg = rec.get("sig")
    return score_sig(sg.get("samples") if isinstance(sg, dict) else None)


# ---- interval helper for "dword 12 delta = passes - n" --------------------------------------------------------------------


# ---- the readings ---------------------------------------------------------------------------------------------------------
def rd_of(x):
    """{field: value} of a reader record {"ran": bool, "rd": [dwords]}, or None."""
    if not isinstance(x, dict) or not x.get("ran"):
        return None
    r = x.get("rd")
    return dict(zip(L.RD_FIELDS, r)) if isinstance(r, list) and len(r) >= len(L.RD_FIELDS) else None


def void_job(rec, j):
    if rec is None:
        return "no record kept"
    if rec.get("class") == "skipped":
        return "not run (" + rec.get("note", "").strip() + ")"
    if rec.get("class") not in RESULT_CLASSES:
        return f"class {rec.get('class')}"
    if j["write"]:
        wr = rec.get("writer") or {}
        if not wr.get("done"):
            return "the writer's flag was not set (it did not run)"
        w = dict(zip(L.WR_FIELDS, wr.get("wr") or []))
        if w.get("sa63_written") != j["sa63"] or w.get("sa63_readback") != w.get("sa63_written"):
            return (f"the sa63 read-back ({w.get('sa63_readback')}) is not what the writer wrote ({w.get('sa63_written')}, the "
                    f"table's {j['sa63']:#x}): the write did not take")
    return None


def hx(v):
    return f"{v:#x}"


def ok_str(b):
    return "yes" if b else "no"


class C3(Stage):
    def judge(self, case, q, obs, note=""):
        """One measurement (a string, or None = cannot tell) against every frozen row of (case, quantity)."""
        res = []
        for pr in self.preds:
            if pr["case"] != case or pr["quantity"] != q:
                continue
            ok = None if obs is None else (obs == pr["value"])
            self.t.add(case, q, pr["model"], pr["set"], ok, note)
            res.append((pr["model"], ok))
        return res

    def void_rows(self, case, why):
        for pr in self.preds:
            if pr["case"] == case:
                self.t.add(case, pr["quantity"], pr["model"], pr["set"], None, why)


def marks_ok(rd, j):
    return all(rd[k] == v for k, v in zip(MARK_REGS, [j["sa63"]] + list(j["ri"])))


def carry_ok(prev, rd0):
    if prev is None or rd0 is None:
        return None
    return all(prev[k] == rd0[k] for k in CARRY_REGS if k in ("sa63", "r20", "r21", "i0", "i1", "sa100", "sa127", "sa20", "sa24")) \
        and (prev["p2"], prev["p3"]) == (rd0["p2"], rd0["p3"])


def score_c3(S):
    kept, stops, sigs = {}, [], []
    prev = None                        # the last reading of the previous job (rdB, else rdA, else rd0)
    prev_gap = False                   # the previous job's record was missing: carry cannot be told
    last_fill_r21 = None
    facts = {"p2p3": [], "rows": {}, "s0": None, "ctl_fail": []}
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = record(S.d, n)
        v = void_job(rec, j)
        if v:
            S.p(f"{n}: NODATA ({v})")
            S.void_rows(n, "void")
            prev, prev_gap = None, True
            if row == "F":
                last_fill_r21 = None                      # post-run fix C7: no step across a fill that was not read
            continue
        cls = rec["class"]
        kept_obs = "yes" if cls == "ok" else "no" if cls == "stop" else None
        kept.setdefault(row, []).append(kept_obs)
        info = f"{n}: class {cls}"
        S.judge(n, "kept", kept_obs, "reader not run" if kept_obs is None else "")
        rd0, rdA, rdB = rd_of(rec.get("rd0")), rd_of(rec.get("rdA")), rd_of(rec.get("rdB"))
        if cls == "stop":
            sg = rec_sig(rec)
            sigs.append((n, sg))
            stops.append(n)
            S.p(info + f" (tick stopped; the stage ends); {sig_line(sg)}")
            S.void_rows_except(n, "kept")
            prev, prev_gap = None, True
            if row == "F":
                last_fill_r21 = None                      # post-run fix C7: no step across a fill that was not read
            continue
        if cls == "noreader" or rd0 is None or (j["write"] and (rdA is None or rdB is None)):
            S.p(info + " (tick kept, a reader did not run: cannot tell)")
            S.void_rows_except(n, "kept")
            prev, prev_gap = None, True
            if row == "F":
                last_fill_r21 = None                      # post-run fix C7: no step across a fill that was not read
            continue
        # ---- S0 -----------------------------------------------------------------------------------------------------
        if row == "S0":
            S.judge(n, "rd0_pclink", hx(rd0["pclink"]))
            S.judge(n, "rd0_p0p1", f"{rd0['p0']}{rd0['p1']}")
            S.judge(n, "rd0_p2p3", f"{rd0['p2']}{rd0['p3']}")
            S.judge(n, "rd0_sa64", str(rd0["sa64"]))
            S.judge(n, "rd0_sa63", str(rd0["sa63"]))
            S.judge(n, "rd0_sa20", str(rd0["sa20"]))
            S.judge(n, "rd0_sa24", str(rd0["sa24"]))
            facts["s0"] = rd0
            S.p(info + f"; S0 as found: pclink {hx(rd0['pclink'])} p {rd0['p0']}{rd0['p1']}{rd0['p2']}{rd0['p3']} sa63 {rd0['sa63']:#x} "
                f"sa64 {rd0['sa64']:#x}")
            prev, prev_gap = rd0, False
            continue
        # ---- the writer's jobs --------------------------------------------------------------------------------------
        cr = carry_ok(prev, rd0) if not prev_gap else None
        S.judge(n, "carry", None if cr is None else ok_str(cr), "previous job not read" if cr is None else "")
        am = marks_ok(rdA, j)
        S.judge(n, "a_markers", ok_str(am))
        S.judge(n, "a_pclink", hx(rdA["pclink"]))
        S.judge(n, "a_p0", str(rdA["p0"]))
        S.judge(n, "a_p1", str(rdA["p1"]))
        S.judge(n, "a_p2p3", f"{rdA['p2']}{rdA['p3']}")
        if (j["flags"][2], j["flags"][3]) != (1, 1):
            facts["p2p3"].append((n, (rdA["p2"], rdA["p3"]), (j["flags"][2], j["flags"][3])))
        dn = ""
        if not am:
            facts["ctl_fail"].append(n)
            dn = "; CONTROL FAILED: a marker was not read at the next event (" + ", ".join(
                k for k, v_ in zip(MARK_REGS, [j["sa63"]] + list(j["ri"])) if rdA[k] != v_) + "): the perturbation rows are cannot tell"
        gate = ok_str if am else (lambda b: None)         # a failed control: the rows after the perturbation cannot be told
        gnote = "" if am else "control failed"
        gv = (lambda x: x) if am else (lambda x: None)    # post-run fix C7: the failed control gates every row after it
        # ---- the perturbation's rows -----------------------------------------------------------------------------
        b = rdB
        res = {}
        if row == "N":
            S.judge(n, "b_markers", gate(marks_ok(b, j)), gnote)
            S.judge(n, "b_p0p1", gv(f"{b['p0']}{b['p1']}"), gnote)
            S.judge(n, "b_pclink", gv(hx(b["pclink"])), gnote)
            S.judge(n, "b_p2p3", gv(f"{b['p2']}{b['p3']}"), gnote)
            res["markers"] = marks_ok(b, j)
        elif row == "F":
            ik = b["i0"] == j["ri"][2] and b["i1"] == j["ri"][3]
            S.judge(n, "b_i_kept", gate(ik), gnote)
            S.judge(n, "b_r_replaced", gate(b["r20"] != j["ri"][0] and b["r21"] != j["ri"][1]), gnote)
            S.judge(n, "b_r20_zero", gate(b["r20"] == 0), gnote)
            if j["rep"]:
                step = None if last_fill_r21 is None else hx((b["r21"] - last_fill_r21) & 0xFFFFFFFF)
                S.judge(n, "b_r21_step", step if am else None, "no previous fill reading" if step is None else gnote)
            S.judge(n, "b_sa63_kept", gate(b["sa63"] == j["sa63"]), gnote)
            S.judge(n, "b_p0p1", gv(f"{b['p0']}{b['p1']}"), gnote)
            S.judge(n, "b_pclink", gv(hx(b["pclink"])), gnote)
            S.judge(n, "b_p2p3", gv(f"{b['p2']}{b['p3']}"), gnote)
            last_fill_r21 = b["r21"] if am else None       # post-run fix C7: a fill whose control failed is no base for a step
            res.update({"i": ik, "r_replaced": b["r20"] != j["ri"][0] and b["r21"] != j["ri"][1], "sa63": b["sa63"] == j["sa63"]})
        else:
            ik = b["i0"] == j["ri"][2] and b["i1"] == j["ri"][3]
            rk = b["r20"] == j["ri"][0] and b["r21"] == j["ri"][1]
            sk = b["sa63"] == j["sa63"]
            S.judge(n, "b_i_kept", gate(ik), gnote)
            S.judge(n, "b_r_kept", gate(rk), gnote)
            S.judge(n, "b_sa63_kept", gate(sk), gnote)
            S.judge(n, "b_p2p3", gv(f"{b['p2']}{b['p3']}"), gnote)
            S.judge(n, "b_p0p1", gv(f"{b['p0']}{b['p1']}"), gnote)
            S.judge(n, "b_pclink", gv(hx(b["pclink"])), gnote)
            S.judge(n, "b_sa20_sa24_zero", gate(b["sa20"] == 0 and b["sa24"] == 0), gnote)
            res.update({"i": ik, "r": rk, "sa63": sk, "r20": b["r20"] == j["ri"][0], "r21": b["r21"] == j["ri"][1]})
        if row != "F" or True:
            for r_ in SA_PLAIN:
                S.judge(n, f"b_{r_}_same", gate(b[r_] == rdA[r_]), gnote)
        res["sa_plain"] = {r_: (rdA[r_], b[r_]) for r_ in SA_PLAIN}
        res["p"] = (b["p2"], b["p3"])
        res["r_vals"] = (b["r20"], b["r21"])
        res["ctl"] = am
        facts["rows"].setdefault(row, []).append((n, res))
        S.p(info + f"; next event: pclink {hx(rdA['pclink'])} p {rdA['p0']}{rdA['p1']}{rdA['p2']}{rdA['p3']} (flags {''.join(map(str, j['flags']))}); "
            f"after {j['perturb']}: p {b['p0']}{b['p1']}{b['p2']}{b['p3']} sa63 {b['sa63']:#x} r20 {b['r20']:#x} r21 {b['r21']:#x} "
            f"i0 {b['i0']:#x} i1 {b['i1']:#x}" + dn)
        prev, prev_gap = b, False
    # ---- verdict lines ----------------------------------------------------------------------------------------------
    pp = facts["p2p3"]
    if pp:
        keep_n = sum(1 for _, got, fl in pp if got == fl)
        set_n = sum(1 for _, got, fl in pp if got == (1, 1))
        if keep_n == len(pp):
            S.p(f"Q124 p2/p3 at the next entry, {len(pp)} discriminating jobs (a flag 0): H-KEEP supported (the writer's p2 p3 read back "
                f"{keep_n} of {len(pp)}), H-SET refuted")
        elif set_n == len(pp):
            S.p(f"Q124 p2/p3 at the next entry, {len(pp)} discriminating jobs (a flag 0): H-SET supported (p2 = p3 = 1 in {set_n} of "
                f"{len(pp)}), H-KEEP refuted")
        else:
            S.p(f"Q124 p2/p3 at the next entry, {len(pp)} discriminating jobs: mixed (H-KEEP {keep_n}, H-SET {set_n}): cannot tell")
    else:
        S.p("Q124 p2/p3: no discriminating job was read")
    for row, what in (("L", "reload (no reset)"), ("R", "debugfs reset and reload"), ("F", "client fill"), ("N", "1200 ms")):
        rs_all = facts["rows"].get(row, [])
        if not rs_all:
            S.p(f"Q158 {row} ({what}): not read")
            continue
        # post-run fix C7: a job whose control failed is not counted, and the line names it
        rs = [(x, r) for x, r in rs_all if r["ctl"]]
        gated = [x for x, r in rs_all if not r["ctl"]]
        gtail = (f"; {len(gated)} job{'s' if len(gated) != 1 else ''} with a failed control not counted ({', '.join(gated)})"
                 if gated else "")
        if not rs:
            S.p(f"Q158 {row} ({what}): cannot tell" + gtail)
            continue
        if row == "N":
            m = sum(1 for _, r in rs if r["markers"])
            S.p(f"Q158 N ({what}): sa63, r20, r21, i0, i1 kept in {m} of {len(rs)} jobs" + gtail)
            continue
        parts = [f"i0/i1 {sum(1 for _, r in rs if r['i'])}/{len(rs)}", f"sa63 {sum(1 for _, r in rs if r['sa63'])}/{len(rs)}"]
        if row == "F":
            parts.append(f"r20/r21 replaced {sum(1 for _, r in rs if r['r_replaced'])}/{len(rs)}")
        else:
            parts.append(f"r20/r21 both survived {sum(1 for _, r in rs if r['r'])}/{len(rs)} (r20 {sum(1 for _, r in rs if r['r20'])}/{len(rs)}, "
                         f"r21 {sum(1 for _, r in rs if r['r21'])}/{len(rs)})")
        S.p(f"Q158 {row} ({what}): kept " + ", ".join(parts) + "; p2 p3 after: " + " ".join(f"{r['p'][0]}{r['p'][1]}" for _, r in rs) + gtail)
    # start state and sa100/sa127: as found
    s0 = facts["s0"]
    if s0:
        S.p(f"start state S0 (as found after the stage's own arm): sa100/sa127 as found {s0['sa100']:#x} {s0['sa127']:#x}, sa20 {s0['sa20']:#x}, "
            f"sa24 {s0['sa24']:#x}, i0 {s0['i0']:#x}, i1 {s0['i1']:#x}, r20 {s0['r20']:#x}, r21 {s0['r21']:#x}, p {s0['p0']}{s0['p1']}"
            f"{s0['p2']}{s0['p3']}, pclink {s0['pclink']:#x}")
        if s0["sa100"] == 0 and s0["sa127"] == 0:
            S.p("sa100 and sa127 read 0 at S0: our task cannot write them (R2-1 b), so their persistence across a reload or reset is not "
                "informative (a register that was never set stays 0); the start state is what S0 shows")
        else:
            S.p("sa100 and sa127 are not 0 at S0 (set before this run): 'unchanged' in every later reading is persistence of an old value")
    elif S.table["jobs"]:
        S.p("start state: S0 was not read")
    for h in ("H-KEEP", "H-ALL"):
        rows_ = [r for r in S.t.rows if r[1] == "b_r_kept" and r[2].startswith(h)]
        if rows_ and all(r[4] is not None for r in rows_):
            S.p(f"{h}, its r20/r21 row only (both kept after a reload or a reset): " + ("held in all " + str(len(rows_)) if all(r[4] for r in rows_) else
                f"FAILED in {sum(1 for r in rows_ if r[4] is False)} of {len(rows_)} jobs"))
            allrows = [r for r in S.t.rows if r[2].startswith(h + " ") and r[1] in ("b_i_kept", "b_r_kept", "b_sa63_kept")]
            S.p(f"{h} as a whole (its i, r and sa63 rows after a reload or a reset): {sum(1 for r in allrows if r[4] is True)} held, "
                f"{sum(1 for r in allrows if r[4] is False)} FAILED of {len(allrows)}")
    if facts["ctl_fail"]:
        S.p("controls failed in: " + ", ".join(facts["ctl_fail"]))
    stop_sig = "; ".join(f"{x}: {sg['class']}{' (E537)' if sg['matches_e537'] else ''}" for x, sg in sigs)
    note = S.stage_note()
    nk = sum(1 for v in kept.values() for k in v if k == "yes")
    nt = sum(len(v) for v in kept.values())
    return (f"c3: kept {nk} of {nt} read jobs, stops {len(stops)} {stops}" + (f" [{stop_sig}]" if stops else "")
            + f"; controls failed {facts['ctl_fail'] or 'none'}; rows: {S.t.line()}" + (f"; {note}" if note else ""))


# ---- gate, freeze, main ---------------------------------------------------------------------------------------------------
def gate(stage, root):
    print(f"GATE {stage} OPEN (no previous stage)")
    return 0


def freeze_problem():
    if os.environ.get("C3_NO_FREEZE_CHECK") == "1":
        return None
    r = subprocess.run([str(R3 / "run" / "freeze_c3.sh"), "verify"], capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stdout + r.stderr).strip().splitlines()[-1:]


def score(stage, d, base=None):
    S = C3(stage, d, base)
    summary = score_c3(S)
    return S, summary


def main(argv):
    if len(argv) >= 4 and argv[1] == "gate":
        return gate(argv[2], argv[3])
    if len(argv) >= 3 and argv[1] == "sig":
        for f in argv[2:]:
            text = pathlib.Path(f).read_text()
            sm = []
            for part in text.split("\n===\n"):
                r, hc = parse_regs_text(part)
                sm.append({"regs": {hex(k): v for k, v in r.items()}, "hc12": hc.get(12)})
            print(f, sig_line(score_sig(sm)))
        return 0
    if len(argv) < 3 or argv[1] != "c3":
        print("usage: score_c3.py c3 OUTDIR | gate c3 ROOT | sig FILE...")
        return 2
    prob = freeze_problem()
    if prob:
        print(f"REFUSING: the frozen files changed ({prob})")
        return 3
    S, summary = score(argv[1], argv[2])
    for ln in S.lines:
        print(ln)
    print("SUMMARY: " + summary)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
