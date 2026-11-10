#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_scorer.py: the C3 scorer (score/score_c3.py) on past-run fixtures and synthetic worlds.  Offline; standard library only.
Fixtures (read-only, from the data tree): E537's stop dump, E536's reader slots (the controls, a writer round, a fill round); the
synthetic worlds are the outcomes the frozen predictions name (H-KEEP, H-ALL, H-SET), every void and cannot-tell state, and
fit, held-out, replicate and control rows apart.

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
os.environ["C3_NO_FREEZE_CHECK"] = "1"
import c3layout as L  # noqa: E402
import score_c3 as S  # noqa: E402

DATA = pathlib.Path.home() / "src/resgx545-data/firmware-tasks"
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


# ---- the world: a simulated laptop at the level of what the reader sees -----------------------------------------------------
def sig_pair(kind="busy"):
    base = {hex(L.REG_CLKSTAT): 0x000CCFA0, hex(L.REG_SERV_EVENT): 0x9E0, hex(L.REG_EVENT_TIMER): 0x01038EC3,
            hex(L.REG_EVENT_STATUS): 0x20000000}
    if kind == "pending":
        base[hex(L.REG_CLKSTAT)] = 0x20
    if kind == "empty":
        base.update({hex(L.REG_CLKSTAT): 0x20, hex(L.REG_SERV_EVENT): 0x10000, hex(L.REG_EVENT_STATUS): 0})
    b2 = dict(base)
    b2[hex(L.REG_EVENT_TIMER)] = 0x01038EC3 - 0x5000
    return {"phase": "after-writer", "samples": [{"regs": base, "hc12": 0x9DB}, {"regs": b2, "hc12": 0x9DB}]}


class World:
    """kind: keep (the sketch: i, sa63 and sa100/127 survive a reload and a reset, r20/r21 do not, p2 p3 as the writer left them),
    all (r20 and r21 survive too), set (the next entry has p2 = p3 = 1 whatever the writer left), wipe (nothing survives)."""

    def __init__(self, kind="keep", s0=None):
        self.kind = kind
        self.st = {"sa63": 0, "r20": 0, "r21": 0x1000, "i0": L.E533["i0"], "i1": L.E533["i1"], "sa100": L.E533["sa100"],
                   "sa127": L.E533["sa127"], "sa20": 0, "sa24": 0, "p2": 0, "p3": 0, "pclink": 0x98}
        self.st.update(s0 or {})
        self.fills = 0

    def rd(self, p1=1, p2p3=None):
        s = self.st
        p2, p3 = p2p3 if p2p3 is not None else (s["p2"], s["p3"])
        d = {"pclink": s["pclink"], "p0": 1, "p1": p1, "p2": p2, "p3": p3, "r20": s["r20"], "r21": s["r21"], "i0": s["i0"],
             "i1": s["i1"], "sa63": s["sa63"], "sa64": 2, "sa65": 2 << 24, "sa100": s["sa100"], "sa127": s["sa127"],
             "sa20": s["sa20"], "sa24": s["sa24"], "pa0": 2, "pa1": 2 << 24, "pa2": 0x01061A70, "pass": 7}
        return [d[k] for k in L.RD_FIELDS] + [0] * (L.RD_N - len(L.RD_FIELDS))

    def write(self, j):
        s = self.st
        s["sa63"] = j["sa63"]
        s["r20"], s["r21"], s["i0"], s["i1"] = j["ri"]
        s["p2"], s["p3"] = (1, 1) if self.kind == "set" else (j["flags"][2], j["flags"][3])

    def perturb(self, kind):
        s = self.st
        if kind == "fill":
            self.fills += 1
            s["r20"], s["r21"], s["p2"], s["p3"] = 0, 0x1000 * self.fills, 0, 1
        elif kind in ("reload", "reset"):
            if self.kind in ("keep", "set"):
                s["r20"], s["r21"] = 0, 0x3000
            elif self.kind == "wipe":
                s["r20"], s["r21"], s["i0"], s["i1"], s["sa63"] = 0, 0x1000, 0, 0, 0
            s["p2"], s["p3"] = 0, 0


def c_rec(j, w, cls="ok", sig=None, **over):
    """The record the runner keeps for job j in world w (and w is advanced)."""
    rec = {"name": j["name"], "set": j["set"], "op": "start", "row": j["row"], "job": j, "class": cls, "rc": 0, "note": "",
           "run": RUN, "ccbctl_pre": [2, 0], "ticks": [{"ok": True}]}
    rec["rd0"] = {"ran": True, "rd": w.rd()}
    if j["write"]:
        w.write(j)
        rec["writer"] = {"issued": True, "done": True, "ms": 0.4,
                         "wr": [2, 2 << 24, 0x01061A70, 0, j["sa63"], j["sa63"]] + [0] * 10}
        rec["rdA"] = {"ran": True, "rd": w.rd(p1=j["flags"][1])}
        rec["perturb"] = {"kind": j["perturb"]}
        w.perturb(j["perturb"])
        rec["rdB"] = {"ran": True, "rd": w.rd()}
    else:
        rec["writer"] = {"issued": False, "done": False, "ms": None, "wr": None}
    if sig is not None:
        rec["sig"] = sig
    rec.update(over)
    return rec


def write_stage(tmp, recs, exit_code=0, why=""):
    d = pathlib.Path(tmp) / "c3"
    d.mkdir(parents=True, exist_ok=True)
    for n, r in recs.items():
        (d / f"{n}.json").write_text(json.dumps(r))
    (d / "stage.json").write_text(json.dumps({"stage": "c3", "run": RUN, "exit": exit_code, "why": why, "jobs_run": list(recs)}))
    return d


def run_world(tmp, kind="keep", s0=None, mods=None, stop_at=None):
    """Build and score a whole stage in world `kind`; mods = {job: f(rec, job, world) -> rec or None (no record)}."""
    t = S.load_table("c3")
    w = World(kind, s0)
    recs = {}
    for j in t["jobs"]:
        if stop_at and j["name"] == stop_at:
            recs[j["name"]] = c_rec(j, w, cls="stop", sig=sig_pair())
            for k in ("rdA", "rdB"):
                recs[j["name"]].pop(k, None)
            break
        r = c_rec(j, w)
        f = (mods or {}).get(j["name"])
        if f:
            r = f(r, j, w)
        if r is not None:
            recs[j["name"]] = r
    d = write_stage(tmp, recs, exit_code=8 if stop_at else 0)
    return S.score("c3", d)


def tally(st, case=None, q=None, model=None):
    return [r for r in st.t.rows if (case is None or r[0] == case) and (q is None or r[1] == q) and (model is None or r[2].startswith(model))]


def verdicts(st, case=None, q=None, model=None):
    return sorted({r[4] for r in tally(st, case, q, model)}, key=str)


# ---- the tests ------------------------------------------------------------------------------------------------------------
def test_tables():
    t = S.load_table("c3")
    check([j["name"] for j in t["jobs"]] == ["s0", "n1", "n2", "n3", "f1", "f2", "f3", "l1", "l2", "l3", "r1", "r2", "r3"],
          "13 jobs in the order S0, N x3, F x3, L x3, R x3 (the fill rows before the reload and reset rows)")
    check(t["stop_budget"] == 0 and t["blob"] == "start" and t["arm"] == "slots=0x1 entry=0", "stop budget 0 (a stop ends the stage), blob start, arm line")
    rows = {j["row"]: j["perturb"] for j in t["jobs"]}
    check(rows == {"S0": "none", "N": "gap", "F": "fill", "L": "reload", "R": "reset"}, "each row has its own perturbation")
    ms = [j["sa63"] for j in t["jobs"] if j["write"]] + [x for j in t["jobs"] if j["write"] for x in j["ri"]]
    check(len(set(ms)) == len(ms) and all(m & 0x80000000 and m != 0x02000000 for m in ms), "every marker is different, bit 31 set, not a tick's pa1")
    fl = {tuple(j["flags"]) for j in t["jobs"] if j["write"]}
    check(fl == set(L.FLAGS) and any(f[2:] != (1, 1) for f in fl), "the three flag patterns, two of them with a 0 in p2 or p3 (they discriminate H-KEEP from H-SET)")
    P = S.load_preds("c3")
    check({p["case"] for p in P} == {j["name"] for j in t["jobs"]}, "every job has frozen prediction rows and every case is a job")
    check(all(p["set"] in ("fit", "heldout", "replicate", "control") for p in P), "every row has a label")
    check({p["model"].split(" ")[0] for p in P if p["quantity"] == "b_r_kept"} == {"H-KEEP", "H-ALL"}, "r20/r21 after a reload or a reset: H-KEEP and H-ALL are both frozen")
    check(all(j["sa63"] != 0 for j in t["jobs"] if j["write"]) and not any(j["write"] for j in t["jobs"] if j["row"] == "S0"), "S0 writes nothing")


def test_world_keep(tmp):
    st, summ = run_world(tmp, "keep")
    bad = [r for r in st.t.rows if r[4] is False and not r[2].startswith(("H-ALL", "H-SET"))]
    alt = {r[2].split(" ")[0] for r in st.t.rows if r[4] is False}
    check(not bad and alt == {"H-ALL", "H-SET"}, f"the sketch's world (H-KEEP): only the alternative models H-ALL and H-SET FAIL ({bad[:3]}, {alt})")
    check(verdicts(st, q="a_markers") == [True] and verdicts(st, q="carry") == [True], "the controls hold in every job: markers at the next event, state carried between jobs")
    kinds = {r[3] for r in st.t.rows}
    check({"fit", "held out", "replicate", "control"} <= kinds, f"fit, held-out, replicate and control rows are tallied apart ({sorted(kinds)})")
    check(verdicts(st, case="l1", q="b_r_kept", model="H-KEEP") == [True] and verdicts(st, case="l1", q="b_r_kept", model="H-ALL") == [False],
          "reload: r20/r21 gone holds H-KEEP and refutes H-ALL")
    check(verdicts(st, q="b_r21_step") == [True], "the fill counter steps by 0x1000 a fill (f2, f3)")
    check("held out" in summ and "fit: " in summ and "refuted" in summ and "H-ALL" in summ and "H-SET" in summ,
          f"the summary tallies the kinds apart and names the refuted alternatives ({summ[:300]})")
    txt = "\n".join(st.lines)
    check("H-KEEP supported" in txt and "H-SET refuted" in txt, "the p2/p3 verdict line: H-KEEP supported, H-SET refuted (2 discriminating jobs of 3 per row)")
    check("S0" in txt and "start state" in txt, "the start-state lines are printed")


def test_world_all(tmp):
    st, summ = run_world(tmp, "all")
    check(set(verdicts(st, q="b_r_kept", model="H-KEEP")) == {False} and set(verdicts(st, q="b_r_kept", model="H-ALL")) == {True},
          "r20/r21 surviving the reload and the reset: H-ALL holds, H-KEEP is refuted (6 of 6 jobs)")
    check(len(tally(st, q="b_r_kept", model="H-KEEP")) == 6, "six L/R jobs carry the r rows")
    check("refuted" in summ and "H-KEEP" in summ, f"the summary names the refuted model ({summ[:240]})")


def test_world_set(tmp):
    st, summ = run_world(tmp, "set")
    k = verdicts(st, q="a_p2p3", case="n2", model="H-KEEP") + verdicts(st, q="a_p2p3", case="n3", model="H-KEEP")
    s = verdicts(st, q="a_p2p3", case="n2", model="H-SET") + verdicts(st, q="a_p2p3", case="n3", model="H-SET")
    check(k == [False, False] and s == [True, True], "p2 = p3 = 1 after every writer: H-SET holds, H-KEEP fails in the discriminating jobs")
    check(verdicts(st, q="a_p2p3", case="n1", model="H-KEEP") == [True] and verdicts(st, q="a_p2p3", case="n1", model="H-SET") == [True],
          "flags 0 0 1 1 (E536's) do not discriminate: both models hold on n1")
    check("H-SET supported" in "\n".join(st.lines), "the verdict line: H-SET supported")


def test_world_wipe(tmp):
    st, summ = run_world(tmp, "wipe")
    check(set(verdicts(st, q="b_i_kept", case="l1")) == {False} and set(verdicts(st, q="b_i_kept", case="r2")) == {False},
          "a world where nothing survives: i0/i1 not kept after a reload or a reset (both models fail)")
    check("FAILED" in summ, "the summary says FAILED")


def test_controls(tmp):
    def bad_marker(r, j, w):
        r["rdA"]["rd"][L.RD_FIELDS.index("r21")] ^= 1
        return r
    st, summ = run_world(tmp, "keep", mods={"f2": bad_marker})
    check(verdicts(st, case="f2", q="a_markers") == [False], "a control that fails: f2's marker at the next event is not what was written: FAILED")
    check(set(verdicts(st, case="f2", q="b_i_kept")) == {None}, "its perturbation rows are cannot tell (the control failed)")
    check("control" in "\n".join(st.lines) and "f2" in "\n".join(st.lines), "the control failure is printed")

    def broken_carry(r, j, w):
        r["rd0"]["rd"][L.RD_FIELDS.index("i0")] ^= 4
        return r
    st, _ = run_world(tmp, "keep", mods={"l2": broken_carry})
    check(verdicts(st, case="l2", q="carry") == [False] and verdicts(st, case="l1", q="carry") == [True],
          "a job that starts from a state other than the previous job left: carry FAILED for that job only")


def test_states(tmp):
    st, summ = run_world(tmp, "keep", mods={"n2": lambda r, j, w: dict(r, **{"class": "noreader"}, rdA={"ran": False, "rd": None})})
    check(set(verdicts(st, case="n2")) == {None}, "noreader: tick kept, reader not run: every row of the job is cannot tell")
    st, _ = run_world(tmp, "keep", mods={"f1": lambda r, j, w: None})
    check(set(verdicts(st, case="f1")) == {None} and "f1: NODATA" in "\n".join(st.lines), "no record: NODATA, rows void")
    st, _ = run_world(tmp, "keep", mods={"l1": lambda r, j, w: dict(r, writer=dict(r["writer"], done=False))})
    check("writer's flag" in "\n".join(st.lines) and set(verdicts(st, case="l1")) == {None}, "the writer's flag not set: void")
    def readback(r, j, w):
        r["writer"]["wr"][5] ^= 1
        return r
    st, _ = run_world(tmp, "keep", mods={"r1": readback})
    check("read-back" in "\n".join(st.lines) and set(verdicts(st, case="r1")) == {None}, "an sa63 read-back that is not what the writer wrote: void")
    st, _ = run_world(tmp, "keep", mods={"n3": lambda r, j, w: dict(r, **{"class": "unhealthy"})})
    check(set(verdicts(st, case="n3")) == {None}, "a class that is not a result (unhealthy): void")
    st, _ = run_world(tmp, "keep", mods={"s0": lambda r, j, w: dict(r, rd0={"ran": False, "rd": None})})
    check(set(verdicts(st, case="s0", q="rd0_pclink")) == {None}, "S0 with no reader record: cannot tell")


def test_stop(tmp):
    st, summ = run_world(tmp, "keep", stop_at="f2")
    txt = "\n".join(st.lines)
    check(verdicts(st, case="f2", q="kept") == [False] and "f2: class stop" in txt and "signature busy" in txt and "matches E537" in txt,
          "a tick stop: kept FAILED, the signature scored against E537's")
    check(verdicts(st, case="l1") == [None] and "l1: NODATA" in txt, "jobs after the stop were not run: NODATA")
    check("stage exit 8" in summ and "stops 1" in summ, f"the summary says the stage ended by a stop ({summ[:200]})")


def test_s0_start_state(tmp):
    st, summ = run_world(tmp, "keep")
    check(verdicts(st, case="s0", q="rd0_pclink") == [True] and verdicts(st, case="s0", q="rd0_p2p3") == [True],
          "S0: pclink 0x98 and p2 p3 = 0 0 as E792's A0 read them")
    check("sa100/sa127 as found" in "\n".join(st.lines), "S0's sa100, sa127, i0, i1, r20, r21 are printed as found")
    st, _ = run_world(tmp, "keep", s0={"sa100": 0, "sa127": 0})
    check("not informative" in "\n".join(st.lines), "sa100 = sa127 = 0 at S0: persistence of an unwritten register is not informative")
    st, _ = run_world(tmp, "keep", s0={"sa20": 0x20})
    check(verdicts(st, case="s0", q="rd0_sa20") == [False], "sa20 not 0 at S0: that fit row FAILS")


def test_e536_fixture(tmp):
    """E536's own readings as C3's reader records: the controls are S0's shape, the fill round is F's."""
    rounds = json.loads((DATA / "p1130-b-tailpair/b-rounds.json").read_text())["rounds"]
    ctl = json.loads((DATA / "p1130-b-tailpair/b-controls.json").read_text())["rounds"][0]
    fill = [r for r in rounds if r["kind"] == "fill"][0]

    def to_rd(sl):
        a, b, c = sl["10"], sl["11"], sl["12"]
        d = {"pclink": a[0], "p0": a[1], "p1": a[2], "p2": a[3], "p3": b[0], "r20": b[1], "r21": b[2], "i0": b[3], "i1": 0,
             "sa63": 0, "sa64": c[0], "sa65": 2 << 24, "sa100": 0, "sa127": 0, "sa20": 0, "sa24": 0, "pa0": 2, "pa1": 2 << 24,
             "pa2": 0, "pass": 1}
        return [d[k] for k in L.RD_FIELDS] + [0] * (L.RD_N - len(L.RD_FIELDS))
    c, f = to_rd(ctl["slots"]), to_rd(fill["slots"])
    fd = dict(zip(L.RD_FIELDS, f))
    cd = dict(zip(L.RD_FIELDS, c))
    check(cd["pclink"] == 0x98 and (cd["p0"], cd["p1"], cd["p2"], cd["p3"]) == (1, 1, 0, 0) and cd["sa64"] == 2,
          "E536's control: pclink 0x98, p = 1 1 0 0, sa64 2")
    check(fd["pclink"] == 0x98 and (fd["p0"], fd["p1"], fd["p2"], fd["p3"]) == (1, 1, 0, 1) and fd["r20"] == 0 and fd["r21"] == 0x1000,
          "E536's fill round: pclink 0x98, p = 1 1 0 1, r20 0, r21 0x1000")
    t = S.load_table("c3")
    w = World("keep", {"i0": cd["i0"], "r21": cd["r21"]})
    recs = {"s0": c_rec(t["jobs"][0], w)}
    recs["s0"]["rd0"]["rd"] = c
    j = [x for x in t["jobs"] if x["name"] == "f1"][0]
    r = c_rec(j, w)
    r["rdB"]["rd"] = f[:L.RD_FIELDS.index("i0")] + [j["ri"][2], j["ri"][3]] + f[L.RD_FIELDS.index("i1") + 1:]
    r["rdB"]["rd"][L.RD_FIELDS.index("sa63")] = j["sa63"]
    for k in ("sa100", "sa127", "sa20", "sa24"):
        r["rdB"]["rd"][L.RD_FIELDS.index(k)] = r["rdA"]["rd"][L.RD_FIELDS.index(k)]
    recs["f1"] = r
    d = write_stage(tmp, recs, exit_code=0)
    st, _ = S.score("c3", d)
    check(verdicts(st, case="s0", q="rd0_pclink") == [True] and verdicts(st, case="s0", q="rd0_p2p3") == [True],
          "the scorer reads E536's control as S0 (pclink 0x98, p2 p3 0 0)")
    ok = {q: verdicts(st, case="f1", q=q) for q in ("b_pclink", "b_p0p1", "b_p2p3", "b_r_replaced", "b_r20_zero", "b_i_kept")}
    check(all(v == [True] for v in ok.values()), f"the scorer reads E536's fill round as F's rows (pclink, p, r20, r21, i) ({ok})")


def test_gate_and_freeze():
    with tempfile.TemporaryDirectory() as tmp:
        check(S.gate("c3", tmp) == 0, "gate c3: no previous stage, open")
    check(S.freeze_problem() is None, "the freeze check is skipped under C3_NO_FREEZE_CHECK (tests only)")


def main():
    test_signature()
    test_tables()
    with tempfile.TemporaryDirectory() as tmp:
        test_world_keep(tmp)
    for f in (test_world_all, test_world_set, test_world_wipe, test_controls, test_states, test_stop, test_s0_start_state,
              test_e536_fixture):
        with tempfile.TemporaryDirectory() as tmp:
            f(tmp)
    test_gate_and_freeze()
    print(f"{len(FAIL)} failed" if FAIL else "all scorer checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
