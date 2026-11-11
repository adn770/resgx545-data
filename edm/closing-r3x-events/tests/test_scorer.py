#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_scorer.py: the R3x-events scorer (score/score_r3.py) on past-run fixtures and synthetic worlds.  Offline; standard library only.

Fixtures (all read-only, from the data and scratch trees): E537's stop dumps (regs and status: CCB read 3 after write 2, HostCtl dword
14 = 0xad002600), E793's two stops (closing2/r3-events/out/b: read = write, dword 14 = 0), R3's real A0 reader record and B0 ring page,
S2b's e5c hold page.  Synthetic worlds: one per hypothesis, each built from what the hypothesis predicts, so that every hypothesis WINS
(every row of its model held) in its own world and LOSES (a row of its model FAILED) in the others': stage h H-NOTENDED / H-REARM, stage e
H-EXIT / H-BODY / H-TICKONLY, stage d H-CCB / H-HANDLER / H-ONCE; and every void and cannot-tell state, the stop bookkeeping, the gates.

    ../../closing/pixel-faults/.venv/bin/python tests/test_scorer.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R3 / "gen"))
sys.path.insert(0, str(R3 / "score"))
os.environ["R3_NO_FREEZE_CHECK"] = "1"
import r3layout as L  # noqa: E402
import score_r3 as S  # noqa: E402

DATA = pathlib.Path.home() / "src/resgx545-data/firmware-tasks"
C2 = R3.parent.parent / "closing2"
R3EV = C2 / "r3-events/out"
S2B = R3.parent.parent / "closing/s2b/out"
FAIL = []
RUN = "test-run"
STAMP0 = 0x10000000
K0 = 2
E537 = L.E537
SKIPS = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def fixture(path, what):
    if not path.exists():
        SKIPS.append(what)
        print(f"skip (fixture absent): {what}")
        return False
    return True


# ---- samples and stop signatures -------------------------------------------------------------------------------------------
def sample(kind="busy", t=0.1, rmw=0, hc14=0, w=K0, hc12=0x9DB, d=None, timer_off=0, serv=0x9E0):
    """One signature sample.  kind busy: E537's registers (clk 0xccfa0, USE0_SERV_EVENT 0x9e0, EVENT_STATUS 0x20000000); idle: the
    running EDM (clk 0x20, EMPTY set, EVENT_STATUS 0x20000000 as in 234 of 234 kept reads); pending: idle with events queued."""
    regs = {"0x8": 0x000CCFA0, "0xb14": serv, "0xacc": 0x01038EC3 - timer_off, "0x12c": 0x20000000, "0xb20": 0x10000, "0x118": 0x400,
            "0xc04": 0, "0xc08": 0}
    if kind == "idle":
        regs.update({"0x8": 0x20, "0xb14": 0x10000 | (hc12 & 0xFFFF)})
    elif kind == "pending":
        regs.update({"0x8": 0x20})
    elif kind == "empty":
        regs.update({"0x8": 0x20, "0xb14": 0x10000, "0x12c": 0})
    sm = {"t": t, "regs": regs, "hc12": hc12, "hc14": hc14, "ccb": [w, (w + rmw) % 256], "pass": None}
    if d is not None:
        sm["pass"] = [hc12 + d, hc12 + d]
    return sm


def sig_pair(kind="busy", rmw=0, hc14=0, w=K0, d=None, serv=0x9E0, phase="after-reader"):
    s1 = sample(kind, 0.1, rmw, hc14, w, d=d, serv=serv)
    s2 = sample(kind, 0.13, rmw, hc14, w, d=d, timer_off=0x5000, serv=serv)
    return {"phase": phase, "samples": [s1, s2]}


def e537_samples():
    text = (DATA / "p1130-b2-variants/tailpair-stop1-regs.txt").read_text()
    r, hc, cc = L.parse_regs(text)
    s1 = {"regs": {hex(k): v for k, v in r.items()}, "hc12": hc.get(12), "hc14": hc.get(14), "ccb": cc}
    r2 = dict(r)
    r2[L.REG_EVENT_TIMER] = r[L.REG_EVENT_TIMER] - 0x4000
    s2 = {"regs": {hex(k): v for k, v in r2.items()}, "hc12": hc.get(12), "hc14": hc.get(14), "ccb": cc}
    return s1, s2, r


def test_signature_and_marks():
    s1, s2, r = e537_samples()
    check(r[L.REG_CLKSTAT] == 0x000CCFA0 and r[L.REG_SERV_EVENT] == 0x9E0 and r[L.REG_EVENT_STATUS] == 0x20000000
          and r[L.REG_EVENT_TIMER] == 0x01038EC3, "the E537 dump parses: 0x0008 0xccfa0, 0x0b14 0x9e0, 0x012c 0x20000000, 0x0acc 0x01038ec3")
    sg = S.score_sig([s1, s2])
    check(sg["class"] == "busy" and sg["matches_e537"] and all(sg["elements"].values()) and sg["hostctl12_moved"] is False,
          f"E537's own dump (a second sample with the timer advanced) scores busy and matches E537 ({sg['class']})")
    check(all(sg["exact_e537_values"].values()), "the exact E537 values (clock status, USE0_SERV_EVENT) are recognised")
    check("event_status_0x20000000" not in sg["elements"] and sg["recorded"]["event_status_0x20000000"] is True,
          "0x012c is recorded, not part of the match (0b)")

    def mod(kw, base=(s1, s2)):
        a, b = json.loads(json.dumps(base[0])), json.loads(json.dumps(base[1]))
        for sm in (a, b):
            for k, v in kw.items():
                sm["regs"][hex(k)] = v
        return S.score_sig([a, b])
    check(mod({L.REG_EVENT_STATUS: 0})["matches_e537"] is True and mod({L.REG_EVENT_STATUS: 0x400})["matches_e537"] is True,
          "0b: a busy stop with CR_EVENT_STATUS 0 (or anything) still matches E537's signature")
    check(S.score_sig([s1])["class"] == "unreadable", "one sample only: unreadable (the timer cannot be seen counting)")
    bad = json.loads(json.dumps(s2))
    del bad["regs"][hex(L.REG_SERV_EVENT)]
    check(S.score_sig([s1, bad])["class"] == "unreadable", "a missing signature register: unreadable")
    ip = mod({L.REG_CLKSTAT: 0x20})
    check(ip["class"] == "idle-pending" and not ip["matches_e537"] and not ip["elements"]["busy"], "clock idle, USE0_SERV_EVENT bit 16 clear: idle-pending")
    ie = mod({L.REG_CLKSTAT: 0x20, L.REG_SERV_EVENT: 0x10000})
    check(ie["class"] == "idle-empty" and not ie["matches_e537"], "clock idle, EMPTY set: idle-empty")
    check(S.score_sig([s1, json.loads(json.dumps(s1))])["elements"]["timer_counting"] is False, "a timer that did not move is not 'counting'")
    check("matches E537" in S.sig_line(sg) and "unreadable" in S.sig_line(S.score_sig([])) and "recorded" in S.sig_line(sg), "the signature line is readable")
    # marks: E537's dump
    mk = S.marks_from_samples([s1, s2])
    check(mk == {"ccb": [2, 3], "rmw": 1, "hc14": 0xAD002600}, f"E537's dump: CCB write 2 read 3 (read - write +1), HostCtl dword 14 0xad002600 ({mk})")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(DATA / "p1130-b2-variants/tailpair-stop1-regs.txt", pathlib.Path(tmp) / "stop-d3-regs.txt")
        check(S.marks_from_dump(tmp, "d3") == mk, "the marks read from E537's regs dump file are the same")
    st = DATA / "p1130-b2-variants/tailpair-stop1-status.txt"
    r_, hc_, cc_, sent = L.parse_status(st.read_text())
    check(cc_ == [2, 3] and hc_[14] == 0xAD002600 and hc_[12] == 0x9DB and r_[8] == 0xCCFA0 and sent == 196,
          "E537's status dump parses too (hostctl rows are 8 dwords, little endian; ccbctl [2, 3]; ccb_sent 196)")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(st, pathlib.Path(tmp) / "stop-d3-status.txt")
        check(S.marks_from_dump(tmp, "d3") == mk, "...and so are the marks from the status dump file (no regs file)")
    # E793's two stops: read = write, dword 14 = 0, the same busy signature
    for nm in ("stop-b1", "stop-b1-r2"):
        f = R3EV / f"b/{nm}-regs.txt"
        if fixture(f, f"E793 {nm}"):
            r, hc, cc = L.parse_regs(f.read_text())
            a = {"regs": {hex(k): v for k, v in r.items()}, "hc12": hc.get(12), "hc14": hc.get(14), "ccb": cc}
            r2 = dict(r)
            r2[L.REG_EVENT_TIMER] -= 0x3000
            b = {"regs": {hex(k): v for k, v in r2.items()}, "hc12": hc.get(12), "hc14": hc.get(14), "ccb": cc}
            m2 = S.marks_from_samples([a, b])
            sg2 = S.score_sig([a, b])
            check(m2 == {"ccb": [2, 2], "rmw": 0, "hc14": 0} and sg2["class"] == "busy" and sg2["matches_e537"],
                  f"E793 {nm}: busy, matches the signature, read = write, dword 14 = 0 ({m2})")
    check(L.signed8(3 - 2) == 1 and L.signed8(1 - 2) == -1 and L.signed8((0 - 255) & 0xFF) == 1 and L.signed8(0) == 0, "signed8: read - write as -128..127")


def test_d_instrument():
    tri = [[100 + i + 7, 100 + i, 100 + i + 7] for i in range(20)]
    check(S.d_vals(tri) == [7] * 20 and S.d_mode(S.d_vals(tri)) == (7, 1.0), "D = page pass - dword 12; one modal value")
    tri2 = tri + [[50, 40, 51], [None, 3, None]]
    check(len(S.d_vals(tri2)) == 20, "a triple whose page reads differ, or with a missing value, is dropped")
    mix = [[110, 100, 110]] * 5 + [[111, 100, 111]] * 3
    check(S.d_mode(S.d_vals(mix)) == (10, 5 / 8), "the mode of a mix of D0 and D0 + 1")
    check(S.interval_near((-52, -48), -50, 8) is True and S.interval_near((-70, -66), -50, 8) is False and S.interval_near((-60, -45), -50, 8) is None
          and S.interval_near(None, -50, 8) is None, "interval_near: inside, outside, straddling, unknown")
    check(S.d_vals([[0, 0xFFFFFFFF, 0]]) == [1], "D wraps as a signed 32-bit value")


# ---- shared builders --------------------------------------------------------------------------------------------------------
def write_stage(tmp, stage, recs, exit_code=0, why=""):
    d = pathlib.Path(tmp) / stage
    d.mkdir(parents=True, exist_ok=True)
    for n, r in recs.items():
        (d / f"{n}.json").write_text(json.dumps(r))
    (d / "stage.json").write_text(json.dumps({"stage": stage, "run": RUN, "exit": exit_code, "why": why, "jobs_run": list(recs)}))
    return d


def skipped_rec(j, why="row stopped"):
    return {"name": j["name"], "set": j["set"], "op": j["op"], "row": j["row"], "job": j, "class": "skipped", "rc": None, "note": why, "run": RUN}


def txt(st):
    return "\n".join(st.lines)


def rows_of(st, model):
    return [r for r in st.t.rows if r[2] == model or r[2].startswith(model + " ")]


def verdict(st, model):
    """'wins': every scored row of the model held; 'loses': a row FAILED; 'none': no row; 'open': only cannot-tell rows."""
    rs = rows_of(st, model)
    if not rs:
        return "none"
    if any(r[4] is False for r in rs):
        return "loses"
    if all(r[4] is True for r in rs):
        return "wins"
    return "open"


def d0_triples(d0=7, n=20, h0=0x9D0):
    return [[h0 + i + d0, h0 + i, h0 + i + d0] for i in range(n)]


def ring_page(entries, acted=0, passes=40, drops=0, hold=None, count=0):
    """A results page with slot 0's rungs: entries = [(flag, pa0, pa1, pa2, stamp)]."""
    pg = [0] * L.PAGE_DWORDS
    pg[0] = L.MAGIC
    for j, (f, a, b, c, s) in enumerate(entries[:L.RUNGS[0]]):
        o = L.RING_BASE[0] + L.RUNG * j
        pg[o:o + 5] = [f, a, b, c, s]
    pg[L.ACTED] = acted
    pg[L.COUNT] = count
    pg[L.DROP] = drops
    if hold:
        pg[L.HOLD_ENTRY], pg[L.HOLD_EXIT] = hold
    return pg


def tick(i, flag=1, K=K0, base=STAMP0 + 20000, extra=0):
    return (flag, 2, K << 24, 0x01061A70, base + 25000 * i + (3 if i % 2 else -2) + extra)


# ---- stage h -----------------------------------------------------------------------------------------------------------------
def h_rec(j, world):
    """world NOTENDED: a held EDM looks exactly like a task still running (E537's registers, the count frozen, D0 + 1);
    world REARM: the signature inside the hold is an idle EDM's."""
    hold = j["hold"]
    pg = ring_page([tick(i) for i in range(6)])
    n = j["n"]
    if hold:
        t_entry = STAMP0 + 30000
        pg[L.HOLD_ENTRY], pg[L.HOLD_EXIT] = t_entry, t_entry + int(L.hold_units_of(n))
    ins = []
    for k, ms in enumerate(j["sig_ms"]):
        if not hold:
            sp = sig_pair("idle", d=7)
            st = [0, 0]
        elif world == "NOTENDED":
            sp = sig_pair("busy", d=8)
            st = [L.STATE_BUSY, L.STATE_BUSY]
        else:
            sp = sig_pair("idle", d=7)
            st = [L.STATE_BUSY, L.STATE_BUSY]
        ins.append({"ms": ms, "t_ms": ms + 0.4, "state": st, "samples": sp["samples"]})
    return {"name": j["name"], "set": j["set"], "op": "holdsig", "row": j["row"], "job": j, "class": "ok", "rc": 0, "note": "", "run": RUN,
            "page": pg, "page2": list(pg), "window_stamp": STAMP0, "ticks": [{"ok": True}], "d0": d0_triples(7), "inside": ins}


def h_world(tmp, world="NOTENDED", mods=None):
    t = S.load_table("h")
    recs = {j["name"]: h_rec(j, world) for j in t["jobs"]}
    for n, f in (mods or {}).items():
        recs[n] = f(t, recs[n]) if callable(f) else f
    return t, write_stage(tmp, "h", recs)


def test_stage_h():
    with tempfile.TemporaryDirectory() as tmp:
        t, d = h_world(tmp, "NOTENDED")
        st, summ = S.score("h", d)
        check("h: H0 held" in summ and "H1 reads H-NOTENDED (3 of 3 jobs look exactly like a running task)" in summ and "D offset [1] one value in 3" in summ,
              f"H-NOTENDED world: H0 held, H1 reads H-NOTENDED, D offset 1 in 3 of 3 ({summ[:230]})")
        check(verdict(st, "H-NOTENDED") == "wins" and verdict(st, "H-REARM") == "loses", "H-NOTENDED world: H-NOTENDED wins, H-REARM loses")
        ctl = [r for r in st.t.rows if r[3] == "control"]
        check(ctl and all(r[4] is True for r in ctl) and {r[0] for r in ctl} >= {"h0", "h1"}, "controls (H0 idle and modal D0, H1's hold band) held")
        check({r[3] for r in st.t.rows} >= {"control", "held out", "replicate"}, "control, held-out and replicate rows tallied apart")
    with tempfile.TemporaryDirectory() as tmp:
        t, d = h_world(tmp, "REARM")
        st, summ = S.score("h", d)
        check("H1 reads H-REARM" in summ and verdict(st, "H-REARM") == "wins" and verdict(st, "H-NOTENDED") == "loses",
              "H-REARM world (an idle signature inside the hold): H-REARM wins, H-NOTENDED loses")
        check("differ in" in txt(st) and "busy" in txt(st), "the differing elements are named")
    # one element differs in one job: mixed
    with tempfile.TemporaryDirectory() as tmp:
        def one_diff(t, r):
            r["inside"][1]["samples"] = sig_pair("busy", d=8, serv=0x9E0)["samples"]
            r["inside"][1]["samples"][1]["regs"]["0xb14"] = 0x9E1        # the count moved: not frozen
            return r
        t, d = h_world(tmp, "NOTENDED", {"h1-r2": one_diff})
        st, summ = S.score("h", d)
        check("H1 mixed" in summ, "a count that moved in one job: H1 mixed, not H-NOTENDED")
    # D = D0 + 2 is neither value
    with tempfile.TemporaryDirectory() as tmp:
        def d2(t, r):
            for i in r["inside"]:
                i["samples"] = sig_pair("busy", d=9)["samples"]
            return r
        t, d = h_world(tmp, "NOTENDED", {"h1": d2})
        st, summ = S.score("h", d)
        rows = {(r[0], r[1]): r[4] for r in st.t.rows if r[2] == "H-NOTENDED"}
        check(rows[("h1", "d_vs_d0")] is False and rows[("h1", "elements")] is True and rows[("h1-r2", "d_vs_d0")] is True,
              "D0 + 2 in the hold: the d_vs_d0 row FAILS, the elements row holds (separate rows)")
    # controls that can fail
    with tempfile.TemporaryDirectory() as tmp:
        def busy_h0(t, r):
            for i in r["inside"]:
                i["samples"] = sig_pair("busy", d=7)["samples"]
            return r
        t, d = h_world(tmp, "NOTENDED", {"h0": busy_h0})
        st, summ = S.score("h", d)
        rows = {(r[0], r[1]): r[4] for r in st.t.rows if r[2].startswith("control")}
        check(rows[("h0", "idle")] is False and "H0 DIFFERS" in summ, "H0 reads busy: the idle control FAILS, 'H0 DIFFERS'")
        def noisy(t, r):
            r["d0"] = [[a + (i % 5), h, b + (i % 5)] for i, (a, h, b) in enumerate(r["d0"])]
            return r
        t, d = h_world(tmp, "NOTENDED", {"h0-r2": noisy})
        st, summ = S.score("h", d)
        rows = {(r[0], r[1]): r[4] for r in st.t.rows if r[2].startswith("control")}
        check(rows[("h0-r2", "d0_modal")] is False, "a D0 spread over 5 values is not 'one modal value': the control FAILS")
    with tempfile.TemporaryDirectory() as tmp:
        def band(t, r):
            r["page"][L.HOLD_EXIT] += 5000
            r["page2"] = list(r["page"])
            return r
        t, d = h_world(tmp, "NOTENDED", {"h1": band})
        st, summ = S.score("h", d)
        rows = {(r[0], r[1]): r[4] for r in st.t.rows if r[1] == "hold_band"}
        check(rows[("h1", "hold_band")] is False, "a hold outside its knob band: the hold_band control FAILS")
    # cannot tell: a sample fell outside the hold
    with tempfile.TemporaryDirectory() as tmp:
        def out(t, r):
            r["inside"][1]["state"] = [L.STATE_BUSY, L.STATE_DONE]
            return r
        t, d = h_world(tmp, "NOTENDED", {"h1": out})
        st, summ = S.score("h", d)
        rows = [r for r in st.t.rows if r[0] == "h1" and r[1] in ("elements", "d_vs_d0")]
        check(rows and all(r[4] is None for r in rows) and "fell outside the hold" in txt(st), "a signature that left the hold (STATE done): cannot tell, never a pass")
    # void: no record, a class that is not a result, a stale record
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("h")
        recs = {j["name"]: h_rec(j, "NOTENDED") for j in t["jobs"]}
        recs["h0"]["class"] = "unhealthy"
        d = write_stage(tmp, "h", recs)
        (d / "h1-r3.json").write_text(json.dumps(dict(recs["h1-r3"], run="an older run")))
        st, summ = S.score("h", d)
        check("h0: NODATA (class unhealthy)" in txt(st), "void: a class that is not a result")
        # a stop in stage h
    with tempfile.TemporaryDirectory() as tmp:
        def stop(t, r):
            r.update({"class": "stop", "sig": sig_pair("busy", rmw=0, hc14=0, d=9), "p3": {"answered": False, "ms": 500.0}})
            return r
        t, d = h_world(tmp, "NOTENDED", {"h0": stop})
        st, summ = S.score("h", d)
        check("h0: class stop" in txt(st) and "stops 1 ['h0']" in summ, "a stop in stage h is read and named (a surprise)")


# ---- stages c and d -----------------------------------------------------------------------------------------------------------
def wr_record(j, K, written, sa_before=(0, 2), readback=None, cmd=None):
    cmd = j["cmd"] if cmd is None else cmd
    w = [2, K << 24, 0x01061A70, sa_before[0], sa_before[1], K << 24, written & 0xFFFFFFFF, (written if readback is None else readback) & 0xFFFFFFFF,
         0, 0, 0, 0, 0, 0, 0, 1]
    if cmd == L.CMD_E537:
        e = E537
        w[9:13] = [e["sa63"], e["sa63"], e["sa64"], e["sa64"]]
    return w


def a_rec(j, cls="ok", K=K0, rd=None, tick_ok=True, reader_ran=True, writer_done=True, sig=None, wr_over=None, d12=None, p3=None, marks=None,
          passes=None):
    """A stage c / d record: the writer (cmd 10, 11, 12), the reader at the next event, the brackets, D."""
    row, cmd = j["row"], j["cmd"]
    word = L.word65(j.get("w65"), K)
    if cmd == L.CMD_RUN64:
        word = 0
    wr = wr_record(j, K, 0 if word is None else word) if cmd else None
    if wr and wr_over:
        wr = wr_over(wr)
    base = dict(pclink=0x98, p0=1, p1=1, p2=0, p3=0, r20=0, r21=0x3000, i0=0xB5000020, i1=0xB5000021, sa64=2, sa65=K << 24, sa63=0,
                pa0=2, pa1=K << 24, pa2=0x01061A70, passes=5)
    if row == "C5":
        base["pclink"], base["p1"] = 6, 0                    # E792 / A4: the other path
    base.update(rd or {})
    rdl = [base[k] for k in ("pclink", "p0", "p1", "p2", "p3", "r20", "r21", "i0", "i1", "sa64", "sa65", "sa63", "pa0", "pa1", "pa2", "passes")]
    np_ = j.get("npass", 0)
    h0 = 0x9D0
    P = 6 if passes is None else passes
    if cmd == L.CMD_RUN64:
        P = np_ + 12 if passes is None else passes
        d12v = -np_ if d12 is None else d12
    else:
        d12v = 0 if d12 is None else d12
    rec = {"name": j["name"], "set": j["set"], "op": "alias2", "row": row, "job": j, "class": cls, "rc": 0, "note": "", "run": RUN,
           "ccbctl_pre": [K, K], "w65_word": word if cmd in (L.CMD_WORD65, L.CMD_E537) else None,
           "writer": {"issued": bool(cmd), "done": writer_done, "ms": 0.4, "wr": wr if (cmd and writer_done) else None},
           "reader": {"ran": reader_ran, "ms": 1.5, "rd": rdl if reader_ran else None},
           "bracket": {"before": [100, h0, 100], "after": [100 + P, h0 + P + d12v, 100 + P]}, "ticks": [{"ok": tick_ok}],
           "d0": d0_triples(7), "d_post": d0_triples(7 + (np_ if cmd == L.CMD_RUN64 else 0)),
           "marks_post": marks or {"ccb": [K, K], "hc14": 0, "hc12": h0}}
    if sig is not None:
        rec["sig"] = sig
    if p3 is not None:
        rec["p3"] = p3
    return rec


def stop_over(sig=None, p3=None, **kw):
    def f(t, r):
        r.update({"class": "stop", "sig": sig or sig_pair("busy"), "reader": {"ran": False, "ms": None, "rd": None}, "p3": p3 or {"answered": False, "ms": 500.0}})
        r.pop("marks_post", None)
        r.update(kw)
        return r
    return f


def c_world(tmp, mods=None, stage="c", exit_code=0):
    t = S.load_table(stage)
    recs = {j["name"]: a_rec(j) for j in t["jobs"]}
    for n, f in (mods or {}).items():
        recs[n] = f(t, recs[n]) if callable(f) else f
    return t, write_stage(tmp, stage, recs, exit_code=exit_code)


def test_stage_c():
    with tempfile.TemporaryDirectory() as tmp:
        t, d = c_world(tmp)
        st, summ = S.score("c", d)
        check("c: C0 held" in summ and "C1 kept 3 of 3" in summ and "C5 kept 2 of 2" in summ and "stops 0" in summ, f"default world: C0 held, every row kept ({summ[:150]})")
        fit = [r for r in st.t.rows if r[3] == "fit"]
        ho = [r for r in st.t.rows if r[3] == "held out"]
        check(fit and all(r[4] for r in fit) and {r[0] for r in fit} == {"c0", "c0-r2"}, "fit rows are C0's only (E791 A0), all held")
        check(ho and not any(r[0].startswith("c0") for r in ho) and all(r[4] for r in ho), "held-out rows are C1-C5, kept apart from the fit rows, all held")
        c1 = {(r[1], r[2]): r[4] for r in st.t.rows if r[0] == "c1"}
        check(c1[("read_minus_write", NOHANDLER)] is True and c1[("dword14", NOHANDLER)] is True, "C1 kept: read = write and dword 14 = 0 (the mark rows of a kept job)")
        c5 = {(r[1]): r[4] for r in st.t.rows if r[0] == "c5"}
        check(c5["pclink"] is True and c5["d12_delta"] is True and c5["d_shift"] is True, "C5: pclink 6, dword 12 - passes = -50, D shift +50: rows hold")
    # C5: the closed task did not take the other path / did count the ticks
    with tempfile.TemporaryDirectory() as tmp:
        t, d = c_world(tmp, {"c5": lambda t, r: a_rec(t["jobs"][11], rd={"pclink": 0x98, "p1": 1}, d12=-10)})
        st, summ = S.score("c", d)
        c5 = {(r[1]): r[4] for r in st.t.rows if r[0] == "c5"}
        check(c5["pclink"] is False and c5["d12_delta"] is False, "C5 with pclink 0x98 and 40 ticks counted: the pclink and d12_delta rows FAIL")
    # a stop at C3: the first stop is read with its marks and P3
    with tempfile.TemporaryDirectory() as tmp:
        mods = {"c3": stop_over(sig=sig_pair("busy", rmw=0, hc14=0, d=9), p3={"answered": False, "ms": 501.0, "ring_new_entries": None})}
        t, d = c_world(tmp, mods)
        st, summ = S.score("c", d)
        txt_ = txt(st)
        check("c3: class stop" in txt_ and "signature busy, matches E537" in txt_ and "read - write +0" in txt_ and "P3 NOT answered" in txt_ and "D0 7, D at the stop 9 (+2)" in txt_,
              "a stop in C3: the signature, the marks, P3 and D against D0 are all in the line")
        kept = {r[2]: r[4] for r in st.t.rows if r[0] == "c3" and r[1] == "kept"}
        check(kept == {NOHANDLER: False}, "C3 stop: the kept row of the no-handler model FAILS")
        p3 = {r[2]: r[4] for r in st.t.rows if r[0] == "c3" and r[1] == "p3_answered"}
        check(p3 == {"H-NOTENDED": True, "H-REARM": False}, "P3 not answered: H-NOTENDED's row holds, H-REARM's fails")
        check("P3 answered in 0 of 1 stops" in summ and "stops 1 ['c3']" in summ, "the SUMMARY counts P3 and the stop")
        r2 = [r for r in st.t.rows if r[0] == "c3-r2"]
        check("c3-r2: class ok" in txt_, "(the scorer reads c3-r2 as recorded; the runner skips a stopped row's replicates)")
    # a skipped replicate
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("c")
        j2 = [j for j in t["jobs"] if j["name"] == "c3-r2"][0]
        t, d = c_world(tmp, {"c3": stop_over(), "c3-r2": skipped_rec(j2)})
        st, summ = S.score("c", d)
        check("c3-r2: not run" in txt(st), "a replicate skipped by the stop rule is 'not run', not NODATA")
    # P3 answered (H-REARM)
    with tempfile.TemporaryDirectory() as tmp:
        t, d = c_world(tmp, {"c2": stop_over(p3={"answered": True, "ms": 12.0})})
        st, summ = S.score("c", d)
        p3 = {r[2]: r[4] for r in st.t.rows if r[0] == "c2" and r[1] == "p3_answered"}
        check(p3 == {"H-NOTENDED": False, "H-REARM": True}, "P3 answered: H-REARM's row holds, H-NOTENDED's fails")
    # void and cannot-tell states
    with tempfile.TemporaryDirectory() as tmp:
        t, d = c_world(tmp, {"c1": lambda t, r: a_rec(t["jobs"][2], writer_done=False),
                             "c1-r2": lambda t, r: a_rec(t["jobs"][3], wr_over=lambda w: w[:7] + [w[7] ^ 1] + w[8:]),
                             "c2": lambda t, r: a_rec(t["jobs"][5], wr_over=lambda w: w[:5] + [0x07000000] + w[6:]),
                             "c3": lambda t, r: dict(r, **{"class": "unhealthy"}),
                             "c4": lambda t, r: a_rec(t["jobs"][9], wr_over=lambda w: w[:6] + [0x1234] + [0x1234] + w[8:]),
                             "c5": lambda t, r: a_rec(t["jobs"][11], passes=20)})
        st, summ = S.score("c", d)
        txt_ = txt(st)
        check("c1: NODATA (the writer's flag was not set" in txt_, "void: the writer's flag was not set")
        check("c1-r2: NODATA (the read-back" in txt_, "void: the read-back is not what the writer wrote")
        check("c2: NODATA (the task's own record of sa65 at entry has count byte 0x7" in txt_, "void: the entry's count byte is not K")
        check("c3: NODATA (class unhealthy)" in txt_, "void: a class that is not a result")
        check("c4: NODATA (the word written (0x1234) is not the row's" in txt_, "void: the word written is not the row's")
        check("c5: NODATA (C5's own pass counter advanced 20, not the 50 passes" in txt_, "void: C5's own pass counter did not advance 50")
        bad = [r for r in st.t.rows if r[0] in ("c1", "c2") and r[4] is not None]
        check(not bad, "void rows count as cannot tell, never held or failed")
    with tempfile.TemporaryDirectory() as tmp:
        t, d = c_world(tmp, {"c2": lambda t, r: dict(r, **{"class": "noreader", "reader": {"ran": False, "ms": None, "rd": None}})})
        st, summ = S.score("c", d)
        rows = [r for r in st.t.rows if r[0] == "c2" and r[1] == "kept"]
        check(rows and all(r[4] is None for r in rows) and "the reader did not run: cannot tell" in txt(st), "reader not run but tick kept: cannot tell")
    # C0 differs: later pclink claims cannot tell
    with tempfile.TemporaryDirectory() as tmp:
        t, d = c_world(tmp, {"c0": lambda t, r: a_rec(t["jobs"][0], rd={"pclink": 6})})
        st, summ = S.score("c", d)
        c1 = [r for r in st.t.rows if r[0] == "c1" and r[1] == "next_pclink"]
        check("C0 DIFFERS" in summ and c1 and all(r[4] is None for r in c1), "C0 differs from E791's A0: the rows that lean on it cannot tell")
    # the K byte is the count of the job (after a reset the count is 2 again; a bumped count K = 5 is read as K)
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("c")
        recs = {j["name"]: a_rec(j, K=5) for j in t["jobs"]}
        d = write_stage(tmp, "c", recs)
        st, summ = S.score("c", d)
        check("C0 held" in summ and "c1: class ok" in txt(st) and not [r for r in st.t.rows if r[4] is False], "K = 5: sa65 K << 24 and the words follow K, nothing fails")
    # stage exit
    with tempfile.TemporaryDirectory() as tmp:
        t, d = c_world(tmp, {"c3": stop_over(), "c3-r2": skipped_rec(S.load_table("c")["jobs"][8]), "c4": stop_over()}, exit_code=8,
                       )
        st, summ = S.score("c", d)
        check("stage exit 8" in summ and "stops 2" in summ, "a second stop: stage exit 8 is in the SUMMARY")


NOHANDLER = S.NOHANDLER


# ---- fixtures: real A0, real B0 ---------------------------------------------------------------------------------------------
def test_real_fixtures():
    f = R3EV / "a/a0.json"
    if fixture(f, "R3 a0.json"):
        real = json.loads(f.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            t = S.load_table("c")
            recs = {j["name"]: a_rec(j) for j in t["jobs"]}
            j0 = t["jobs"][0]
            r = dict(real, name="c0", job=j0, row="C0", op="alias2", set="fit", run=RUN)
            r["d0"], r["d_post"] = d0_triples(7), d0_triples(7)
            r["marks_post"] = {"ccb": real["ccbctl_pre"], "hc14": 0, "hc12": 0x9D0}
            recs["c0"] = r
            d = write_stage(tmp, "c", recs)
            st, summ = S.score("c", d)
            c0 = {r_[1]: r_[4] for r_ in st.t.rows if r_[0] == "c0"}
            check("C0 held" in summ and all(v is True for v in c0.values()) and len(c0) == 6,
                  f"R3's real A0 reader record (E791: pclink 0x98, p1 1, sa64 2, sa65 K<<24, sa63 0) scores as C0: all 6 rows hold ({c0})")
    f = R3EV / "b/b0.json"
    if fixture(f, "R3 b0.json"):
        real = json.loads(f.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            t = S.load_table("e")
            recs = e_world_recs(t, "EXIT")
            r = dict(real, name="e0", job=t["jobs"][0], row="E0", op="act", set="control", run=RUN)
            r["marks_post"] = {"ccb": [2, 2], "hc14": 0, "hc12": 0}
            r["d0"] = d0_triples(7)
            recs["e0"] = r
            d = write_stage(tmp, "e", recs)
            st, summ = S.score("e", d)
            e0 = {r_[1]: r_[4] for r_ in st.t.rows if r_[0] == "e0"}
            check(e0 == {"acted": True, "entries": True, "grid": True},
                  f"R3's real B0 ring page (14 entries on the 25000 grid, flags 1) scores as E0: entries 14 +-2, grid, nothing acted ({e0})")
    f = S2B / "e5c/ctl90.json"
    if fixture(f, "S2b ctl90.json"):
        real = json.loads(f.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            t = S.load_table("h")
            recs = {j["name"]: h_rec(j, "NOTENDED") for j in t["jobs"]}
            h1 = recs["h1"]
            h1["page"] = real["page"]
            h1["page2"] = real["page2"]
            h1["window_stamp"] = None
            d = write_stage(tmp, "h", recs)
            st, summ = S.score("h", d)
            band = {r_[0]: r_[4] for r_ in st.t.rows if r_[1] == "hold_band"}
            check(band.get("h1") is True, "S2b's ctl90 page (a real 90-tick hold) is in the hold band the scorer demands for H1")


# ---- stage d ------------------------------------------------------------------------------------------------------------------
def mk_marks(K=K0, rmw=0, hc14=0):
    return {"ccb": [K, (K + rmw) % 256], "hc14": hc14, "hc12": 0x9D0}


def d_world(tmp, world):
    """CCB: bit 8 alone stops it (D1 kept x3, D2 stops, D3 stops, D4 not run); HANDLER: D1 stops (reps skipped), D2 kept, D3 stops;
    ONCE: nothing stops (D4 runs)."""
    t = S.load_table("d")
    J = {j["name"]: j for j in t["jobs"]}
    recs = {}
    for n, j in J.items():
        recs[n] = a_rec(j)
    stop_ccb = stop_over(sig=sig_pair("busy", rmw=1, hc14=L.ASSERT_WORD, d=9))
    stop_plain = stop_over(sig=sig_pair("busy", rmw=0, hc14=0, d=9))
    if world == "CCB":
        recs["d2"] = stop_ccb(t, recs["d2"])
        recs["d3"] = stop_ccb(t, recs["d3"])
        recs["d4"] = skipped_rec(J["d4"], "all_kept:D3:1 not met")
    elif world == "HANDLER":
        recs["d1"] = stop_plain(t, recs["d1"])
        recs["d1-r2"] = skipped_rec(J["d1-r2"])
        recs["d1-r3"] = skipped_rec(J["d1-r3"])
        recs["d3"] = stop_plain(t, recs["d3"])
        recs["d4"] = skipped_rec(J["d4"], "all_kept:D3:1 not met")
    elif world == "ONCE":
        pass
    return t, recs


def test_stage_d():
    # world CCB
    with tempfile.TemporaryDirectory() as tmp:
        t, recs = d_world(tmp, "CCB")
        d = write_stage(tmp, "d", recs, exit_code=8, why="second stop")
        st, summ = S.score("d", d)
        check(verdict(st, "H-CCB") == "wins" and verdict(st, "H-HANDLER") == "loses" and verdict(st, "H-ONCE") == "loses",
              "H-CCB world: H-CCB wins (every row held), H-HANDLER and H-ONCE lose")
        check("H-CCB supported" in summ and "D3 shows the same marks" in summ and "read-write 1, dword 14 0xad002600" in summ, f"the SUMMARY reads H-CCB ({summ[:300]})")
        check("[d2: busy (E537), read-write 1" in summ and "d3: busy (E537)" in summ and "P3 answered in 0 of 2 stops" in summ and "stage exit 8" in summ,
              "the SUMMARY names both stops with their marks, P3 and the stage exit")
        check({r[0] for r in st.t.rows if r[3] == "fit"} == {"d3"}, "D3 is the fit row (E537's own dump), D1/D2 are held out")
    # world HANDLER
    with tempfile.TemporaryDirectory() as tmp:
        t, recs = d_world(tmp, "HANDLER")
        d = write_stage(tmp, "d", recs, exit_code=8)
        st, summ = S.score("d", d)
        check(verdict(st, "H-HANDLER") == "wins" and verdict(st, "H-CCB") == "loses" and verdict(st, "H-ONCE") == "loses",
              "H-HANDLER world (no bit 8 needed: D1 stops, D2 keeps it, D3 stops without the assert mark): H-HANDLER wins, H-CCB and H-ONCE lose")
        check("H-HANDLER supported" in summ, "the SUMMARY reads H-HANDLER")
        check("d1-r2: not run" in txt(st), "D1's replicates are skipped after D1 stopped")
    # world ONCE
    with tempfile.TemporaryDirectory() as tmp:
        t, recs = d_world(tmp, "ONCE")
        d = write_stage(tmp, "d", recs)
        st, summ = S.score("d", d)
        check(verdict(st, "H-ONCE") == "wins" and verdict(st, "H-CCB") == "loses" and verdict(st, "H-HANDLER") == "loses",
              "H-ONCE world (nothing stops, D4 runs): H-ONCE wins, H-CCB and H-HANDLER lose")
        check("H-ONCE" in summ and "stops 0" in summ and "D0 held" in summ, f"the SUMMARY reads H-ONCE ({summ[:160]})")
        d4 = [r for r in st.t.rows if r[0] == "d4"]
        check(any(r[1] == "kept" and r[2] == "H-ONCE" and r[4] is True for r in d4), "D4 ran (D3 kept the tick) and kept it: H-ONCE's D4 row holds")
    # E537's real dump as D3: the fit row
    f = DATA / "p1130-b2-variants/tailpair-stop1-regs.txt"
    if fixture(f, "E537 regs"):
        s1, s2, r = e537_samples()
        with tempfile.TemporaryDirectory() as tmp:
            t, recs = d_world(tmp, "CCB")
            recs["d3"]["sig"] = {"phase": "after-reader", "samples": [dict(s1, t=0.1, ccb=[2, 3], pass_=None), dict(s2, t=0.13)]}
            recs["d2"]["sig"] = recs["d3"]["sig"]
            d = write_stage(tmp, "d", recs, exit_code=8)
            st, summ = S.score("d", d)
            d3 = {(r_[1], r_[2]): r_[4] for r_ in st.t.rows if r_[0] == "d3"}
            check(d3[("read_minus_write", "H-CCB")] is True and d3[("dword14", "H-CCB")] is True and d3[("sig_busy", "H-CCB")] is True
                  and d3[("dword14", "H-HANDLER")] is False,
                  "E537's own registers as D3: H-CCB's marks rows hold (read +1, dword 14 0xad002600, busy), H-HANDLER's 'no assert mark' FAILS")
    # D1 and D2 both stop: the stage ends before D3
    with tempfile.TemporaryDirectory() as tmp:
        t, recs = d_world(tmp, "CCB")
        J = {j["name"]: j for j in t["jobs"]}
        recs["d1"] = stop_over(sig=sig_pair("busy", rmw=0, hc14=0))(t, recs["d1"])
        recs["d1-r2"] = skipped_rec(J["d1-r2"])
        recs["d1-r3"] = skipped_rec(J["d1-r3"])
        recs["d3"] = skipped_rec(J["d3"], "second stop ended the stage")
        d = write_stage(tmp, "d", recs, exit_code=8)
        st, summ = S.score("d", d)
        check("D1 and D2 both stop it" in summ and "d3: not run" in txt(st), "D1 and D2 both stop: neither H-CCB nor H-HANDLER alone, D3 not run")
    # D4 with E537's combination: the words check
    with tempfile.TemporaryDirectory() as tmp:
        t, recs = d_world(tmp, "ONCE")
        J = {j["name"]: j for j in t["jobs"]}
        recs["d4"] = a_rec(J["d4"], wr_over=lambda w: w[:10] + [0xDEAD] + w[11:])
        d = write_stage(tmp, "d", recs)
        st, summ = S.score("d", d)
        check("d4: NODATA (D4: an sa read-back is not what the writer wrote)" in txt(st), "void: D4's sa63 read-back is not what the writer wrote")
    # the word the writer wrote must be the row's: D3's literal
    with tempfile.TemporaryDirectory() as tmp:
        t, recs = d_world(tmp, "ONCE")
        J = {j["name"]: j for j in t["jobs"]}
        recs["d3"] = a_rec(J["d3"], wr_over=lambda w: w[:6] + [0xB009C4DC] + [0xB009C4DC] + w[8:])
        d = write_stage(tmp, "d", recs)
        st, summ = S.score("d", d)
        check("d3: NODATA (the word written (0xb009c4dc) is not the row's (0xb009c5dc)" in txt(st), "void: D3 wrote bit 8 clear (D1's word), not E537's")
    # K read after the arm (reset + arm each job): the count byte of the record is K of that job
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("d")
        J = {j["name"]: j for j in t["jobs"]}
        r = a_rec(J["d2"], K=2)
        check(r["w65_word"] == (2 << 24 | 0x100), "D2's word is K << 24 | 0x100 with K the count after the arm")


# ---- stage e ------------------------------------------------------------------------------------------------------------------
def e_page(j, world, mode):
    """slot 0's ring for a job of stage e, by row and world; returns (page, extras)."""
    row = j["row"]
    if row == "E0":
        return ring_page([tick(i) for i in range(14)]), {}
    if row == "X1":
        ent = [tick(i) for i in range(3)] + [tick(3, flag=L.TAIL_FLAG)]
        if mode == "stop":
            return ring_page(ent, acted=1), {}
        ent += [tick(i) for i in range(4, 14)]
        return ring_page(ent, acted=1), {}
    if row == "X20":
        ent = [tick(i, flag=L.TAIL_FLAG) for i in range(16)]
        return ring_page(ent, acted=20, drops=4), {}
    # B3: a kick entry with flag 3
    ent = [tick(i) for i in range(3)]
    kick = (L.SKIP_FLAG, 0, (K0 << 24) | L.KICK_LOW, 0x0100700C, STAMP0 + 20000 + 25000 * 3 + 9000)
    ent.append(kick)
    if mode == "stop":
        return ring_page(ent, acted=1), {}
    ent += [tick(i) for i in range(4, 14)]
    ent = ent[:3] + [kick] + [tick(i) for i in range(4, 14)]
    return ring_page(ent, acted=1), {}


def e_rec(j, world):
    """worlds: EXIT (X1 and X20 keep the tick, B3 stops), BODY (X1 stops, B3 stops), TICKONLY (X1 and X20 keep it, B3 keeps it)."""
    row = j["row"]
    stop = (row == "X1" and world == "BODY") or (row == "B3" and world in ("EXIT", "BODY"))
    pg, _ = e_page(j, world, "stop" if stop else "keep")
    P = 14 + j["count"]
    rec = {"name": j["name"], "set": j["set"], "op": "act", "row": row, "job": j, "class": "stop" if stop else "ok", "rc": 0, "note": "", "run": RUN,
           "page": pg, "page2": list(pg), "window_stamp": STAMP0, "ticks": [{"ok": True}], "ccbctl_pre": [K0, K0], "d0": d0_triples(7),
           "bracket": {"before": [50, 0x9D0, 50], "after": [50 + P, 0x9D0 + P - (j["count"] if row == "X20" else 0), 50 + P]}}
    if row == "B3":
        rec["kick"] = {"ms": 501.0, "errno": 110, "text": "no completion", "answered": False}
        rec["kick_errors"] = [110]
        if not stop:
            rec["class"] = "kick-timeout"
        rec["no_p3"] = True
    if stop:
        rmw = -1 if row == "B3" else 0
        rec["sig"] = sig_pair("busy", rmw=rmw, hc14=0, d=9)
        if row != "B3":
            rec["p3"] = {"answered": False, "ms": 500.5, "ring_new_entries": 0}
    else:
        rec["marks_post"] = mk_marks(K0, -1 if row == "B3" else 0, 0)
    return rec


def e_world_recs(t, world):
    recs = {}
    for j in t["jobs"]:
        recs[j["name"]] = e_rec(j, world)
    if world == "BODY":
        J = {j["name"]: j for j in t["jobs"]}
        for n in ("x1-r2", "x20", "x20-r2"):
            recs[n] = skipped_rec(J[n])
    return recs


def test_stage_e():
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        d = write_stage(tmp, "e", e_world_recs(t, "EXIT"), exit_code=8)
        st, summ = S.score("e", d)
        check(verdict(st, "H-EXIT") == "wins" and verdict(st, "H-BODY") == "loses" and verdict(st, "H-TICKONLY") == "loses",
              f"H-EXIT world: H-EXIT wins, H-BODY and H-TICKONLY lose ({[ (r[0], r[1], r[2]) for r in rows_of(st, 'H-EXIT') if r[4] is not True]})")
        check("E0 held; H-EXIT (a tick pass handed to a fast-path task keeps the tick, a skipped kick pass stops it)" in summ and "stops 1 [b3: busy (E537), read-write -1, dword 14 0x0]" in summ,
              f"the SUMMARY reads H-EXIT ({summ[:200]})")
        b3 = [r for r in st.t.rows if r[0] == "b3"]
        check({r[1] for r in b3} >= {"kept", "sig_busy", "miscinfo_answered", "read_minus_write", "kick_entry", "acted"}, "B3's rows: kept, busy, miscinfo not answered, read = write - 1, one kick entry, acted")
        check("P3" not in txt(st).split("b3:")[1].split("\n")[0], "B3's line has no P3 (its own kick is the probe)")
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        d = write_stage(tmp, "e", e_world_recs(t, "BODY"), exit_code=8)
        st, summ = S.score("e", d)
        check(verdict(st, "H-BODY") == "wins" and verdict(st, "H-EXIT") == "loses" and verdict(st, "H-TICKONLY") == "loses",
              f"H-BODY world: H-BODY wins, H-EXIT and H-TICKONLY lose ({[ (r[0], r[1]) for r in rows_of(st, 'H-BODY') if r[4] is not True]})")
        check("H-BODY (a tick pass handed to a fast-path task stops it too)" in summ and "stops 2 [x1: busy (E537), read-write 0, dword 14 0x0; b3: busy (E537), read-write -1" in summ and "x1-r2: not run" in txt(st),
              "the SUMMARY reads H-BODY, two stops, X1's replicate and X20 not run")
        x1 = {(r[1], r[2]): r[4] for r in st.t.rows if r[0] == "x1"}
        check(x1[("read_minus_write", "H-BODY")] is True and x1[("dword14", "H-BODY")] is True and x1[("sig_busy", "H-BODY")] is True,
              "X1 stop: read = write, dword 14 = 0, busy (H-BODY's marks hold)")
        p3 = {r[2]: r[4] for r in st.t.rows if r[0] == "x1" and r[1] == "p3_answered"}
        check(p3 == {"H-NOTENDED": True, "H-REARM": False}, "X1's stop sent P3: not answered")
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        d = write_stage(tmp, "e", e_world_recs(t, "TICKONLY"))
        st, summ = S.score("e", d)
        check(verdict(st, "H-TICKONLY") == "wins" and verdict(st, "H-EXIT") == "loses" and verdict(st, "H-BODY") == "loses",
              f"H-TICKONLY world: H-TICKONLY wins, H-EXIT and H-BODY lose ({[ (r[0], r[1]) for r in rows_of(st, 'H-TICKONLY') if r[4] is not True]})")
        check("H-TICKONLY (the skipped kick pass keeps the tick)" in summ and "stops 0" in summ, "the SUMMARY reads H-TICKONLY")
    # the mixed world: X1 stops, B3 keeps: no hypothesis fits
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        recs = e_world_recs(t, "BODY")
        recs["b3"] = e_rec([j for j in t["jobs"] if j["name"] == "b3"][0], "TICKONLY")
        d = write_stage(tmp, "e", recs, exit_code=0)
        st, summ = S.score("e", d)
        check("mixed, no hypothesis fits" in summ, "X1 stops and B3 keeps the tick: no hypothesis fits, said so")
    # E793's real stop dump as an X1 stop (the H-BODY shape): a copy of its page with the skipped pass flagged 4
    f = R3EV / "b/b1.json"
    if fixture(f, "E793 b1.json") and fixture(R3EV / "b/stop-b1-regs.txt", "E793 stop dump"):
        real = json.loads(f.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            t = S.load_table("e")
            recs = e_world_recs(t, "BODY")
            J = {j["name"]: j for j in t["jobs"]}
            pg = list(real["page"])
            for k in range(L.RUNGS[0]):
                o = L.RING_BASE[0] + L.RUNG * k
                if pg[o] == L.SKIP_FLAG:
                    pg[o] = L.TAIL_FLAG
            pg[L.ACTED] = 1
            pg[L.COUNT] = 0
            r = dict(real, name="x1", job=J["x1"], row="X1", op="act", set="heldout", run=RUN, page=pg, page2=list(pg), d0=d0_triples(7))
            r["sig"] = dict(real["sig"])
            r.pop("marks_post", None)
            r["p3"] = {"answered": False, "ms": 500.0}
            recs["x1"] = r
            d = write_stage(tmp, "e", recs, exit_code=8)
            shutil.copy(R3EV / "b/stop-b1-regs.txt", d / "stop-x1-regs.txt")
            st, summ = S.score("e", d)
            x1 = {(r_[1], r_[2]): r_[4] for r_ in st.t.rows if r_[0] == "x1"}
            check(x1.get(("kept", "H-BODY")) is True and x1.get(("read_minus_write", "H-BODY")) is True and x1.get(("dword14", "H-BODY")) is True
                  and x1.get(("sig_busy", "H-BODY")) is True and x1.get(("kept", "H-EXIT")) is False,
                  "E793's real stop (page, signature, dump: read = write, dword 14 = 0) read as an X1 stop: every H-BODY row holds, H-EXIT's kept row fails")
    # void and cannot-tell
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        J = {j["name"]: j for j in t["jobs"]}
        recs = e_world_recs(t, "EXIT")
        pg = list(recs["x1"]["page"])
        pg[L.ACTED] = 3
        recs["x1"] = dict(recs["x1"], page=pg, page2=list(pg))
        pg2 = list(recs["x20"]["page"])
        pg2[L.ACTED] = 0
        recs["x20"] = dict(recs["x20"], page=pg2, page2=list(pg2))
        pg3 = ring_page([tick(i) for i in range(14)], acted=1)             # acted but no flagged entry, no drop
        recs["x1-r2"] = dict(recs["x1-r2"], page=pg3, page2=list(pg3))
        pg4 = ring_page([tick(i) for i in range(16)], acted=20, drops=3)    # ring full before the acted pass
        recs["x20-r2"] = dict(recs["x20-r2"], page=pg4, page2=list(pg4))
        pg5 = list(recs["e0"]["page"])
        pg5[L.RING_BASE[0]] = 7
        recs["e0"] = dict(recs["e0"], page=pg5, page2=list(pg5))
        recs["e0-r2"] = dict(recs["e0-r2"], page2=[0] * L.PAGE_DWORDS)
        d = write_stage(tmp, "e", recs, exit_code=8)
        st, summ = S.score("e", d)
        txt_ = txt(st)
        check("x1: NODATA (the acted count was not taken as designed (ACTED 3, want 1))" in txt_, "void: ACTED is not the design's")
        check("x20: " in txt_ and "ACTED 0 of 20" in txt_ and "cannot tell" in txt_, "ACTED 0: the KIND of pass never came: cannot tell")
        check("x1-r2:" in txt_ and "the acted pass is not in the ring (not logged first): cannot tell" in txt_, "an acted pass that was not logged first: cannot tell")
        check("ring full before the acted pass: cannot tell" in txt_, "a ring full before the acted pass: cannot tell")
        check("e0: NODATA (corrupt ring" in txt_, "a corrupt flag in the ring: NODATA")
        check("e0-r2: NODATA (the ring changed after the window closed" in txt_, "window-0 proof: a ring that changed after the close is void")
        check(not [r for r in st.t.rows if r[0] in ("x1", "x20", "x1-r2", "x20-r2") and r[4] is not None], "none of those rows counts as held or failed")
    # a kick answered in B3 (miscinfo answered although the kick pass ended): the row fails
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        recs = e_world_recs(t, "EXIT")
        recs["b3"]["kick"] = {"ms": 12.0, "text": "MISCINFO ok", "answered": True}
        recs["b3"].pop("kick_errors", None)
        d = write_stage(tmp, "e", recs, exit_code=8)
        st, summ = S.score("e", d)
        m = {r[2]: r[4] for r in st.t.rows if r[0] == "b3" and r[1] == "miscinfo_answered"}
        check(m == {"H-EXIT": False, "H-BODY": False, "H-TICKONLY": False}, "B3: a miscinfo that WAS answered fails all three 'not answered' rows")
    # E0 differing
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        recs = e_world_recs(t, "EXIT")
        pg = ring_page([tick(i, extra=(0 if i < 6 else 7000)) for i in range(14)])
        recs["e0"] = dict(recs["e0"], page=pg, page2=list(pg))
        d = write_stage(tmp, "e", recs, exit_code=8)
        st, summ = S.score("e", d)
        e0 = {r[1]: r[4] for r in st.t.rows if r[0] == "e0"}
        check(e0["grid"] is False and "E0 DIFFERS" in summ, "a tick off the grid in E0: the grid control FAILS, 'E0 DIFFERS'")
    # X1 next gap off the grid
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        recs = e_world_recs(t, "EXIT")
        pg = ring_page([tick(i) for i in range(3)] + [tick(3, flag=L.TAIL_FLAG)] + [tick(i + 1) for i in range(4, 8)], acted=1)
        recs["x1"] = dict(recs["x1"], page=pg, page2=list(pg))
        d = write_stage(tmp, "e", recs, exit_code=8)
        st, summ = S.score("e", d)
        x1 = {(r[1]): r[4] for r in st.t.rows if r[0] == "x1" and r[2] == "H-EXIT"}
        check(x1["next_gap"] is False and x1["kept"] is True, "X1 kept but the next tick came 50000 later: the next_gap row FAILS, the kept row holds")


# ---- stop bookkeeping, gates, tables -------------------------------------------------------------------------------------------
def test_gate():
    with tempfile.TemporaryDirectory() as tmp:
        check(S.gate("h", tmp) == 0, "gate h: no previous stage, open")
        check(S.gate("c", tmp) == 1, "gate c: no kept stage.json of h: closed")
        write_stage(tmp, "h", {}, exit_code=0)
        check(S.gate("c", tmp) == 0, "gate c: h finished (exit 0): open, derived from the kept stage.json")
        write_stage(tmp, "h", {}, exit_code=8)
        check(S.gate("c", tmp) == 0, "gate c: h ended by its second stop (exit 8), reset and gate exact: open for the lead's --from")
        write_stage(tmp, "h", {}, exit_code=4)
        check(S.gate("c", tmp) == 1, "gate c: h exited 4: closed")
        write_stage(tmp, "c", {}, exit_code=0)
        check(S.gate("e", tmp) == 0, "gate e: c finished: open")
        write_stage(tmp, "e", {}, exit_code=3)
        check(S.gate("d", tmp) == 1, "gate d: e exited 3 (watchdog): closed")
        write_stage(tmp, "e", {}, exit_code=0)
        check(S.gate("d", tmp) == 0, "gate d: e finished: open")


def test_tables():
    tabs = {s: S.load_table(s) for s in L.STAGES}
    for st, t in tabs.items():
        check([j["row"] for j in t["jobs"] if j["name"] == L.rep_name(j["row"], 0)] == L.ROW_ORDER[st], f"stage {st} has exactly the rows {L.ROW_ORDER[st]}")
        pcases = {p["case"] for p in S.load_preds(st)}
        check(pcases == {j["name"] for j in t["jobs"]}, f"stage {st}: every job has frozen prediction rows and every case is a job")
        check(all(p["set"] in ("fit", "heldout", "replicate", "control") for p in S.load_preds(st)), f"stage {st}: every row has a label")
        check(t["stop_budget"] == L.STOP_BUDGET[st] and t["blob"] == L.BLOB_OF[st], f"stage {st}: stop budget {L.STOP_BUDGET[st]} (h: the first stop ends it; c, e, d: the second), blob {L.BLOB_OF[st]}")
    counts = {st: len(t["jobs"]) for st, t in tabs.items()}
    check(counts == {"h": 6, "c": 13, "e": 7, "d": 7}, f"job counts h 6, c 13, e 7, d 7 ({counts}): maxima, the run-if rows are skipped when their condition fails")
    check([j["name"] for j in tabs["e"]["jobs"]][-1] == "b3" and [j["name"] for j in tabs["d"]["jobs"]][-2:] == ["d3", "d4"],
          "B3 is LAST in stage e; D3 is last of the expected stops in stage d (D4 after it, only if D3 kept the tick)")
    check(all(j["w65"] and j["w65"].get("or", 0) & L.TESTED_PA1_MASK == 0 for j in tabs["c"]["jobs"] if j["row"] in ("C1", "C3")),
          "C1 and C3 carry no bit that some ukernel code tests (their 'no handler' bits are outside 0x780790)")
    j = [x for x in tabs["c"]["jobs"] if x["row"] == "C3"][0]
    check(j["w65"]["or"] == 0x1C04C and (j["w65"]["or"] & L.TESTED_PA1_MASK) == 0, "C3's bits 2, 3, 6, 14, 15, 16 (0x1c04c) are outside the tested mask")
    ds = {x["name"]: x for x in tabs["d"]["jobs"]}
    check(ds["d1"]["w65"] == {"lit": 0xB009C4DC} and ds["d3"]["w65"] == {"lit": 0xB009C5DC} and ds["d2"]["w65"] == {"k": 1, "or": 0x100},
          "D1, D2, D3 words: E537's with bit 8 clear, K << 24 | 0x100, E537's")
    d4 = ds["d4"]
    check((d4["w63"], d4["w64"], d4["w65"], d4["ri"]) == (0xD7C5F5AE, 0xB0150D9D, {"lit": 0xB009C5DC}, [0xF8A4AC80, 0xFCF393C8, 0xA958E53C, 0xD90C0733]),
          "D4's words are E537's (sa63, sa64, sa65, r20, r21, i0, i1)")
    mk = DATA / "p1130-b2-variants/b2-markers.json"
    if fixture(mk, "E537 markers"):
        m = json.loads(mk.read_text())["markers"][0]
        check([m[10], m[0], m[9], m[5], m[6], m[7], m[8]] == [E537[k] for k in ("sa63", "sa64", "sa65", "r20", "r21", "i0", "i1")],
              "E537's seven words in r3layout are the first writer's markers of b2-markers.json (state3.s: sa64 m0, r20 m5, r21 m6, i0 m7, i1 m8, sa65 m9, sa63 m10)")


# ---- post-run fixes (POSTRUN-FIX.md, 2026-11-11) ---------------------------------------------------------------------------
def test_postrun_fixes():
    # C5 (the audit's repro): X1 jobs whose acted pass never came (ACTED 0, class ok) are cannot tell; the stage's hypothesis line
    # must not count them as X1 keeping the tick
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        recs = e_world_recs(t, "EXIT")
        for n in ("x1", "x1-r2"):
            r = recs[n]
            for k in ("page", "page2"):
                pg = list(r[k])
                pg[L.ACTED] = 0
                r[k] = pg
        d = write_stage(tmp, "e", recs, exit_code=8)
        st, summ = S.score("e", d)
        check("the KIND of pass never came in the window (ACTED 0): cannot tell" in txt(st) and "H-EXIT (a tick pass" not in summ
              and "B3 stopped, X1 not read" in summ, f"C5: X1 with ACTED 0 is cannot tell and not counted for the stage line ({summ[:120]})")
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("e")
        recs = e_world_recs(t, "EXIT")
        r = recs["x1-r2"]
        for k in ("page", "page2"):
            pg = list(r[k])
            pg[L.ACTED] = 0
            r[k] = pg
        d = write_stage(tmp, "e", recs, exit_code=8)
        st, summ = S.score("e", d)
        check("E0 held; H-EXIT (a tick pass" in summ, "C5: the X1 rep that decided still reads H-EXIT")


def main():
    test_signature_and_marks()
    test_d_instrument()
    test_stage_h()
    test_stage_c()
    test_real_fixtures()
    test_stage_d()
    test_stage_e()
    test_gate()
    test_tables()
    test_postrun_fixes()
    print(f"{len(FAIL)} failed" if FAIL else "all scorer checks passed" + (f" ({len(SKIPS)} fixtures absent)" if SKIPS else ""))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
