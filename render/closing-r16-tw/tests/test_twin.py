# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the table against the plan (closing16/plan/rank-round16.md section 2
"r16-tw", section 3; closing16/DECISIONS-R16.md R16-2 a) and the session build rules: one stage
tw16 of 17 jobs on t14 with 256 scratch pages, SAFE CLASS (#limit 0, no expectfault, no knob, no
noreset, no idle, no clock-gate option), on_stop = end; the plan's rows (six bilinear: inside, the
left edge, the right edge, the v edge, 16 x 16 inside and across the right edge; eight point: two
at H 8, two at H 16, four at H 64 with u in (0, 0.4) and (1, 1.4)) and its three controls (the
bit-clear references at 32 x 8 and 16 x 64, E1049's tw-bl32 rerun), each readable and able to
fail; the scorer's gates are the generator's."""
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
import tw16 as T  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
PLAN = {  # name: (W, H, kind, u's integer part at x = 0)
    "pt32h8": (32, 8, "point", 1), "pt128h8": (128, 8, "point", 0),
    "pt32h16": (32, 16, "point", 0), "pt128h16": (128, 16, "point", 2),
    "pt16h64u0": (16, 64, "point", 0), "pt16h64u1": (16, 64, "point", 1),
    "pt64h64u0": (64, 64, "point", 0), "pt64h64u1": (64, 64, "point", 1),
    "bl64in": (64, 32, "bil", 0), "bl64left": (64, 32, "bil", 2),
    "bl128right": (128, 32, "bil", 1), "bl128vedge": (128, 32, "bil", 0),
    "bl16h16in": (16, 16, "bil", 0), "bl128h16right": (128, 16, "bil", 1)}
CONTROLS = {"ref32h8": (32, 8), "ref16h64": (16, 64), "bl32r": (32, 32)}


def limit():
    for ln in open(os.path.join(KP, "tables", "tw16.txt")):
        if ln.startswith("#limit"):
            return int(ln.split()[1])


def test_one_stage_that_ends_the_session():
    assert list(CFG["stages"]) == ["tw16"]
    assert CFG["stages"]["tw16"].get("on_stop") == "end"
    assert not CFG["knobs"] and CFG["health_tool"] == "t10"
    assert CFG["prefix"] == "r16w" and CFG["srcversion"] == "B60AB0B475DD1E8972419B5"


def test_safe_class_rows():
    t = K.table(KP, "tw16")
    assert len(t) == 17 and limit() == 0
    for r in t:
        assert r["risk"] == "safe" and "expectfault" not in r["knobs"], r["name"]
        assert not any(k.startswith(("dbg:", "idle:")) or k == "noreset" for k in r["knobs"])
        assert r["knobs"] in (["-"], ["reads:pixels"]), r["name"]


def test_the_plans_rows_and_controls():
    t = {r["name"]: r for r in K.table(KP, "tw16")}
    assert set(t) == set(PLAN) | set(CONTROLS)
    for n, (w, h, kind, ui) in PLAN.items():
        _, sset, rw, rh, rkind, b14, _, _ = T.row(n)
        assert (sset, rw, rh, rkind, b14) == ("heldout", w, h, kind, True), n
        assert T.fl(T.uv(n, 0, 0)[0]) == ui, n
    for n, (w, h) in CONTROLS.items():
        assert t[n]["set"] == "control" and t[n]["reads"] == ("pixels",)
        assert T.row(n)[2:4] == (w, h), n
    assert sum(T.row(n)[4] == "bil" for n in PLAN) == 6
    assert sorted(T.row(n)[3] for n in PLAN if T.row(n)[4] == "point") == [8, 8, 16, 16] + [64] * 4


def test_controls_can_fail_are_readable_and_gate():
    c = K.controls(KP, "tw16")
    assert set(c) == set(CONTROLS)
    SK.refuse_unreadable(c, score.producible)
    preds = K.predictions(KP, "tw16")
    assert all(len({m for mv in preds[n].values() for m in mv}) == 1 for n in c)
    assert score.GATE == T.GATE and score.ZERO == T.BL32
    t = [r["name"] for r in K.table(KP, "tw16")]
    for n, ref in T.GATE.items():
        if ref:
            assert t.index(ref) < t.index(n) and T.row(ref)[3] == T.row(n)[3], (n, ref)


def test_tool_and_options():
    for r in K.table(KP, "tw16"):
        a = r["args"].split()
        assert r["tool"] == "t14" and a[:5] == ["probe", "--temps", "32", "--coords", "--pixels"]
        assert a[5:7] == ["--scratch-pages", "256"] and len(a) == 8
        assert a[7] == f'"$S/bins/{r["name"]}.bin"'
        assert not any(x in CFG["forbid_options"] for x in a)
        assert not any("clock" in x or "clkgate" in x for x in a)
