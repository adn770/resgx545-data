#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score_s2.py STAGE OUTDIR [--gate]: score one S2 stage from what the runner kept (out/STAGE/: NAME.json, cases.tsv,
stage.json).  Written before the run and frozen (run/freeze_s2.sh); refuses unless `run/freeze_s2.sh verify` passes.
Prints a line a job and one `SUMMARY:` line.  With --gate (stages e1c e2r e4c e4h e4l e5c) it also writes
gates/STAGE.gate ("GATE STAGE OPEN ..." or "GATE STAGE CLOSED ...") and exits 0 only when the gate is open: the
driver runs the next stage only then, and the laptop runner refuses the next stage without the open gate file.

Void before any match: a missing or unreadable record, no page, a page that is not 1024 dwords or lost its header,
a class that is not a result, a rung flag that is neither 0 nor 1, a window that did not close (page2 differs), an
area dword still INITFILL.  Void jobs never count as a pass; a stage with too few valid jobs is "cannot tell".
Standard library only.  Tests call score(stage, dir) directly (no freeze check).
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
S2 = HERE.parent
sys.path.insert(0, str(S2 / "gen"))
import s2layout as L  # noqa: E402

GATED = {"e4c", "e4m", "e4l", "e5c"}
RESULT_CLASSES = {"ok", "kick-timeout", "stuck"}
T = L.TICK_UNITS                     # 25000 counts a tick: S2 run 3's clock control (e1c median 25000, e4c 25000 to
                                     # 25001); E009's 25001 put run 3's 90-tick exits 5 and 10 units on the wrong side
GUARD = 1250                         # 50 us: a natural tick this close after the exit cannot be told from a held one


# ---- reading ---------------------------------------------------------------------------------
def load_table(stage):
    return json.loads((S2 / "tables" / f"{stage}.json").read_text())


def load_preds(stage):
    rows = (S2 / "predictions" / f"{stage}.tsv").read_text().splitlines()[1:]
    return [dict(zip(("case", "quantity", "value", "model", "set"), r.split("\t"))) for r in rows if r.strip()]


def record(d, name):
    """The job's record, only if this stage's last run (stage.json) wrote it: a file left by an earlier run of the
    same stage (nothing is ever deleted) is not read."""
    try:
        st = json.loads((pathlib.Path(d) / "stage.json").read_text())
        rec = json.loads((pathlib.Path(d) / f"{name}.json").read_text())
    except (OSError, ValueError):
        return None
    if name not in st.get("jobs_run", []) or rec.get("run") != st.get("run"):
        return None
    return rec


def void_of(rec, need_page2=False):
    """Why a record must not be read (None: it may)."""
    if rec is None:
        return "no record kept"
    if rec.get("class") not in RESULT_CLASSES:
        return f"class {rec.get('class')}"
    if rec.get("rc") is None:
        return "no rc recorded"
    pg = rec.get("page")
    if not isinstance(pg, list) or len(pg) != L.PAGE_DWORDS:
        return "no page, or a truncated page"
    if pg[0] != L.MAGIC:
        return "the page header is not the kernel's magic"
    if need_page2:
        p2 = rec.get("page2")
        if not isinstance(p2, list) or len(p2) != L.PAGE_DWORDS:
            return "no second page (window-0 proof)"
        if p2[L.RING_BASE[0]:L.RING_END] != pg[L.RING_BASE[0]:L.RING_END]:
            return "the ring changed after the window closed (window 0 did not take)"
    return None


def ring(page):
    """{slot: [(pa0, pa1, pa2, stamp), ...]} in rung order; raises ValueError on a corrupt flag."""
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
    """s - ref in CR_TIMER counts, across a wrap.  E009 measured TIMER counting UP at core/16 (24.94 MHz); the p1141
    draft decoder assumed a 25-bit down-counter.  Neither width is recorded, so: modulo 2^32, and when both values
    are below 2^25 and the difference is beyond 2^23 counts (336 ms, longer than any S2 window), modulo 2^25."""
    d = (s - ref) & 0xFFFFFFFF
    d = d - (1 << 32) if d & 0x80000000 else d
    if s < (1 << 25) and ref < (1 << 25) and abs(d) > (1 << 23):
        d = d + (1 << 25) if d < 0 else d - (1 << 25)
    return d


def bits(x):
    return [b for b in range(32) if x >> b & 1]


def diffs(entries):
    """Successive CR_TIMER differences in rung (arrival) order, made positive when the counter counts down (all of
    them negative); the direction is reported by direction()."""
    st = [e[3] for e in entries]
    d = [rel(b, a) for a, b in zip(st, st[1:])]
    return [-x for x in d] if d and all(x < 0 for x in d) else d


def direction(entries):
    st = [e[3] for e in entries]
    d = [rel(b, a) for a, b in zip(st, st[1:])]
    return "none" if not d else "up" if all(x > 0 for x in d) else "down" if all(x < 0 for x in d) else "mixed"


def on_grid(d, tol=500):
    k = round(d / T)
    return k >= 1 and abs(d - k * T) <= tol, k


def median(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else None


class Stage:
    def __init__(self, stage, d):
        self.stage, self.d = stage, pathlib.Path(d)
        self.table = load_table(stage)
        self.preds = load_preds(stage)
        self.lines = []
        st = self.d / "stage.json"
        try:
            self.stagerec = json.loads(st.read_text())
        except (OSError, ValueError):
            self.stagerec = None

    def p(self, s):
        self.lines.append(s)

    def jobs(self, prefix=""):
        return [j for j in self.table["jobs"] if j["name"].startswith(prefix)]

    def stage_note(self):
        if self.stagerec is None:
            return "no stage.json (the stage did not finish writing)"
        if self.stagerec.get("exit") != 0:
            return f"stage exit {self.stagerec.get('exit')}: {self.stagerec.get('why', '')}"
        return None


# ---- E1 --------------------------------------------------------------------------------------
def score_e1c(S):
    res = {"q50": [], "q8": [], "kick": [], "q50k": []}
    kick_counts, held_out = [], {}
    diffs_all, dirs = [], []
    q153, q157 = [], []
    for j in S.table["jobs"]:
        rec = record(S.d, j["name"])
        v = void_of(rec, need_page2=True)
        kind = j["name"].split("-")[0]
        if v is None:
            try:
                r = ring(rec["page"])
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v:
            S.p(f"{j['name']}: NODATA ({v})")
            res[kind].append(None)
            continue
        drops = rec["page"][L.DROP:L.DROP + 4]
        n_all = sum(len(r[k]) for k in range(4))
        if kind == "q50":
            ok = n_all == 0
            S.p(f"{j['name']}: {n_all} entries (predicted 0, E538 quiet) {'held' if ok else 'FAILED'}")
        elif kind == "q8":
            e0 = r[0]
            ds = diffs(e0)
            dirs.append(direction(e0))
            grid = [on_grid(d) for d in ds]
            diffs_all += [d for d, (g, k) in zip(ds, grid) if g and k == 1]
            # the window was open t_close_ms as the host measured it (the 8 ms sleep overshoots): ticks at 997.46 Hz
            want = rec.get("t_close_ms", 0) * 0.99746
            ok = (len(e0) >= 4 and abs(len(e0) - want) <= 1.5 and n_all == len(e0) and not any(drops)
                  and all(e[0] == L.TICK_PA0 for e in e0))
            q153.append(all(e[1] == L.TICK_PA1 for e in e0))
            q157.append(all(e[2] == L.PA2_CONST for e in e0))
            S.p(f"{j['name']}: slot 0 {len(e0)} entries (window open {rec.get('t_close_ms', 0):.2f} ms: {want:.1f} "
                f"ticks), other slots {n_all - len(e0)}, drops {drops}; pa1 "
                f"{sorted({hex(e[1]) for e in e0})} pa2 {sorted({hex(e[2]) for e in e0})}; diffs {ds} "
                f"{'held' if ok else 'FAILED'}")
        elif kind == "q50k":
            ok = n_all == 0
            S.p(f"{j['name']}: {n_all} entries (predicted 0: the window-1 filter at a count of "
                f"{sorted(kick_counts)[-1] + 1 if kick_counts else '?'}, after the kicks) {'held' if ok else 'FAILED'}")
        else:
            ok, line, kc = score_kick(r)
            if kc is not None:
                kick_counts.append(kc)
            S.p(f"{j['name']}: {line}; kick read {(rec.get('kick') or {}).get('ms', 0):.2f} ms")
            for part in ("pa2 phase", "count +1", "pa2 range", "ticks"):
                held_out.setdefault(part, []).append(f"{part} held" in line)
        res[kind].append(ok)
    clock = median(diffs_all)
    up = all(d == "up" for d in dirs) and dirs
    S.p(f"clock control: median tick-to-tick CR_TIMER difference {clock} (E009 predicts {T}, counting up; window "
        f"[{T - 250}, {T + 250}]); counting {dirs}; "
        f"{'held' if up and clock and abs(clock - T) <= 250 else 'FAILED or cannot tell: E4 counts in CR_TIMER units only'}")
    S.p(f"q8 ticks: pa1 = 0x02000000 (count 2) in {sum(map(bool, q153))} of {len(q153)} jobs, pa2 = 0x01061a70 in "
        f"{sum(map(bool, q157))} of {len(q157)}")
    steps = [b - a for a, b in zip(kick_counts, kick_counts[1:])]
    S.p(f"kick counts K in job order {kick_counts} (held out, fit: S2 run 1 gave 2, 3, 4): "
        f"{'held' if kick_counts == [2, 3, 4] else 'FAILED or cannot tell'}; steps {steps}")
    S.p("held-out kick predictions (fit: S2 run 1): " + ", ".join(f"{k} {sum(v)}/{len(v)}" for k, v in held_out.items()))
    # the gate: the instrument controls only (quiet, ticks, the kick's identity, the filter after the kicks); the
    # kick's pa2 phase, count step and count values are held-out science, reported, not gated
    full = all(len(v) == n and all(x is True for x in v) for v, n in
               ((res["q50"], 3), (res["q8"], 2), (res["kick"], 3), (res["q50k"], 2)))
    why = None if full else "a control failed or is void: " + ", ".join(
        f"{k} {sum(1 for x in v if x)}/{len(v)}" for k, v in res.items())
    note = S.stage_note()
    if note:
        full, why = False, note
    verdict = "controls held" if full else "cannot tell" if any(x is None for v in res.values() for x in v) else "a control FAILED"
    return full, why, (f"e1c: {verdict} (quiet 50 ms {res['q50']}, ticks {res['q8']}, kick {res['kick']}, quiet after "
                       f"the kicks {res['q50k']}); clock {clock}; kick counts {kick_counts}; held out "
                       + ", ".join(f"{k} {sum(v)}/{len(v)}" for k, v in held_out.items()))


def score_kick(r):
    """(ok, line, K) for one kick job's ring (window 2).  ok is the gated control (fit: S2 run 1): exactly one entry
    that is not a plain tick, in slot 0, with the kick's words (pa0 0, pa1[23:0] 0x100).  The line also scores the
    held-out predictions: pa2 range, pa2 phase against the neighbouring tick, the count step, the ticks."""
    allv = [(k,) + x for k in range(4) for x in r[k]]
    non = [e for e in allv if not L.is_plain_tick(e[1], e[2])]
    ok = len(non) == 1 and non[0][0] == 0 and L.is_kick(non[0][1], non[0][2])
    if not ok:
        return False, (f"kick FAILED: {len(non)} non-tick entries "
                       f"{[(e[0], hex(e[1]), hex(e[2]), hex(e[3])) for e in non][:4]}"), None
    e0 = r[0]
    i = next(n for n, e in enumerate(e0) if L.is_kick(e[0], e[1]))
    kx = e0[i]
    K = L.count_of(kx[1])
    before, after = e0[:i], e0[i + 1:]
    parts = [f"kick held: pa1 {kx[1]:#010x} pa2 {kx[2]:#010x} (K {K}, {len(before)} ticks before, {len(after)} after)"]
    parts.append(f"pa2 range {'held' if L.evt_ok(kx[2]) and kx[2] != L.PA2_CONST else 'FAILED'}")
    since = (L.EVT_RELOAD - (kx[2] & L.LOW24)) / 16          # CR_TIMER units since the last tick, by pa2
    if before:
        resid = rel(kx[3], before[-1][3]) - since
    elif after:
        resid = rel(after[0][3], kx[3]) - (L.EVT_RELOAD / 16 - since)
    else:
        resid = None
    parts.append(f"pa2 phase {'cannot tell' if resid is None else 'held' if abs(resid) <= 50 else 'FAILED'}"
                 f" (residual {resid if resid is None else round(resid, 1)})")
    cs_ok = all(L.count_of(e[1]) == K for e in before) and all(L.count_of(e[1]) == K + 1 for e in after) and after
    parts.append(f"count +1 {'held' if cs_ok else 'FAILED'} (before {sorted({L.count_of(e[1]) for e in before})}, "
                 f"after {sorted({L.count_of(e[1]) for e in after})})")
    ticks = before + after
    tk_ok = (all(e[0] == L.TICK_PA0 and (e[1] & L.LOW24) == 0 and e[2] == L.PA2_CONST for e in ticks)
             and all(on_grid(d)[0] for seg in (before, after) for d in diffs(seg)))
    parts.append(f"ticks {'held' if tk_ok and ticks else 'FAILED'}")
    return True, "; ".join(parts), K


def entries_of(rec):
    """Every slot's entries merged by CR_TIMER (Q111's arrival order): [(slot, pa0, pa1, pa2, stamp)], the ring."""
    r = ring(rec["page"])
    ev = [(k,) + x for k in range(4) for x in r[k]]
    ref = ev[0][4] if ev else 0
    return sorted(ev, key=lambda e: rel(e[4], ref)), r


def score_e1j(S):
    allowed = {}
    for p in S.preds:
        if p["quantity"] == "pa1_bits_allowed":
            allowed[(p["case"], p["model"])] = set(int(x) for x in p["value"].split(",") if x != "")
    base = {}
    for ln in (S2 / "predictions" / "e1-baseline-order.tsv").read_text().splitlines()[1:]:
        kind, run, cnt, order = ln.split("\t")
        base.setdefault(kind, []).append(f"{order} (x{cnt}, {run})")
    fill_v, explained = [], {"H1": [0, 0], "H2": [0, 0]}
    slot_ok, slot_n, evt, nev, full_rings, nkick = 0, 0, 0, 0, 0, 0
    bit8, counts = {}, set()
    for j in S.table["jobs"]:
        name = j["name"]
        kind = j["trigger"][5:]
        rec = record(S.d, name)
        v = void_of(rec, need_page2=True)
        if v is None and kind == "partial" and "overflowed" not in (rec.get("tool_out") or ""):
            v = "no overflowed render: render_pb_pages 0x30 did not act (no partial render)"
        if v is None:
            try:
                ev, r = entries_of(rec)
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v:
            S.p(f"{name}: NODATA ({v})")
            if kind == "fill":
                fill_v.append(None)
            continue
        drops = rec["page"][L.DROP:L.DROP + 4]
        if any(drops):
            full_rings += 1
        ev = [e for e in ev if not L.is_plain_tick(e[1], e[2])]
        nev += len(ev)
        for e in ev:
            slot_n += 1
            slot_ok += e[0] == L.pds_slot(e[1], e[2])
            counts.add(L.count_of(e[2]))
            evt += L.evt_ok(e[3])
            nkick += L.is_kick(e[1], e[2])
        bit8[kind] = bit8.get(kind, []) + [sum(1 for e in ev if e[0] == 0 and e[2] >> 8 & 1)]
        # pa1[23:0] only: pa1[31:24] is the count (S2 run 1); bit 8 (a host kick) is allowed under both maps
        evbits = [set(bits(e[2] & L.LOW24)) for e in ev]
        for h in ("H1", "H2"):
            a = allowed[(name, h)]
            explained[h][0] += sum(1 for b in evbits if b <= a)
            explained[h][1] += len(evbits)
        wb = [set(bits(e[2] & L.LOW24)) for e in ev if not L.is_kick(e[1], e[2])]   # the witness ignores CCB kicks
        allb = set().union(*wb) if wb else set()
        if kind == "fill":
            if not wb:
                fill_v.append("none")
            elif 4 in allb and 18 not in allb:
                fill_v.append("H1")
            elif 18 in allb and 4 not in allb:
                fill_v.append("H2")
            else:
                fill_v.append("H3")
        t0 = ev[0][4] if ev else 0
        S.p(f"{name}: {len(ev)} event entries, drops {drops}: " + "; ".join(
            f"s{e[0]} +{rel(e[4], t0)} pa0 {e[1]:#x} pa1 {e[2]:#010x} bits {bits(e[2])} pa2 {e[3]:#x}" for e in ev[:20]))
        if not j["name"].endswith(("-r2", "-r3")):
            S.p(f"  baseline first-rise orders of {kind} (status bits, E547): {'; '.join(base.get(kind, ['none']))}")
    nf = [x for x in fill_v if x is not None]
    if len(nf) < 2:
        q033 = "cannot tell (fewer than 2 valid fill jobs)"
    elif all(x == "none" for x in nf):
        q033 = "cannot tell: the fill's event does not reach the EDM in any job (a result for 12.6)"
    elif sum(x == "H1" for x in nf) >= 2 and "H2" not in nf:
        q033 = "H1 (reversed, E155) on the fill"
    elif sum(x == "H2" for x in nf) >= 2 and "H1" not in nf:
        q033 = "H2 (same position, E146) on the fill"
    elif sum(x == "H3" for x in nf) >= 2:
        q033 = "H3 (neither map) on the fill"
    else:
        q033 = f"mixed on the fill {fill_v}: cannot tell"
    if slot_ok != slot_n:
        q033 = f"cannot tell (instrument control failed: the dispatch rule held on {slot_ok} of {slot_n} entries)"
    S.p(f"PDS #13 dispatch rule (E146) on every event entry: {slot_ok} of {slot_n} (the instrument control)")
    S.p(f"rows 4-8, entries whose bits the map explains: H1 {explained['H1'][0]}/{explained['H1'][1]}, "
        f"H2 {explained['H2'][0]}/{explained['H2'][1]}")
    S.p(f"bit-8 slot-0 entries a job (a job's own CCB kick may log one; no witness, S2 run 1): {bit8}; entries with "
        f"the kick's words: {nkick}")
    S.p(f"count bytes pa1[31:24] seen on job events: {sorted(counts)}; pa2 in EVENT_TIMER's format and range: {evt} of "
        f"{nev} (held out); jobs whose ring filled: {full_rings}")
    note = S.stage_note()
    summ = (f"e1j: Q033 {q033} (fill jobs {fill_v}); explained H1 {explained['H1'][0]}/{explained['H1'][1]} H2 "
            f"{explained['H2'][0]}/{explained['H2'][1]}; dispatch {slot_ok}/{slot_n}; pa2 EVENT_TIMER {evt}/{nev}; "
            f"counts {sorted(counts)}" + (f"; {note}" if note else ""))
    return None, None, summ


# ---- E2a -------------------------------------------------------------------------------------
def area(page, base):
    vals = page[base:base + 12]
    return None if L.INITFILL in vals else dict(zip(L.AREA_FIELDS, vals))


def score_e2r(S):
    good, valid = 0, 0
    hd = []
    for j in S.table["jobs"]:
        rec = record(S.d, j["name"])
        v = void_of(rec)
        A = B = None
        if v is None:
            A, B = area(rec["page"], L.AREA_A), area(rec["page"], L.AREA_B)
            if A is None or B is None:
                v = "an area still holds INITFILL"
            elif rec["page"][L.ECHO] != j["runid"]:
                v = f"the echo {rec['page'][L.ECHO]:#x} is not the run id"
        if v:
            S.p(f"{j['name']}: NODATA ({v})")
            continue
        valid += 1
        m = A["sa66"] == L.PA2_CONST
        good += m
        d = {"sa64=2": A["sa64"] == 2, "sa65=pa1": A["sa65"] == A["pa1"], "sa66=pa2": A["sa66"] == A["pa2"],
             "pa0=2": A["pa0"] == 2, "not H-F (sa0 != pa0)": A["sa0"] != A["pa0"]}
        hd.append(all(d.values()) and m)
        S.p(f"{j['name']}: A " + " ".join(f"{k} {v:#x}" for k, v in A.items()) + f" | B pa3 {B['pa3']:#x} pa4 "
            f"{B['pa4']:#x} sa67 {B['sa67']:#x} sa68 {B['sa68']:#x} | sa66 {'= 0x01061a70' if m else 'DIFFERS'}; {d}")
    note = S.stage_note()
    ok = valid == 3 and good == 3 and not note
    why = None if ok else (note or f"sa66 = 0x01061a70 in {good} of {valid} valid jobs (3 of 3 needed)")
    reading = ("H-D read side held (sa64..66 = pa0..pa2)" if valid == 3 and all(hd) else
               "H-S (sa66 is not pa2's word)" if valid == 3 and good == 0 else
               "cannot tell" if valid < 3 else "mixed")
    return ok, why, f"e2r: {reading}; sa66 prediction {good} of {valid} valid ({len(S.table['jobs'])} jobs)"


def score_e2w(S):
    out = {2: [], 3: []}
    restored = []
    ctl = record(S.d, "ctl")
    vc = void_of(ctl)
    ctl_ok = vc is None and area(ctl["page"], L.AREA_A) is not None and area(ctl["page"], L.AREA_A)["sa66"] == L.PA2_CONST
    S.p(f"ctl: {'sa66 = 0x01061a70 (as e2r)' if ctl_ok else 'FAILED or NODATA: ' + str(vc)}")
    for j in S.table["jobs"]:
        if j["cmd"] not in (2, 3):
            continue
        rec = record(S.d, j["name"])
        v = void_of(rec)
        sa, pa, c = ("sa67", "pa3", L.AREA_C) if j["cmd"] == 2 else ("sa68", "pa4", L.AREA_C + 2)
        if v is None:
            B = area(rec["page"], L.AREA_B)
            C = rec["page"][c:c + 2]
            M = rec.get("mark_value")
            if B is None or L.INITFILL in C or M is None:
                v = "an area still holds INITFILL, or no mark recorded"
            elif C[1] != M:
                v = f"{sa} read {C[1]:#x} right after the write of {M:#x}: the write did not take"
        if v:
            S.p(f"{j['name']}: NODATA ({v})")
            continue
        r = {"same-pass " + pa: C[0] == M, "next-pass " + sa: B[sa] == M, "next-pass " + pa: B[pa] == M}
        S.p(f"{j['name']} ({j['set']}): M {M:#x}; {pa} same pass {C[0]:#x}, next pass {pa} {B[pa]:#x} {sa} "
            f"{B[sa]:#x}; {r}")
        if j["set"] != "restore":
            out[j["cmd"]].append(r)
        else:
            restored.append(f"{j['name']} {'ok' if C[1] == M else 'DIFFERS'}")
    verdict = []
    for cmd, rs in out.items():
        pa = "pa3" if cmd == 2 else "pa4"
        if not ctl_ok:
            verdict.append(f"cmd {cmd}: cannot tell (instrument control failed: the ctl read pass)")
            continue
        if len(rs) < 2:
            verdict.append(f"cmd {cmd}: cannot tell ({len(rs)} valid)")
            continue
        f = sum(x["same-pass " + pa] for x in rs)
        if f == len(rs):
            verdict.append(f"cmd {cmd}: H-D ({pa} follows in {f}/{len(rs)})")
        elif f == 0:
            verdict.append(f"cmd {cmd}: cannot tell, the alias holds for the PDS words only ({pa} follows 0/{len(rs)})")
        else:
            verdict.append(f"cmd {cmd}: mixed ({f}/{len(rs)})")
    note = S.stage_note()
    rest = f"; restores {restored}" if len(restored) == 2 else (f"; restores {restored} (NOT all verified: sa67/sa68 "
                                                                 f"may still hold the S2 marker)")
    return None, None, ("e2w: " + "; ".join(verdict) + f"; ctl {'ok' if ctl_ok else 'FAILED/void'}" + rest
                        + (f"; {note}" if note else ""))


# ---- E4 / E5 ---------------------------------------------------------------------------------
def score_e4c(S):
    res, ds_all = [], []
    for j in S.table["jobs"]:
        rec = record(S.d, j["name"])
        v = void_of(rec, need_page2=True)
        if v is None:
            try:
                r = ring(rec["page"])
            except ValueError as e:
                v = f"corrupt ring: {e}"
        if v:
            S.p(f"{j['name']}: NODATA ({v})")
            res.append(None)
            continue
        e0 = r[0]
        ds = diffs(e0)
        grid = [on_grid(d) for d in ds]
        ok = len(e0) == L.RUNGS[0] and all(g and k == 1 for g, k in grid) and all(e[0] == 2 for e in e0)
        ds_all += ds
        S.p(f"{j['name']}: {len(e0)} entries, drops {rec['page'][L.DROP]}, diffs {ds} {'held' if ok else 'FAILED'}")
        res.append(ok)
    note = S.stage_note()
    ok = len(res) == 3 and all(x is True for x in res) and not note
    why = None if ok else note or f"control {res}"
    return ok, why, f"e4c: control {'held' if ok else 'FAILED or void'} {res}; median diff {median(ds_all)}"


def timer_sign(rec):
    """+1 when CR_TIMER's exit stamp is after its entry stamp counting up, -1 counting down (rel() of the pair)."""
    pg = rec["page"]
    return 1 if rel(pg[L.HOLD_EXIT], pg[L.HOLD_ENTRY]) >= 0 else -1


def hold_shape(rec):
    """(shape, detail) of the slot-0 stamps around the hold; shape 'cannot tell ...' when the data cannot say."""
    pg = rec["page"]
    E, X = pg[L.HOLD_ENTRY], pg[L.HOLD_EXIT]
    if L.INITFILL in (E, X):
        return "NODATA", "no hold stamps"
    sgn = timer_sign(rec)                  # time runs from the entry stamp to the exit stamp, whatever the counter does

    def r(s, ref):
        return sgn * rel(s, ref)

    e0 = sorted(ring(pg)[0], key=lambda e: r(e[3], E))
    hu = r(X, E)
    pre = [e for e in e0 if r(e[3], E) <= 0]
    inside = [e for e in e0 if 0 < r(e[3], E) < hu]
    post = [e for e in e0 if r(e[3], E) >= hu]
    det = {"hold_units": hu, "timer": "up" if sgn > 0 else "down", "pre": len(pre), "inside": len(inside),
           "post": len(post), "drops": pg[L.DROP], "post_offsets": [r(e[3], X) for e in post][:16]}
    if inside:
        return "OVERLAP", det
    if not pre:
        return "cannot tell (no pass logged before the hold)", det
    phi = pre[-1][3]
    floorH = (r(X, phi)) // T                  # grid ticks phi + kT, k = 1..floorH, fell inside the hold
    nxt = (floorH + 1) * T                     # the first grid tick after the exit, from phi
    det["floorH"] = floorH

    def dev(s):
        return (r(s, phi) + T // 2) % T - T // 2

    det["exit_phase"] = r(X, phi) - floorH * T       # units from the last held grid tick to the exit
    det["to_next_tick"] = nxt - r(X, phi)
    if floorH == 0:
        # S2b fix: no grid tick fell inside the hold; every hypothesis predicts nothing (run 3's LOST was vacuous)
        return "no tick held (nothing to tell)", det
    if nxt - r(X, phi) <= GUARD:
        # S2b fix: one-sided; only the next natural tick landing just after the exit looks like a held one (a grid tick
        # just BEFORE the exit was inside the hold and cannot appear after it: run 3's guard was symmetric)
        return "cannot tell (the next grid tick fell within 50 us after the exit)", det
    # S2b fix: the burst is every entry after the exit and before the next grid tick (less the guard), not a chain of
    # entries spaced under 5000 units
    burst = [e for e in post if r(e[3], phi) < nxt - GUARD]
    # a long drain may run past the next grid tick: entries that continue the chain (under 5000 units apart) stay in
    # the burst, and then one of them may be that natural tick, so the count is q or q - 1
    crossed = False
    for e in post[len(burst):]:
        if burst and r(e[3], burst[-1][3]) < 5000:
            burst.append(e)
            crossed = True
        else:
            break
    after = post[len(burst):]
    grid_ok = all(abs(dev(e[3])) <= 1250 for e in after)
    q = len(burst)
    qmin = q - 1 if crossed else q
    # the ring full with nothing logged after the burst: the burst may go on past the last rung, and the drop
    # counter also counts the natural ticks after it, so q is only a lower bound (review item 5)
    truncated = len(e0) == L.RUNGS[0] and bool(burst) and not after
    det.update({"q": q, "q_min": qmin, "crossed_next_tick": crossed, "q_is_lower_bound": truncated,
                "after": len(after), "after_on_grid": grid_ok,
                # for the pa2 signature: each burst entry's pa2 and its units after the exit, and the first entry's
                # units after the last held grid tick (what a sample latched when the drain began would read)
                "burst": [[e[2], r(e[3], X)] for e in burst],
                "first_after_last_held": (r(burst[0][3], phi) - floorH * T) if burst else None})
    if not post:
        return ("cannot tell (ring full before the exit)" if len(e0) == L.RUNGS[0] else
                "cannot tell (no pass after the hold)"), det
    # post-run fix C8 (POSTRUN-FIX.md): one short of floorH is ALL within one tick and PARTIAL alike (at H = 5 a burst
    # of 4 is what the cap min(H, 4) predicts), so it is ALL-or-PARTIAL, never ALL
    if truncated and qmin >= 2:
        return (f"ALL-or-PARTIAL(>={qmin}, ring full)" if qmin < floorH else "ALL"), det

    def cls(k):
        return ("LOST" if k == 0 else "ONE" if k == 1 else "ALL" if floorH <= k <= floorH + 1
                else f"ALL-or-PARTIAL({k})" if k == floorH - 1 else f"PARTIAL({k})")

    if cls(q) != cls(qmin):
        return f"cannot tell (the drain ran past the next grid tick: {q} or {qmin})", det
    return cls(q) + ("" if grid_ok else "/offgrid"), det


def hold_job(S, j, rec):
    v = void_of(rec, need_page2=True)
    if v is None:
        if rec["page"][L.ECHO] != j["runid"]:
            v = f"the echo {rec['page'][L.ECHO]:#x} is not the run id"
        elif j.get("trigger", "none") != "none" and rec.get("state_at_trigger") != L.STATE_BUSY:
            v = f"state {rec.get('state_at_trigger')} when the trigger went: the hold had not started (no overlap)"
    if v is None:
        lo, hi = (int(x) for x in next(p["value"] for p in S.preds if p["case"] == j["name"]
                                       and p["quantity"] == "hold_units").split(".."))
        try:
            shape, det = hold_shape(rec)
        except ValueError as e:
            return None, f"corrupt ring: {e}", {}
        if shape == "NODATA":
            return None, det, {}
        if not lo <= det["hold_units"] <= hi:
            return None, f"the hold took {det['hold_units']} counts, outside [{lo}, {hi}]: the knob did not act as set", det
        return shape, None, det
    return None, v, {}


def pa2_signature(det, H):
    """True/False/None: the first min(H, 3) burst entries read 0x01061a74, and with H >= 4 the 4th an EVENT_TIMER
    sample whose (400000 - pa2[23:0]) / 16 equals the first entry's time after the last held grid tick within 25
    (fit: S2 run 3); None when there is no burst of the predicted length to read."""
    b = det.get("burst") or []
    need = min(H, L.QUEUE_CAP)
    if len(b) < need or need == 0:
        return None
    if any(p != L.TICKS_QUEUED_PA2 for p, _ in b[:min(H, 3)]):
        return False
    if H >= 4:
        p4 = b[3][0]
        since = (L.EVT_RELOAD - (p4 & L.LOW24)) / 16
        if not (L.evt_ok(p4) and p4 not in (L.TICKS_QUEUED_PA2, L.PA2_CONST)):
            return False
        return abs(since - det["first_after_last_held"]) <= 25
    return True


def window_count(rec, H):
    """(count, predicted, held): slot-0 entries logged plus drops (every pass while the window was open) against
    open_ms * 0.99746 - H + min(H, 4) (fit: S2 run 3): an instrument that does not use the stamps."""
    pg = rec["page"]
    count = len(ring(pg)[0]) + pg[L.DROP]
    want = rec.get("t_close_ms", 0) * 0.99746 - H + min(H, L.QUEUE_CAP)
    return count, round(want, 1), abs(count - want) <= 1.5


def score_hold(S, stage):
    shapes, valid, told, held_n = {}, 0, 0, 0
    sig_n, sig_t, win_n, win_t = 0, 0, 0, 0
    for j in S.table["jobs"]:
        rec = record(S.d, j["name"])
        shape, v, det = hold_job(S, j, rec)
        if v:
            S.p(f"{j['name']}: NODATA ({v})")
            continue
        valid += 1
        H = j.get("held_ticks", det.get("floorH", 0))
        want_q = next((int(p["value"]) for p in S.preds if p["case"] == j["name"] and p["quantity"] == "q"), None)
        alts = {p["model"]: int(p["value"]) for p in S.preds if p["case"] == j["name"] and p["quantity"] == "q_alt"}
        design = det.get("floorH") == H
        if shape.startswith("cannot tell") or shape.startswith("no tick held") or want_q is None:
            held = None
        else:
            told += 1
            q = det.get("q")
            held = (q == want_q) if design else None
            held_n += bool(held)
        q = det.get("q")
        fits = [m for m, k in alts.items() if k == q]
        sig = pa2_signature(det, H) if design else None
        cnt, want_c, win_ok = window_count(rec, H)
        if sig is not None:
            sig_t += 1
            sig_n += bool(sig)
        win_t += 1
        win_n += bool(win_ok)
        S.p(f"{j['name']}: n {j['n']} H {H} (held {det.get('floorH')}{'' if design else ', NOT the design'}) shape {shape}"
            f" q {q} (cap prediction {want_q}: {'held' if held else 'FAILED' if held is False else 'cannot tell'}; "
            f"also fits {fits or 'none of LOST, ONE, ALL'}); pa2 signature "
            f"{'held' if sig else 'FAILED' if sig is False else 'cannot tell'}; window count {cnt} against {want_c} "
            f"{'held' if win_ok else 'FAILED'}; exit {det.get('exit_phase')} units after the last held tick, "
            f"{det.get('to_next_tick')} before the next; burst {det.get('burst')}; passes "
            f"{rec['page'][L.PASS:L.PASS + 4]} busy flags {rec['page'][L.OVL:L.OVL + 4]}")
        shapes.setdefault(H, []).append(shape)
    note = S.stage_note()
    ok = valid == len(S.table["jobs"]) and not note       # the gate is safety and the knob, not the prediction
    why = None if ok else note or f"{len(S.table['jobs']) - valid} job(s) void"
    return ok, why, (f"{stage}: shapes by H {shapes}; cap q = min(H, 4) held in {held_n} of {told} told; pa2 "
                     f"signature {sig_n}/{sig_t}; window count {win_n}/{win_t} ({valid} valid, "
                     f"{len(S.table['jobs'])} jobs); gate {'passes' if ok else 'fails'}")


def prev_shapes(stage, d):
    """The shapes of the stage whose control this one repeats (e5c: e4l), from its kept directory d."""
    out = []
    ref = type("Ref", (), {"preds": load_preds(stage)})
    for j in load_table(stage)["jobs"]:
        shape, v, _ = hold_job(ref, j, record(d, j["name"]))
        if not v:
            out.append(shape)
    return out


def shape_class(s):
    """ONE, ALL, ALL-or-PARTIAL, PARTIAL, LOST, OVERLAP: the shape without its count and its /offgrid flag; None for
    a cannot-tell or void shape."""
    if not s or s.startswith("cannot tell") or s.startswith("no tick held") or s == "NODATA":
        return None
    return re.split(r"[(/]", s)[0]


def control_match(ctl_shapes, ref_shapes):
    """(ok, detail): the E5 control against e4l by shape class.  Cannot-tell shapes are dropped from both sides; ok
    needs at least one told control, at least one told reference, every told control's class among the reference's
    told classes (no told mismatch).  No dependence on order."""
    ref = sorted({c for c in map(shape_class, ref_shapes) if c})
    told = [c for c in map(shape_class, ctl_shapes) if c]
    bad = [c for c in told if c not in ref]
    ok = bool(ref) and bool(told) and not bad
    return ok, {"reference": ref, "control": told, "mismatch": bad}


def score_e5c(S):
    ref = prev_shapes("e4l", S.d.parent / "e4l")
    ctl_shapes, ctl_void, kicks = [], 0, []
    for j in S.table["jobs"]:
        rec = record(S.d, j["name"])
        shape, v, det = hold_job(S, j, rec)
        if v:
            S.p(f"{j['name']}: NODATA ({v})")
            if j["name"].startswith("ctl"):
                ctl_void += 1
            else:
                kicks.append(None)
            continue
        if j["name"].startswith("ctl"):
            S.p(f"{j['name']}: shape {shape} (class {shape_class(shape)}) against e4l {ref}")
            ctl_shapes.append(shape)
            continue
        pg = rec["page"]
        X = pg[L.HOLD_EXIT]
        kick = [e for e in ring(pg)[0] if L.is_kick(e[0], e[1])]      # the kick's words (S2 run 1), not pa1 bit 24
        hold_ms = det["hold_units"] / L.TIMER_HZ * 1000
        overlap = rec.get("t_trigger_ms", 1e9) < hold_ms - 5
        text = (rec.get("kick") or {}).get("text", "")
        mi = (rec.get("kick") or {}).get("ms", 0)
        if not overlap:
            r = "no overlap (does not count)"
        elif not kick:
            r = "LOST" if "no MISCINFO_READY" in text else "LOST? (no kick entry, but the read was answered)"
        elif all(0 <= timer_sign(rec) * rel(e[3], X) <= 5000 for e in kick):
            r = "QUEUED"
        else:
            r = f"OTHER (kick entries at {[timer_sign(rec) * rel(e[3], X) for e in kick]} from the exit)"
        b = det.get("burst") or []
        place = [i for i, (p, off) in enumerate(b) if any(timer_sign(rec) * rel(e[3], X) == off and e[2] == p
                                                           for e in kick)]
        S.p(f"{j['name']}: kick at +{rec.get('t_trigger_ms', 0):.2f} ms, miscinfo {mi:.1f} ms, hold {hold_ms:.1f} ms, "
            f"{len(kick)} kick entries (pa0 0, pa1[23:0] 0x100): {r}; place in the drain {place} of {len(b)} "
            f"(window 2; burst pa2 {[hex(p) for p, _ in b]})")
        kicks.append(r)
    note = S.stage_note()
    cm_ok, cm = control_match(ctl_shapes, ref)
    S.p(f"control against e4l by shape class: {'reproduced' if cm_ok else 'NOT reproduced'} {cm}")
    ok = (cm_ok and ctl_void == 0 and len(ctl_shapes) == 2 and all(k is not None for k in kicks)
          and len(kicks) == 3 and not note)
    why = None if ok else note or f"control {cm} ({ctl_void} void), kicks {kicks}"
    return ok, why, f"e5c: control {'reproduced' if cm_ok else 'NOT reproduced'} {cm}; kick {kicks}"


def tool_us(rec):
    import re
    m = re.search(r"^tri \d+x\d+ #1: (\d+) us", rec.get("tool_out") or "", re.M)
    return int(m.group(1)) if m else None


def job_events(ev):
    """The job's own event entries of (slot, pa0, pa1, pa2, CR_TIMER) entries: not the host's GETMISCINFO kicks (slot 0,
    pa0 0, pa1 low 24 bits 0x100) and not plain ticks (post-run fix C4, POSTRUN-FIX.md)."""
    return [e for e in ev if not L.is_kick(e[1], e[2]) and not L.is_plain_tick(e[1], e[2])]


QUEUE_WINDOW = 5000                 # CR_TIMER units after the exit: the job's events at the exit (QUEUED)


def e5t_reading(jev, sg, X):
    """A completed, waited held job read from its job events: QUEUED only when every one lies in [0, QUEUE_WINDOW]
    units after the exit (two-sided; post-run fix C4)."""
    if not jev:
        return "LOST? (no job event entry, the job completed)"
    t = [sg * rel(e[4], X) for e in jev]
    if all(0 <= x <= QUEUE_WINDOW for x in t):
        return "QUEUED (the job's events at the exit)"
    return f"OTHER (job entries at {t} from the exit)"


def score_e5t(S):
    base, rows, ctl_bad = [], [], []
    for j in S.table["jobs"]:
        rec = record(S.d, j["name"])
        if "nohold" in j["name"]:
            v = void_of(rec, need_page2=True)
            if v:
                S.p(f"{j['name']}: NODATA ({v})")
                ctl_bad.append(f"{j['name']} void")
                continue
            ev = [(k,) + e for k in range(4) for e in ring(rec["page"])[k]]
            jev = job_events(ev)
            us = tool_us(rec)
            if us is not None:
                base.append(us)
            else:
                ctl_bad.append(f"{j['name']} no render time")
            if not jev:
                ctl_bad.append(f"{j['name']} no job event entry")
            S.p(f"{j['name']}: {len(jev)} job event entries (control: >= 1; {len(ev) - len(jev)} host kick entries not "
                f"counted), tri {us} us")
            continue
        shape, v, det = hold_job(S, j, rec)
        stuck = bool(rec) and rec.get("class") == "stuck" and rec.get("state_at_trigger") == L.STATE_BUSY \
            and isinstance(rec.get("page"), list) and len(rec["page"]) == L.PAGE_DWORDS
        if v and not stuck:
            S.p(f"{j['name']}: NODATA ({v})")
            rows.append(None)
            continue
        pg = rec["page"]
        X = pg[L.HOLD_EXIT]
        sg = timer_sign(rec) if X != L.INITFILL and pg[L.HOLD_ENTRY] != L.INITFILL else 1
        ev = [(k,) + e for k in range(4) for e in ring(pg)[k]]
        jev = job_events(ev)
        us = tool_us(rec)
        waited = us is not None and base and us > median(base) + 5000
        if stuck:
            r = "LOST (the job did not complete while held; page read before the release)"
        elif not waited:
            r = "no overlap shown (the job's time is not longer than without the hold): does not count"
        else:
            r = e5t_reading(jev, sg, X)
        S.p(f"{j['name']}: tri {us} us (no-hold median {median(base)}), {len(jev)} job entries ({len(ev) - len(jev)} "
            f"host kick entries not counted): {r}")
        rows.append(r)
    note = S.stage_note() if not any(r and r.startswith("LOST (") for r in rows) else None
    if ctl_bad:
        return None, None, (f"e5t: cannot tell (instrument control failed: {ctl_bad}); held triangle as read {rows}"
                            + (f"; {note}" if note else ""))
    return None, None, f"e5t: control tri times {base}; held triangle {rows}" + (f"; {note}" if note else "")


SCORERS = {"e4c": score_e4c, "e4m": lambda S: score_hold(S, "e4m"), "e4l": lambda S: score_hold(S, "e4l"),
           "e5c": score_e5c, "e5t": score_e5t}     # S2b; the E1 and E2 scorers stay in the file, unused


def env_problem(stage, d):
    """Why the stage's env.json does not close the hash chain to the Mac's frozen files (None: it does): the table
    and the blob the laptop ran must be the ones here, and env.json must be of the stage's last run."""
    try:
        env = json.loads((pathlib.Path(d) / "env.json").read_text())
        st = json.loads((pathlib.Path(d) / "stage.json").read_text())
    except (OSError, ValueError):
        return "no env.json or stage.json"
    blob = load_table(stage)["blob"]
    want_t = hashlib.sha256((S2 / "tables" / f"{stage}.json").read_bytes()).hexdigest()
    want_b = hashlib.sha256((S2 / "bins" / f"{blob}.blob").read_bytes()).hexdigest()
    if env.get("table_sha256") != want_t:
        return f"env.json table sha256 {str(env.get('table_sha256'))[:12]} is not tables/{stage}.json's {want_t[:12]}"
    if env.get("blob_sha256") != want_b:
        return f"env.json blob sha256 {str(env.get('blob_sha256'))[:12]} is not bins/{blob}.blob's {want_b[:12]}"
    if env.get("run") != st.get("run"):
        return f"env.json is of run {env.get('run')}, stage.json of {st.get('run')}"
    return None


def score(stage, d, **kw):
    S = Stage(stage, d)
    ok, why, summ = SCORERS[stage](S)
    if not any(r for r in (record(d, j["name"]) for j in S.table["jobs"])):
        ok, why, summ = False, "no job record at all", f"{stage}: cannot tell (no data)"
    else:
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
    r = subprocess.run([str(S2 / "run" / "freeze_s2.sh"), "verify"], capture_output=True, text=True)
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
        # the run id ties the gate to this run of the stage: the laptop runner compares it with its stage.json
        line = f"GATE {stage} {'OPEN' if ok else 'CLOSED'} run={run} {why or ''}".strip()
        gates = pathlib.Path(a[a.index("--gates") + 1]) if "--gates" in a else S2 / "gates"
        gates.mkdir(exist_ok=True)
        (gates / f"{stage}.gate").write_text(line + "\n")
        print(line)
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
