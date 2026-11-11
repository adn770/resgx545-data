#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_r3.py STAGE OUTDIR | gate STAGE ROOT | sig FILE...: score one R3-events stage (a, b, k7) from what the runner kept
(out/STAGE/: NAME.json, cases.tsv, stage.json, env.json, stop-*.json).  Written before the run and frozen (run/freeze_r3.sh);
refuses unless `run/freeze_r3.sh verify` passes (the check is skipped under R3_NO_FREEZE_CHECK=1, set by the tests only).
Prints a line a job and one `SUMMARY:` line.  Standard library only.

States a row can end in: held / FAILED (a prediction against a measurement), cannot tell (the measurement does not decide:
the reader did not run but the tick was kept, A0 differs from the controls, the signature dump is unreadable, a kick count the
rows cannot separate) and void (the job must not be read: no record, a class that is not a result, no page, a writer whose flag
was never set, a read-back that is not what the writer wrote, a hold outside its knob band, a skip that was never taken).  Void
and cannot-tell rows never count as a pass.  The tally keeps fit rows, held-out rows, replicates and controls apart.

STOP SIGNATURE.  Every tick stop is classed from the registers the runner dumped BEFORE the reset (two samples 30 ms apart):
  busy          the clock status (reg 0x0008) is not idle (0x20): a task or a unit is running
  idle-pending  idle, but USE0_SERV_EVENT (reg 0x0B14) bit 16 (EMPTY) is clear: events queued, none served
  idle-empty    idle and EMPTY set: nothing queued, nothing running
It is scored against E537's: busy (0x000ccfa0), USE0_SERV_EVENT 0x9e0 (EMPTY clear, count frozen), EVENT_TIMER counting,
EVENT_STATUS 0x20000000; `matches E537` needs all four.

`gate STAGE ROOT` exits 0 when the previous stage's own kept stage.json (ROOT/PREV/stage.json) says it finished (exit 0, or 8: a
second stop ended it, reset and gate exact) - derived from kept output only, so restaging never closes it.
"""
import gzip
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
import r3layout as L  # noqa: E402

T = L.TICK_UNITS
RESULT_CLASSES_A = {"ok", "stop", "noreader"}
RESULT_CLASSES_B = {"ok", "stop"}
RESULT_CLASSES_K = {"ok", "kick-timeout"}
GUARD_TICK = 500
NEXT_GAP_TOL = 50
GATE_OF = {"b": "a", "k7": "b"}
GATE_EXITS = (0, 8)


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


def void_ring(rec, classes, hold=False):
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
    """{slot: [(flag, pa0, pa1, pa2, stamp), ...]} in rung order (flag 1 logged, 3 skipped); ValueError on a corrupt flag."""
    out = {}
    for k in range(4):
        rows = []
        for j in range(L.RUNGS[k]):
            o = L.RING_BASE[k] + L.RUNG * j
            f = page[o]
            if f not in (0, 1, L.SKIP_FLAG):
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


# ---- stage a --------------------------------------------------------------------------------------------------------------
WR_WRITES = (L.CMD_A1, L.CMD_A2, L.CMD_A3, L.CMD_A4, L.CMD_A5, L.CMD_RESTORE63)


def void_alias(rec, j):
    if rec is None:
        return "no record kept"
    if rec.get("class") == "skipped":
        return "not run (" + rec.get("note", "").strip() + ")"
    if rec.get("class") not in RESULT_CLASSES_A:
        return f"class {rec.get('class')}"
    cmd = j["cmd"]
    wr = rec.get("writer") or {}
    if cmd and not wr.get("done"):
        return "the writer's flag was not set (it did not run)"
    if cmd in WR_WRITES and isinstance(wr.get("wr"), list):
        w = dict(zip(L.WR_FIELDS, wr["wr"]))
        if w["written"] != w["readback"]:
            return f"the read-back ({w['readback']:#x}) is not what the writer wrote ({w['written']:#x}): the write did not take"
        if cmd == L.CMD_A3 and w["readback2"] != w["sa65_before"]:
            return "A3: sa65 was not restored before the tail call"
    elif cmd in WR_WRITES:
        return "no writer record"
    return None


def rd_of(r):
    return dict(zip(L.RD_FIELDS, r)) if isinstance(r, list) and len(r) >= len(L.RD_FIELDS) else None


def score_a(S):
    ctl_ok = None
    kept, stops, sigs, results = {}, [], [], {}
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = record(S.d, n)
        v = void_alias(rec, j)
        if v:
            S.p(f"{n}: NODATA ({v})")
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "void")
            continue
        cls = rec["class"]
        rd1 = rd_of((rec.get("reader") or {}).get("rd")) if (rec.get("reader") or {}).get("ran") else None
        rd2 = rd_of((rec.get("reader2") or {}).get("rd")) if (rec.get("reader2") or {}).get("ran") else None
        K = (rec.get("ccbctl_pre") or [None])[0]
        kept_obs = True if cls == "ok" else False if cls == "stop" else None
        kept.setdefault(row, []).append(kept_obs)
        info = f"{n}: class {cls}"
        # kept, per model
        for pr in S.preds:
            if pr["case"] == n and pr["quantity"] == "kept":
                S.t.add(n, "kept", pr["model"], pr["set"], None if kept_obs is None else (kept_obs == (pr["value"] == "yes")),
                        "reader not run" if kept_obs is None else "")
        if cls == "stop":
            sg = rec_sig(rec)
            sigs.append((n, sg))
            stops.append(n)
            S.p(info + f" (tick stopped after the writer's pass); {sig_line(sg)}")
            continue
        if cls == "noreader":
            S.p(info + " (tick kept, the reader did not run: cannot tell)")
            continue
        if rd1 is None:
            S.p(info + " (kept but no reader record: cannot tell)")
            continue
        got = {"pclink": rd1["pclink"], "p1": rd1["p1"], "sa64": rd1["sa64"], "sa65": rd1["sa65"], "sa63": rd1["sa63"]}
        results[n] = got
        iv = d12_minus_passes(rec)
        if row == "A0":
            want = {"pclink": 0x98, "p1": 1, "sa64": 2, "sa65": ((K or 0) % 256) << 24 if K is not None else None, "sa63": 0}
            diff = {k: (got[k], want[k]) for k in want if want[k] is None or got[k] != want[k]}
            ok_c = not diff
            ctl_ok = ok_c if ctl_ok is None else (ctl_ok and ok_c)
            for q in want:
                S.tally_preds(n, q, {"E536/E537": None if want[q] is None else got[q] == want[q]})
            S.p(info + f"; reader pclink {got['pclink']:#x} p1 {got['p1']} sa64 {got['sa64']:#x} sa65 {got['sa65']:#x} sa63 {got['sa63']:#x}"
                + ("" if ok_c else f"; A0 DIFFERS {diff}"))
            continue
        dn = ""
        if row == "A1":
            mk = j["marker"]
            persists = None if rd2 is None else (rd1["sa63"] == mk and rd2["sa63"] == mk)
            S.tally_preds(n, "marker_persists_1200ms", {"H-ALIAS": persists})
            dn = f"; sa63 at the next event {rd1['sa63']:#x}, after 1200 ms {rd2['sa63']:#x}" if rd2 else "; no 1200 ms reader"
        if row in ("A2", "A5", "A4"):
            wantp = int(S.pred_value(n, "pclink", "H-ALIAS"), 0)
            wantq = int(S.pred_value(n, "p1", "H-ALIAS"))
            S.tally_preds(n, "pclink", {"H-ALIAS": None if not ctl_ok else got["pclink"] == wantp})
            S.tally_preds(n, "p1", {"H-ALIAS": None if not ctl_ok else got["p1"] == wantq})
            dn = f"; pclink {got['pclink']:#x} (want {wantp:#x}) p1 {got['p1']} (want {wantq})"
        if row == "A4":
            says = interval_says(iv, -1)
            S.tally_preds(n, "d12_delta", {"H-ALIAS": says})
            dn += f"; d12 - passes in {iv} (want -1)"
        S.p(info + dn)
    # stage-level readings
    for h, row, text in (("H-63", "A1", "sa63 stops it"), ("H-P11", "A6", "p0 = p1 = 1 with r and i written stops it")):
        ks = kept.get(row, [])
        if not ks:
            S.p(f"{h}: row {row} not read")
        elif False in ks:
            S.p(f"{h} ({text}): {row} stopped the tick in {ks.count(False)} of {len(ks)} reps: supported")
        elif all(k is True for k in ks):
            S.p(f"{h} ({text}): {row} kept the tick {len(ks)} of {len(ks)}: refuted")
        else:
            S.p(f"{h} ({text}): {row} cannot tell ({ks})")
    a4 = [results[x] for x in results if x.startswith("a4")]
    if a4:
        other = [r["pclink"] == 6 and r["p1"] == 0 for r in a4]
        S.p("H-ALIAS (sa64 write, A4): "
            + ("the next entry shows the other path (pclink 6, p1 0) in every kept A4 rep: supported" if all(other) else
               "no rep shows pclink 6 and p1 0" if not any(other) else "mixed"))
    if ctl_ok is None:
        S.p("A0: no readable control")
    stop_sig = "; ".join(f"{x}: {sg['class']}{' (E537)' if sg['matches_e537'] else ''}" for x, sg in sigs)
    note = S.stage_note()
    nk = sum(1 for v in kept.values() for k in v if k is True)
    nt = sum(len(v) for v in kept.values())
    verdict = "A0 held" if ctl_ok else ("A0 DIFFERS" if ctl_ok is False else "A0 not read")
    return (f"a: {verdict}; kept {nk} of {nt} read jobs, stops {len(stops)} {stops}" + (f" [{stop_sig}]" if stops else "")
            + f"; Q152 rows: {S.t.line()}" + (f"; {note}" if note else ""))


# ---- stage b --------------------------------------------------------------------------------------------------------------
def score_b(S):
    kept_by_row = {}
    stops = []
    ctl_ok = []
    for j in S.table["jobs"]:
        n, row, N = j["name"], j["row"], j["skip"]
        rec = record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        v = void_ring(rec, RESULT_CLASSES_B)
        r = None
        if v is None:
            try:
                r = ring(rec["page"])
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v is None and rec.get("class") == "ok" and rec["page"][L.SKIPPED] != N:
            v = f"the skip was not taken as designed (SKIPPED {rec['page'][L.SKIPPED]}, want {N})"
        if v is None and rec.get("class") == "stop" and N and rec["page"][L.SKIPPED] == 0:
            v = "the tick stopped before any skip was taken"
        if v:
            S.p(f"{n}: NODATA ({v})")
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "void")
            continue
        pg = rec["page"]
        drops = pg[L.DROP:L.DROP + 4]
        ev = from_stamp(merged(r), rec.get("window_stamp"))
        s0 = [e for e in ev if e[0] == 0]
        skipped = [e for e in s0 if e[1] == L.SKIP_FLAG]
        norm = [e for e in s0 if e[1] == 1]
        kept_obs = rec["class"] == "ok"
        kept_by_row.setdefault(row, []).append(kept_obs)
        g = gaps(s0)
        info = f"{n}: class {rec['class']}, {len(s0)} entries (skipped {len(skipped)}, logged {len(norm)}), SKIPPED {pg[L.SKIPPED]}, drops {drops}"
        if rec["class"] == "stop":
            sg = rec_sig(rec)
            stops.append((n, sg))
            for pr in S.preds:
                if pr["case"] == n and pr["quantity"] == "kept":
                    S.t.add(n, "kept", pr["model"], pr["set"], pr["value"] == "no")
            S.p(info + f"; the tick STOPPED after the skip; entries after the last skipped one: "
                f"{len([e for e in s0 if rel(e[5], skipped[-1][5]) > 0]) if skipped else 'n/a'}; {sig_line(sg)}")
            continue
        for pr in S.preds:
            if pr["case"] == n and pr["quantity"] == "kept":
                S.t.add(n, "kept", pr["model"], pr["set"], pr["value"] == "yes")
        if row == "B0":
            grid = len(s0) >= 4 and all(on_grid(x) for x in g)
            ctl_ok.append(grid and not skipped)
            S.tally_preds(n, "skipped", {"control": len(skipped) == 0})
            S.tally_preds(n, "grid", {"control": grid})
            S.p(info + f"; gaps on the 25000 grid: {grid}")
            continue
        if not skipped:
            S.p(info + "; no skipped entry in the ring (the window did not hold it): cannot tell")
            continue
        last = skipped[-1]
        after = [e for e in s0 if rel(e[5], last[5]) > 0]
        nxt = rel(after[0][5], last[5]) if after else None
        ok_gap = None if nxt is None else abs(nxt - T) <= NEXT_GAP_TOL
        S.tally_preds(n, "skipped", {"design": len(skipped) == N})
        S.tally_preds(n, "next_gap", {"H-FREE": ok_gap})
        iv = d12_minus_passes(rec)
        S.tally_preds(n, "d12_delta", {"H-FREE": interval_says(iv, -N)})
        extra = ""
        if row == "B2":
            ok_grid = None if len(s0) < 4 else all(on_grid(x, NEXT_GAP_TOL) for x in g)
            S.tally_preds(n, "grid_kept", {"H-FREE": ok_grid})
            extra = f"; whole-ring grid (+-{NEXT_GAP_TOL}) {ok_grid}"
        S.p(info + f"; next entry after the last skipped: +{nxt} (want {T}+-{NEXT_GAP_TOL}); d12 - passes in {iv} (want {-N}){extra}")
    stop_sig = "; ".join(f"{x}: {sg['class']}{' (E537)' if sg['matches_e537'] else ''}" for x, sg in stops)
    b1 = kept_by_row.get("B1", [])
    h = ("H-FREE (skipped task end costs nothing)" if b1 and all(b1) else "H-STOP (a skipped task end stops the tick)" if b1 and not any(b1)
         else "mixed" if b1 else "B1 not read")
    note = S.stage_note()
    verdict = "B0 held" if ctl_ok and all(ctl_ok) else ("B0 DIFFERS" if ctl_ok else "B0 not read")
    return (f"b: {verdict}; B1 reads {h}; stops {len(stops)}" + (f" [{stop_sig}]" if stops else "") + f"; Q152 rows: {S.t.line()}"
            + (f"; {note}" if note else ""))


# ---- stage k7 -------------------------------------------------------------------------------------------------------------
def hold_band(rec, n):
    pg = rec["page"]
    h = rel(pg[L.HOLD_EXIT], pg[L.HOLD_ENTRY])
    want = L.hold_units_of(n)
    return abs(h - want) <= 0.002 * want + 50, h, want


def score_k7(S):
    classes = {"EACH": [], "MERGE": [], "ONE": [], "OTHER": []}
    shown = []
    for j in S.table["jobs"]:
        n = j["name"]
        rec = record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        v = void_ring(rec, RESULT_CLASSES_K)
        r = None
        if v is None:
            try:
                r = ring(rec["page"])
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v is None and rec.get("state_at_trigger") != L.STATE_BUSY:
            v = f"the hold was not running when the kick was due (state {rec.get('state_at_trigger')})"
        if v:
            S.p(f"{n}: NODATA ({v})")
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "void")
            continue
        pg = rec["page"]
        band, hu, hw = hold_band(rec, j["n"])
        ev = from_stamp(merged(r), rec.get("window_stamp"))
        ev = [e for e in ev if e[0] == 0]
        exit_stamp = pg[L.HOLD_EXIT]
        burst = [e for e in ev if 0 <= rel(e[5], exit_stamp) <= 2000]
        kicks = [e for e in ev if e_kick(e)]
        late = [e for e in ev if rel(e[5], exit_stamp) > 2000 and e_tick(e)]
        K0 = (rec.get("ccbctl_after_arm") or [None])[0]
        cc = (rec.get("ccbctl_after") or [None])[0]
        kick = rec.get("kick") or {}
        err = bool(rec.get("kick_errors")) or "no SW_EVENT" in kick.get("text", "") or "no MISCINFO_READY" in kick.get("text", "")
        read_ok = (not err) if j["kick"] != "none" else None
        kks = sorted(L.count_of(e[3]) for e in kicks)
        in_burst = all(0 <= rel(e[5], exit_stamp) <= 2000 for e in kicks)
        drops = pg[L.DROP]
        info = (f"{n}: kicks {j['kick']}, hold {hu} units (want {hw:.0f}, band {band}), {len(ev)} entries, burst {len(burst)}, kick entries "
                f"{len(kicks)} K {kks}, all kicks in the burst {in_burst}, ticks after K {sorted({L.count_of(e[3]) for e in late})}, "
                f"ccbctl0 {K0} -> {cc}, read {'ok' if read_ok else 'FAILED' if read_ok is False else 'n/a'}, drops {drops}")
        S.tally_preds(n, "hold_band", {"S2 run 3": band})
        shown.append(band)
        if drops and not late:          # drops after the burst are harmless (the window outlasts 16 rungs); none inside it is not
            S.p(info + "; ring full before the burst ended: cannot tell")
            for pr in S.preds:
                if pr["case"] == n and pr["quantity"] != "hold_band":
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "ring full")
            continue
        if j["kick"] == "none":
            S.tally_preds(n, "kick_entries", {"S2b": len(kicks) == 0})
            S.tally_preds(n, "burst", {"S2b": len(burst) == 4})
        elif j["kick"] == "misc1":
            S.tally_preds(n, "kick_entries", {"S2b": len(kicks) == 1})
            ta = sorted({L.count_of(e[3]) for e in late})
            S.tally_preds(n, "ticks_after_K", {"E746": None if K0 is None or not late else ta == [K0 + 1]})
            S.tally_preds(n, "ccbctl0", {"E746": None if K0 is None or cc is None else cc == K0 + 1})
        else:
            two = len(kicks) == 2
            S.tally_preds(n, "kick_entries", {"H-EACH": two, "H-MERGE": len(kicks) == 1})
            S.tally_preds(n, "kick_K", {"H-EACH": None if K0 is None or len(kicks) != 2 else kks == [K0, K0 + 1]})
            ta = sorted({L.count_of(e[3]) for e in late})
            S.tally_preds(n, "ticks_after_K", {"H-EACH": None if K0 is None or not late else ta == [K0 + 2]})
            S.tally_preds(n, "ccbctl0", {"H-EACH": None if K0 is None or cc is None else cc == K0 + 2})
            S.tally_preds(n, "read_ok", {"H-EACH": read_ok, "H-MERGE": None if read_ok is None else (not read_ok)})
            klass = ("EACH" if two and read_ok and in_burst else "MERGE" if len(kicks) == 1 and read_ok is False else
                     "ONE" if len(kicks) == 1 else "OTHER")
            classes[klass].append(n)
            info += f"; outcome {klass}"
        S.p(info)
    note = S.stage_note()
    verdict = "hold band held" if shown and all(shown) else "cannot tell (a hold left its band)" if shown else "no job read"
    cl = "; ".join(f"{k} {v}" for k, v in classes.items() if v) or "no two-kick job read"
    return f"k7: {verdict}; two-kick outcomes: {cl}; Q290 rows: {S.t.line()}" + (f"; {note}" if note else "")


SCORERS = {"a": score_a, "b": score_b, "k7": score_k7}


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
