#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_r1.py STAGE OUTDIR [--gates DIR] [--gate]: score one R1-events stage (k, t, d0, d1) from what the runner kept
(out/STAGE/: NAME.json, NAME.tool.txt.gz, cases.tsv, stage.json, env.json).  Written before the run and frozen
(run/freeze_r1.sh); refuses unless `run/freeze_r1.sh verify` passes.  Prints a line a job and one `SUMMARY:` line.
Only stage d0 has a gate (it opens d1, the 4096x4096 jobs): with --gate it writes gates/d0.gate and exits 0 only when
the gate is open.  Standard library only (the tests use the scratch venv's python, never needed on the laptop).

States a row can end in: held / FAILED (a prediction against a measurement), cannot tell (the measurement does not
decide: a variant not shown, a ring that filled, a threshold not bracketed, a control that failed, a raise that did not
reproduce) and void (the job must not be read: no record, a class that is not a result, no page, a window that did not
close, the job's own pre-read of CR_EVENT_STATUS2 not 0x400, no o0 line).  Void and cannot-tell rows never count as a
pass.  The tally keeps fit rows, held-out rows, replicates and controls apart (the label of the frozen row).
"""
import gzip
import hashlib
import json
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R1 = HERE.parent
sys.path.insert(0, str(R1 / "gen"))
import r1layout as L  # noqa: E402

T = L.TICK_UNITS
RESULT_CLASSES = {"ok", "kick-timeout"}
GUARD_TICK = 500


# ---- reading ---------------------------------------------------------------------------------------------------------
def load_table(stage):
    return json.loads((R1 / "tables" / f"{stage}.json").read_text())


def load_preds(stage):
    rows = (R1 / "predictions" / f"{stage}.tsv").read_text().splitlines()[1:]
    return [dict(zip(("case", "quantity", "value", "model", "set"), r.split("\t"))) for r in rows if r.strip()]


def pred(preds, case, quantity, model=None):
    for p in preds:
        if p["case"] == case and p["quantity"] == quantity and (model is None or p["model"].startswith(model)):
            return p
    return None


def record(d, name):
    """The job's record, only if this stage's last run (stage.json) wrote it (nothing is ever deleted: an older file of
    the same stage is not read)."""
    try:
        st = json.loads((pathlib.Path(d) / "stage.json").read_text())
        rec = json.loads((pathlib.Path(d) / f"{name}.json").read_text())
    except (OSError, ValueError):
        return None
    if name not in st.get("jobs_run", []) or rec.get("run") != st.get("run"):
        return None
    return rec


def gz_text(d, name, suffix):
    p = pathlib.Path(d) / f"{name}.{suffix}.gz"
    try:
        return gzip.open(p).read().decode(errors="replace")
    except OSError:
        return None


def void_ring(rec):
    """Why a ring job's record must not be read (None: it may)."""
    if rec is None:
        return "no record kept"
    if rec.get("class") not in RESULT_CLASSES:
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
    """{slot: [(pa0, pa1, pa2, stamp), ...]} in rung order; ValueError on a corrupt flag."""
    out = {}
    for k in range(4):
        rows = []
        for j in range(L.RUNGS[k]):
            o = L.RING_BASE[k] + L.RUNG * j
            f = page[o]
            if f not in (0, 1):
                raise ValueError(f"slot {k} rung {j} flag {f:#x}")
            if f == 1:
                rows.append(tuple(page[o + 1:o + 5]))
        out[k] = rows
    return out


def rel(s, ref):
    d = (s - ref) & 0xFFFFFFFF
    d = d - (1 << 32) if d & 0x80000000 else d
    if s < (1 << 25) and ref < (1 << 25) and abs(d) > (1 << 23):
        d = d + (1 << 25) if d < 0 else d - (1 << 25)
    return d


def merged(r):
    """Every slot's entries merged by CR_TIMER stamp: [(slot, pa0, pa1, pa2, stamp)] (Q111's arrival order)."""
    ev = [(k,) + x for k in range(4) for x in r[k]]
    ref = ev[0][4] if ev else 0
    return sorted(ev, key=lambda e: rel(e[4], ref))


def from_stamp(ev, stamp):
    """The entries from the window's own CR_TIMER stamp on (earlier entries belong to nothing of this job)."""
    return [e for e in ev if rel(e[4], stamp) >= 0] if stamp is not None else ev


def is_tick(e):
    return L.is_plain_tick(e[1], e[2])


def e_kick(e):                      # e = (slot, pa0, pa1, pa2, stamp)
    return e[1] == 0 and (e[2] & L.LOW24) == L.KICK_LOW


def e_tick(e):
    return L.is_plain_tick(e[1], e[2])


def e_bit(e):
    """The one bit of pa1[23:0] of a job event (or None)."""
    m = e[2] & L.LOW24
    return m.bit_length() - 1 if m and m & (m - 1) == 0 else None


def on_grid(d, tol=GUARD_TICK):
    k = round(d / T)
    return k >= 1 and abs(d - k * T) <= tol


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
            cons = [m for m, v in by.items() if v and all(x is True for x in v)]
            ref = [m for m, v in by.items() if any(x is False for x in v)]
            ct = [m for m, v in by.items() if any(x is None for x in v) and not any(x is False for x in v)]
            n_ok = sum(1 for r in rs if r[4] is True)
            n_bad = sum(1 for r in rs if r[4] is False)
            n_ct = sum(1 for r in rs if r[4] is None)
            parts.append(f"{k}: {n_ok} held, {n_bad} FAILED, {n_ct} cannot tell/void"
                         + (f"; refuted {sorted(ref)}" if ref else "") + (f"; cannot tell {sorted(ct)}" if ct else ""))
        return "; ".join(parts) if parts else "no rows"


class Stage:
    def __init__(self, stage, d):
        self.stage, self.d = stage, pathlib.Path(d)
        self.table = load_table(stage)
        self.preds = load_preds(stage)
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
        """Add one measurement against every frozen row of (case, quantity): ok_by_model maps a model-name prefix to the
        verdict (True, False, None); rows without a matching function are not scored (alternatives are listed)."""
        for pr in self.preds:
            if pr["case"] != case or pr["quantity"] != quantity:
                continue
            for pref, ok in ok_by_model.items():
                if pr["model"].startswith(pref):
                    self.t.add(case, quantity, pr["model"], pr["set"], ok, note)


# ---- stage k (Q290) ------------------------------------------------------------------------------------------------
def counts_of(es, which):
    return sorted({L.count_of(e[2]) for e in es if which(e)})


def window_ticks_ok(ticks):
    """The clock control: successive tick stamps on the 25000 grid (+-500); needs >= 4 ticks."""
    st = [e[4] for e in ticks]
    d = [rel(b, a) for a, b in zip(st, st[1:])]
    return len(ticks) >= 4 and all(on_grid(x) for x in d)


def score_k(S):
    clock, shown = [], []
    for j in S.table["jobs"]:
        n = j["name"]
        rec = record(S.d, n)
        v = void_ring(rec)
        r = None
        if v is None:
            try:
                r = ring(rec["page"])
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v:
            S.p(f"{n}: NODATA ({v})")
            for pr in S.preds:
                if pr["case"] == n and pr["set"] != "alternative":
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "void")
            continue
        drops = rec["page"][L.DROP:L.DROP + 4]
        ev = from_stamp(merged(r), rec.get("window_stamp"))          # from the window's own CR_TIMER stamp on
        ticks = [e for e in ev if e_tick(e)]
        kicks = [e for e in ev if e_kick(e)]
        non = [e for e in ev if not e_tick(e)]
        base = n.split("-")[0]
        cc = rec.get("ccbctl_after") or [None, None]
        ident = rec.get("ident_after_arm")
        calls = rec.get("arm_calls")
        # the variant's own control: the kernel log counted as many GETMISCINFO answers as the runner's arm path made
        v_ok = None if ident is None or calls is None else ident == calls
        shown.append(v_ok)
        info = f"{n}: {len(ev)} entries (ticks {len(ticks)}, kicks {len(kicks)}, others {len(non) - len(kicks)}), drops {drops}, ident {ident}/{calls} calls, ccbctl {cc}"
        if base in ("k0", "k1", "k2", "k3"):
            ks = counts_of(ev, e_tick)
            clk = window_ticks_ok(ticks) if ticks else None
            clock.append(clk)
            want = int(pred(S.preds, n, "K_ticks")["value"])
            alt = pred(S.preds, n, "K_ticks_alt")
            ok_k = None if (not ticks or any(drops) or non or v_ok is not True) else (ks == [want])
            S.tally_preds(n, "K_ticks", {"H-KW": ok_k})
            if alt:
                S.t.add(n, "K_ticks_alt", alt["model"], "alternative", None if ok_k is None else ks == [int(alt["value"])])
            ok_c = None if cc[0] is None or v_ok is not True else cc[0] == int(pred(S.preds, n, "ccbctl0")["value"])
            S.tally_preds(n, "ccbctl0", {"H-KW": ok_c})
            ok_i = None if ident is None else ident == int(pred(S.preds, n, "ident_after_arm")["value"])
            S.tally_preds(n, "ident_after_arm", {"kernel source": ok_i})
            S.p(info + f"; K of the ticks {ks} (want {want}), clock {'on grid' if clk else clk}")
        elif base == "k4":
            kk = [e for e in ev if e_kick(e)]
            ok_n = None if any(drops) else (len(non) == 1 and len(kk) == 1 and kk[0][0] == 0)
            S.tally_preds(n, "nontick_entries", {"E746": ok_n})
            if len(kk) == 1:
                kx = kk[0]
                K = L.count_of(kx[2])
                after = [e for e in ticks if rel(e[4], kx[4]) > 0]
                S.tally_preds(n, "K_kick", {"E746": K == int(pred(S.preds, n, "K_kick")["value"])})
                ok_a = None if not after or v_ok is not True else counts_of(after, e_tick) == [int(pred(S.preds, n, "K_ticks_after")["value"])]
                S.tally_preds(n, "K_ticks_after", {"E746": ok_a})
                S.p(info + f"; kick K {K}, K of the ticks after {counts_of(after, e_tick)}")
            else:
                S.tally_preds(n, "K_kick", {"E746": None})
                S.tally_preds(n, "K_ticks_after", {"E746": None})
                S.p(info + "; kick not found as one entry")
            ok_c = None if cc[0] is None else cc[0] == int(pred(S.preds, n, "ccbctl0")["value"])
            S.tally_preds(n, "ccbctl0", {"H-KW": ok_c})
            S.tally_preds(n, "ident_after_arm", {"kernel source": None if ident is None else ident == 2})
            clock.append(window_ticks_ok([e for e in ticks if rel(e[4], kk[0][4]) > 0]) if len(kk) == 1 and sum(
                1 for e in ticks if rel(e[4], kk[0][4]) > 0) >= 4 else None)
        elif base == "k5":
            errs = rec.get("kick_errors") or []
            ks = [L.count_of(e[2]) for e in kk_sorted(ev)]
            after = ticks
            vals = {"H-KW": None, "H-SAT": None}
            if errs or any(drops) or len(ks) != 4:
                S.p(info + f"; K of the kicks {ks}, kick errors {len(errs)}: cannot tell")
            else:
                vals["H-KW"] = ks == [0, 1, 2, 3]
                vals["H-SAT"] = ks == [255, 255, 255, 255]
                S.p(info + f"; K of the kicks {ks}; K of the ticks {counts_of(after, e_tick)}")
            S.tally_preds(n, "K_kicks", {"H-KW": vals["H-KW"]})
            alt = pred(S.preds, n, "K_kicks_alt")
            S.t.add(n, "K_kicks_alt", alt["model"], "alternative", vals["H-SAT"])
            tk_ok = None if (errs or not after or len(ks) != 4) else counts_of(after, e_tick) == [4]
            S.tally_preds(n, "K_ticks_after", {"H-KW": tk_ok})
            S.tally_preds(n, "ccbctl0", {"H-KW": None if errs or cc[0] is None else cc[0] == 4})
            it = rec.get("ident_total")
            S.tally_preds(n, "ident_total", {"kernel source": None if errs or it is None else it == 260})
            clock.append(window_ticks_ok(after) if len(after) >= 4 else None)
        elif base == "k6":
            seq = [(L.count_of(e[2]), e[0] == 0 and e[1] == 0 and e_bit(e) == 8) for e in ev if not e_tick(e)]
            n08 = sum(1 for _, b in seq if b)
            rule = None if (any(drops) or len(seq) < 2 or n08 < 2) else all(
                seq[i + 1][0] == seq[i][0] + (1 if seq[i][1] else 0) for i in range(len(seq) - 1))
            S.tally_preds(n, "K_step_rule", {"fit": rule, "E747": rule})
            S.tally_preds(n, "entries_00_8_min", {"E747": None if any(drops) else n08 >= 2})
            S.p(info + f"; (K, is (0,8)) {seq}; step rule {rule}")
    cl = [c for c in clock if c is not None]
    S.p(f"clock control: window ticks on the 25000 grid in {sum(cl)} of {len(cl)} windows with >= 4 ticks")
    S.p(f"arm variants shown (kernel-log GETMISCINFO answers = the arm path's calls): {sum(1 for s in shown if s is True)} of "
        f"{len(shown)} jobs")
    note = S.stage_note()
    ok_all = all(s is True for s in shown) and bool(shown) and all(c is True for c in cl)
    verdict = "controls held" if ok_all else "cannot tell (a control failed or is void)"
    return None, None, f"k: {verdict}; Q290 rows: {S.t.line()}" + (f"; {note}" if note else "")


def kk_sorted(ev):
    return [e for e in ev if e_kick(e)]


# ---- stage t (Q082) --------------------------------------------------------------------------------------------------
def void_probe(rec):
    if rec is None:
        return "no record kept"
    if rec.get("class") not in RESULT_CLASSES:
        return f"class {rec.get('class')}"
    if rec.get("status2_pre") != 0x400:
        return f"the job's own pre read of CR_EVENT_STATUS2 is {rec.get('status2_pre')!r}, not 0x400 (no reset before it)"
    if not isinstance(rec.get("status2_post"), int):
        return "no post read of CR_EVENT_STATUS2"
    if rec.get("tool_rc") not in (0,):
        return f"tool rc {rec.get('tool_rc')}"
    return None


def parse_o0(txt):
    """('fill', n) for 'o0 0x00000000 (N of N)'; ('tri', n_covered_with_o0_0) from the 'o0 mixed' line; None."""
    m = re.search(r"o0 (0x[0-9a-f]{8}) \((\d+) of (\d+)\)", txt or "")
    if m:
        return ("fill" if m[1] == "0x00000000" else "other", int(m[2]) if m[1] == "0x00000000" else 0)
    m = re.search(r"o0 mixed(.*)$", txt or "", re.M)
    if m:
        for v, c in re.findall(r"(0x[0-9a-f]{8}) x(\d+)", m[1]):
            if v == "0x00000000":
                return ("tri", int(c))
        return ("tri", 0)
    return None


def job_time_us(txt):
    m = re.search(r"job time: (\d+) us", txt or "")
    return int(m[1]) if m else None


def linear_ok(xs, ys):
    """The knob proof of a fill ladder: the job time grows with the iteration count (slope > 0, correlation >= 0.8)."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0 or syy == 0:
        return False
    return sxy > 0 and sxy / (sxx * syy) ** 0.5 >= 0.8


def bit6(status2):
    return bool(status2 & 0x40)


def first_set(ladder):
    """ladder {iters: True/False/None}.  (lowest set iteration, highest clear iteration below it, monotone) or None."""
    its = sorted(i for i, v in ladder.items() if v is not None)
    if not its:
        return None
    sets = [i for i in its if ladder[i]]
    if not sets:
        return (None, its[-1], True)
    lo = min(sets)
    clear_below = [i for i in its if i < lo and not ladder[i]]
    mono = all(ladder[i] for i in its if i > lo)
    return (lo, max(clear_below) if clear_below else None, mono)


def score_t(S):
    ladders = {}                         # (row, shape, kind) -> {iters: bit6}
    times = {}
    voids = []
    obs = {}
    for j in S.table["jobs"]:
        n = j["name"]
        rec = record(S.d, n)
        v = void_probe(rec) if j["op"] == "probe" else None
        if j["op"] == "hold_fault":
            s1 = (rec or {}).get("snap1_status2")
            ok_ = rec is not None and rec.get("class") in RESULT_CLASSES and isinstance(s1, int) and rec.get("status2_pre") == 0x400
            if not ok_:
                S.p(f"{n}: NODATA (class {(rec or {}).get('class')}, pre {(rec or {}).get('status2_pre')!r}, snap {s1!r})")
                S.t.add(n, "status2", "E357/E764", "control", None, "void")
            else:
                held = s1 == 0x480
                S.t.add(n, "status2", "E357/E764", "control", held)
                S.p(f"{n}: held TA fault: status2 {s1:#x} at snap 1, {rec.get('snap2_status2')!r} at snap 2 (predicted 0x480) "
                    f"{'held' if held else 'FAILED'}")
            continue
        if v:
            S.p(f"{n}: NODATA ({v})")
            voids.append(n)
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "void")
            ladders.setdefault((j["row"], j["shape"], j["kind"]), {})[j["iters"]] = None
            continue
        txt = rec.get("tool_out", "")
        o0 = parse_o0(txt)
        if j["kind"] == "vtx" and "o0" in txt:
            o0 = ("vtx", 1)                       # the stock vertex program leaves the pixel shader alone: no o0 = 0 test
        post = rec["status2_post"]
        if o0 is None or o0[1] == 0:
            S.p(f"{n}: NODATA (no o0 = 0 pixel in the tool output: the loop did not end or the job did not draw)")
            voids.append(n)
            ladders.setdefault((j["row"], j["shape"], j["kind"]), {})[j["iters"]] = None
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "void")
            continue
        b6 = bit6(post)
        ladders.setdefault((j["row"], j["shape"], j["kind"]), {})[j["iters"]] = b6
        obs[n] = post
        tu = job_time_us(txt)
        if tu is not None:
            times.setdefault((j["row"], j["shape"], j["kind"]), []).append((j["iters"], tu))
        # per-job rows
        for pr in S.preds:
            if pr["case"] != n or pr["quantity"] != "status2":
                continue
            opts = {int(x, 16) for x in pr["value"].split("|")}
            S.t.add(n, "status2", pr["model"], pr["set"], post in opts)
        S.p(f"{n}: status2 {post:#x} after (pre {rec['status2_pre']:#x}), o0 = 0 on {o0[1]} pixels"
            + (f", job time {tu} us" if tu is not None else ""))
    # knob proofs: the loop ran (job time grows with the iteration count on each fill ladder)
    kp = []
    for key, ts in sorted(times.items()):
        ts.sort()
        ok = linear_ok([a for a, _ in ts], [b for _, b in ts])
        kp.append(ok)
        S.p(f"knob proof {key}: job time vs iterations {ts} -> {'grows' if ok else 'cannot tell' if ok is None else 'DOES NOT GROW'}")
    # ladder-level hypotheses (frozen rows threshold_iters)
    L8 = {k: v for k, v in ladders.items()}

    def lad(row, shape, kind):
        return L8.get((row, shape, kind), {})

    def decided(lad_, pts):
        return all(lad_.get(p) is not None for p in pts)

    # T0 control
    l0 = lad("T0", "fill", "b8")
    c53 = [rec_b6(S, n) for n in ("t0-b8-53", "t0-b8-53-r2")]
    c56 = [rec_b6(S, n) for n in ("t0-b8-56", "t0-b8-56-r2")]
    t0ok = None if any(x is None for x in c53 + c56) else (not any(c53)) and all(c56)
    S.t.add("T0", "control", "E431", "control", t0ok)
    S.p(f"T0 control (53 -> 0x400, 56 -> 0x440 in all four runs): {'held' if t0ok else 'cannot tell' if t0ok is None else 'FAILED'}")
    # T1
    l1 = lad("T1", "fill", "b16")
    if decided(l1, (20, 26, 28, 29, 30, 56)):
        h_ti = (not l1[26]) and all(l1[i] for i in (28, 29, 30, 56)) and not l1[20]
        h_it = not any(l1[i] for i in (20, 26, 28, 29, 30)) and l1[56]
    else:
        h_ti = h_it = None
    S.tally_preds("T1", "threshold_iters", {"H-TIME": h_ti, "H-ITER": h_it})
    S.p(f"T1 (body 16) ladder {sorted(l1.items())}: first set {first_set(l1)}; H-TIME/H-INSTR {h_ti}, H-ITER {h_it}")
    # T2
    l2 = lad("T2", "fill", "b4")
    if decided(l2, (50, 80, 100, 105, 112, 115, 120)):
        h_ti2 = (not l2[50]) and not l2[80] and not l2[100] and not l2[105] and l2[112] and l2[115] and l2[120]
        h_it2 = (not l2[50]) and all(l2[i] for i in (80, 100, 105, 112, 115, 120))
    else:
        h_ti2 = h_it2 = None
    S.tally_preds("T2", "threshold_iters", {"H-TIME": h_ti2, "H-ITER": h_it2})
    S.p(f"T2 (body 4) ladder {sorted(l2.items())}: first set {first_set(l2)}; H-TIME/H-INSTR {h_ti2}, H-ITER {h_it2}")
    # T3: occupancy
    sizes = (8, 32, 128, 256)
    l3 = {s: lad("T3", f"tri{s}", "b8") for s in sizes}
    pts = (53, 56)
    if all(decided(l3[s], pts) for s in sizes) and decided(l3[8], (440,)) :
        fs = [first_set(l3[s])[0] for s in sizes]
        mono = all(a is not None and b is not None and a >= b for a, b in zip(fs, fs[1:]))
        h_time3 = (not l3[8][56]) and l3[8][440] and (not l3[256][53]) and l3[256][56] and mono
        h_flat3 = all((not l3[s][53]) and l3[s][56] for s in sizes)
    else:
        h_time3 = h_flat3 = None
        fs = [first_set(l3[s])[0] if l3[s] and first_set(l3[s]) else None for s in sizes]
    S.tally_preds("T3", "threshold_iters", {"H-TIME": h_time3, "H-INSTR": h_flat3})
    S.p("T3 first-set iterations by size " + str(dict(zip(sizes, fs))) + f": H-TIME {h_time3}, H-INSTR = H-ITER {h_flat3}")
    # T4: latency
    l4f, l4t = lad("T4", "fill", "ld8"), lad("T4", "tri8", "ld8")
    if decided(l4f, (40, 50, 53, 56)) and decided(l4t, (50, 53, 56)):
        h_time4 = (not l4f[40]) and (not l4f[50]) and l4f[56] and l4t[50]
        h_flat4 = all((not x[50]) and (not x[53]) and x[56] for x in (l4f, l4t))
    else:
        h_time4 = h_flat4 = None
    S.tally_preds("T4", "threshold_iters", {"H-TIME": h_time4, "H-INSTR": h_flat4})
    S.p(f"T4 fill {sorted(l4f.items())} tri8 {sorted(l4t.items())}: H-TIME {h_time4}, H-INSTR = H-ITER {h_flat4}")
    ctl_ok = t0ok is True and all(k is not False for k in kp)
    S.verdicts = {"T0": t0ok, "T1": (h_ti, h_it), "T2": (h_ti2, h_it2), "T3": (h_time3, h_flat3), "T4": (h_time4, h_flat4),
                  "ladders": {f"{k[0]}-{k[1]}-{k[2]}": sorted(v.items()) for k, v in ladders.items()}, "voids": voids}
    note = S.stage_note()
    summ = (f"t: {'T0 control held' if t0ok else 'T0 control cannot tell' if t0ok is None else 'T0 control FAILED'}; "
            f"{len(voids)} void jobs; hypotheses by ladder (H-TIME / H-INSTR-H-ITER): T1 {h_ti}/{h_it}, T2 {h_ti2}/{h_it2}, "
            f"T3 {h_time3}/{h_flat3}, T4 {h_time4}/{h_flat4}; rows: {S.t.line()}")
    return None, None, summ + ("" if ctl_ok else "; a control failed or is void: the ladders are cannot tell") + (f"; {note}" if note else "")


def rec_b6(S, name):
    rec = record(S.d, name)
    if void_probe(rec):
        return None
    o0 = parse_o0(rec.get("tool_out", ""))
    if o0 is None or o0[1] == 0:
        return None
    return bit6(rec["status2_post"])


# ---- stages d0 and d1 (Q033) -----------------------------------------------------------------------------------------
E747_TRI64 = [(0, 8), (1, 9), (3, 4), (3, 22)] + [(0, 8)] * 5


def seq_of(ev):
    return [(e[0], e_bit(e)) for e in ev if not e_tick(e)]


def dispatch_ok(ev):
    return all(e[0] == L.pds_slot(e[1], e[2]) for e in ev if not e_tick(e))


def timeline(text):
    m = re.search(r"^timeline: regs (.*?) samples", text or "", re.M)
    if not m:
        return None
    regs = m[1].split()
    rows = [[int(x, 0) if i == 0 else int(x, 16) for i, x in enumerate(ln.split()[1:])]
            for ln in text.splitlines() if ln.startswith("tl ")]
    return regs, rows


def knob_value(tl, text):
    """The 0x0624 value of THIS job: the first row at or after the header's `start` whose 0x0724 low half is non-zero."""
    m = re.search(r"^timeline: .* start (\d+) end", text or "", re.M)
    if not tl or not m:
        return None
    start = int(m[1])
    regs, rows = tl
    if "0x0624" not in regs or "0x0724" not in regs:
        return None
    i24, i4 = regs.index("0x0624") + 1, regs.index("0x0724") + 1
    for r in rows:
        if r[0] >= start and (r[i4] & 0xffff):
            return r[i24]
    return None


def n_partial(tl):
    """Partial renders: the 0x0658 bit-0 stretches of the timeline."""
    regs, rows = tl
    if "0x0658" not in regs:
        return None
    ip = regs.index("0x0658") + 1
    n, inpr = 0, False
    for r in rows:
        if r[ip] & 1:
            if not inpr:
                n += 1
            inpr = True
        else:
            inpr = False
    return n


def status_bit_pulses(tl):
    """The rising edges of CR_EVENT_STATUS bits in the job's timeline, in time order: [(time ns, bit)]."""
    regs, rows = tl
    if "0x012c" not in regs:
        return None
    i = regs.index("0x012c") + 1
    out, prev = [], None
    for r in rows:
        v = r[i]
        if prev is not None:
            for b in range(32):
                if (v >> b & 1) and not (prev >> b & 1):
                    out.append((r[0], b))
        prev = v
    return out


def lcs(a, b):
    m = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) - 1, -1, -1):
        for j in range(len(b) - 1, -1, -1):
            m[i][j] = m[i + 1][j + 1] + 1 if a[i] == b[j] else max(m[i + 1][j], m[i][j + 1])
    return m[0][0]


def d_job(S, j):
    """(rec, ring, merged entries, void reason) of one D job."""
    n = j["name"]
    rec = record(S.d, n)
    v = void_ring(rec)
    r = ev = None
    if v is None:
        tr = rec.get("tool_rc")
        out = rec.get("tool_out", "")
        if tr not in (0, 3, 1) or (tr != 0 and "scene overflowed" not in out and "overflowed" not in out and tr != 3):
            v = f"tool rc {tr}"
    if v is None:
        try:
            r = ring(rec["page"])
            ev = from_stamp(merged(r), rec.get("window_stamp"))      # from the window's own CR_TIMER stamp on
        except ValueError as e:
            v = f"corrupt ring: {e}"
    if v is None and rec.get("knobs_readback") is not None:
        for k, val in j.get("knobs", {}).items():
            rb = rec["knobs_readback"].get(k)
            if rb is None or int(str(rb), 0) != int(val, 0):
                v = f"knob {k} read back {rb!r}, wanted {val}"
    return rec, r, ev, v


def score_d0(S):
    ok_rows = []
    for j in S.table["jobs"]:
        n = j["name"]
        rec, r, ev, v = d_job(S, j)
        if v:
            S.p(f"{n}: NODATA ({v})")
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "void")
            ok_rows.append(None)
            continue
        drops = rec["page"][L.DROP:L.DROP + 4]
        # a window of its own: the entries from the first non-tick entry on (nothing logged before the job)
        seq = seq_of(ev)
        dsp = dispatch_ok(ev)
        b19 = sum(1 for e in ev if e[2] & (1 << 19))
        S.p(f"{n}: {len(seq)} entries {seq}, drops {drops}, dispatch {'100%' if dsp else 'NOT 100%'}, bit-19 entries {b19}")
        S.tally_preds(n, "dispatch", {"E146": dsp})
        S.tally_preds(n, "bit19_entries", {"E747": None if any(drops) else b19 == 0})
        if n.startswith("d0-tri64"):
            ok = None if any(drops) else seq == E747_TRI64
            S.tally_preds(n, "entries", {"E747": ok})
            ok_rows.append(ok is True and dsp)
        else:
            sl2 = {e_bit(e) for e in ev if e[0] == 2}
            ok = None if any(drops) else sl2 == {21, 10}
            S.tally_preds(n, "slot2_bits", {"E747": ok})
            ok_rows.append(ok is True and dsp)
    full = len(ok_rows) == 3 and all(x is True for x in ok_rows)
    why = None if full else "a control failed or is void: " + ", ".join(str(x) for x in ok_rows)
    note = S.stage_note()
    if note:
        full, why = False, note
    return full, why, (f"d0: {'controls held (D0 and D1: E747 reproduced, dispatch 100%)' if full else 'cannot tell or FAILED: ' + str(why)}; "
                       f"rows: {S.t.line()}")


def score_d1(S):
    res = {}
    for j in S.table["jobs"]:
        n = j["name"]
        rec, r, ev, v = d_job(S, j)
        txt = gz_text(S.d, n, "tool.txt")
        tl = timeline(txt) if txt else None
        b09 = rec.get("buf09") if rec else None
        if v is None and (tl is None or b09 is None or len(b09) < 39):
            v = "no timeline or no control block kept"
        if v is None:
            knob = knob_value(tl, txt)
            want = pred(S.preds, n, "knob0624_first")
            if knob is None:
                v = "no status rise: the job's own 0x0624 value is unknown"
            elif int(want["value"], 16) != knob:
                v = f"knob did not land: 0x0624 {knob:#x}, wanted {want['value']}"
        if v:
            S.p(f"{n}: NODATA ({v})")
            res[n] = None
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "void")
            continue
        drops = rec["page"][L.DROP:L.DROP + 4]
        b19 = [e for e in ev if e[2] & (1 << 19)]
        raised = b09[38] == 0x20
        nparts = n_partial(tl)
        pulses = status_bit_pulses(tl)
        p3 = [x for x in pulses if x[1] == 3] if pulses is not None else None
        seq_ring = [22 - e_bit(e) for e in ev if not e_tick(e) and e_bit(e) not in (None, 8, 19)]
        seq_tl = [b for _, b in (pulses or []) if b not in (3, 14, 31) and b <= 22]
        res[n] = dict(raised=raised, b19=len(b19), nparts=nparts, drops=drops)
        S.p(f"{n}: 0x0624 {knob:#x}, raise {raised} (dword 38 {b09[38]:#x}), partial renders {nparts}, entries {len(ev)}, drops "
            f"{drops}, bit-19 entries {len(b19)} in slots {sorted({e[0] for e in b19})}, status bit-3 pulses "
            f"{None if p3 is None else len(p3)}")
        tag = n.split("-")[0]
        full0 = any(drops)
        slot0_full = bool(drops[0])
        ok_raise = raised == (tag == "d2")
        S.tally_preds(n, "raise", {"S1 post hoc": ok_raise if tag == "d2" else None, "proposal D3": ok_raise if tag == "d3" else None,
                                   "E704": ok_raise if tag == "d4" else None})
        S.tally_preds(n, "knob0624_first", {"knob": True})
        if tag == "d2":
            if not raised:
                ok = {"H-RAISE": None}                  # the raise did not reproduce: nothing is concluded
            elif b19 and all(e[0] == 0 for e in b19):
                ok = {"H-RAISE": True}
            elif b19:
                ok = {"H-RAISE": False}
            else:
                ok = {"H-RAISE": None if slot0_full else False}
            S.tally_preds(n, "bit19_entries", ok)
        elif tag == "d3":
            if raised:
                ok = {"H-RAISE": None}                  # a raise where none was predicted: the premise failed
            elif b19:
                ok = {"H-RAISE": False}
            else:
                ok = {"H-RAISE": None if slot0_full else True}
            S.tally_preds(n, "bit19_entries", ok)
            # H-THRESH is the alternative row: >= 1 whenever the TA reaches thr0 (a partial render happened)
            alt = pred(S.preds, n, "bit19_entries_alt")
            if alt:
                reach = bool(nparts)
                S.t.add(n, "bit19_entries_alt", alt["model"], "alternative",
                        None if (raised or not reach or slot0_full) else bool(b19))
        else:
            ok = {"H-RAISE": None if raised else (False if b19 else (None if slot0_full else True))}
            S.tally_preds(n, "bit19_entries", ok)
        # D5: the status bit-3 pulses against the ring's bit-19 entries
        if p3 is None:
            d5 = None
        else:
            d5 = (len(p3) == len(b19)) and lcs(seq_ring, seq_tl) >= min(len(seq_ring), len(seq_tl)) - 1
        S.tally_preds(n, "D5_bit3_pulses", {"D5": d5})
    note = S.stage_note()
    # the instrument verdict per hypothesis, from the first job of each condition (the replicates are in the tally)
    d2 = [v for k, v in res.items() if k.startswith("d2") and v]
    d3 = [v for k, v in res.items() if k.startswith("d3") and v]
    d4 = [v for k, v in res.items() if k.startswith("d4") and v]
    pos = [x["b19"] > 0 for x in d2 if x["raised"]]
    neg = [x["b19"] > 0 for x in d3 if not x["raised"]]
    if not pos:
        head = "cannot tell: no D2 job raised (the raise did not reproduce) or all are void"
    elif all(pos) and not any(neg):
        head = "H-RAISE favoured (bit 19 in the raise jobs, none in the no-raise jobs)" + ("" if not any(x["b19"] for x in d4) else " but D4 logged one")
    elif all(pos) and any(neg):
        head = "H-THRESH favoured (bit 19 also in no-raise jobs)"
    elif not any(pos):
        head = "H-NEVER (or the ring lost it): no bit-19 entry in any raise job"
    else:
        head = "mixed: bit 19 in some raise jobs only"
    return None, None, f"d1: {head}; rows: {S.t.line()}" + (f"; {note}" if note else "")


SCORERS = {"k": score_k, "t": score_t, "d0": score_d0, "d1": score_d1}
GATED = {"d0"}


def env_problem(stage, d):
    """Why env.json does not close the hash chain to the Mac's frozen files (None: it does)."""
    try:
        env = json.loads((pathlib.Path(d) / "env.json").read_text())
        st = json.loads((pathlib.Path(d) / "stage.json").read_text())
    except (OSError, ValueError):
        return "no env.json or stage.json"
    want_t = hashlib.sha256((R1 / "tables" / f"{stage}.json").read_bytes()).hexdigest()
    if env.get("table_sha256") != want_t:
        return f"env.json table sha256 {str(env.get('table_sha256'))[:12]} is not tables/{stage}.json's {want_t[:12]}"
    blob = load_table(stage)["blob"]
    if blob:
        want_b = hashlib.sha256((R1 / "bins" / f"{blob}.blob").read_bytes()).hexdigest()
        if env.get("blob_sha256") != want_b:
            return f"env.json blob sha256 {str(env.get('blob_sha256'))[:12]} is not bins/{blob}.blob's {want_b[:12]}"
    tool = (R1 / "TOOL.sha256").read_text().split()[0]
    if env.get("tool_sha256") != tool:
        return f"env.json tool sha256 {str(env.get('tool_sha256'))[:12]} is not the staged tool's {tool[:12]}"
    if env.get("run") != st.get("run"):
        return f"env.json is of run {env.get('run')}, stage.json of {st.get('run')}"
    return None


def score(stage, d, check_env=True):
    S = Stage(stage, d)
    ok, why, summ = SCORERS[stage](S)
    if not any(r for r in (record(d, j["name"]) for j in S.table["jobs"])):
        ok, why, summ = False, "no job record at all", f"{stage}: cannot tell (no data)"
    elif check_env:
        bad = env_problem(stage, d)
        if bad:
            ok, why, summ = False, bad, f"{stage}: cannot tell (env.json does not match the frozen files: {bad})"
    S.lines.append(f"SUMMARY: {summ}")
    return ok, why, "\n".join(S.lines)


def main(a):
    if len(a) < 2 or a[0] not in SCORERS:
        print(__doc__)
        return 2
    stage, d = a[0], a[1]
    r = subprocess.run([str(R1 / "run" / "freeze_r1.sh"), "verify"], capture_output=True, text=True)
    if r.returncode:
        print("REFUSING: the frozen files do not verify:\n" + r.stdout + r.stderr)
        return 3
    ok, why, text = score(stage, d)
    print(text)
    if "--gate" in a:
        if stage not in GATED:
            print(f"{stage} has no gate")
            return 2
        try:
            run = json.loads((pathlib.Path(d) / "stage.json").read_text()).get("run")
        except (OSError, ValueError):
            run, ok, why = None, False, "no stage.json"
        line = f"GATE {stage} {'OPEN' if ok else 'CLOSED'} run={run} {why or ''}".strip()
        gates = pathlib.Path(a[a.index("--gates") + 1]) if "--gates" in a else R1 / "gates"
        gates.mkdir(exist_ok=True)
        (gates / f"{stage}.gate").write_text(line + "\n")
        print(line)
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
