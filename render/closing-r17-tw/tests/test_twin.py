# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the table against the plan (closing17/plan/rank-round17.md section 2
"r17-tw", section 3; closing17/DECISIONS-R17.md R17-1 to R17-4 a) and the session build rules: one
stage tw17 of 14 jobs on t14 with 256 scratch pages, SAFE CLASS (#limit 0, no expectfault, no knob,
no noreset, no idle, no clock-gate option), on_stop = end; the plan's rows (bilinear: bl16left,
bl64grid, bl128off3, bl256edge, bl512edge, bl256corner; point: pt128off, pt256off, pt512off) and
controls (E1058's bl64left rerun, the bit-clear 256 x 32 and 512 x 16 references), plus the
[check]'s W 2048 pair (deviation 1), each control readable and able to fail; the scorer's gates
are the generator's."""
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
import tw17 as T  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
PLAN = {  # name: (W, H, kind, u's integer part at x = 0)
    "bl16left": (16, 32, "bil", 1), "bl64grid": (64, 32, "bil", 2),
    "bl128off3": (128, 32, "bil", 0), "pt128off": (128, 32, "point", 1),
    "pt256off": (256, 16, "point", 2), "pt512off": (512, 16, "point", 0),
    "bl256edge": (256, 32, "bil", 2), "bl512edge": (512, 32, "bil", 0),
    "bl256corner": (256, 32, "bil", 2), "bl2048edge": (2048, 16, "bil", 1)}
CONTROLS = {"bl64leftr": (64, 32), "ref256": (256, 32), "ref512h16": (512, 16),
            "ref2048h16": (2048, 16)}


def limit():
    for ln in open(os.path.join(KP, "tables", "tw17.txt")):
        if ln.startswith("#limit"):
            return int(ln.split()[1])


def test_one_stage_that_ends_the_session():
    assert list(CFG["stages"]) == ["tw17"]
    assert CFG["stages"]["tw17"].get("on_stop") == "end"
    assert not CFG["knobs"] and CFG["health_tool"] == "t10"
    assert CFG["prefix"] == "r17w" and CFG["srcversion"] == "B60AB0B475DD1E8972419B5"
    assert CFG["freeze"]["resgx545"].startswith("c2180e6") and \
        CFG["freeze"]["data"].startswith("af46e8077")


def test_tools_bound_as_r16_tw():
    t14, t10 = CFG["tools"]["t14"], CFG["tools"]["t10"]
    assert t14["sha256"] == "aa550b94585aaf6eb5d9b7927d320ad31ea8d1e206b8c5e99e4435c7f0a83859"
    assert t14["source"].startswith("c58f9f9c87aa3f8370d2b66917898550d86f6879:")
    assert t14["recipe"] == "data:render/closing-r14-flag/lead/build_tool14.sh"
    assert t10["sha256"].startswith("9bedc2d6") and t10["source"].startswith("a581c06")


def test_safe_class_rows():
    t = K.table(KP, "tw17")
    assert len(t) == 14 and limit() == 0
    for r in t:
        assert r["risk"] == "safe" and "expectfault" not in r["knobs"], r["name"]
        assert not any(k.startswith(("dbg:", "idle:")) or k == "noreset" for k in r["knobs"])
        assert r["knobs"] in (["-"], ["reads:pixels"]), r["name"]


def test_the_plans_rows_and_controls():
    t = {r["name"]: r for r in K.table(KP, "tw17")}
    assert set(t) == set(PLAN) | set(CONTROLS)
    for n, (w, h, kind, ui) in PLAN.items():
        _, sset, rw, rh, rkind, b14, _, _ = T.row(n)
        assert (sset, rw, rh, rkind, b14) == ("heldout", w, h, kind, True), n
        assert T.fl(T.uv(n, 0, 0)[0]) == ui, n
    for n, (w, h) in CONTROLS.items():
        assert t[n]["set"] == "control" and t[n]["reads"] == ("pixels",)
        assert T.row(n)[2:4] == (w, h), n
    assert sum(T.row(n)[4] == "bil" for n in PLAN) == 7


def test_controls_can_fail_are_readable_and_gate():
    c = K.controls(KP, "tw17")
    assert set(c) == set(CONTROLS)
    SK.refuse_unreadable(c, score.producible)
    preds = K.predictions(KP, "tw17")
    assert all(len({m for mv in preds[n].values() for m in mv}) == 1 for n in c)
    assert score.GATE == T.GATE and score.ZERO == T.CTL_REP


def test_tool_and_options():
    for r in K.table(KP, "tw17"):
        a = r["args"].split()
        assert r["tool"] == "t14" and a[:5] == ["probe", "--temps", "32", "--coords", "--pixels"]
        assert a[5:7] == ["--scratch-pages", "256"] and len(a) == 8
        assert a[7] == f'"$S/bins/{r["name"]}.bin"'
        assert not any(x in CFG["forbid_options"] for x in a)
        assert not any("clock" in x or "clkgate" in x for x in a)
