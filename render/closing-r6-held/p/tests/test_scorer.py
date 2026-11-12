#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_scorer.py: the scorer of R5-events (score/sc_h.py) on REAL records, before the freeze.

1. Replays (the brief's round 5 addition): the kept round 4 files it must hold on and the ones it must fail on, as the plan names them
   (exp-events-r5.md section 5, "Dry runs"): r4's b1p (E836, out/a1/e3p) read as h1's b1p must hold the marks and the count 20; E823's b1
   (closing-r3k-events out/e3b) read as h1's b1p must print H-HWR FAILED (and the count FAILED); r4's b0 read as h1's b0 must pass every
   control its files can measure; a missing dump is cannot tell with the path printed, never a pass.  The copies are in
   tests/fixtures/real/ (SOURCES.txt).
2. Worlds built from those records (renamed, given the arm and post-watch dumps the r5 runner adds, their page stamps or counters edited
   where the world says): every family verdict the SUMMARY can print, the gates (a failed B0, a gap off the clock), the clock groups of
   h2.  Exit 0 when every check holds."""
import copy
import json
import os
import pathlib
import re
import sys
import tempfile

sys.dont_write_bytecode = True
os.environ["R3_NO_FREEZE_CHECK"] = "1"
R5 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R5 / "score"))
sys.path.insert(0, str(R5 / "gen"))
import r5layout as L  # noqa: E402
import score_p  # noqa: E402
import sc_h  # noqa: E402

FX = R5 / "tests" / "fixtures" / "real"
R4D, R3D, R5D = FX / "r4-e3p", FX / "r3k-e3b", FX / "r5-h1"
FAIL = []
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r6hpscore-", dir=os.environ.get("MOCK_DIR") or None))


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def verdicts(s, names):
    out = {}
    for n in names:
        m = re.search(re.escape(n) + r" (consistent|REFUTED|mixed|cannot tell)", s)
        out[n] = m.group(1) if m else None
    return out


def rowmap(rows):
    """{(quantity, model prefix): (got, ok, note)}"""
    return {(q, m.split(" ")[0]): (got, ok, note) for q, v, m, s, got, ok, note in rows}


# ---- 1. replays ------------------------------------------------------------------------------------------------------------------
def t_replays():
    # round 5's kept stops (E855), the job part P repeats: every E855 row holds, the peek rows cannot tell (no file), never a pass
    for name in ("b1p", "b1p-r2"):
        rows, info = sc_h.replay("p1", name, R5D, name)
        m = rowmap(rows)
        for q in ("lockups", "iflags", "sw_events", "dword9", "dword57", "dword58", "dword14", "ccb", "status_bit6", "ta3d_dword28",
                  "p3_answered", "tick_alive"):
            check(m[(q, "H-HWR")][1] is True, f"replay E855 {name} as p1 {name}: H-HWR {q} held ({m[(q, 'H-HWR')][0]})")
        check(m[("ticks_after_kick", "H-TICKS")][:2] == (20, True), f"replay E855 {name}: the count 20 held")
        check(m[("bit18_in_watch", "H-LEVEL")][1] is True and m[("bit18_after_bit18", "H-W")][1] is True, f"replay E855 {name}: H-LEVEL, H-W held")
        ctl = [(q, ok) for (q, h), (got, ok, note) in m.items() if h == "control" and q != "peek_format"]
        check(all(ok for q, ok in ctl), f"replay E855 {name}: every control but the peek's passes ({ctl})")
        pk = [(q, h, m[(q, h)][1], m[(q, h)][2][:40]) for (q, h) in m if q.startswith("peek_")]
        check(len(pk) == 5 and all(ok is None and "no peek read" in n for q, h, ok, n in pk),
              f"replay E855 {name}: the 5 peek rows cannot tell, `no peek read` ({pk})")
    rows, info = sc_h.replay("p1", "b0", R5D, "b0")
    m = rowmap(rows)
    meas = [(q, ok) for (q, h), (got, ok, note) in m.items() if h == "control" and got is not None]
    check(meas and all(ok for q, ok in meas) and len(meas) == len([1 for (q, h) in m if h == "control"]) - 1,
          f"replay E855 b0 as p1 b0: every control but the peek's is measured and passes ({meas})")
    rows, info = sc_h.replay("p1", "b1p", R4D, "b1p")
    m = rowmap(rows)
    for q in ("lockups", "iflags", "sw_events", "dword9", "dword57", "dword58", "dword14", "ccb", "status_bit6", "ta3d_dword28", "p3_answered", "tick_alive"):
        check(m[(q, "H-HWR")][1] is True, f"replay r4 b1p as p1 b1p: H-HWR {q} held ({m[(q, 'H-HWR')][0]})")
    for q in ("lockups", "iflags", "sw_events", "dword58"):
        check(m[(q, "H-NOMARK")][1] is False, f"replay r4 b1p: H-NOMARK {q} FAILED")
    check(m[("ticks_after_kick", "H-TICKS")][:2] == (20, True), f"replay r4 b1p: the count 20 held ({m[('ticks_after_kick', 'H-TICKS')]})")
    check(m[("tick_gap", "control")][1] is True and m[("skipped", "control")][1] is True, "replay r4 b1p: its gap and skip controls pass")
    check(all(m[(q, h)][1] is None and "no peek read" in m[(q, h)][2] for q, h in (("peek_stop", "H-R6"), ("peek_stop_eq_arm", "H-IDLE"),
                                                                              ("peek_format", "control"))),
          "replay r4 b1p: the peek rows cannot tell (no peek read: the rgn4 kernel had none), never a pass")
    check(all(m[(q, "control")][1] is None and "before r5" in m[(q, "control")][2] for q in ("timer_clock_read", "arm_dword6", "arm_marks")),
          "replay r4 b1p: the r5 instruments it lacks are cannot tell, with the reason")
    check(m[("bit18_after_bit15", "H-W")][1] is True and m[("bit18_after_bit18", "H-W")][1] is True, "replay r4 b1p: H-W held (E837's fit)")
    rows, info = sc_h.replay("p1", "b1p", R3D, "b1")
    m = rowmap(rows)
    for q in ("lockups", "iflags", "sw_events", "dword58"):
        check(m[(q, "H-HWR")][1] is False, f"replay E823 b1 as p1 b1p: H-HWR {q} FAILED (the rows can fail; {m[(q, 'H-HWR')][0]})")
        check(m[(q, "H-NOMARK")][1] is True, f"replay E823 b1: H-NOMARK {q} held")
    check(m[("ticks_after_kick", "H-TICKS")][:2] == (0, False), f"replay E823 b1: the count 0 FAILED ({m[('ticks_after_kick', 'H-TICKS')][:2]})")
    rows, info = sc_h.replay("p1", "b0", R4D, "b0")
    m = rowmap(rows)
    meas = [(q, ok) for (q, h), (got, ok, note) in m.items() if h == "control" and got is not None]
    check(meas and all(ok for q, ok in meas), f"replay r4 b0 as p1 b0: every control its files measure passes ({meas})")
    check(m[("post_marks", "control")][1] is None and "before r5" in m[("post_marks", "control")][2], "replay r4 b0: post_marks cannot tell (no dump then)")
    # a missing dump: cannot tell with the path, never a pass
    d = BASE / "nodump"
    d.mkdir()
    (d / "b1p.json").write_text((R4D / "b1p.json").read_text())
    rows, info = sc_h.replay("p1", "b1p", d, "b1p")
    m = rowmap(rows)
    check(m[("lockups", "H-HWR")][1] is None and str(d / "stop-b1p-status.txt") in m[("lockups", "H-HWR")][2],
          f"a missing stop dump: lockups cannot tell, the path printed ({m[('lockups', 'H-HWR')][2][:90]})")
    check(not any(ok for (q, h), (got, ok, note) in m.items() if q in ("lockups", "iflags", "sw_events", "dword58", "dword57")),
          "a missing stop dump: no marks row is a pass")


# ---- 2. worlds from real records -------------------------------------------------------------------------------------------------
def status_with(text, hc=None, ta=None):
    """A status text with HostCtl / TA3DCtl dwords replaced (the r4 dump's own layout)."""
    m = L.parse_marks(text)
    h, t = dict(m["hc"]), dict(m["ta"])
    h.update(hc or {})
    t.update(ta or {})
    out = []
    for ln in text.splitlines():
        mm = re.match(r"(hostctl|ta3dctl)\[\s*(\d+)\]:\s+((?:[0-9a-f]{2}\s*)+)$", ln)
        if mm:
            first = int(mm.group(2))
            n = len(mm.group(3).split()) // 4
            src = h if mm.group(1) == "hostctl" else t
            ln = f"{mm.group(1)}[{first:2d}]: " + " ".join(f"{(src.get(first + i, 0) >> (8 * k)) & 0xFF:02x}" for i in range(n) for k in range(4))
        out.append(ln)
    return "\n".join(out) + "\n"


STOP_ST = (R4D / "stop-b1p-status.txt").read_text()
ARM_ST = status_with(STOP_ST, hc={3: 0, 8: 0}, ta={57: 0, 58: 0})
B0, B1P = json.loads((R4D / "b0.json").read_text()), json.loads((R4D / "b1p.json").read_text())
E823B1 = json.loads((R3D / "b1.json").read_text())
B0R5, B1PR5 = json.loads((R5D / "b0.json").read_text()), json.loads((R5D / "b1p.json").read_text())


def scale_stamps(page, k):
    """The slot 0 ring's CR_TIMER stamps stretched by k after the first entry (a slower clock's grid)."""
    pg = list(page)
    b = L.RING_BASE[0]
    s0 = pg[b + 4]
    for j in range(L.RUNGS[0]):
        o = b + L.RUNG * j
        if pg[o]:
            pg[o + 4] = (s0 + int((pg[o + 4] - s0) * k)) & 0xFFFFFFFF
    return pg


def pk(v, text=None):
    """One peek read as the runner keeps it."""
    tx = text if text is not None else f"reg 0x0694 0x{v:08x}\n"
    return {"text": tx, "err": "", "rc": 0, "value": L.parse_peek(tx)}


def make_job(d, name, src, j, stop=True, srcdir=R4D, srcname="b1p", clock=0, edit=None, run="w-1", keep_arm=False):
    rec = copy.deepcopy(src)
    rec.update({"name": name, "run": run, "job": j, "row": j["row"], "set": j["set"], "timer_clock_read": L.knob_text(clock)})
    rec["slot3_seen"] = True
    if not keep_arm:
        rec["status_arm"] = status_with(ARM_ST, hc={6: L.eff_clock(clock)})
        rec.pop("marks_arm", None)
    if not stop and not keep_arm:
        rec["status_post"] = ARM_ST
    if clock:
        for k in ("page", "page2"):
            rec[k] = scale_stamps(rec[k], L.eff_clock(clock) / L.FW_CLOCK)
    if "peek" not in rec:          # part P's reads (H-R6's outcome) on the worlds built from older records; a world's edit overrides
        rec["peek"] = ({"arm": pk(0), "after_watch": pk(0)} if not j["skip"] else
                       {"arm": pk(0), "stop": pk(2), "after_clears": pk(2), "after_recovery": pk(0)} if stop else
                       {"arm": pk(0), "after_watch": pk(0), "after_recovery": pk(0)})
    if edit:
        edit(rec)
    (d / f"{name}.json").write_text(json.dumps(rec))
    if stop:
        for kind in ("status.txt", "regs.txt"):
            (d / f"stop-{name}-{kind}").write_text((srcdir / f"stop-{srcname}-{kind}").read_text())
        (d / f"stop-{name}-own_res.json").write_text(json.dumps(rec["page"]))
    return rec


def world(stage, name, build):
    d = BASE / f"{stage}-{name}"
    d.mkdir()
    t = json.loads((R5 / "tables" / f"{stage}.json").read_text())
    names = []
    for j in t["jobs"]:
        if build(d, j) is not False:
            names.append(j["name"])
    (d / "stage.json").write_text(json.dumps({"stage": stage, "run": "w-1", "exit": 0, "jobs_run": names, "stops": 0}))
    S, summ = score_p.score(stage, d)
    return S, summ


def t_worlds():
    # h1 held: r4's b0 and b1p as every job
    def held(d, j):
        make_job(d, j["name"], B0 if not j["skip"] else B1P, j, stop=bool(j["skip"]))
    S, s = world("p1", "held", held)
    v = verdicts(s, ("H-HWR", "H-NOMARK", "H-TICKS", "H-LEVEL", "H-PULSE", "H-W", "H-ALL", "H-NONE"))
    check(v == {"H-HWR": "consistent", "H-NOMARK": "REFUTED", "H-TICKS": "consistent", "H-LEVEL": "consistent", "H-PULSE": "REFUTED",
                "H-W": "consistent", "H-ALL": "REFUTED", "H-NONE": "REFUTED"} and "B0 held" in s, f"p1 world from r4's files: as frozen ({v}; {s[:160]})")
    none = sorted({q for c, q, m, k, ok, n in S.t.rows if ok is None})
    check(none == [], f"r4 world (part P's peek reads added): no cannot-tell row ({none})")
    check(len(S.t.rows) == len(S.preds), f"p1 world: every frozen row was scored ({len(S.t.rows)} of {len(S.preds)})")

    # h1 with E823's stop as the B1P jobs: H-HWR refuted, H-NOMARK consistent, H-TICKS refuted
    def e823(d, j):
        if not j["skip"]:
            return make_job(d, j["name"], B0, j, stop=False)
        make_job(d, j["name"], E823B1, j, srcdir=R3D, srcname="b1", edit=lambda r: r.update(slot3_seen=True))
    S, s = world("p1", "e823", e823)
    v = verdicts(s, ("H-HWR", "H-NOMARK", "H-TICKS"))
    check(v == {"H-HWR": "REFUTED", "H-NOMARK": "consistent", "H-TICKS": "REFUTED"}, f"p1 world from E823's b1: H-HWR REFUTED ({v})")

    # a gap off its clock voids the job; a failed B0 gates the stage
    def gapoff(d, j):
        make_job(d, j["name"], B0 if not j["skip"] else B1P, j, stop=bool(j["skip"]),
                 edit=(lambda r: r.update(page=scale_stamps(r["page"], 2), page2=scale_stamps(r["page2"], 2))) if j["name"] == "b1p" else None)
    S, s = world("p1", "gapoff", gapoff)
    b1 = [(q, ok, n) for c, q, m, k, ok, n in S.t.rows if c == "b1p" and k != "control"]
    check(all(ok is None for q, ok, n in b1) and "control not a pass" in b1[0][2], "a B1P whose gap is not its clock's: its rows are cannot tell")

    def b0fail(d, j):
        make_job(d, j["name"], B0 if not j["skip"] else B1P, j, stop=bool(j["skip"]),
                 edit=(lambda r: r.update(tool_rc=1)) if not j["skip"] else None)
    S, s = world("p1", "b0fail", b0fail)
    check("B0 NOT held" in s and all(ok is None for c, q, m, k, ok, n in S.t.rows if k != "control"),
          f"a failed B0 gates every row of the stage ({s[:80]})")

    # r6-held part P: the peek worlds, from E855's kept files with the reads part P adds
    def peekw(arm, stop, rec_after, text=None):
        def build(d, j):
            src = B0R5 if not j["skip"] else B1PR5
            def ed(r):
                if not j["skip"]:
                    r["peek"] = {"arm": pk(arm), "after_watch": pk(arm)}
                else:
                    r["peek"] = {"arm": pk(arm), "stop": pk(stop, text), "after_clears": pk(stop, text), "after_recovery": pk(rec_after)}
            make_job(d, j["name"], src, j, stop=bool(j["skip"]), srcdir=R5D, srcname="b1p", edit=ed, keep_arm=True)
        return build
    S, s = world("p1", "r6", peekw(0, 2, 0))
    v = verdicts(s, ("H-R6", "H-IDLE", "H-RESET", "H-HWR"))
    check(v == {"H-R6": "consistent", "H-IDLE": "REFUTED", "H-RESET": "consistent", "H-HWR": "consistent"} and "B0 held" in s,
          f"peek world: the stop reads 2, the arm and recovery 0: H-R6 consistent, H-IDLE REFUTED ({v}; {s[:120]})")
    none = sorted({q for c, q, m, k, ok, n in S.t.rows if ok is None})
    check(not none and len(S.t.rows) == len(S.preds), f"peek world: every frozen row decided ({none}; {len(S.t.rows)} of {len(S.preds)})")
    S, s = world("p1", "idle", peekw(0, 0, 0))
    v = verdicts(s, ("H-R6", "H-IDLE"))
    check(v == {"H-R6": "REFUTED", "H-IDLE": "consistent"}, f"peek world: the stop read equals the arm read (0): H-R6 FAILS, H-IDLE ({v})")
    S, s = world("p1", "idle5", peekw(5, 5, 5))
    v = verdicts(s, ("H-R6", "H-IDLE"))
    check(v == {"H-R6": "REFUTED", "H-IDLE": "consistent"}, f"peek world: arm 5, stop 5: H-R6 REFUTED ({v})")
    S, s = world("p1", "armtwo", peekw(2, 2, 2))
    rows = [(q, ok, n) for c, q, m, k, ok, n in S.t.rows if q in ("peek_stop", "peek_stop_eq_arm")]
    check(rows and all(ok is None and "already 2" in n for q, ok, n in rows), f"peek world: an arm read of 2 makes H-R6 / H-IDLE cannot tell ({rows[:2]})")
    S, s = world("p1", "sticky", peekw(0, 2, 2))
    check(verdicts(s, ("H-RESET",))["H-RESET"] == "REFUTED", "peek world: 2 still read after the recovery: H-RESET REFUTED")
    S, s = world("p1", "badfmt", peekw(0, 2, 0, text="reg 0x0694 skip\n"))
    b1 = [(q, ok) for c, q, m, k, ok, n in S.t.rows if c == "b1p" and k == "control" and q == "peek_format"]
    rest = [ok for c, q, m, k, ok, n in S.t.rows if c == "b1p" and k != "control"]
    check(b1 == [("peek_format", False)] and all(x is None for x in rest), f"peek world: a stop read that is not one `reg 0x0694` line fails the "
          f"format control and voids the job's rows ({b1})")


def main():
    t_replays()
    t_worlds()
    print(f"{len(FAIL)} failed" if FAIL else "all scorer checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
