#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_scorer.py: the R3k scorers (score/score_r3.py, scorelib.py, sc_ring.py, sc_e2b.py, sc_e3.py) on kept fixtures and synthetic worlds.  Offline;
standard library only.

Fixtures (tests/fixtures, copied from the data and L3's kept output): E537's stop dump and L3's D2 (CCB read 3 after write 2, HostCtl dword 14 =
0xad002600), L3's B3 stop (read = write - 1), L1's dd-p1 output (the geometry control of k0t).  Synthetic worlds: one per hypothesis, each built from
what the hypothesis predicts, so that every hypothesis WINS (every scored row of its model held) in its own world and LOSES (a row of its model
FAILED) in the others': stage f H-BOTH / H-CFI / H-PHAS / H-ANY / H-PLACE / H-BEFORE, stage t H-TIMER / H-NOTIMER, kb H-KW / H-LATCH / H-HWC, e2b H-D /
H-B / H-P, e3h and e3a H-W / H-ALL / H-NONE, e3b H-STOP3 / H-FREE3 with level or pulse; and every void and cannot-tell state, the stop bookkeeping, the gates.

    ../../closing/pixel-faults/.venv/bin/python tests/test_scorer.py
"""
import gzip
import hashlib
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
import scorelib as C  # noqa: E402
import score_r3 as S  # noqa: E402
import sc_ring  # noqa: E402

FX = R3 / "tests" / "fixtures"
FAIL = []
RUN = "test-run"
STAMP0 = 0x10000000
K0 = 2
TICK_PA2 = 0x01061A70
T = L.TICK_UNITS


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


# ---- samples and stop signatures -------------------------------------------------------------------------------------------
def sample(kind="busy", t=0.1, rmw=0, hc14=0, w=K0, hc12=0x9DB, timer_off=0):
    regs = {"0x8": 0x000CCFA0, "0xb14": 0x9E0, "0xacc": 0x01038EC3 - timer_off, "0x12c": 0x20000000, "0xb20": 0x10000, "0x118": 0x400, "0xc04": 0, "0xc08": 0}
    if kind == "idle":
        regs.update({"0x8": 0x20, "0xb14": 0x10000 | (hc12 & 0xFFFF)})
    return {"t": t, "regs": regs, "hc12": hc12, "hc14": hc14, "ccb": [w, (w + rmw) % 256], "pass": None}


def sig_pair(kind="busy", rmw=0, hc14=0):
    return {"phase": "after-window", "samples": [sample(kind, 0.1, rmw, hc14), sample(kind, 0.13, rmw, hc14, timer_off=0x5000)]}


def e537_samples(name="e537-regs.txt"):
    r, hc, cc = L.parse_regs((FX / name).read_text())
    s1 = {"regs": {hex(k): v for k, v in r.items()}, "hc12": hc.get(12), "hc14": hc.get(14), "ccb": cc}
    r2 = dict(r)
    r2[L.REG_EVENT_TIMER] = r[L.REG_EVENT_TIMER] - 0x4000
    return s1, {"regs": {hex(k): v for k, v in r2.items()}, "hc12": hc.get(12), "hc14": hc.get(14), "ccb": cc}


def test_signature_and_marks():
    s1, s2 = e537_samples()
    sg = C.score_sig([s1, s2])
    check(sg["class"] == "busy" and sg["matches_e537"] and all(sg["elements"].values()) and sg["hostctl12_moved"] is False,
          f"E537's own dump scores busy and matches E537 ({sg['class']})")
    check("event_status_0x20000000" not in sg["elements"] and sg["recorded"]["event_status_0x20000000"] is True, "0x012c is recorded, not part of the match (0b)")
    check(C.score_sig([s1])["class"] == "unreadable", "one sample only: unreadable")
    mk = C.marks_from_samples([s1, s2])
    check(mk == {"ccb": [2, 3], "rmw": 1, "hc14": 0xAD002600}, f"E537's dump: read - write +1, dword 14 0xad002600 ({mk})")
    a, b = e537_samples("l3-d2-regs.txt")
    check(C.marks_from_samples([a, b]) == mk, "L3's D2 stop carries E537's marks")
    a, b = e537_samples("l3-b3-regs.txt")
    check(C.marks_from_samples([a, b]) == {"ccb": [3, 2], "rmw": -1, "hc14": 0}, "L3's B3 stop: read = write - 1, dword 14 0")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(FX / "l3-d2-status.txt", pathlib.Path(tmp) / "stop-d2-status.txt")
        check(C.marks_from_dump(tmp, "d2") == mk, "the marks read from a status dump file are the same")
    check(L.signed8(3 - 2) == 1 and L.signed8(1 - 2) == -1 and L.signed8(0) == 0, "signed8: read - write as -128..127")
    ip = json.loads(json.dumps([s1, s2]))
    for sm in ip:
        sm["regs"][hex(L.REG_CLKSTAT)] = 0x20
    check(C.score_sig(ip)["class"] == "idle-pending", "clock idle, EMPTY clear: idle-pending")


def test_d_instrument():
    tri = [[100 + i + 7, 100 + i, 100 + i + 7] for i in range(20)]
    check(C.d_vals(tri) == [7] * 20 and C.d_mode(C.d_vals(tri)) == (7, 1.0), "D = page pass - dword 12; one modal value")
    check(len(C.d_vals(tri + [[50, 40, 51], [None, 3, None]])) == 20, "a triple whose page reads differ, or with a missing value, is dropped")
    check(C.interval_near((-52, -48), -50, 8) is True and C.interval_near((-70, -66), -50, 8) is False and C.interval_near((-60, -45), -50, 8) is None, "interval_near")


# ---- builders ---------------------------------------------------------------------------------------------------------------
def write_stage(tmp, stage, recs, exit_code=0, why=""):
    d = pathlib.Path(tmp) / stage
    d.mkdir(parents=True, exist_ok=True)
    for n, r in recs.items():
        (d / f"{n}.json").write_text(json.dumps(r))
    (d / "stage.json").write_text(json.dumps({"stage": stage, "run": RUN, "exit": exit_code, "why": why, "jobs_run": list(recs)}))
    return d


def skipped_rec(j, why="row stopped"):
    return {"name": j["name"], "set": j["set"], "op": j["op"], "row": j["row"], "job": j, "class": "skipped", "rc": None, "note": why, "run": RUN}


def verdict(st, model):
    """'wins': every scored row of the model held; 'loses': a row FAILED; 'none': no row; 'open': only cannot-tell rows."""
    rs = [r for r in st.t.rows if r[2] == model or r[2].startswith(model + " ")]
    if not rs:
        return "none"
    if any(r[4] is False for r in rs):
        return "loses"
    if all(r[4] is True for r in rs):
        return "wins"
    return "open"


def ring_page(entries, acted=0, act=0, drops=0, magic=True):
    pg = [0] * L.PAGE_DWORDS
    pg[0] = L.MAGIC if magic else 0
    for j, (f, a, b, c, s) in enumerate(entries[:L.RUNGS[0]]):
        o = L.RING_BASE[0] + L.RUNG * j
        pg[o:o + 5] = [f, a, b, c, s]
    pg[L.ACTED], pg[L.ACT_SEEN], pg[L.DROP] = acted, act, drops
    return pg


def ticks(n, k=K0, start=STAMP0 + 3000, flag=1, step=T):
    return [(flag, 2, k << 24, TICK_PA2, start + i * step) for i in range(n)]


def base_rec(j, cls, page=None, rc=0, **kw):
    rec = {"name": j["name"], "set": j["set"], "op": j["op"], "row": j["row"], "job": j, "class": cls, "rc": rc, "note": "", "run": RUN,
           "window_stamp": STAMP0, "page": page, "page2": list(page) if page else None}
    rec.update(kw)
    return rec


def load(stage):
    return json.loads((R3 / "tables" / f"{stage}.json").read_text())


# ---- stages f and t ---------------------------------------------------------------------------------------------------------
def act_world(stage, stops):
    """Records of stage f or t for the table's jobs: stops = {job name: True} for a tick stop; every other run job keeps the tick.  A job whose
    run_if is not met (an earlier row of its gate stopped or was not all kept) is skipped, as the runner does; a stopped row's replicates too."""
    tab = load(stage)
    recs, kept, stopped_rows = {}, {}, set()
    for j in tab["jobs"]:
        n, row = j["name"], j["row"]
        gate = j.get("run_if")
        if row in stopped_rows or (gate and not all(kept.get(gate.split(":")[1], [False]))):
            recs[n] = skipped_rec(j)
            continue
        if row == "E0":
            page = ring_page(ticks(14))
            recs[n] = base_rec(j, "ok", page)
            kept.setdefault(row, []).append(True)
            continue
        act = j["act"]
        flag = L.TAIL_FLAG if act in L.ACT_ENDS_TAIL else L.SKIP_FLAG
        es = ticks(3) + [(flag, 2, K0 << 24, TICK_PA2, STAMP0 + 3000 + 3 * T)]
        stopped = stops.get(n, False)
        if not stopped:
            es += ticks(4, start=STAMP0 + 3000 + 4 * T)
        page = ring_page(es, acted=1, act=act)
        rec = base_rec(j, "stop" if stopped else "ok", page, bracket={"before": [10, 100, 10], "after": [20, 110, 20]})
        if stopped:
            rec["sig"] = sig_pair("busy")
            rec["p3"] = {"answered": False, "ms": 500, "before": {}, "after": {}}
            stopped_rows.add(row)
        else:
            rec["marks_post"] = {"ccb": [2, 2], "hc14": 0, "hc12": 100}
        kept.setdefault(row, []).append(not stopped)
        recs[n] = rec
    return tab, recs


def score_world(stage, recs, tab=None, exit_code=0):
    with tempfile.TemporaryDirectory() as tmp:
        d = write_stage(tmp, stage, recs, exit_code)
        st, summary = S.score(stage, d)
        return st, summary


def test_f_worlds():
    worlds = {"H-BOTH": {"fcf": True, "fph": True}, "H-CFI": {"fph": True}, "H-PHAS": {"fcf": True}, "H-ANY": {}}
    models = ("H-BOTH", "H-CFI", "H-PHAS", "H-ANY")
    for name, stops_ in worlds.items():
        global stops
        stops = stops_
        tab, recs = act_world("f", stops_)
        st, summary = score_world("f", recs)
        v = {m: verdict(st, m) for m in models}
        check(v[name] == "wins" and all(v[m] == "loses" for m in models if m != name), f"stage f, world {name}: it wins, the others lose ({v})")
        check(name in summary and "E0 held" in summary, f"stage f, world {name}: the summary names it ({summary[:90]})")
    stops = {"fb": True}
    tab, recs = act_world("f", stops)
    st, summary = score_world("f", recs)
    check(verdict(st, "H-PLACE") == "wins" and verdict(st, "H-BOTH") == "loses" and "H-PLACE" in summary and recs["fcf"]["class"] == "skipped",
          f"stage f, world H-PLACE: the exact replica stops, the single rows are skipped ({summary[:120]})")
    stops = {"fc4": True}
    tab, recs = act_world("f", stops)
    st, summary = score_world("f", recs)
    check(verdict(st, "H-BEFORE") == "wins" and verdict(st, "H-EXITPATH") == "loses" and "H-BEFORE" in summary and "did NOT keep" in summary,
          f"stage f, world H-BEFORE: the control stops, nothing else is read ({summary[:120]})")
    # the stop carries E793's signature and the stop rows score
    stops = {"fcf": True, "fph": True}
    tab, recs = act_world("f", stops)
    st, summary = score_world("f", recs, exit_code=8)
    check("stops 2" in summary and "fcf: busy (E537)" in summary and "P3 answered in 0 of 2 stops" in summary and "stage exit 8" in summary,
          f"stage f: two stops, busy, P3 not answered, the exit 8 is noted ({summary[:200]})")
    for name, stops_, want in (("H-TIMER", {}, "H-TIMER"), ("H-NOTIMER", {"t2": True}, "H-NOTIMER")):
        stops = stops_
        tab, recs = act_world("t", stops_)
        st, summary = score_world("t", recs)
        other = "H-NOTIMER" if name == "H-TIMER" else "H-TIMER"
        check(verdict(st, name) == "wins" and verdict(st, other) == "loses" and want in summary, f"stage t, world {name}: wins, {other} loses ({summary[:110]})")
    stops = {"t1": True}
    tab, recs = act_world("t", stops)
    st, summary = score_world("t", recs)
    check(verdict(st, "H-TIMERW-STOPS") == "wins" and "H-TIMERW-STOPS" in summary and recs["t2"]["class"] == "skipped", "stage t, world H-TIMERW-STOPS: T2 is not run")


def test_void_states():
    global stops
    stops = {}
    tab, recs = act_world("f", {})
    j = [x for x in tab["jobs"] if x["name"] == "fb"][0]
    cases = {"a ring that changed after the close": lambda r: r["page2"].__setitem__(L.RING_BASE[0], 0),
             "a page without the kernel's magic": lambda r: r["page"].__setitem__(0, 0),
             "a corrupt flag": lambda r: r["page"].__setitem__(L.RING_BASE[0], 9)}
    for label, mod in cases.items():
        rs = json.loads(json.dumps(recs))
        mod(rs["fb"])
        st, summary = score_world("f", rs)
        check(any(r[4] is None for r in st.t.rows if r[0] == "fb") and any("NODATA" in ln for ln in st.lines), f"{label}: the job is void (NODATA, no row counts as a pass)")
    rs = json.loads(json.dumps(recs))
    rs["fb"]["page"][L.ACTED] = 0
    st, summary = score_world("f", rs)
    check(any("the KIND of pass never came" in ln for ln in st.lines) and all(r[4] is None for r in st.t.rows if r[0] == "fb" and r[1] == "kept"), "ACTED 0: cannot tell")
    rs = json.loads(json.dumps(recs))
    rs["fb"]["page"][L.ACTED] = 3
    st, summary = score_world("f", rs)
    check(any("not taken as designed" in ln for ln in st.lines), "ACTED not the design's count: void")
    rs = json.loads(json.dumps(recs))
    rs["fb"]["page"] = ring_page(ticks(16), acted=1, act=5, drops=3)
    rs["fb"]["page2"] = list(rs["fb"]["page"])
    st, summary = score_world("f", rs)
    check(any("ring full before the acted pass" in ln for ln in st.lines), "a ring full before the acted pass: cannot tell")
    rs = json.loads(json.dumps(recs))
    rs["fb"]["class"] = "unhealthy"
    st, summary = score_world("f", rs)
    check(any("NODATA" in ln for ln in st.lines), "a class that is not a result (unhealthy): void")
    with tempfile.TemporaryDirectory() as tmp:
        d = write_stage(tmp, "f", recs)
        st = json.loads((d / "stage.json").read_text())
        st["run"] = "another-run"
        (d / "stage.json").write_text(json.dumps(st))
        S2, summ = S.score("f", d)
        check(all(r[4] is None for r in S2.t.rows) or not S2.t.rows or any("NODATA" in ln for ln in S2.lines), "a stale record (another run's stage.json) is not read")


# ---- kb ---------------------------------------------------------------------------------------------------------------------
def kb_world(hyp):
    """Records of stage kb: K per hypothesis (KW: the word; LATCH: the word at the last kick; HWC: the count of kicks)."""
    tab = load("kb")
    recs = {}
    for j in tab["jobs"]:
        n, row = j["name"], j["row"]
        W0, kicks0 = 2, 2
        w = W0
        # ticks before the action: K = 2 in every world
        es, t = [], STAMP0 + 1000
        pre = [(1, 2, (2 << 24), TICK_PA2, t + i * T) for i in range(2)]
        t_set = pre[-1][4] + T // 2
        k_now = 2
        word, latched, kcount = 2, 2, 2
        post_set = []
        if j["set_kicker"] is not None:
            word = j["set_kicker"]
        kfun = lambda: {"H-KW": word, "H-LATCH": latched, "H-HWC": kcount}[hyp]
        post_set = [(1, 2, kfun() << 24, TICK_PA2, t_set + (i + 1) * T) for i in range(5)]
        entries = pre + post_set
        t_kick = None
        kicks_after = kicks0
        wofs = 2
        if j["kick"]:
            t_kick = entries[-1][4] + T // 2
            kick_k = kfun()
            if not j["no_bump"]:
                word += 1
            kcount += 1
            latched = word
            wofs = 3
            kicks_after = kicks0 + 1
            entries.append((1, 0, (kick_k << 24) | L.KICK_LOW, TICK_PA2, t_kick))
            entries += [(1, 2, kfun() << 24, TICK_PA2, t_kick + (i + 1) * T) for i in range(5)]
        rec = base_rec(j, "ok", ring_page(entries), stamp_after_set=t_set, stamp_before_set=t_set - 100, set_ok=j["set_kicker"] is not None,
                       kicker_before={"w": 2, "wofs": 2, "rofs": 2, "kicks": 2, "raw": "kicker 2 ccbctl 2 2 kicks 2"},
                       kicker_after={"w": word, "wofs": wofs, "rofs": wofs, "kicks": kicks_after, "raw": f"kicker {word} ccbctl {wofs} {wofs} kicks {kicks_after}"},
                       no_bump_after="N", kick={"answered": True, "ms": 0.2} if j["kick"] else None)
        if j["kick"]:
            rec["stamp_before_kick"] = t_kick - 100
        recs[n] = rec
    return tab, recs


def test_kb_worlds():
    models = ("H-KW", "H-LATCH", "H-HWC")
    for hyp in models:
        tab, recs = kb_world(hyp)
        st, summary = score_world("kb", recs)
        v = {m: verdict(st, m) for m in models}
        check(v[hyp] == "wins" and all(v[m] == "loses" for m in models if m != hyp), f"kb, world {hyp}: it wins, the others lose ({v})")
        check(f"consistent with ['{hyp}']" in summary and "Q0 held" in summary, f"kb, world {hyp}: the summary ({summary[:110]})")
        ctl = [r for r in st.t.rows if r[3] == "control"]
        check(ctl and all(r[4] is True for r in ctl), f"kb, world {hyp}: every control row held (kicker file, ccbctl, kicks, answered) ({len(ctl)} rows)")
    tab, recs = kb_world("H-KW")
    recs["q1"]["page"] = ring_page(ticks(2))          # nothing after the set
    recs["q1"]["page2"] = list(recs["q1"]["page"])
    st, summary = score_world("kb", recs)
    check(any(r[0] == "q1" and r[4] is None for r in st.t.rows), "kb: no tick after the write: cannot tell, not a pass")
    tab, recs = kb_world("H-KW")
    recs["q1"]["set_ok"] = False
    st, summary = score_world("kb", recs)
    check(any("kicker write was refused" in ln for ln in st.lines), "kb: a refused kicker write voids the job")


# ---- e2b --------------------------------------------------------------------------------------------------------------------
def e2b_world(hyp):
    tab = load("e2b")
    recs = {}
    regs = {"pa2": TICK_PA2, "pa3": 0x04000004, "pa4": 0x00030001, "sa66": TICK_PA2, "sa67": 0x04000004, "sa68": 0x00030001}
    for j in tab["jobs"]:
        n, cmd, M = j["name"], j["cmd"], j["marker"]
        A = [2, 0x02000000, regs["pa2"], regs["pa3"], regs["pa4"], 2, 0x02000000, regs["sa66"], regs["sa67"], regs["sa68"], 0x32004000, 5000]
        C_ = [0] * 8
        if cmd in (2, 3):
            pa_n, sa_n = ("pa3", "sa67") if cmd == 2 else ("pa4", "sa68")
            regs[sa_n] = M
            regs[pa_n] = M
            o = L.PW_C_OF[cmd][0] - L.PW_C
            C_[o], C_[o + 1] = regs[pa_n], regs[sa_n]
        elif cmd in (4, 5, 6):
            pa_n, sa_n = {4: ("pa3", "sa67"), 5: ("pa4", "sa68"), 6: ("pa2", "sa66")}[cmd]
            if hyp == "H-D":
                regs[pa_n] = regs[sa_n] = M
            elif hyp == "H-P":
                regs[pa_n] = M
            o = L.PW_C_OF[cmd][0] - L.PW_C
            C_[o], C_[o + 1] = regs[pa_n], regs[sa_n]
        B = [2, 0x02000000, TICK_PA2, regs["pa3"], regs["pa4"], 2, 0x02000000, regs["sa66"], regs["sa67"], regs["sa68"], 0x32004000, 5100]
        if cmd == 6:
            B[2] = TICK_PA2
        recs[n] = base_rec(j, "ok", [L.MAGIC] + [0] * (L.PAGE_DWORDS - 1), area_a=A, area_c=C_, area_b=B, writer_ms=1.0, next_ms=2.0)
    return tab, recs


def test_e2b_worlds():
    models = ("H-D alias", "H-B lost", "H-P private")
    for hyp, name in zip(("H-D", "H-B", "H-P"), models):
        tab, recs = e2b_world(hyp)
        st, summary = score_world("e2b", recs)
        v = {m: verdict(st, m) for m in models}
        check(v[name] == "wins" and all(v[m] == "loses" for m in models if m != name), f"e2b, world {hyp}: it wins, the others lose ({v})")
        check(f"consistent with ['{name}']" in summary and "controls held" in summary, f"e2b, world {hyp}: the summary ({summary[:120]})")
    tab, recs = e2b_world("H-D")
    recs["r"]["area_a"][3] = 0x1234
    st, summary = score_world("e2b", recs)
    check("a CONTROL DIFFERS" in summary, "e2b: a read row that differs from E748's words fails the control")


# ---- e3h, e3a ---------------------------------------------------------------------------------------------------------------
def e3_world(stage, hyp, latch=True):
    tab = load(stage)
    recs = {}
    for j in tab["jobs"]:
        s2 = [0x440 if latch else 0x400, 0x440 if latch else 0x400,
              {"H-W": 0x440, "H-ALL": 0x400, "H-NONE": 0x440}[hyp], {"H-W": 0x400, "H-ALL": 0x400, "H-NONE": 0x440}[hyp], 0x440 if latch else 0x400]
        steps = [{"step": i + 1, "what": st[0], "arg": st[1] if len(st) > 1 else None, "ok": True, "status2": s2[i]} for i, st in enumerate(j["steps"])]
        recs[j["name"]] = base_rec(j, "ok", None, steps=steps, status2_pre=0x400, route="host" if stage == "e3h" else "fw")
    return tab, recs


def test_e3_worlds():
    for stage in ("e3h", "e3a"):
        for hyp in ("H-W", "H-ALL", "H-NONE"):
            tab, recs = e3_world(stage, hyp)
            st, summary = score_world(stage, recs)
            v = {m: verdict(st, m) for m in ("H-W", "H-ALL", "H-NONE")}
            check(v[hyp] == "wins" and all(v[m] == "loses" for m in v if m != hyp), f"{stage}, world {hyp}: it wins, the others lose ({v})")
            check(f"['{hyp}']" in summary, f"{stage}, world {hyp}: the summary ({summary[:90]})")
    tab, recs = e3_world("e3h", "H-W", latch=False)
    st, summary = score_world("e3h", recs)
    check(all(r[4] is None for r in st.t.rows if r[1] in ("s2_step3", "s2_step4", "s2_step5")) and "cannot tell" in summary and verdict(st, "H-W") == "loses",
          "e3h: step 1 did not latch: the held-out steps are cannot tell, the fit rows FAIL (the control of the round)")


# ---- e3b --------------------------------------------------------------------------------------------------------------------
def e3b_world(stop, level, w_hyp):
    tab = load("e3b")
    recs = {}
    for j in tab["jobs"]:
        n, row = j["name"], j["row"]
        er = [(3, 0, 0x02000010, TICK_PA2, STAMP0 + 4000)]
        flag = L.SKIP_FLAG if row != "B0" else 1
        er = [(flag, 0, 0x02000010, TICK_PA2, STAMP0 + 4000)]
        page = ring_page([(1, 2, 2 << 24, TICK_PA2, STAMP0 + 3000)])
        o = L.RING_BASE[3]
        page[o:o + 5] = er[0][0:1] + er[0][1:4] + (er[0][4],)
        page[L.SKIPPED] = 0 if row == "B0" else 1
        page2 = list(page)
        stopped = stop and row != "B0"
        bit18 = [0x20000000 | (0x40000 if (row != "B0" and level) else 0)] * 30
        a15 = {"H-W": 0x40000, "H-ALL": 0, "H-NONE": 0x40000}[w_hyp]
        a18 = {"H-W": 0, "H-ALL": 0, "H-NONE": 0x40000}[w_hyp]
        rec = base_rec(j, "stop" if stopped else "ok", page, watch=[[i * 1.5, b, 0x440] for i, b in enumerate(bit18)],
                       tool_rc=0 if row == "B0" else "timeout", tool_out="diff: 0 of 2048" if row == "B0" else "",
                       knobs={"hold_recovery": "N" if row == "B0" else "Y", "hold_recovery_after": "N"}, route="fw" if row == "B2" else "host")
        if row != "B0":
            rec["clears"] = {"bit15": {"ok": True, "reads": [{"ms_after": 1, "status": 0x20000000 | a15, "status2": 0x440}, {"ms_after": 3, "status": 0x20000000 | a15, "status2": 0x440}]},
                             "bit18": {"ok": True, "reads": [{"ms_after": 1, "status": 0x20000000 | a18, "status2": 0x440}, {"ms_after": 3, "status": 0x20000000 | a18, "status2": 0x440}]}}
            if stopped:
                rec["clears"]["bit29"] = {"ok": True, "reads": [{"ms_after": 1, "status": 0}, {"ms_after": 3, "status": 0x20000000}]}
                rec["sig"] = sig_pair("busy")
                rec["p3"] = {"answered": False, "ms": 500, "before": {}, "after": {}}
        recs[n] = skipped_rec(j) if (stop and row == "B2") else rec
    return tab, recs


def test_e3b_worlds():
    tab, recs = e3b_world(True, True, "H-W")
    st, summary = score_world("e3b", recs, exit_code=8)
    check(verdict(st, "H-STOP3") == "wins" and verdict(st, "H-FREE3") == "loses" and verdict(st, "H-LEVEL") == "wins" and verdict(st, "H-PULSE") == "loses"
          and verdict(st, "H-W") == "wins" and verdict(st, "H-ALL") == "loses" and verdict(st, "H-NONE") == "loses",
          f"e3b, world STOP3 + LEVEL + W: those win, FREE3, PULSE, ALL and NONE lose ({summary[:160]})")
    check("H-STOP3" in summary and "stops 1" in summary, "e3b: the summary reads H-STOP3 with 1 stop")
    for hyp in ("H-ALL", "H-NONE"):
        tab, recs = e3b_world(True, True, hyp)
        st, summary = score_world("e3b", recs, exit_code=8)
        check(verdict(st, hyp) == "wins" and all(verdict(st, m) == "loses" for m in ("H-W", "H-ALL", "H-NONE") if m != hyp), f"e3b, world {hyp}")
    tab, recs = e3b_world(False, True, "H-W")
    recs["b2"]["class"] = "ok"
    st, summary = score_world("e3b", recs)
    check(verdict(st, "H-FREE3") == "wins" and verdict(st, "H-STOP3") == "loses" and "H-FREE3" in summary, "e3b, world FREE3: it wins")
    tab, recs = e3b_world(True, False, "H-W")
    st, summary = score_world("e3b", recs, exit_code=8)
    check(verdict(st, "H-PULSE") == "wins" and verdict(st, "H-LEVEL") == "loses", "e3b, world PULSE: it wins")
    check(all(r[4] is None for r in st.t.rows if r[1] in ("bit18_after_bit15", "bit18_after_bit18")), "e3b: bit 18 never held: the clear rows are cannot tell")
    tab, recs = e3b_world(True, True, "H-W")
    recs["b1"]["page"][L.RING_BASE[3] + 1] = 5
    recs["b1"]["page2"] = list(recs["b1"]["page"])
    st, summary = score_world("e3b", recs, exit_code=8)
    check(any("b1" in ln and "end-of-render entries 0" in ln for ln in st.lines), "e3b: a ring without the end-of-render entry reads 0 entries")


# ---- K0 ---------------------------------------------------------------------------------------------------------------------
def k0f_rec(tab, **kw):
    j = tab["jobs"][0]
    rec = base_rec(j, "ok", None, srcversion={"loaded": L.EXPECT_SRCV, "installed": L.EXPECT_SRCV}, files={f: True for f in L.K0F_FILES},
                   defaults=dict(L.K0F_DEFAULTS), kicker={"w": 2, "wofs": 2, "rofs": 2, "kicks": 2, "raw": "kicker 2 ccbctl 2 2 kicks 2"},
                   kregnow={"rows": [[0x814, 0], [0x98, 0], [0x0, 0], [0x740, 0], [0xC00, 0x10], [0xC04, 0]], "raw": ""})
    rec.update(kw)
    return {j["name"]: rec}


def test_k0():
    tab = load("k0f")
    st, summary = score_world("k0f", k0f_rec(tab))
    check("defaults as designed" in summary and S.failed_controls(st) == [], "k0f: the defaults of the new module read as designed")
    for label, kw, part in (("kick_no_bump Y", {"defaults": dict(L.K0F_DEFAULTS, kick_no_bump="Y")}, "kick_no_bump"),
                            ("a clear row shown by kregnow", {"kregnow": {"rows": [[0x114, 0], [0xC00, 0], [0xC04, 0]], "raw": ""}}, "kregnow_no_clear_rows"),
                            ("the old srcversion", {"srcversion": {"loaded": L.OLD_SRCV, "installed": L.OLD_SRCV}}, "srcversion_new"),
                            ("a missing file", {"files": dict({f: True for f in L.K0F_FILES}, kicker=False)}, "files_present"),
                            ("a kicker line off format", {"kicker": {"w": None, "wofs": None, "rofs": None, "kicks": None, "raw": "x"}}, "kicker_format")):
        st, summary = score_world("k0f", k0f_rec(tab, **kw))
        check(S.failed_controls(st) and part in summary, f"k0f: {label}: a control fails ({summary[:70]})")
    # k0t on L1's kept dd-p1 output
    tab = load("k0t")
    text = gzip.open(FX / "dd-p1.txt.gz", "rb").read().decode()
    import re
    keep = [ln for ln in text.splitlines() if re.match(r"probe \S+: (o0 mixed|row \d+:)", ln)]
    gd = [j for j in tab["jobs"] if j["row"] == "GD"][0]
    px = [j for j in tab["jobs"] if j["row"] == "PX"][0]
    h = lambda b: hashlib.sha256(gzip.open(FX / b, "rb").read()).hexdigest()
    rec_gd = base_rec(gd, "ok", None, tool_rc=0, o0_lines=[ln.split(": ", 1)[1] for ln in text.splitlines() if re.match(r"probe \S+: o0 ", ln)],
                      lines_sha256=hashlib.sha256(("\n".join(keep) + "\n").encode()).hexdigest(),
                      dump_sha256={"dd-p1__0.param.bin": h("dd-p1.dd-p1__0.param.bin.gz"), "dd-p1__0.tadata.bin": h("dd-p1.dd-p1__0.tadata.bin.gz")},
                      status2_pre=0x400, status2_post=0x400)
    rec_px = base_rec(px, "ok", None, tool_rc=0, o0_lines=["o0 0xff00ff00 (256 of 256)"], status2_pre=0x400, status2_post=0x400)
    st, summary = score_world("k0t", {gd["name"]: rec_gd, px["name"]: rec_px})
    check("both jobs as L1 and L2 kept them" in summary and S.failed_controls(st) == [], f"k0t: L1's own kept dd-p1 output matches the frozen hashes ({summary[:90]})")
    bad = json.loads(json.dumps(rec_gd))
    bad["lines_sha256"] = "0" * 64
    st, summary = score_world("k0t", {gd["name"]: bad, px["name"]: rec_px})
    check(S.failed_controls(st) and "CONTROL DIFFERS" in summary, "k0t: a changed picture fails the control")
    bad = json.loads(json.dumps(rec_gd))
    bad["dump_sha256"]["dd-p1__0.param.bin"] = "0" * 64
    st, summary = score_world("k0t", {gd["name"]: bad, px["name"]: rec_px})
    check(not S.failed_controls(st) and any(r[1] == "param_sha256" and r[4] is False for r in st.t.rows),
          "k0t: a changed render buffer fails the held-out row, not a control (render buffers may depend on addresses)")
    bad = json.loads(json.dumps(rec_px))
    bad["status2_post"] = 0x440
    st, summary = score_world("k0t", {gd["name"]: rec_gd, px["name"]: bad})
    check(S.failed_controls(st), "k0t: STATUS2 left at 0x440 after the pixel job fails the control")


# ---- gates ------------------------------------------------------------------------------------------------------------------
def test_gates():
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        check(S.gate("k0f", root) == 0, "the first stage's gate is open")
        check(S.gate("k0t", root) == 1, "no kept stage.json of the previous stage: closed")
        for prev, nxt, code, want in (("k0f", "k0t", 0, 0), ("f", "t", 8, 0), ("f", "t", 4, 1), ("e2b", "e3h", 5, 1)):
            d = root / prev
            d.mkdir(exist_ok=True)
            (d / "stage.json").write_text(json.dumps({"exit": code, "run": "x", "why": "w"}))
            check(S.gate(nxt, root) == want, f"gate {nxt}: {prev} exit {code} -> {'open' if want == 0 else 'closed'}")
        (root / "k0h").mkdir()
        (root / "k0h" / "stage.json").write_text(json.dumps({"exit": 0, "run": "x"}))
        check(S.gate("f", root) == 0, "K1's first stage opens on K0's last: k0h exit 0")
    check(S.CONTROL_STAGES == ("k0f", "k0t", "k0c", "k0h"), "the K0 stages are the control stages (exit 9 on a failed control)")


def main():
    test_signature_and_marks()
    test_d_instrument()
    test_f_worlds()
    test_void_states()
    test_kb_worlds()
    test_e2b_worlds()
    test_e3_worlds()
    test_e3b_worlds()
    test_k0()
    test_gates()
    print(f"{len(FAIL)} failed" if FAIL else "all scorer checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
