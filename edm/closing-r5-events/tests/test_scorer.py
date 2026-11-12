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
import score_r5e  # noqa: E402
import sc_h  # noqa: E402

FX = R5 / "tests" / "fixtures" / "real"
R4D, R3D = FX / "r4-e3p", FX / "r3k-e3b"
FAIL = []
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r5escore-", dir=os.environ.get("MOCK_DIR") or None))


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
    rows, info = sc_h.replay("h1", "b1p", R4D, "b1p")
    m = rowmap(rows)
    for q in ("lockups", "iflags", "sw_events", "dword9", "dword57", "dword58", "dword14", "ccb", "status_bit6", "ta3d_dword28", "p3_answered", "tick_alive"):
        check(m[(q, "H-HWR")][1] is True, f"replay r4 b1p as h1 b1p: H-HWR {q} held ({m[(q, 'H-HWR')][0]})")
    for q in ("lockups", "iflags", "sw_events", "dword58"):
        check(m[(q, "H-NOMARK")][1] is False, f"replay r4 b1p: H-NOMARK {q} FAILED")
    check(m[("ticks_after_kick", "H-TICKS")][:2] == (20, True), f"replay r4 b1p: the count 20 held ({m[('ticks_after_kick', 'H-TICKS')]})")
    check(m[("tick_gap", "control")][1] is True and m[("skipped", "control")][1] is True, "replay r4 b1p: its gap and skip controls pass")
    check(m[("dpm_task_state", "R6-DPM")][1] is None and "skip" in m[("dpm_task_state", "R6-DPM")][2],
          "replay r4 b1p: 0x0694 cannot tell (the regs file lists it as skip), never a pass")
    check(all(m[(q, "control")][1] is None and "before r5" in m[(q, "control")][2] for q in ("timer_clock_read", "arm_dword6", "arm_marks")),
          "replay r4 b1p: the r5 instruments it lacks are cannot tell, with the reason")
    check(m[("bit18_after_bit15", "H-W")][1] is True and m[("bit18_after_bit18", "H-W")][1] is True, "replay r4 b1p: H-W held (E837's fit)")
    rows, info = sc_h.replay("h1", "b1p", R3D, "b1")
    m = rowmap(rows)
    for q in ("lockups", "iflags", "sw_events", "dword58"):
        check(m[(q, "H-HWR")][1] is False, f"replay E823 b1 as h1 b1p: H-HWR {q} FAILED (the rows can fail; {m[(q, 'H-HWR')][0]})")
        check(m[(q, "H-NOMARK")][1] is True, f"replay E823 b1: H-NOMARK {q} held")
    check(m[("ticks_after_kick", "H-TICKS")][:2] == (0, False), f"replay E823 b1: the count 0 FAILED ({m[('ticks_after_kick', 'H-TICKS')][:2]})")
    rows, info = sc_h.replay("h1", "b0", R4D, "b0")
    m = rowmap(rows)
    meas = [(q, ok) for (q, h), (got, ok, note) in m.items() if h == "control" and got is not None]
    check(meas and all(ok for q, ok in meas), f"replay r4 b0 as h1 b0: every control its files measure passes ({meas})")
    check(m[("post_marks", "control")][1] is None and "before r5" in m[("post_marks", "control")][2], "replay r4 b0: post_marks cannot tell (no dump then)")
    # a missing dump: cannot tell with the path, never a pass
    d = BASE / "nodump"
    d.mkdir()
    (d / "b1p.json").write_text((R4D / "b1p.json").read_text())
    rows, info = sc_h.replay("h1", "b1p", d, "b1p")
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


def make_job(d, name, src, j, stop=True, srcdir=R4D, srcname="b1p", clock=0, edit=None, run="w-1"):
    rec = copy.deepcopy(src)
    rec.update({"name": name, "run": run, "job": j, "row": j["row"], "set": j["set"], "timer_clock_read": L.knob_text(clock)})
    rec["slot3_seen"] = True
    rec["status_arm"] = status_with(ARM_ST, hc={6: L.eff_clock(clock)})
    rec.pop("marks_arm", None)
    if not stop:
        rec["status_post"] = ARM_ST
    if clock:
        for k in ("page", "page2"):
            rec[k] = scale_stamps(rec[k], L.eff_clock(clock) / L.FW_CLOCK)
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
    S, summ = score_r5e.score(stage, d)
    return S, summ


def t_worlds():
    # h1 held: r4's b0 and b1p as every job
    def held(d, j):
        make_job(d, j["name"], B0 if not j["skip"] else B1P, j, stop=bool(j["skip"]))
    S, s = world("h1", "held", held)
    v = verdicts(s, ("H-HWR", "H-NOMARK", "H-TICKS", "H-LEVEL", "H-PULSE", "H-W", "H-ALL", "H-NONE"))
    check(v == {"H-HWR": "consistent", "H-NOMARK": "REFUTED", "H-TICKS": "consistent", "H-LEVEL": "consistent", "H-PULSE": "REFUTED",
                "H-W": "consistent", "H-ALL": "REFUTED", "H-NONE": "REFUTED"} and "B0 held" in s, f"h1 world from r4's files: as frozen ({v}; {s[:160]})")
    none = sorted({q for c, q, m, k, ok, n in S.t.rows if ok is None})
    check(none == ["dpm_task_state"], f"h1 world: the only cannot-tell rows are 0x0694's ({none})")
    check(len(S.t.rows) == len(S.preds), f"h1 world: every frozen row was scored ({len(S.t.rows)} of {len(S.preds)})")

    # h1 with E823's stop as the B1P jobs: H-HWR refuted, H-NOMARK consistent, H-TICKS refuted
    def e823(d, j):
        if not j["skip"]:
            return make_job(d, j["name"], B0, j, stop=False)
        make_job(d, j["name"], E823B1, j, srcdir=R3D, srcname="b1", edit=lambda r: r.update(slot3_seen=True))
    S, s = world("h1", "e823", e823)
    v = verdicts(s, ("H-HWR", "H-NOMARK", "H-TICKS"))
    check(v == {"H-HWR": "REFUTED", "H-NOMARK": "consistent", "H-TICKS": "REFUTED"}, f"h1 world from E823's b1: H-HWR REFUTED ({v})")

    # a gap off its clock voids the job; a failed B0 gates the stage
    def gapoff(d, j):
        make_job(d, j["name"], B0 if not j["skip"] else B1P, j, stop=bool(j["skip"]),
                 edit=(lambda r: r.update(page=scale_stamps(r["page"], 2), page2=scale_stamps(r["page2"], 2))) if j["name"] == "b1p" else None)
    S, s = world("h1", "gapoff", gapoff)
    b1 = [(q, ok, n) for c, q, m, k, ok, n in S.t.rows if c == "b1p" and k != "control"]
    check(all(ok is None for q, ok, n in b1) and "control not a pass" in b1[0][2], "a B1P whose gap is not its clock's: its rows are cannot tell")

    def b0fail(d, j):
        make_job(d, j["name"], B0 if not j["skip"] else B1P, j, stop=bool(j["skip"]),
                 edit=(lambda r: r.update(tool_rc=1)) if not j["skip"] else None)
    S, s = world("h1", "b0fail", b0fail)
    check("B0 NOT held" in s and all(ok is None for c, q, m, k, ok, n in S.t.rows if k != "control"),
          f"a failed B0 gates every row of the stage ({s[:80]})")

    # h2: H-TICKS (20 at both clocks) and H-TIME (the counter edited to 10 and 5 ticks)
    def dose(time_world):
        def build(d, j):
            c = j["timer_clock"]
            if not j["skip"]:
                return make_job(d, j["name"], B0, j, stop=False, clock=c)

            def edit(r):
                if time_world:
                    n = 10 if c == 800000 else 5
                    for k in ("page", "page2"):
                        r[k][L.DROP] = 0
                        b = L.RING_BASE[0]
                        ticks = [o for o in (b + L.RUNG * x for x in range(L.RUNGS[0])) if r[k][o]]
                        keep = 5 + 1 + n                     # 5 ticks before, the kick, n after
                        for o in ticks[keep:]:
                            r[k][o:o + L.RUNG] = [0] * L.RUNG
            make_job(d, j["name"], B1P, j, clock=c, edit=edit)
        return build
    S, s = world("h2", "ticks", dose(False))
    v = verdicts(s, ("H-TICKS", "H-TIME", "H-HWR"))
    check(v == {"H-TICKS": "consistent", "H-TIME": "REFUTED", "H-HWR": "consistent"}, f"h2 world: H-TICKS at 800000 and 1600000 ({v}; {s[:200]})")
    S, s = world("h2", "time", dose(True))
    v = verdicts(s, ("H-TICKS", "H-TIME"))
    check(v == {"H-TICKS": "REFUTED", "H-TIME": "consistent"}, f"h2 world: H-TIME (10 and 5 ticks) ({v})")

    # h2's clock groups: B0B failing gates only the 1600000 rows
    def groupfail(d, j):
        c = j["timer_clock"]
        if not j["skip"]:
            return make_job(d, j["name"], B0, j, stop=False, clock=c, edit=(lambda r: r.update(tool_rc=1)) if c == 1600000 else None)
        make_job(d, j["name"], B1P, j, clock=c)
    S, s = world("h2", "group", groupfail)
    a = [ok for c, q, m, k, ok, n in S.t.rows if c.startswith("b1pa") and k != "control"]
    b = [ok for c, q, m, k, ok, n in S.t.rows if c.startswith("b1pb") and k != "control"]
    check(any(x is not None for x in a) and all(x is None for x in b), "h2: a failed B0B gates the 1600000 rows only")

    # h3: H-STATE (a stop with marks after the early clears) and H-ACK18 (tick alive, no lockup)
    def h3(stop):
        def build(d, j):
            c = j["timer_clock"]
            if not j["skip"]:
                return make_job(d, j["name"], B0, j, stop=False, clock=c)

            def edit(r):
                r["status_before_clears"] = {"status": 0x20040000}
                r["clears"] = {"bit15": {"reads": [{"ms_after": 1, "status": 0x20040000}, {"ms_after": 3, "status": 0x20040000}]},
                               "bit18": {"reads": [{"ms_after": 1, "status": 0x20000000}, {"ms_after": 3, "status": 0x20000000}]}}
                r["misc"] = {"answered": True, "ms": 0.8}
                for k in ("page", "page2"):                  # the miscinfo's kick entry after the 3rd tick after the fill's kick
                    pg = r[k]
                    b = L.RING_BASE[0]
                    rungs = [pg[b + L.RUNG * x:b + L.RUNG * x + L.RUNG] for x in range(L.RUNGS[0])]
                    kick = next(x for x, e in enumerate(rungs) if e[0] and e[1] == 0)
                    misc = [1, 0, (3 << 24) | L.KICK_LOW, 0x01000001, (rungs[kick + 3][4] + 10) & 0xFFFFFFFF, 0, 0, 0]
                    rungs = rungs[:kick + 4] + [misc] + rungs[kick + 4:-1]
                    pg[b:b + L.RUNG * L.RUNGS[0]] = [x for e in rungs for x in e]
                    pg[L.DROP] = 11 if stop else 0
                if stop:
                    r["sig"]["samples"][0]["regs"][hex(L.REG_EVENT_STATUS)] = 0x20000000
                else:
                    r["class"] = "ok"
                    r["status_post"] = ARM_ST
                    r.pop("p3", None)
            make_job(d, j["name"], B1P, j, clock=c, stop=stop, edit=edit)
        return build
    S, s = world("h3", "state", h3(True))
    v = verdicts(s, ("H-STATE", "H-ACK18", "H-TICKS", "H-W", "H-ALL", "H-NONE", "H-LEVEL"))
    check(v == {"H-STATE": "consistent", "H-ACK18": "REFUTED", "H-TICKS": "consistent", "H-W": "consistent", "H-ALL": "REFUTED",
                "H-NONE": "REFUTED", "H-LEVEL": "consistent"}, f"h3 world: H-STATE, H-W on a running EDM ({v}; {s[:220]})")
    S, s = world("h3", "ack18", h3(False))
    v = verdicts(s, ("H-STATE", "H-ACK18"))
    check(v == {"H-STATE": "REFUTED", "H-ACK18": "consistent"}, f"h3 world: H-ACK18 (tick alive, no lockup) ({v})")


def main():
    t_replays()
    t_worlds()
    print(f"{len(FAIL)} failed" if FAIL else "all scorer checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
