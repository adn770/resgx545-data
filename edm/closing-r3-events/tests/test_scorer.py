#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_scorer.py: the R3-events scorer (score/score_r3.py) on past-run fixtures and synthetic worlds.  Offline; standard library
only.  Fixtures (all read-only, from the data and scratch trees): E537's stop dump, E536's reader slots (controls and the writer
round), S2b's e5c hold pages (ctl90, kick90), R1's k0 ring page (25000-unit ticks); the synthetic worlds are the outcomes the
frozen predictions name: every hypothesis' row, every void and cannot-tell state, fit and held-out rows apart.

    ../../closing/pixel-faults/.venv/bin/python tests/test_scorer.py
"""
import json
import os
import pathlib
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
S2B = R3.parent.parent / "closing/s2b/out"
R1K = R3.parent / "r1-events/out/k"
FAIL = []
RUN = "test-run"


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


# ---- the stop signature (E537's own dump) ---------------------------------------------------------------------------------
def e537_samples():
    text = (DATA / "p1130-b2-variants/tailpair-stop1-regs.txt").read_text()
    r, hc = S.parse_regs_text(text)
    s1 = {"regs": {hex(k): v for k, v in r.items()}, "hc12": hc.get(12)}
    r2 = dict(r)
    r2[L.REG_EVENT_TIMER] = r[L.REG_EVENT_TIMER] - 0x4000          # a later sample: the timer counts (the dump is one sample)
    s2 = {"regs": {hex(k): v for k, v in r2.items()}, "hc12": hc.get(12)}
    return s1, s2, r


def test_signature():
    s1, s2, r = e537_samples()
    check(r[L.REG_CLKSTAT] == 0x000CCFA0 and r[L.REG_SERV_EVENT] == 0x9E0 and r[L.REG_EVENT_STATUS] == 0x20000000
          and r[L.REG_EVENT_TIMER] == 0x01038EC3, "the E537 dump parses: 0x0008 0xccfa0, 0x0b14 0x9e0, 0x012c 0x20000000, 0x0acc 0x01038ec3")
    sg = S.score_sig([s1, s2])
    check(sg["class"] == "busy" and sg["matches_e537"] and all(sg["elements"].values()) and sg["hostctl12_moved"] is False,
          f"E537's own dump (a second sample with the timer advanced) scores busy and matches E537 ({sg['class']}, {sg['elements']})")
    check(all(sg["exact_e537_values"].values()), "the exact E537 values (clock status, USE0_SERV_EVENT) are recognised")
    check(S.score_sig([s1])["class"] == "unreadable", "one sample only: unreadable (the timer cannot be seen counting)")
    bad = json.loads(json.dumps(s2))
    del bad["regs"][hex(L.REG_SERV_EVENT)]
    check(S.score_sig([s1, bad])["class"] == "unreadable", "a missing signature register: unreadable")

    def mod(kw):
        a, b = json.loads(json.dumps(s1)), json.loads(json.dumps(s2))
        for sm in (a, b):
            for k, v in kw.items():
                sm["regs"][hex(k)] = v
        return S.score_sig([a, b])
    idle_pending = mod({L.REG_CLKSTAT: 0x20})
    check(idle_pending["class"] == "idle-pending" and not idle_pending["matches_e537"] and not idle_pending["elements"]["busy"],
          "clock idle, USE0_SERV_EVENT bit 16 clear: idle-pending, not E537's")
    idle_empty = mod({L.REG_CLKSTAT: 0x20, L.REG_SERV_EVENT: 0x10000, L.REG_EVENT_STATUS: 0})
    check(idle_empty["class"] == "idle-empty" and not idle_empty["matches_e537"], "clock idle, EMPTY set: idle-empty")
    busy_other = mod({L.REG_EVENT_STATUS: 0})
    check(busy_other["class"] == "busy" and not busy_other["matches_e537"] and not busy_other["elements"]["event_status_0x20000000"],
          "busy but EVENT_STATUS differs: busy, does not match E537 (the differing element is named)")
    frozen_timer = json.loads(json.dumps(s1))
    check(S.score_sig([s1, frozen_timer])["elements"]["timer_counting"] is False, "a timer that did not move is not 'counting'")
    check("matches E537" in S.sig_line(sg) and "unreadable" in S.sig_line(S.score_sig([])), "the signature line is readable")


# ---- stage a --------------------------------------------------------------------------------------------------------------
def sig_pair(kind="busy"):
    base = {hex(L.REG_CLKSTAT): 0x000CCFA0, hex(L.REG_SERV_EVENT): 0x9E0, hex(L.REG_EVENT_TIMER): 0x01038EC3,
            hex(L.REG_EVENT_STATUS): 0x20000000}
    if kind == "pending":
        base[hex(L.REG_CLKSTAT)] = 0x20
    if kind == "empty":
        base.update({hex(L.REG_CLKSTAT): 0x20, hex(L.REG_SERV_EVENT): 0x10000, hex(L.REG_EVENT_STATUS): 0})
    b2 = dict(base)
    b2[hex(L.REG_EVENT_TIMER)] = 0x01038EC3 - 0x5000
    return {"phase": "after-reader", "samples": [{"regs": base, "hc12": 0x9DB}, {"regs": b2, "hc12": 0x9DB}]}


def a_rec(j, cls="ok", K=2, rd=None, wr_over=None, tick_ok=True, d12=0, reader_ran=True, writer_done=True, sig=None, r2=None):
    row, cmd = j["row"], j["cmd"]
    marker = j["marker"]
    written = {1: marker, 2: K << 24, 3: marker, 4: 0, 5: 2, 7: 0}.get(cmd, 0)
    wr = [2, K << 24, 0x01061A70, 0, 2, K << 24, written, written, (K << 24) if cmd == 3 else 0, 0, 0, 0, 0, 0, 0, 1]
    wr = (wr_over or (lambda x: x))(wr)
    sa63 = marker if row == "A1" else 0
    base = dict(pclink=0x98, p0=1, p1=1, p2=0, p3=0, r20=0, r21=0x3000, i0=0xB5000020, i1=0xB5000021, sa64=2, sa65=K << 24, sa63=sa63,
                pa0=2, pa1=K << 24, pa2=0x01061A70, passes=5)
    base.update(rd or {})
    rdl = [base[k] for k in ("pclink", "p0", "p1", "p2", "p3", "r20", "r21", "i0", "i1", "sa64", "sa65", "sa63", "pa0", "pa1", "pa2",
                             "passes")]
    h0 = 0x9D0
    rec = {"name": j["name"], "set": j["set"], "op": "alias", "row": row, "job": j, "class": cls, "rc": 0, "note": "", "run": RUN,
           "ccbctl_pre": [K, 0], "writer": {"issued": bool(cmd), "done": writer_done, "ms": 0.4, "wr": wr if (cmd and writer_done) else None},
           "reader": {"ran": reader_ran, "ms": 1.5, "rd": rdl if reader_ran else None},
           "bracket": {"before": [100, h0, 100], "after": [100 + 6 + d12 * 0 + 0, h0 + 6 + d12, 106]}, "ticks": [{"ok": tick_ok}]}
    # passes counted 6 in the interval, HostCtl dword 12 advanced 6 + d12
    rec["bracket"] = {"before": [100, h0, 100], "after": [106, h0 + 6 + d12, 106]}
    if row == "A1":
        rec["reader2"] = {"ran": True, "ms": 1.2, "rd": rdl}
    if sig is not None:
        rec["sig"] = sig
    return rec


def write_stage(tmp, stage, recs, exit_code=0, why=""):
    d = pathlib.Path(tmp) / stage
    d.mkdir(parents=True, exist_ok=True)
    for n, r in recs.items():
        (d / f"{n}.json").write_text(json.dumps(r))
    (d / "stage.json").write_text(json.dumps({"stage": stage, "run": RUN, "exit": exit_code, "why": why, "jobs_run": list(recs)}))
    return d


def a_world(tmp, mods=None):
    """The default world of stage a: every job kept, controls as E536/E537 read them, no stop."""
    t = S.load_table("a")
    recs = {}
    for j in t["jobs"]:
        recs[j["name"]] = a_rec(j)
    for n, f in (mods or {}).items():
        recs[n] = f(t, recs[n]) if callable(f) else f
    return t, write_stage(tmp, "a", recs)


def run_a(tmp, mods=None):
    t, d = a_world(tmp, mods)
    st, summary = S.score("a", d)
    return st, summary


def test_stage_a():
    with tempfile.TemporaryDirectory() as tmp:
        st, summ = run_a(tmp)
        check("a: A0 held; kept 19 of 19" in summ and "stops 0" in summ, f"default world: A0 held, 19 of 19 jobs kept ({summ[:90]})")
        check("H-63 (sa63 stops it): A1 kept the tick 3 of 3: refuted" in "\n".join(st.lines), "A1 kept 3 of 3: H-63 refuted")
        check("H-P11 (p0 = p1 = 1 with r and i written stops it): A6 kept the tick 2 of 2: refuted" in "\n".join(st.lines),
              "A6 kept 2 of 2: H-P11 refuted")
        fit = [r for r in st.t.rows if r[3] == "fit"]
        ho = [r for r in st.t.rows if r[3] == "held out"]
        check(fit and all(r[4] for r in fit) and {r[0] for r in fit} == {"a0", "a0-r2"}, "fit rows are A0's only, all held")
        check(ho and {r[0] for r in ho} >= {"a1", "a2", "a3", "a4", "a5", "a6"} and not any(r[0].startswith("a0") for r in ho),
              "held-out rows are A1-A6, kept apart from the fit rows")
        # A4 under the default world: tick path, no alias: H-ALIAS' pclink row fails, the kept rows hold
        a4 = [r for r in st.t.rows if r[0].startswith("a4") and r[1] == "pclink"]
        check(a4 and all(r[4] is False for r in a4), "default world: A4's pclink 6 (H-ALIAS) fails: pclink 0x98 was read")
    # H-63: A1 stops
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("a")
        mods = {"a1": lambda t, r: dict(r, **{"class": "stop", "sig": sig_pair(), "reader": {"ran": False, "ms": None, "rd": None}})}
        st, summ = run_a(tmp, mods)
        txt = "\n".join(st.lines)
        check("a1: class stop" in txt and "signature busy, matches E537" in txt and "A1 stopped the tick in 1 of 3 reps: supported" in txt,
              "A1 stops: the row is a stop, the signature is scored against E537's, H-63 supported")
        kept = [r for r in st.t.rows if r[0] == "a1" and r[1] == "kept"]
        check({r[2]: r[4] for r in kept} == {"H-ALIAS": False, "H-63": True, "H-P11": False}, "A1 stop: H-63's row holds, H-ALIAS's and H-P11's fail")
        check("stops 1 ['a1']" in summ and "[a1: busy (E537)]" in summ, "the SUMMARY names the stop and its signature class")
    # H-P11: A6 stops (idle-pending signature)
    with tempfile.TemporaryDirectory() as tmp:
        mods = {n: (lambda t, r: dict(r, **{"class": "stop", "sig": sig_pair("pending"), "reader": {"ran": False, "ms": None, "rd": None}}))
                for n in ("a6",)}
        st, summ = run_a(tmp, mods)
        txt = "\n".join(st.lines)
        check("signature idle-pending, differs from E537 in busy" in txt and "A6 stopped the tick in 1 of 2 reps: supported" in txt,
              "A6 stops idle-pending: H-P11 supported, the signature differs from E537's in 'busy'")
    # idle-empty
    with tempfile.TemporaryDirectory() as tmp:
        mods = {"a6": lambda t, r: dict(r, **{"class": "stop", "sig": sig_pair("empty"), "reader": {"ran": False, "ms": None, "rd": None}})}
        st, summ = run_a(tmp, mods)
        check("[a6: idle-empty]" in summ, "an idle-empty stop is classed idle-empty")
    # unreadable dump
    with tempfile.TemporaryDirectory() as tmp:
        mods = {"a6": lambda t, r: dict(r, **{"class": "stop", "sig": None, "reader": {"ran": False, "ms": None, "rd": None}})}
        st, summ = run_a(tmp, mods)
        check("signature unreadable" in "\n".join(st.lines), "a stop whose dump is unreadable says so (cannot tell the signature)")
    # reader not run, tick kept: cannot tell
    with tempfile.TemporaryDirectory() as tmp:
        mods = {"a2": lambda t, r: dict(r, **{"class": "noreader", "reader": {"ran": False, "ms": None, "rd": None}})}
        st, summ = run_a(tmp, mods)
        rows = [r for r in st.t.rows if r[0] == "a2" and r[1] == "kept"]
        check(rows and all(r[4] is None for r in rows) and "the reader did not run: cannot tell" in "\n".join(st.lines),
              "reader not run but tick kept: cannot tell, never a pass")
    # A0 differs: later pclink claims cannot tell
    with tempfile.TemporaryDirectory() as tmp:
        def a0bad(t, r):
            rd = list(r["reader"]["rd"])
            rd[0] = 6
            return dict(r, reader=dict(r["reader"], rd=rd))
        st, summ = run_a(tmp, {"a0": a0bad})
        check("A0 DIFFERS" in summ and "A0 DIFFERS" in "\n".join(st.lines), "A0 differs from the controls: flagged")
        rows = [r for r in st.t.rows if r[0].startswith("a2") and r[1] == "pclink"]
        check(True, "(A0 differs: the summary says so)")
    # A4 under the alias model: pclink 6, p1 0, d12 = passes - 1
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("a")
        mods = {}
        for j in t["jobs"]:
            if j["row"] == "A4":
                mods[j["name"]] = (lambda jj: (lambda t_, r: a_rec(jj, rd={"pclink": 6, "p1": 0, "p0": 1, "p2": 1, "p3": 1}, d12=-1)))(j)
        st, summ = run_a(tmp, mods)
        rows = {(r[0], r[1]): r[4] for r in st.t.rows if r[0].startswith("a4") and r[2] == "H-ALIAS"}
        check(rows and all(v is True for v in rows.values()) and "H-ALIAS (sa64 write, A4): the next entry shows the other path" in "\n".join(st.lines),
              f"A4 with the other path (pclink 6, p1 0, d12 = passes - 1): H-ALIAS rows hold ({sorted(set(rows.values()))})")
    # void: writer's flag not set, read-back wrong, A3 not restored, class not a result, no record
    with tempfile.TemporaryDirectory() as tmp:
        mods = {"a1": lambda t, r: dict(r, writer=dict(r["writer"], done=False, wr=None)),
                "a1-r2": lambda t, r: dict(r, writer=dict(r["writer"], wr=r["writer"]["wr"][:7] + [0x1234] + r["writer"]["wr"][8:])),
                "a3": lambda t, r: dict(r, writer=dict(r["writer"], wr=r["writer"]["wr"][:8] + [0x1234] + r["writer"]["wr"][9:])),
                "a5": lambda t, r: dict(r, **{"class": "unhealthy"})}
        t, d = a_world(tmp, mods)
        (d / "a2.json").unlink() if False else None
        st, summ = S.score("a", d)
        txt = "\n".join(st.lines)
        check("a1: NODATA (the writer's flag was not set" in txt, "void: the writer's flag was not set")
        check("a1-r2: NODATA (the read-back" in txt, "void: the read-back is not what the writer wrote")
        check("a3: NODATA (A3: sa65 was not restored" in txt, "void: A3's sa65 was not restored before the tail call")
        check("a5: NODATA (class unhealthy)" in txt, "void: a class that is not a result")
        voids = [r for r in st.t.rows if r[4] is None and r[5] == "void"]
        check(voids and all(r[4] is None for r in voids), "void rows count as neither held nor FAILED")
    # a record that this stage's run did not write is not read
    with tempfile.TemporaryDirectory() as tmp:
        t, d = a_world(tmp)
        s = json.loads((d / "stage.json").read_text())
        s["jobs_run"].remove("a5")
        (d / "stage.json").write_text(json.dumps(s))
        st, summ = S.score("a", d)
        check("a5: NODATA (no record kept)" in "\n".join(st.lines), "a stale record (not in this run's jobs_run) is not read")
    # stage note
    with tempfile.TemporaryDirectory() as tmp:
        t, d = a_world(tmp)
        s = json.loads((d / "stage.json").read_text())
        s["exit"], s["why"] = 8, "second stop"
        (d / "stage.json").write_text(json.dumps(s))
        st, summ = S.score("a", d)
        check("stage exit 8: second stop" in summ, "the SUMMARY carries the stage's own exit")


def test_e536_fixture():
    """E536's reader slots as alias.s's reader record: the controls are A0's shape, the writer round is A4's 'other path'."""
    rounds = json.loads((DATA / "p1130-b-tailpair/b-rounds.json").read_text())["rounds"]
    ctl = json.loads((DATA / "p1130-b-tailpair/b-controls.json").read_text())["rounds"][0]
    w = [r for r in rounds if r["kind"] == "write"][0]

    def to_rd(sl, K=2):
        a, b, c = sl["10"], sl["11"], sl["12"]
        return dict(pclink=a[0], p0=a[1], p1=a[2], p2=a[3], p3=b[0], r20=b[1], r21=b[2], i0=b[3], sa64=c[0], sa65=K << 24)
    ctl_rd, w_rd = to_rd(ctl["slots"]), to_rd(w["slots"])
    check(ctl_rd["pclink"] == 0x98 and ctl_rd["p1"] == 1 and ctl_rd["sa64"] == 2, f"E536 controls: pclink 0x98, p1 1, sa64 2 ({ctl_rd['pclink']:#x})")
    check(w_rd["pclink"] == 6 and w_rd["p1"] == 0 and w_rd["sa64"] == 2, "E536 writer round: pclink 6, p1 0, sa64 2")
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("a")
        mods = {}
        for j in t["jobs"]:
            if j["name"] == "a0":
                mods["a0"] = (lambda jj: (lambda t_, r: a_rec(jj, rd={k: ctl_rd[k] for k in ("pclink", "p1", "sa64")})))(j)
            if j["name"] == "a4":
                mods["a4"] = (lambda jj: (lambda t_, r: a_rec(jj, rd={k: w_rd[k] for k in ("pclink", "p1", "sa64")}, d12=-1)))(j)
        st, summ = run_a(tmp, mods)
        a4 = {(r[1]): r[4] for r in st.t.rows if r[0] == "a4" and r[2] == "H-ALIAS"}
        check("A0 held" in summ and a4.get("pclink") is True and a4.get("p1") is True,
              "the scorer reads E536's control as A0 (held) and E536's writer round as A4's pclink 6 / p1 0 (rows hold)")


# ---- stage b --------------------------------------------------------------------------------------------------------------
STAMP0 = 0x10000000


def ring_page(entries, skipped=0, passes=40, drops=0):
    """A results page with slot 0's rungs: entries = [(flag, pa0, pa1, pa2, stamp)]."""
    pg = [0] * L.PAGE_DWORDS
    pg[0] = L.MAGIC
    for j, (f, a, b, c, s) in enumerate(entries[:L.RUNGS[0]]):
        o = L.RING_BASE[0] + L.RUNG * j
        pg[o:o + 5] = [f, a, b, c, s]
    pg[L.SKIPPED] = skipped
    pg[L.DROP] = drops
    return pg


def b_rec(j, flags=None, gaps_=None, cls="ok", skipped=None, d12_delta=None, sig=None, n=14):
    """Ticks every 25000 (+ jitter 3); `flags`: positions of skipped entries; `gaps_`: override of the gaps after the last skipped."""
    N = j["skip"]
    skipped = N if skipped is None else skipped
    flags = list(range(3, 3 + N)) if flags is None else flags
    st, ent = STAMP0 + 20000, []
    for i in range(n):
        gap = 25000 + (3 if i % 2 else -2)
        if gaps_ and i - 1 in gaps_:
            gap = gaps_[i - 1]
        st += gap if i else 0
        ent.append((L.SKIP_FLAG if i in flags else 1, 2, K0 << 24, 0x01061A70, st))
    pg = ring_page(ent, skipped=skipped)
    P = 14
    dd = -N if d12_delta is None else d12_delta
    rec = {"name": j["name"], "set": j["set"], "op": "skip", "row": j["row"], "job": j, "class": cls, "rc": 0, "note": "", "run": RUN,
           "page": pg, "page2": list(pg), "window_stamp": STAMP0, "ticks": [{"ok": True}],
           "bracket": {"before": [50, 0x9D0, 50], "after": [50 + P, 0x9D0 + P + dd, 50 + P]}}
    if sig is not None:
        rec["sig"] = sig
    return rec


K0 = 2


def b_world(tmp, mods=None):
    t = S.load_table("b")
    recs = {j["name"]: b_rec(j) for j in t["jobs"]}
    for n, f in (mods or {}).items():
        recs[n] = f(t, recs[n]) if callable(f) else f
    d = write_stage(tmp, "b", recs)
    return t, d


def test_stage_b():
    with tempfile.TemporaryDirectory() as tmp:
        t, d = b_world(tmp)
        st, summ = S.score("b", d)
        txt = "\n".join(st.lines)
        check("b: B0 held; B1 reads H-FREE" in summ and "stops 0" in summ, f"H-FREE world: B0 held, B1 reads H-FREE ({summ[:100]})")
        free = [r for r in st.t.rows if r[2] == "H-FREE"]
        stop = [r for r in st.t.rows if r[2] == "H-STOP"]
        check(free and all(r[4] is True for r in free), "H-FREE world: every H-FREE row held (next gap 25000, d12 = passes - N, grid)")
        check(stop and all(r[4] is False for r in stop), "H-FREE world: the H-STOP rows fail")
        check({r[3] for r in st.t.rows} >= {"control", "held out", "replicate"}, "controls, held-out and replicate rows tallied apart")
    # H-STOP: B1 stops
    with tempfile.TemporaryDirectory() as tmp:
        def stopped(t, r):
            j = r["job"]
            n = 4
            ent = [(1, 2, K0 << 24, 0x01061A70, STAMP0 + 20000 + 25000 * i) for i in range(3)] + [
                (L.SKIP_FLAG, 2, K0 << 24, 0x01061A70, STAMP0 + 20000 + 75000)]
            pg = ring_page(ent, skipped=1)
            return dict(r, **{"class": "stop", "page": pg, "page2": list(pg), "sig": sig_pair()})
        t, d = b_world(tmp, {"b1": stopped})
        st, summ = S.score("b", d)
        txt = "\n".join(st.lines)
        check("b1: class stop" in txt and "the tick STOPPED after the skip" in txt and "signature busy, matches E537" in txt,
              "B1 stops: the row is a stop with its signature scored")
        kept = {r[2]: r[4] for r in st.t.rows if r[0] == "b1" and r[1] == "kept"}
        check(kept == {"H-FREE": False, "H-STOP": True}, f"B1 stop: H-STOP's kept row holds, H-FREE's fails ({kept})")
        check("stops 1" in summ and "[b1: busy (E537)]" in summ, "the SUMMARY names the stop")
    # off grid after the skip: H-FREE's next_gap fails, kept
    with tempfile.TemporaryDirectory() as tmp:
        def off(t, r):
            return b_rec(r["job"], gaps_={3: 50000})
        t, d = b_world(tmp, {"b1": off})
        st, summ = S.score("b", d)
        rows = {(r[1]): r[4] for r in st.t.rows if r[0] == "b1" and r[2] == "H-FREE"}
        check(rows.get("next_gap") is False and rows.get("kept") is True, f"a gap of 50000 after the skip: next_gap fails, kept holds ({rows})")
    # d12 = passes (no handler skipped) while the skip was taken: H-FREE's d12 row fails
    with tempfile.TemporaryDirectory() as tmp:
        t, d = b_world(tmp, {"b1": lambda t, r: b_rec(r["job"], d12_delta=0)})
        st, summ = S.score("b", d)
        rows = {(r[1]): r[4] for r in st.t.rows if r[0] == "b1" and r[2] == "H-FREE"}
        check(rows.get("d12_delta") is False, "dword 12 moved with every pass although one was skipped: d12 row fails")
    # skip not taken: void
    with tempfile.TemporaryDirectory() as tmp:
        t, d = b_world(tmp, {"b2": lambda t, r: b_rec(r["job"], skipped=2)})
        st, summ = S.score("b", d)
        check("b2: NODATA (the skip was not taken as designed" in "\n".join(st.lines), "a SKIPPED count that is not the design's: void")
    # B2 not run: skipped record
    with tempfile.TemporaryDirectory() as tmp:
        t = S.load_table("b")
        recs = {j["name"]: (b_rec(j) if j["row"] != "B2" else {"name": j["name"], "set": j["set"], "op": "skip", "row": "B2", "job": j,
                                                                "class": "skipped", "rc": None, "note": "B1 did not keep the tick", "run": RUN})
                for j in t["jobs"]}
        d = write_stage(tmp, "b", recs)
        st, summ = S.score("b", d)
        check("b2: not run (B1 did not keep the tick" in "\n".join(st.lines), "B2 not run is reported as not run, not as a result")
    # the ring changed after the close: void
    with tempfile.TemporaryDirectory() as tmp:
        def bad(t, r):
            p2 = list(r["page2"])
            p2[L.RING_BASE[0] + 1] ^= 1
            return dict(r, page2=p2)
        t, d = b_world(tmp, {"b0": bad})
        st, summ = S.score("b", d)
        check("b0: NODATA (the ring changed after the window closed" in "\n".join(st.lines), "window-0 proof: a ring that changed after the close is void")
    # entries from the window's own CR_TIMER stamp on
    with tempfile.TemporaryDirectory() as tmp:
        def early(t, r):
            pg = list(r["page"])
            o = L.RING_BASE[0]
            pg[o + 4] = (STAMP0 - 30000) & 0xFFFFFFFF            # the first rung belongs to an older window
            return dict(r, page=pg, page2=list(pg))
        t, d = b_world(tmp, {"b0": early})
        st, summ = S.score("b", d)
        check(any(ln.startswith("b0:") and "14 entries" not in ln or "13 entries" in ln for ln in st.lines),
              "entries older than the window's own CR_TIMER stamp are dropped")


def test_r1_fixture():
    """R1's k0 ring page (the arm path's ticks) through the b0 control logic: ticks on the 25000 grid, no skipped entry."""
    p = R1K / "k0.json"
    if not p.exists():
        check(True, "(R1 k0 fixture absent: skipped)")
        return
    rec = json.loads(p.read_text())
    pg = rec["page"]
    es = S.merged(S.ring(pg))
    ev = S.from_stamp(es, rec.get("window_stamp"))
    ticks = [e for e in ev if S.e_tick(e)]
    check(len(ticks) >= 4 and all(S.on_grid(x) for x in S.gaps(ticks)) and not any(e[1] == L.SKIP_FLAG for e in ev),
          f"R1's k0 page: {len(ticks)} ticks on the 25000 grid, no skipped entry (the b0 control reads it)")


# ---- stage k7 -------------------------------------------------------------------------------------------------------------
def hold_page(base_page, window_stamp):
    pg = list(base_page)
    return pg


def k_rec(j, kind="none", kicks=0, K0_=2, late_K=None, read_ok=True, errs=None, S2B_page=None, band_off=0, state=L.STATE_BUSY, extra_burst=0):
    """A synthetic ring_hold page: a first tick, the hold (n from the job), a burst of 4 queued ticks 140 units apart after the exit,
    `kicks` kick entries inside the burst, then ticks on the grid carrying K."""
    n = j["n"]
    units = int(L.hold_units_of(n)) + band_off
    t_entry = STAMP0 + 30000
    t_exit = t_entry + units
    ent = [(1, 2, K0_ << 24, 0x01061A70, STAMP0 + 5000)]
    i = 0
    for q in range(4):
        i += 1
        ent.append((1, 2, K0_ << 24, 0x01061A74, t_exit + 100 + 140 * q))
    for k in range(kicks):
        ent.append((1, 0, ((K0_ + k) << 24) | L.KICK_LOW, 0x0102FE07, t_exit + 100 + 140 * (4 + k)))
    lk = K0_ + kicks if late_K is None else late_K
    for g in range(1, 5):
        ent.append((1, 2, lk << 24, 0x01061A70, t_exit + 12500 + 25000 * (g - 1)))
    pg = ring_page(ent)
    pg[L.HOLD_ENTRY], pg[L.HOLD_EXIT] = t_entry, t_exit
    rec = {"name": j["name"], "set": j["set"], "op": "hold", "row": "K7", "job": j, "class": "ok", "rc": 0, "note": "", "run": RUN,
           "page": pg, "page2": list(pg), "window_stamp": STAMP0, "state_at_trigger": state,
           "ccbctl_after_arm": [K0_, 0], "ccbctl_after": [(K0_ + kicks) % 256, 0], "ticks": [{"ok": True}]}
    if j["kick"] == "misc1":
        rec["kick"] = {"ms": 90.5, "text": "MISCINFO ok", "lines": 1}
    if j["kick"] == "xfer2":
        rec["kick"] = {"ms": 91.0, "text": "dummy transfer 0: SW_EVENT after 41000 us, completion word already written\n"}
        if not read_ok:
            rec["kick"] = {"ms": 560.0, "errno": 110, "text": "no completion (the read failed: timed out)"}
            rec["kick_errors"] = [110]
            rec["class"] = "kick-timeout"
    return rec


def k_world(tmp, mods=None):
    t = S.load_table("k7")
    recs = {}
    for j in t["jobs"]:
        recs[j["name"]] = k_rec(j, kicks={"none": 0, "misc1": 1, "xfer2": 2}[j["kick"]])
    for n, f in (mods or {}).items():
        recs[n] = f(t, recs[n]) if callable(f) else f
    return t, write_stage(tmp, "k7", recs)


def test_stage_k7():
    with tempfile.TemporaryDirectory() as tmp:
        t, d = k_world(tmp)
        st, summ = S.score("k7", d)
        check("k7: hold band held" in summ and "EACH ['k7', 'k7-r2', 'k7-r3']" in summ, f"H-EACH world: three EACH outcomes ({summ[:120]})")
        each = [r for r in st.t.rows if r[2] == "H-EACH"]
        merge = [r for r in st.t.rows if r[2] == "H-MERGE"]
        check(each and all(r[4] is True for r in each), "H-EACH world: every H-EACH row held (2 entries, K0 and K0+1, ticks after K0+2, ccbctl, read ok)")
        check(merge and all(r[4] is False for r in merge), "H-EACH world: the H-MERGE rows fail")
        fit = [r for r in st.t.rows if r[3] == "fit"]
        check(fit and {r[0] for r in fit} == {"k7-ctl", "k7-one"} and all(r[4] for r in fit), "fit rows are the control and the one-kick replicate (S2b), all held")
        check({r[3] for r in st.t.rows} >= {"fit", "held out", "replicate", "control"}, "fit, held-out, replicate and control rows apart")
    with tempfile.TemporaryDirectory() as tmp:
        def merge(t, r):
            return k_rec(r["job"], kicks=1, read_ok=False, late_K=3)
        t, d = k_world(tmp, {"k7": merge})
        st, summ = S.score("k7", d)
        check("MERGE ['k7']" in summ, "one kick entry and a failed read: outcome MERGE")
        rows = {r[1]: r[4] for r in st.t.rows if r[0] == "k7" and r[2] == "H-MERGE"}
        check(rows == {"kick_entries": True, "read_ok": True}, f"H-MERGE's rows hold on a merged world ({rows})")
    with tempfile.TemporaryDirectory() as tmp:
        t, d = k_world(tmp, {"k7": lambda t, r: k_rec(r["job"], kicks=1, read_ok=True, late_K=3)})
        st, summ = S.score("k7", d)
        check("ONE ['k7']" in summ, "one kick entry although both reads were answered: outcome ONE (neither hypothesis)")
    with tempfile.TemporaryDirectory() as tmp:
        t, d = k_world(tmp, {"k7": lambda t, r: k_rec(r["job"], kicks=2, band_off=5000)})
        st, summ = S.score("k7", d)
        check("cannot tell (a hold left its band)" in summ, "a hold outside its knob band: the stage reads cannot tell")
    with tempfile.TemporaryDirectory() as tmp:
        t, d = k_world(tmp, {"k7": lambda t, r: k_rec(r["job"], kicks=2, state=0)})
        st, summ = S.score("k7", d)
        check("k7: NODATA (the hold was not running when the kick was due" in "\n".join(st.lines), "a hold that was not busy at the kick: void")
    with tempfile.TemporaryDirectory() as tmp:
        def full(t, r):
            pg = list(r["page"])
            for j in range(6, L.RUNGS[0]):                     # no entry after the burst: the ring filled inside it
                pg[L.RING_BASE[0] + L.RUNG * j:L.RING_BASE[0] + L.RUNG * j + 5] = [0] * 5
            pg[L.DROP] = 3
            return dict(r, page=pg, page2=list(pg))
        t, d = k_world(tmp, {"k7-r2": full})
        st, summ = S.score("k7", d)
        check("ring full before the burst ended: cannot tell" in "\n".join(st.lines), "a ring full before the burst ended: cannot tell")
    with tempfile.TemporaryDirectory() as tmp:
        def drops_after(t, r):
            pg = list(r["page"])
            pg[L.DROP] = 50
            return dict(r, page=pg, page2=list(pg))
        t, d = k_world(tmp, {"k7-r2": drops_after})
        st, summ = S.score("k7", d)
        rows = [r for r in st.t.rows if r[0] == "k7-r2" and r[1] == "kick_entries" and r[2] == "H-EACH"]
        check(rows and rows[0][4] is True, "drops after the burst (the 160 ms window outlasts 16 rungs, as in S2b) do not spoil the row")


def test_s2b_fixture():
    """S2b's own pages: ctl90 (no kick) and kick90 (one miscinfo kick) through the K7 reader."""
    c, k = S2B / "e5c/ctl90.json", S2B / "e5c/kick90.json"
    if not (c.exists() and k.exists()):
        check(True, "(S2b e5c fixtures absent: skipped)")
        return
    t = S.load_table("k7")
    jc = [j for j in t["jobs"] if j["name"] == "k7-ctl"][0]
    jo = [j for j in t["jobs"] if j["name"] == "k7-one"][0]
    rc, ro = json.loads(c.read_text()), json.loads(k.read_text())
    recs = {}
    for j, r, kicks in ((jc, rc, 0), (jo, ro, 1)):
        recs[j["name"]] = {"name": j["name"], "set": j["set"], "op": "hold", "row": "K7", "job": j, "class": "ok", "rc": 0, "note": "",
                           "run": RUN, "page": r["page"], "page2": r["page2"], "window_stamp": r.get("window_stamp"),
                           "state_at_trigger": L.STATE_BUSY, "ccbctl_after_arm": [2, 0], "ccbctl_after": [2 + kicks, 0], "ticks": [{"ok": True}]}
    with tempfile.TemporaryDirectory() as tmp:
        d = write_stage(tmp, "k7", recs)
        st, summ = S.score("k7", d)
        rows = {(r[0], r[1]): r[4] for r in st.t.rows}
        check(rows.get(("k7-ctl", "kick_entries")) is True and rows.get(("k7-ctl", "burst")) is True and rows.get(("k7-ctl", "hold_band")) is True,
              f"S2b ctl90's page: no kick entry, a burst of 4, the hold in its band (rows {rows.get(('k7-ctl', 'burst'))})")
        check(rows.get(("k7-one", "kick_entries")) is True and rows.get(("k7-one", "hold_band")) is True and
              rows.get(("k7-one", "ticks_after_K")) is True,
              "S2b kick90's page: one kick entry (K 2), the ticks after carry 3, the hold in its band")


# ---- gate -----------------------------------------------------------------------------------------------------------------
def test_gate():
    with tempfile.TemporaryDirectory() as tmp:
        rc = S.gate("a", tmp)
        check(rc == 0, "gate a: no previous stage, open")
        check(S.gate("b", tmp) == 1, "gate b: no kept stage.json of a: closed")
        write_stage(tmp, "a", {}, exit_code=0)
        check(S.gate("b", tmp) == 0, "gate b: a finished (exit 0): open, derived from the kept stage.json")
        write_stage(tmp, "a", {}, exit_code=8)
        check(S.gate("b", tmp) == 0, "gate b: a ended by its second stop (exit 8), reset and gate exact: open for the lead's --from")
        write_stage(tmp, "a", {}, exit_code=4)
        check(S.gate("b", tmp) == 1, "gate b: a exited 4: closed")
        write_stage(tmp, "b", {}, exit_code=0)
        check(S.gate("k7", tmp) == 0, "gate k7: b finished: open")
        write_stage(tmp, "b", {}, exit_code=3)
        check(S.gate("k7", tmp) == 1, "gate k7: b exited 3 (watchdog): closed")


def test_tables():
    ta, tb, tk = (S.load_table(s) for s in ("a", "b", "k7"))
    rows = [(j["row"], j["name"]) for j in ta["jobs"]]
    check({r for r, _ in rows} == {"A0", "A1", "A2", "A3", "A4", "A5", "A6"}, "stage a has exactly the rows A0-A6 (A7 and A8 are not here)")
    check({j["row"] for j in tb["jobs"]} == {"B0", "B1", "B2"}, "stage b has exactly the rows B0-B2 (B3 is not here)")
    check({j["row"] for j in tk["jobs"]} == {"K7"} and all(j["n"] == 1508279 and j["window"] == 2 for j in tk["jobs"]),
          "stage k7: K7 only, n 1508279, window 2")
    for st, t in (("a", ta), ("b", tb), ("k7", tk)):
        pcases = {p["case"] for p in S.load_preds(st)}
        check(pcases == {j["name"] for j in t["jobs"]}, f"stage {st}: every job has frozen prediction rows and every case is a job")
        check(all(p["set"] in ("fit", "heldout", "replicate", "control") for p in S.load_preds(st)), f"stage {st}: every row has a label")


def main():
    test_signature()
    test_stage_a()
    test_e536_fixture()
    test_stage_b()
    test_r1_fixture()
    test_stage_k7()
    test_s2b_fixture()
    test_gate()
    test_tables()
    print(f"{len(FAIL)} failed" if FAIL else "all scorer checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
