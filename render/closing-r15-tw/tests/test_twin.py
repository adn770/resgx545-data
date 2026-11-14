# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the table against the plan (closing15/plan/rank-round15.md section 2
"r15-tw", section 3; closing15/DECISIONS-R15.md R15-2 a) and the session build rules: one stage
tw14 of 14 jobs on t14 with 256 scratch pages, SAFE CLASS (#limit 0, no expectfault, no knob, no
noreset, no idle, no clock-gate option), on_stop = end; the plan's rows (W 16 at u in (0, 1) and
(1, 2), W 64 and 128 at u in (0, 1) and (2, 3), a u16 32 x 32, bilinear 32 x 32 and 16 x 32) and
controls (the four bit-clear references, E1047's f1-zero rerun), every control first, readable and
able to fail; the scorer's gates are the generator's."""
import os
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402
import scorekit as SK  # noqa: E402
import tw  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
PLAN = {  # name: (W, format, kind, u's integer part)
    "tw16-u0": (16, 12, "point", 0), "tw16-u1": (16, 12, "point", 1),
    "tw64-u0": (64, 12, "point", 0), "tw64-u2": (64, 12, "point", 2),
    "tw128-u0": (128, 12, "point", 0), "tw128-u2": (128, 12, "point", 2),
    "tw-u16": (32, 9, "u16", 0), "tw-bl32": (32, 12, "bil", 0), "tw-bl16": (16, 12, "bil", 1)}
CONTROLS = {"tw-ref16", "tw-ref64", "tw-ref128", "tw-refu16", "tw-zero"}


def limit():
    for ln in open(os.path.join(KP, "tables", "tw14.txt")):
        if ln.startswith("#limit"):
            return int(ln.split()[1])


def test_one_stage_that_ends_the_session():
    assert list(CFG["stages"]) == ["tw14"]
    assert CFG["stages"]["tw14"].get("on_stop") == "end"
    assert not CFG["knobs"] and CFG["health_tool"] == "t10"


def test_safe_class_rows():
    t = K.table(KP, "tw14")
    assert len(t) == 14 and limit() == 0
    for r in t:
        assert r["risk"] == "safe" and "expectfault" not in r["knobs"], r["name"]
        assert not any(k.startswith(("dbg:", "idle:")) or k == "noreset" for k in r["knobs"])
        assert r["knobs"] in (["-"], ["reads:pixels"]), r["name"]


def test_the_plans_rows_and_controls():
    t = {r["name"]: r for r in K.table(KP, "tw14")}
    assert set(t) == set(PLAN) | CONTROLS
    for n, (w, fmt, kind, ui) in PLAN.items():
        _, sset, rw, rfmt, rkind, b14, _ = tw.row(n)
        assert (sset, rw, rfmt, rkind, b14) == ("heldout", w, fmt, kind, True), n
        u = tw.uv(n, 0, 0)[0]
        assert tw.fl(u) == ui, n          # at x = 0 (the bilinear rows cross ui + 1 later)
    for n in CONTROLS:
        assert t[n]["set"] == "control" and t[n]["reads"] == ("pixels",)


def test_controls_can_fail_are_readable_and_come_first():
    c = K.controls(KP, "tw14")
    assert set(c) == CONTROLS
    SK.refuse_unreadable(c, score.producible)
    preds = K.predictions(KP, "tw14")
    assert all(len({m for mv in preds[n].values() for m in mv}) == 1 for n in c)
    t = K.table(KP, "tw14")
    assert {r["name"] for r in t[:5]} == CONTROLS
    assert score.GATE == tw.GATE and score.ZERO == tw.ZERO


def test_tool_and_options():
    for r in K.table(KP, "tw14"):
        a = r["args"].split()
        assert r["tool"] == "t14" and a[:5] == ["probe", "--temps", "32", "--coords", "--pixels"]
        assert a[5:7] == ["--scratch-pages", "256"] and len(a) == 8
        assert a[7] == f'"$S/bins/{r["name"]}.bin"'
        assert not any(x in CFG["forbid_options"] for x in a)
        assert not any("clock" in x or "clkgate" in x for x in a)
