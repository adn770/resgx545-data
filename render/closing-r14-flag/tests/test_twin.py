# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing14/plan/rank-round14.md section 2 "F1",
"F2"; closing14/DECISIONS-R14.md R14-5 a) and the session build rules: each stage's #limit counts
exactly its planned rows (expectfault rows that are not controls, E946's slip designed out) and the
last planned row is the stage's last row; every planned row comes after a control of its own shape
(no default triangle) that can fail, reads a key its row produces and does not expectfault; f1 runs
on t14 with 256 scratch pages, f2 on t10 with only CR_TE_MTILE1 poked; no knob, no noreset, no idle,
no clock-gate option; f1 ends the session on its stop."""
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

PLANNED = {"f1": 3, "f2": 4}
JOBS = {"f1": 5, "f2": 6}
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def limit(stage):
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.startswith("#limit"):
            return int(ln.split()[1])


def test_stages_in_order_f1_ends_the_session():
    assert list(CFG["stages"]) == ["f1", "f2"]
    assert CFG["stages"]["f1"].get("on_stop") == "end"
    assert not CFG["knobs"]


def test_limit_counts_the_planned_rows_only():
    for st, n in PLANNED.items():
        t = K.table(KP, st)
        assert len(t) == JOBS[st], st
        planned = [r["name"] for r in t if "expectfault" in r["knobs"] and r["set"] != "control"]
        assert len(planned) == n == limit(st), st
        assert planned[-1] == t[-1]["name"], st


def test_controls_can_fail_are_readable_and_come_first():
    for st in PLANNED:
        c = K.controls(KP, st)
        assert c, st
        SK.refuse_unreadable(c, score.producible)
        preds = K.predictions(KP, st)
        assert all(preds.get(n) for n in c), st
        t = K.table(KP, st)
        assert all("expectfault" not in r["knobs"] for r in t if r["set"] == "control")
        assert t[0]["set"] == "control"
    gate = {"f1-tw32": "f1-ref-a", "f1-small": "f1-ref-b", "f1-zero": "f1-ref-b"}
    assert gate == score.F1_GATE
    order = [r["name"] for r in K.table(KP, "f1")]
    assert all(order.index(c) < order.index(r) for r, c in gate.items())
    t2 = K.table(KP, "f2")
    for i, r in enumerate(t2):
        if r["set"] != "control":
            size = r["args"].split("--width ")[1].split()[0]
            assert any(c["set"] == "control" and c["args"].split("--width ")[1].split()[0] == size
                       for c in t2[:i]), r["name"]


def test_tools_and_options():
    for r in K.table(KP, "f1"):
        a = r["args"].split()
        assert r["tool"] == "t14" and a[:5] == ["probe", "--temps", "32", "--coords", "--pixels"]
        assert a[5:7] == ["--scratch-pages", "256"] and len(a) == 8
    for r in K.table(KP, "f2"):
        a = r["args"].split()
        assert r["tool"] == "t10" and a[0] == "tri" and "--dump-render" in a
        pokes = [a[i + 1] for i, x in enumerate(a) if x.startswith("--kpoke")]
        assert all(p.startswith("1:ta:143=") for p in pokes)
        assert ("expectfault" in r["knobs"]) == bool(pokes)
    for st in PLANNED:
        for r in K.table(KP, st):
            assert not any(k.startswith(("dbg:", "idle:")) or k == "noreset" for k in r["knobs"])
            assert not any("clock" in x or "clkgate" in x for x in r["args"].split())
