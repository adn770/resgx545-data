# SPDX-License-Identifier: MIT
"""scorelib.py: what the R3k scorers share (a copy of the helpers of closing3/r3x-events/score/score_r3.py): reading the kept records,
the ring, the stop signature (E537's busy elements; 0x012c recorded, not matched), the CCB marks, D = pass count - HostCtl dword 12, the
Tally of held / FAILED / cannot tell rows and the Stage object.  Standard library only.

States a row can end in: held / FAILED (a prediction against a measurement), cannot tell (the measurement does not decide) and void (the job
must not be read).  Void and cannot-tell rows never count as a pass.  The tally keeps fit rows, held-out rows, replicates and controls apart.
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
import r4layout as L  # noqa: E402

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


