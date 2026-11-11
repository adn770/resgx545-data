#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_r3.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...: score one R3x-events stage (h, c, e, d) from what the runner kept
(out/STAGE/: NAME.json, cases.tsv, stage.json, env.json, stop-*.txt).  Written before the run and frozen (run/freeze_r3.sh); refuses unless
`run/freeze_r3.sh verify` passes (the check is skipped under R3_NO_FREEZE_CHECK=1, set by the tests only).  Prints a line a job and one
`SUMMARY:` line.  Standard library only.  A copy of closing2/r3-events/score/score_r3.py with the round 3 stages.

States a row can end in: held / FAILED (a prediction against a measurement), cannot tell (the measurement does not decide) and void (the
job must not be read: no record, a class that is not a result, no page, a writer whose flag was never set, a read-back that is not what the
writer wrote, a hold outside its knob band, an acted count that is not the design's).  Void and cannot-tell rows never count as a pass.
The tally keeps fit rows, held-out rows, replicates and controls apart.

STOP SIGNATURE (changed from R3: 0x012c is dropped, 0b).  Every tick stop is classed from the registers the runner dumped BEFORE the
reset (two samples 30 ms apart):
  busy          the clock status (reg 0x0008) is not idle (0x20): a task or a unit is running
  idle-pending  idle, but USE0_SERV_EVENT (reg 0x0B14) bit 16 (EMPTY) is clear: events queued, none served
  idle-empty    idle and EMPTY set: nothing queued, nothing running
`matches E537` needs busy, EMPTY clear, the count frozen and EVENT_TIMER counting; CR_EVENT_STATUS (0x12c = 0x20000000 in 234 of 234 kept
reads, healthy and stopped alike) is kept as a recorded value and is not part of the match.  The stop's marks (R3, 0a): the CCB read
offset minus the write offset (E537 +1; E793 0; a kick the skipped pass never served -1) and HostCtl dword 14 (0xad002600 in E537, 0 in
both E793 stops), taken from the signature samples (or the dump files).

D = the task's pass count minus HostCtl dword 12 (taken as a page read, a register read and a page read; a triple whose page reads differ is
dropped).  The row's D0 is the mode of the 20 reads before the row; a stop's D is read against it (P2).

`gate STAGE ROOT` exits 0 when the previous stage's own kept stage.json (ROOT/PREV/stage.json) says it finished (exit 0, or 8: a second stop
ended it, reset and gate exact) - derived from kept output only, so restaging never closes it.
"""
import json
import os
import pathlib
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R3 = HERE.parent
sys.path.insert(0, str(R3 / "gen"))
import r3layout as L  # noqa: E402

T = L.TICK_UNITS
RESULT_CLASSES_C = {"ok", "stop", "noreader"}
RESULT_CLASSES_H = {"ok", "stop"}
RESULT_CLASSES_E = {"ok", "stop", "kick-timeout"}
GUARD_TICK = 500
NEXT_GAP_TOL = 50
GATE_OF = L.GATE_OF
GATE_EXITS = (0, 8)
NOHANDLER = "E155 no handler bit"
KEPT_MODELS = (NOHANDLER, "H-TICKONLY")        # their mark rows (read, dword 14, miscinfo) are about a job that kept the tick
CLK_IDLE_VALUES = (0x20, 0x78)                  # H0: the idle clock status (E537's note; 3 of 234 reads were 0x78)
CLK_BUSY = 0x000CCFA0
STOP_ONLY_QUANTITIES = {"read_minus_write", "dword14", "sig_busy", "kick_entry", "miscinfo_answered"}


# ---- reading ---------------------------------------------------------------------------------------------------------
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


def rel(s, ref):
    d = (s - ref) & 0xFFFFFFFF
    d = d - (1 << 32) if d & 0x80000000 else d
    if s < (1 << 25) and ref < (1 << 25) and abs(d) > (1 << 23):
        d = d + (1 << 25) if d < 0 else d - (1 << 25)
    return d


def void_ring(rec, classes):
    """Why a ring job's record must not be read (None: it may)."""
    if rec is None:
        return "no record kept"
    if rec.get("class") not in classes:
        return f"class {rec.get('class')}"
    if rec.get("rc") is None:
        return "no rc recorded"
    pg, p2 = rec.get("page"), rec.get("page2")
    if not isinstance(pg, list) or len(pg) != L.PAGE_DWORDS:
        return "no page, or a truncated page"
    if pg[0] != L.MAGIC:
        return "the page header is not the kernel's magic"
    if not isinstance(p2, list) or len(p2) != L.PAGE_DWORDS:
        return "no second page (window-0 proof)"
    if p2[L.RING_BASE[0]:L.RING_END] != pg[L.RING_BASE[0]:L.RING_END]:
        return "the ring changed after the window closed (window 0 did not take)"
    return None


def ring(page):
    """{slot: [(flag, pa0, pa1, pa2, stamp), ...]} in rung order (flag 1 logged, 3 own end, 4 tail); ValueError on a corrupt flag."""
    out = {}
    for k in range(4):
        rows = []
        for j in range(L.RUNGS[k]):
            o = L.RING_BASE[k] + L.RUNG * j
            f = page[o]
            if f not in L.RING_FLAGS:
                raise ValueError(f"slot {k} rung {j} flag {f:#x}")
            if f:
                rows.append((f,) + tuple(page[o + 1:o + 5]))
        out[k] = rows
    return out


def merged(r):
    """Every slot's entries merged by CR_TIMER stamp: [(slot, flag, pa0, pa1, pa2, stamp)]."""
    ev = [(k,) + x for k in range(4) for x in r[k]]
    ref = ev[0][5] if ev else 0
    return sorted(ev, key=lambda e: rel(e[5], ref))


def from_stamp(ev, stamp):
    """The entries from the window's own CR_TIMER stamp on (earlier entries belong to nothing of this job)."""
    return [e for e in ev if rel(e[5], stamp) >= 0] if stamp is not None else ev


def e_tick(e):          # e = (slot, flag, pa0, pa1, pa2, stamp)
    return L.is_plain_tick(e[2], e[3])


def e_kick(e):
    return e[2] == 0 and (e[3] & L.LOW24) == L.KICK_LOW


def on_grid(d, tol=GUARD_TICK):
    k = round(d / T)
    return k >= 1 and abs(d - k * T) <= tol


def gaps(es):
    return [rel(b[5], a[5]) for a, b in zip(es, es[1:])]


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
        self.stop_names = []
        self.p3 = []                         # (job, answered) of every stop that sent P3

    def p(self, s):
        self.lines.append(s)

    def stage_note(self):
        if self.stagerec is None:
            return "no stage.json (the stage did not finish writing)"
        if self.stagerec.get("exit") != 0:
            return f"stage exit {self.stagerec.get('exit')}: {self.stagerec.get('why', '')}"
        return None

    def tally_preds(self, case, quantity, ok_by_model, note=""):
        """One measurement against every frozen row of (case, quantity): ok_by_model maps a model-name prefix to the verdict
        (True, False, None); a row whose model matches no prefix is not scored."""
        for pr in self.preds:
            if pr["case"] != case or pr["quantity"] != quantity:
                continue
            for pref, ok in ok_by_model.items():
                if pr["model"].startswith(pref):
                    self.t.add(case, quantity, pr["model"], pr["set"], ok, note)

    def tally_value(self, case, quantity, got, note="", skip_models=()):
        """Every frozen row of (case, quantity) against the measured value `got` (compared to the row's value as text; the row's
        model decides nothing: the row says what its model predicted).  None: cannot tell."""
        for pr in self.preds:
            if pr["case"] == case and pr["quantity"] == quantity and not any(pr["model"].startswith(m) for m in skip_models):
                self.t.add(case, quantity, pr["model"], pr["set"], None if got is None else str(got) == pr["value"], note)

    def pred_value(self, case, quantity, model=None):
        for pr in self.preds:
            if pr["case"] == case and pr["quantity"] == quantity and (model is None or pr["model"].startswith(model)):
                return pr["value"]
        return None

    def nodata(self, n, why):
        self.p(f"{n}: NODATA ({why})")
        for pr in self.preds:
            if pr["case"] == n and pr["quantity"] != "p3_answered":
                self.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "void")


# ---- the stop signature ---------------------------------------------------------------------------------------------------
def parse_regs_text(text):
    """({offset: value}, {hostctl dword: value}) from a `regs` file (as the runner and the landed fwtask_run read it); a
    `skip` value is left out."""
    r, hc, _ = L.parse_regs(text)
    return r, hc


def sample_of(sm):
    """A kept sample {"regs": {"0x8": v, ...}, "hc12": v} as ({int: v}, hc12)."""
    return {int(k, 0): v for k, v in (sm.get("regs") or {}).items()}, sm.get("hc12")


def score_sig(samples):
    """Score a stop from its register samples (two or more, in time order).  Returns a dict: class (busy / idle-pending /
    idle-empty / unreadable), the four elements of E537's signature, matches_e537, note.  0x012c is recorded, not matched (0b)."""
    samples = [s for s in (samples or []) if isinstance(s, dict) and "error" not in s]
    if len(samples) < 2:
        return {"class": "unreadable", "matches_e537": None, "elements": {}, "note": "fewer than two samples"}
    (r1, h1), (r2, h2) = sample_of(samples[0]), sample_of(samples[-1])
    need = (L.REG_CLKSTAT, L.REG_SERV_EVENT, L.REG_EVENT_TIMER)
    if any(r1.get(k) is None or r2.get(k) is None for k in need):
        return {"class": "unreadable", "matches_e537": None, "elements": {}, "note": "a signature register is missing"}
    clk, sv, tm, es = r2[L.REG_CLKSTAT], r2[L.REG_SERV_EVENT], r2[L.REG_EVENT_TIMER], r2.get(L.REG_EVENT_STATUS)
    idle = (clk & ~L.CLK_IDLE) == 0
    empty = bool(sv >> L.SERV_EMPTY_BIT & 1)
    klass = "busy" if not idle else ("idle-empty" if empty else "idle-pending")
    el = {"busy": not idle, "serv_event_empty_clear": not empty, "serv_event_frozen": r1[L.REG_SERV_EVENT] == sv,
          "timer_counting": r1[L.REG_EVENT_TIMER] != tm}
    match = all(el.values())
    return {"class": klass, "matches_e537": match, "elements": el,
            "hostctl12_moved": (h1 != h2) if h1 is not None and h2 is not None else None,
            "values": {"clkstat": clk, "serv_event": sv, "event_timer": tm, "event_status": es},
            "recorded": {"event_status_0x20000000": es == L.E537_SIG["event_status"]},
            "exact_e537_values": {"clkstat": clk == L.E537_SIG["clkstat"], "serv_event": sv == L.E537_SIG["serv_event"]},
            "note": ""}


def sig_line(sg):
    if sg["class"] == "unreadable":
        return f"signature unreadable ({sg['note']})"
    el = sg["elements"]
    miss = [k for k, v in el.items() if not v]
    v = sg["values"]
    es = f", status {v['event_status']:#x} recorded" if v["event_status"] is not None else ""
    return (f"signature {sg['class']}, " + ("matches E537" if sg["matches_e537"] else "differs from E537 in " + ", ".join(miss))
            + f" (clk {v['clkstat']:#x}, serv_event {v['serv_event']:#x}, timer {v['event_timer']:#x}{es})")


def rec_sig(rec):
    sg = rec.get("sig")
    return score_sig(sg.get("samples") if isinstance(sg, dict) else None)


# ---- the stop's marks and the D instrument ----------------------------------------------------------------------------------
def marks_from_samples(samples):
    """{"ccb": [w, r], "rmw": r - w as a signed 8-bit value, "hc14": dword 14} from the last readable sample that has them."""
    for sm in reversed([s for s in (samples or []) if isinstance(s, dict)]):
        cc, h14 = sm.get("ccb"), sm.get("hc14")
        if cc and cc[0] is not None and cc[1] is not None and h14 is not None:
            return {"ccb": cc, "rmw": L.signed8(cc[1] - cc[0]), "hc14": h14}
    return None


def marks_from_dump(d, name):
    """The same from the landed dump files of a stop (stop-NAME-regs.txt, else stop-NAME-status.txt)."""
    d = pathlib.Path(d)
    try:
        r, hc, cc = L.parse_regs((d / f"stop-{name}-regs.txt").read_text())
    except OSError:
        try:
            r, hc, cc, _ = L.parse_status((d / f"stop-{name}-status.txt").read_text())
        except OSError:
            return None
    if not cc or hc.get(L.HC_ASSERT_DWORD) is None:
        return None
    return {"ccb": cc, "rmw": L.signed8(cc[1] - cc[0]), "hc14": hc[L.HC_ASSERT_DWORD]}


def marks_of(S, rec):
    """The marks of a job: a stop's (signature samples, else the dump files), a kept job's (marks_post)."""
    if rec.get("class") == "stop":
        mk = marks_from_samples((rec.get("sig") or {}).get("samples")) or marks_from_dump(S.d, rec["name"])
        return mk
    mp = rec.get("marks_post") or {}
    cc = mp.get("ccb")
    if cc and cc[0] is not None and cc[1] is not None and mp.get("hc14") is not None:
        return {"ccb": cc, "rmw": L.signed8(cc[1] - cc[0]), "hc14": mp["hc14"]}
    return None


def d_vals(triples):
    """D = page pass count - HostCtl dword 12, of the triples whose two page reads agree (signed 32 bit)."""
    out = []
    for t in triples or []:
        try:
            a, h, b = t
        except (TypeError, ValueError):
            continue
        if a is None or h is None or a != b:
            continue
        v = (a - h) & 0xFFFFFFFF
        out.append(v - (1 << 32) if v & 0x80000000 else v)
    return out


def d_mode(vals):
    """(mode, share of the values equal to it) or (None, 0)."""
    if not vals:
        return None, 0.0
    m = max(set(vals), key=lambda v: (vals.count(v), -v))
    return m, vals.count(m) / len(vals)


def d0_of(rec):
    return d_mode(d_vals(rec.get("d0")))[0]


def d_of_samples(samples):
    """D of every sample that has a consistent pass pair and HostCtl dword 12."""
    return d_vals([[s["pass"][0], s.get("hc12"), s["pass"][1]] for s in samples or [] if isinstance(s, dict) and s.get("pass")])


# ---- interval helper for "dword 12 delta = passes - n" --------------------------------------------------------------------
def d12_minus_passes(rec):
    """The interval [lo, hi] that d12 - passes lies in, from the runner's two brackets (page PASS, HostCtl dword 12, page PASS
    before and after), or None.  d12 - P with P in [c - b, d - a]."""
    br = rec.get("bracket")
    if not br:
        return None
    try:
        (a, h0, b), (c, h1, d) = br["before"], br["after"]
    except (KeyError, ValueError, TypeError):
        return None
    d12 = (h1 - h0) & 0xFFFFFFFF
    return d12 - (d - a), d12 - (c - b)


def interval_says(iv, target):
    """True: iv is exactly target; False: target is outside iv; None: iv contains target and more."""
    if iv is None:
        return None
    lo, hi = iv
    if lo == hi == target:
        return True
    if not lo <= target <= hi:
        return False
    return None


def interval_near(iv, target, tol):
    """True: the whole interval is within target +- tol; False: none of it is; None: it straddles the band."""
    if iv is None:
        return None
    lo, hi = iv
    if lo >= target - tol and hi <= target + tol:
        return True
    if hi < target - tol or lo > target + tol:
        return False
    return None


# ---- stop and kept bookkeeping shared by the stages ----------------------------------------------------------------------
def p3_of(rec):
    p3 = rec.get("p3")
    if not isinstance(p3, dict) or p3.get("answered") is None:
        return None
    return bool(p3["answered"])


def score_marks_and_p3(S, n, rec, mk, sg, kept):
    """The rows of a job that read the stop's marks (read offset, dword 14, busy), the kept jobs' mark rows (no-handler and H-TICKONLY
    models), and P3.  A stop-model's mark rows are scored only for a stop; the others only for a job that kept the tick."""
    vals = {"read_minus_write": None if mk is None else str(mk["rmw"]),
            "dword14": None if mk is None else (f"{mk['hc14']:#x}" if mk["hc14"] else "0")}
    for q in ("read_minus_write", "dword14"):
        for pr in S.preds:
            if pr["case"] == n and pr["quantity"] == q:
                is_kept_model = pr["model"] in KEPT_MODELS
                if is_kept_model == kept:
                    S.t.add(n, q, pr["model"], pr["set"], None if vals[q] is None else vals[q] == pr["value"],
                            "" if mk else "no marks readable")
    if not kept:
        busy = None if sg is None or sg["class"] == "unreadable" else sg["class"] == "busy"
        for pr in S.preds:
            if pr["case"] == n and pr["quantity"] == "sig_busy":
                S.t.add(n, "sig_busy", pr["model"], pr["set"], None if busy is None else busy == (pr["value"] == "yes"))
    a = p3_of(rec)
    if not kept and a is not None:
        S.p3.append((n, a))
        S.tally_preds(n, "p3_answered", {"H-NOTENDED": not a, "H-REARM": a})


def mark_text(mk):
    if mk is None:
        return "marks unreadable"
    return f"CCB write {mk['ccb'][0]} read {mk['ccb'][1]} (read - write {mk['rmw']:+d}), HostCtl dword 14 {mk['hc14']:#x}"


def p3_text(rec):
    p3 = rec.get("p3")
    if not isinstance(p3, dict):
        return "no P3"
    extra = f", {p3['ring_new_entries']} new ring entries" if p3.get("ring_new_entries") is not None else ""
    return f"P3 {'answered' if p3.get('answered') else 'NOT answered'} ({p3.get('ms', 0):.0f} ms{extra})"


def d_text(rec, sg_samples=None):
    d0 = d0_of(rec)
    ds = d_of_samples(sg_samples if sg_samples is not None else ((rec.get("sig") or {}).get("samples")))
    dm = d_mode(ds)[0]
    return f"D0 {d0}" + (f", D at the stop {dm} ({dm - d0:+d})" if dm is not None and d0 is not None else "")


# ---- stage h --------------------------------------------------------------------------------------------------------------
def hold_band(rec, n):
    pg = rec["page"]
    h = rel(pg[L.HOLD_EXIT], pg[L.HOLD_ENTRY])
    want = L.hold_units_of(n)
    return abs(h - want) <= 0.002 * want + 50, h, want


def score_h(S):
    h0_ok, h1_all, h1_some, d_offsets = [], [], [], []
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        v = void_ring(rec, RESULT_CLASSES_H)
        if v:
            S.nodata(n, v)
            continue
        cls = rec["class"]
        ins = rec.get("inside") or []
        d0 = d0_of(rec)
        d0mode, d0share = d_mode(d_vals(rec.get("d0")))
        if cls == "stop":
            sg = rec_sig(rec)
            mk = marks_of(S, rec)
            S.stop_names.append(n)
            for pr in S.preds:
                if pr["case"] == n and pr["quantity"] in ("idle", "d0_modal", "hold_band", "elements", "d_vs_d0"):
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "the tick stopped")
            S.p(f"{n}: class stop (the tick stopped in a stage-h job: a surprise); {sig_line(sg)}; {mark_text(mk)}; {p3_text(rec)}; "
                f"{d_text(rec)}")
            continue
        if row == "H0":
            sigs = [score_sig(i["samples"]) for i in ins]
            idle = bool(sigs) and all(
                sg["class"] == "idle-empty" and sg["values"]["clkstat"] in CLK_IDLE_VALUES for sg in sigs if sg["class"] != "unreadable") \
                and all(sg["class"] != "unreadable" for sg in sigs)
            d_vs = d_vals(rec.get("d0"))
            modal = d0mode is not None and len(d_vs) >= 12 and d0share >= 0.7 and all(d0mode <= x <= d0mode + 1 for x in d_vs)
            h0_ok.append(idle and modal)
            S.tally_preds(n, "idle", {"control": idle})
            S.tally_preds(n, "d0_modal", {"control": modal})
            S.p(f"{n}: class ok; signatures {[sg['class'] for sg in sigs]} (clk {[hex(sg['values']['clkstat']) for sg in sigs if sg['class'] != 'unreadable']}); "
                f"D0 {d0mode} in {len(d_vs)} valid reads of 20 (mode share {d0share:.2f}); idle {idle}, modal {modal}")
            continue
        # H1
        band, hu, hw = hold_band(rec, j["n"])
        S.tally_preds(n, "hold_band", {"S2 run 3": band})
        inside = [bool(i["state"]) and all(x == L.STATE_BUSY for x in i["state"]) for i in ins]
        if len(ins) < 2 or not all(inside):
            S.p(f"{n}: class ok; a signature fell outside the hold (STATE {[i['state'] for i in ins]}): cannot tell")
            for q in ("elements", "d_vs_d0"):
                S.tally_preds(n, q, {"H-NOTENDED": None, "H-REARM": None})
            continue
        sigs = [score_sig(i["samples"]) for i in ins]
        if any(sg["class"] == "unreadable" for sg in sigs):
            S.p(f"{n}: class ok; a signature is unreadable: cannot tell")
            for q in ("elements", "d_vs_d0"):
                S.tally_preds(n, q, {"H-NOTENDED": None, "H-REARM": None})
            continue
        allm = all(sg["matches_e537"] and sg["values"]["clkstat"] == CLK_BUSY for sg in sigs)
        h1_all.append(allm)
        diff = sorted({k for sg in sigs for k, vv in sg["elements"].items() if not vv}
                      | ({"clk_exact"} if any(sg["values"]["clkstat"] != CLK_BUSY for sg in sigs) else set()))
        dv = [x for i in ins for x in d_of_samples(i["samples"])]
        offs = sorted({x - d0 for x in dv}) if d0 is not None else []
        d_ok = None if not dv or d0 is None else all(o in (0, 1) for o in offs)
        d_offsets.append(tuple(offs))
        S.tally_preds(n, "elements", {"H-NOTENDED": allm, "H-REARM": not allm})
        S.tally_preds(n, "d_vs_d0", {"H-NOTENDED": d_ok})
        S.p(f"{n}: class ok, hold {hu} units (want {hw:.0f}, band {band}); signatures at {[i['ms'] for i in ins]} ms: "
            f"{[sg['class'] for sg in sigs]}, all elements as a running task {allm}" + ("" if allm else f", differ in {diff}")
            + f"; D0 {d0}, D in the hold minus D0 {offs} (want 0 or 1)")
    note = S.stage_note()
    h0v = "H0 held (idle, D0 one modal value)" if h0_ok and all(h0_ok) else "H0 DIFFERS" if h0_ok else "H0 not read"
    if h1_all and all(h1_all):
        h1v = f"H1 reads H-NOTENDED ({len(h1_all)} of {len(h1_all)} jobs look exactly like a running task)"
        if len(set(d_offsets)) == 1 and d_offsets[0]:
            h1v += f", D offset {list(d_offsets[0])} one value in {len(d_offsets)}"
        else:
            h1v += f", D offsets {sorted(set(d_offsets))}"
    elif h1_all and not any(h1_all):
        h1v = "H1 reads H-REARM (an element of the signature differs from a running task in every job)"
    elif h1_all:
        h1v = "H1 mixed"
    else:
        h1v = "H1 not read"
    return f"h: {h0v}; {h1v}; stops {len(S.stop_names)} {S.stop_names}; Q152 rows: {S.t.line()}" + (f"; {note}" if note else "")


# ---- stages c and d ------------------------------------------------------------------------------------------------------
RESULT_CLASSES_ALIAS = RESULT_CLASSES_C


def rd_of(r):
    return dict(zip(L.RD_FIELDS, r)) if isinstance(r, list) and len(r) >= len(L.RD_FIELDS) else None


def void_alias2(rec, j):
    if rec is None:
        return "no record kept"
    if rec.get("class") == "skipped":
        return "not run (" + rec.get("note", "").strip() + ")"
    if rec.get("class") not in RESULT_CLASSES_ALIAS:
        return f"class {rec.get('class')}"
    cmd = j["cmd"]
    wr = rec.get("writer") or {}
    if cmd and not wr.get("done"):
        return "the writer's flag was not set (it did not run)"
    if not cmd:
        return None
    if not isinstance(wr.get("wr"), list):
        return "no writer record"
    w = dict(zip(L.WR_FIELDS, wr["wr"]))
    K = (rec.get("ccbctl_pre") or [None])[0]
    if cmd in (L.CMD_WORD65, L.CMD_E537, L.CMD_RUN64):
        if w["written"] != w["readback"]:
            return f"the read-back ({w['readback']:#x}) is not what the writer wrote ({w['written']:#x}): the write did not take"
        if K is not None and (w["sa65_before"] >> 24) != (K & 0xFF):
            return f"the task's own record of sa65 at entry has count byte {w['sa65_before'] >> 24:#x}, not K = {K & 0xFF:#x}"
    if cmd in (L.CMD_WORD65, L.CMD_E537) and rec.get("w65_word") is not None and w["written"] != rec["w65_word"] & 0xFFFFFFFF:
        return f"the word written ({w['written']:#x}) is not the row's ({rec['w65_word']:#x})"
    if cmd == L.CMD_E537:
        x = dict(zip(L.WR_X_FIELDS, wr["wr"][L.WR_X - L.WR:L.WR_X - L.WR + 4]))
        if x["sa63_w"] != x["sa63_rb"] or x["sa64_w"] != x["sa64_rb"]:
            return "D4: an sa read-back is not what the writer wrote"
    if cmd == L.CMD_RUN64 and rec.get("class") == "ok":
        br = rec.get("bracket") or {}
        try:
            passes = br["after"][0] - br["before"][2]
        except (KeyError, TypeError, IndexError):
            passes = None
        if passes is None or passes < j["npass"]:
            return f"C5's own pass counter advanced {passes}, not the {j['npass']} passes of the row"
    return None


def score_alias2(S):
    stage = S.stage
    ctl_ok = None
    kept, stops, results = {}, [], {}
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = record(S.d, n)
        v = void_alias2(rec, j)
        if v and rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        if v:
            S.nodata(n, v)
            continue
        cls = rec["class"]
        rd1 = rd_of((rec.get("reader") or {}).get("rd")) if (rec.get("reader") or {}).get("ran") else None
        K = (rec.get("ccbctl_pre") or [None])[0]
        K = None if K is None else K & 0xFF
        kept_obs = True if cls == "ok" else False if cls == "stop" else None
        kept.setdefault(row, []).append(kept_obs)
        info = f"{n}: class {cls}"
        for pr in S.preds:
            if pr["case"] == n and pr["quantity"] == "kept":
                S.t.add(n, "kept", pr["model"], pr["set"], None if kept_obs is None else (kept_obs == (pr["value"] == "yes")),
                        "reader not run" if kept_obs is None else "")
        if cls == "stop":
            sg = rec_sig(rec)
            mk = marks_of(S, rec)
            stops.append((n, sg, mk))
            S.stop_names.append(n)
            score_marks_and_p3(S, n, rec, mk, sg, kept=False)
            S.p(info + f" (tick stopped after the writer's pass); {sig_line(sg)}; {mark_text(mk)}; {p3_text(rec)}; {d_text(rec)}")
            continue
        if cls == "noreader":
            S.p(info + " (tick kept, the reader did not run: cannot tell)")
            continue
        if rd1 is None:
            S.p(info + " (kept but no reader record: cannot tell)")
            continue
        got = {"pclink": rd1["pclink"], "p1": rd1["p1"], "sa64": rd1["sa64"], "sa65": rd1["sa65"], "sa63": rd1["sa63"]}
        results[n] = got
        mk = marks_of(S, rec)
        if row in ("C0", "D0"):
            want = {"pclink": 0x98, "p1": 1, "sa64": 2, "sa65": (K << 24) if K is not None else None, "sa63": 0}
            diff = {k: (got[k], want[k]) for k in want if want[k] is None or got[k] != want[k]}
            ok_c = not diff
            ctl_ok = ok_c if ctl_ok is None else (ctl_ok and ok_c)
            for q in want:
                S.tally_preds(n, q, {"E791 A0": None if want[q] is None else got[q] == want[q]})
            S.p(info + f"; reader pclink {got['pclink']:#x} p1 {got['p1']} sa64 {got['sa64']:#x} sa65 {got['sa65']:#x} sa63 {got['sa63']:#x}; "
                + mark_text(mk) + ("" if ok_c else f"; {row} DIFFERS {diff}"))
            continue
        dn = ""
        if row in ("C1", "C2", "C3", "C4"):
            S.tally_preds(n, "next_pclink", {"E15": None if not ctl_ok else got["pclink"] == 0x98})
            S.tally_preds(n, "next_sa65", {"E15": None if not ctl_ok or K is None else got["sa65"] == K << 24})
            dn = f"; next entry pclink {got['pclink']:#x}, sa65 {got['sa65']:#x} (K << 24 = {(K or 0) << 24:#x})"
        if row == "C5":
            iv = d12_minus_passes(rec)
            S.tally_preds(n, "pclink", {"E792": None if not ctl_ok else got["pclink"] == 6})
            S.tally_preds(n, "d12_delta", {"E792": interval_near(iv, -j["npass"], 8)})
            d0 = d0_of(rec)
            dp = d_mode(d_vals(rec.get("d_post")))[0]
            shift = None if d0 is None or dp is None else dp - d0
            S.tally_preds(n, "d_shift", {"E792": None if shift is None else abs(shift - j["npass"]) <= 1})
            dn = f"; pclink {got['pclink']:#x} (want 0x6), d12 - passes in {iv} (want {-j['npass']} +-8), D shift {shift} (want {j['npass']} +-1)"
        score_marks_and_p3(S, n, rec, mk, None, kept=True)
        S.p(info + dn + "; " + mark_text(mk))
    note = S.stage_note()
    if ctl_ok is None:
        S.p("control: no readable control")
    nk = sum(1 for v in kept.values() for k in v if k is True)
    nt = sum(len(v) for v in kept.values())
    p3s = f"; P3 answered in {sum(1 for _, a in S.p3 if a)} of {len(S.p3)} stops" if S.p3 else ""
    if stage == "c":
        verdict = "C0 held" if ctl_ok else ("C0 DIFFERS" if ctl_ok is False else "C0 not read")
        rd = "; ".join(f"{r} kept {sum(1 for k in v if k is True)} of {len(v)}" for r, v in kept.items() if r != "C0")
        return (f"c: {verdict}; {rd}; stops {len(S.stop_names)} {S.stop_names}{p3s}; Q152 rows: {S.t.line()}" + (f"; {note}" if note else ""))
    # stage d
    d_read = d_verdict(kept, stops, results)
    verdict = "D0 held" if ctl_ok else ("D0 DIFFERS" if ctl_ok is False else "D0 not read")
    stop_sig = "; ".join(f"{x}: {sg['class']}{' (E537)' if sg['matches_e537'] else ''}, read-write {mk['rmw'] if mk else '?'}, "
                         f"dword 14 {hex(mk['hc14']) if mk else '?'}" for x, sg, mk in stops)
    return (f"d: {verdict}; {d_read}; kept {nk} of {nt} read jobs, stops {len(S.stop_names)} {S.stop_names}"
            + (f" [{stop_sig}]" if stops else "") + f"{p3s}; Q152 rows: {S.t.line()}" + (f"; {note}" if note else ""))


def d_verdict(kept, stops, results):
    """E537's stop: H-CCB (bit 8 alone stops it: read = write + 1, dword 14 = 0xad002600), H-HANDLER (a bit with no job stops it:
    D1 stops, no assert mark), H-ONCE (D3 keeps the tick: E537 does not repeat)."""
    by = {n: mk for n, sg, mk in stops}
    d1 = kept.get("D1", [])
    d2 = kept.get("D2", [])
    d3 = kept.get("D3", [])
    assert_d2 = [mk for n, mk in by.items() if n == "d2" and mk and mk["rmw"] == 1 and mk["hc14"] == L.ASSERT_WORD]
    assert_d3 = [mk for n, mk in by.items() if n == "d3" and mk and mk["rmw"] == 1 and mk["hc14"] == L.ASSERT_WORD]
    if d3 and d3[0] is True:
        return "D3 kept the tick: H-ONCE (E537's word alone does not stop it)" + ("; D4 not read" if "D4" not in kept else "")
    if d2 and d2[0] is False and assert_d2 and (not d1 or all(k is True for k in d1)):
        return ("H-CCB supported: bit 8 alone (D2) stops it with read = write + 1 and dword 14 = 0xad002600"
                + (", and D3 shows the same marks" if assert_d3 else "; D3 not read or without the marks"))
    if d1 and d1[0] is False and d2 and d2[0] is True:
        return "H-HANDLER supported: D1 (no bit 8) stops it, D2 (bit 8 alone) keeps it"
    if d1 and d1[0] is False and d2 and d2[0] is False:
        return "D1 and D2 both stop it: neither H-CCB nor H-HANDLER alone (the stage ended before D3)"
    if d3 and d3[0] is False:
        return "D3 stops it" + (" with D2's marks" if assert_d3 else " without D2's marks")
    return "no verdict (a row was not read)"


# ---- stage e --------------------------------------------------------------------------------------------------------------
def score_e(S):
    kept_by_row, stops, ctl_ok = {}, [], []
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        v = void_ring(rec, RESULT_CLASSES_E)
        r = None
        if v is None:
            try:
                r = ring(rec["page"])
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v is None and j["count"] and rec["page"][L.ACTED] not in (0, j["count"]) and rec.get("class") == "ok":
            v = f"the acted count was not taken as designed (ACTED {rec['page'][L.ACTED]}, want {j['count']})"
        if v:
            S.nodata(n, v)
            continue
        pg = rec["page"]
        drops = pg[L.DROP:L.DROP + 4]
        ev = from_stamp(merged(r), rec.get("window_stamp"))
        s0 = [e for e in ev if e[0] == 0]
        acted = [e for e in s0 if e[1] in (L.SKIP_FLAG, L.TAIL_FLAG)]
        cls = rec["class"]
        kept_obs = cls in ("ok", "kick-timeout")
        info = (f"{n}: class {cls}, {len(s0)} entries (acted {len(acted)}, flags {sorted({e[1] for e in s0})}), ACTED {pg[L.ACTED]} of "
                f"{j['count']}, drops {drops}")
        if j["count"] and pg[L.ACTED] == 0:
            S.p(info + "; the KIND of pass never came in the window (ACTED 0): cannot tell")
            for pr in S.preds:
                if pr["case"] == n and pr["quantity"] != "p3_answered":
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "no acted pass")
            continue
        if j["count"] and not acted and drops[0] == 0:
            S.p(info + "; the acted pass is not in the ring (not logged first): cannot tell")
            for pr in S.preds:
                if pr["case"] == n and pr["quantity"] != "p3_answered":
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "acted pass not logged")
            continue
        if j["count"] and not acted and drops[0]:
            S.p(info + "; ring full before the acted pass: cannot tell")
            for pr in S.preds:
                if pr["case"] == n and pr["quantity"] != "p3_answered":
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "ring full")
            continue
        # a job the rows call cannot tell is not counted for the stage line (post-run fix C5, POSTRUN-FIX.md)
        kept_by_row.setdefault(row, []).append(kept_obs)
        S.tally_preds(n, "acted", {"design": pg[L.ACTED] == j["count"], "control": pg[L.ACTED] == 0})
        for pr in S.preds:
            if pr["case"] == n and pr["quantity"] == "kept":
                S.t.add(n, "kept", pr["model"], pr["set"], kept_obs == (pr["value"] == "yes"))
        sg = rec_sig(rec) if cls == "stop" else None
        mk = marks_of(S, rec)
        if cls == "stop":
            stops.append((n, sg, mk))
            S.stop_names.append(n)
        stopped = cls == "stop"
        if row == "E0":
            grid = len(s0) >= 4 and all(on_grid(x) for x in gaps(s0))
            ok = abs(len(s0) - 14) <= 2
            ctl_ok.append(ok and grid and not acted)
            S.tally_preds(n, "entries", {"control": ok})
            S.tally_preds(n, "grid", {"control": grid})
            S.p(info + f"; entries 14 +-2: {ok}, gaps on the 25000 grid: {grid}")
            continue
        extra = ""
        if row in ("X1", "X20"):
            last = acted[-1] if acted else None
            after = [e for e in s0 if last is not None and rel(e[5], last[5]) > 0]
            nxt = rel(after[0][5], last[5]) if after else None
            if row == "X1":
                S.tally_preds(n, "flag4_logged", {"H-EXIT": any(e[1] == L.TAIL_FLAG for e in acted)})
                if not stopped:
                    S.tally_preds(n, "next_gap", {"H-EXIT": None if nxt is None else abs(nxt - T) <= NEXT_GAP_TOL})
                extra = f"; next entry after the acted pass: +{nxt} (want {T}+-{NEXT_GAP_TOL})"
            else:
                iv = d12_minus_passes(rec)
                S.tally_preds(n, "d12_delta", {"H-EXIT": None if stopped else interval_near(iv, -j["count"], 8)})
                extra = f"; d12 - passes in {iv} (want {-j['count']} +-8)"
            score_marks_and_p3(S, n, rec, mk, sg, kept=not stopped)
            if stopped:
                S.p(info + extra + f"; {sig_line(sg)}; {mark_text(mk)}; {p3_text(rec)}; {d_text(rec)}")
            else:
                S.p(info + extra + f"; {mark_text(mk)}")
            continue
        # B3: one kick pass ended with our own nop.end
        kick = rec.get("kick") or {}
        answered = kick.get("answered")
        if answered is None and kick:
            answered = not rec.get("kick_errors") and kick.get("ms", 0) < L.P3_MS
        kicks = [e for e in s0 if e_kick(e)]
        one = len(kicks) == 1 and kicks[0][1] == L.SKIP_FLAG and not [e for e in s0 if rel(e[5], kicks[0][5]) > 0]
        ticks = [e for e in s0 if e_tick(e)]
        grid = len(ticks) >= 4 and all(on_grid(x) for x in gaps(ticks))
        S.tally_preds(n, "miscinfo_answered", {m: None if answered is None else (not answered) == (S.pred_value(n, "miscinfo_answered", m) == "no")
                                               for m in ("H-EXIT", "H-BODY", "H-TICKONLY")})
        S.tally_preds(n, "kick_entry", {"H-EXIT": one, "H-BODY": one})
        S.tally_preds(n, "grid", {"H-TICKONLY": grid})
        score_marks_and_p3(S, n, rec, mk, sg, kept=not stopped)
        S.p(info + f"; kick entries {len(kicks)} (flags {[e[1] for e in kicks]}), nothing after the kick {one}, miscinfo answered {answered}, "
            f"tick gaps on the grid {grid}; {mark_text(mk)}" + (f"; {sig_line(sg)}; {d_text(rec)}" if stopped else ""))
    note = S.stage_note()
    x1 = kept_by_row.get("X1", [])
    b3 = kept_by_row.get("B3", [])
    if x1 and b3:
        if all(x1) and not any(b3):
            h = "H-EXIT (a tick pass handed to a fast-path task keeps the tick, a skipped kick pass stops it)"
        elif not any(x1) and not any(b3):
            h = "H-BODY (a tick pass handed to a fast-path task stops it too)"
        elif all(b3):
            h = "H-TICKONLY (the skipped kick pass keeps the tick)" + ("" if all(x1) else "; X1 stopped: mixed, no hypothesis fits")
        else:
            h = "no hypothesis fits (X1 and B3 disagree with all three)"
    elif x1:
        h = "X1 kept" if all(x1) else "X1 stopped" if not any(x1) else "X1 mixed"
        h += ", B3 not read"
    elif b3:
        h = "B3 kept" if all(b3) else "B3 stopped"
        h += ", X1 not read"
    else:
        h = "X1 and B3 not read"
    p3s = f"; P3 answered in {sum(1 for _, a in S.p3 if a)} of {len(S.p3)} stops" if S.p3 else ""
    stop_sig = "; ".join(f"{x}: {sg['class']}{' (E537)' if sg['matches_e537'] else ''}, read-write {mk['rmw'] if mk else '?'}, "
                         f"dword 14 {hex(mk['hc14']) if mk else '?'}" for x, sg, mk in stops)
    verdict = "E0 held" if ctl_ok and all(ctl_ok) else ("E0 DIFFERS" if ctl_ok else "E0 not read")
    return (f"e: {verdict}; {h}; stops {len(stops)}" + (f" [{stop_sig}]" if stops else "") + f"{p3s}; Q152 rows: {S.t.line()}"
            + (f"; {note}" if note else ""))


SCORERS = {"h": score_h, "c": score_alias2, "e": score_e, "d": score_alias2}


# ---- gate, freeze, main ---------------------------------------------------------------------------------------------------
def gate(stage, root):
    """0 when the previous stage finished according to its own kept stage.json (derived from kept output only)."""
    prev = GATE_OF.get(stage)
    if not prev:
        print(f"GATE {stage} OPEN (no previous stage)")
        return 0
    try:
        st = json.loads((pathlib.Path(root) / prev / "stage.json").read_text())
    except (OSError, ValueError):
        print(f"GATE {stage} CLOSED: no kept stage.json of {prev} under {root}")
        return 1
    if st.get("exit") in GATE_EXITS:
        print(f"GATE {stage} OPEN: {prev} finished (exit {st.get('exit')}, run {st.get('run')})")
        return 0
    print(f"GATE {stage} CLOSED: {prev} exit {st.get('exit')} ({st.get('why', '')[:80]})")
    return 1


def freeze_problem():
    if os.environ.get("R3_NO_FREEZE_CHECK") == "1":
        return None
    r = subprocess.run([str(R3 / "run" / "freeze_r3.sh"), "verify"], capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stdout + r.stderr).strip().splitlines()[-1:]


def score(stage, d, base=None):
    S = Stage(stage, d, base)
    summary = SCORERS[stage](S)
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
    if len(argv) < 3 or argv[1] not in SCORERS:
        print("usage: score_r3.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...")
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
