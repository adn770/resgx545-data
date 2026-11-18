# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the tables against the plan (closing29/plan/rank-round35.md sections 3.2 and
3.4) and the session build rules: two safe stages a then t (#limit 0, no expectfault, no kreg, no
dbg knob, no idle), 40 and 23 jobs; each stage's first row writes (D4: never a reader); every reader
follows its own writer; every control reads keys its row produces and is frozen for each; every
frozen hypothesis differs from its rivals on some held-out row."""
import os
import re
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
TA, TT = K.table(KP, "a"), K.table(KP, "t")
PA, PT = K.predictions(KP, "a"), K.predictions(KP, "t")


def test_two_safe_stages():
    assert list(CFG["stages"]) == ["a", "t"]
    assert CFG["stages"]["t"].get("on_stop") == "end" and not CFG["stages"]["a"].get("on_stop")
    for st in ("a", "t"):
        assert CFG["stages"][st].get("class") is None and not CFG["stages"][st].get("gate")
        assert "#limit 0" in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines()
    assert len(TA) == 40 and len(TT) == 23
    for r in TA + TT:
        assert r["risk"] == "safe"
        for w in r["knobs"]:
            assert not w.startswith(("expect", "kreg:", "dbg:", "pre:", "idle:", "after", "grp:",
                                     "soft")), r["name"]
        assert r["tool"] in ("t30", "t10")
        if r["tool"] == "t10":
            assert r["args"] == "tri"
        else:
            assert re.fullmatch(r'probe --temps (32|8)( --coords)? --pixels "\$S/bins/[\w-]+\.bin"',
                                r["args"]), r["args"]
            assert ("--coords" in r["args"]) == r["args"].endswith('/c.bin"')
            assert ("--temps 8" in r["args"]) == ("/t8-" in r["args"])
    assert not CFG["knobs"] and not CFG["kregs"]
    assert CFG["srcversion"] == "7CE8E38EDB97FC5EA4F6C90" and CFG["prefix"] == "r35s"
    assert CFG["health_tool"] == "t10" and CFG["host_key_alias"] == "cedar"
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")
    assert CFG["freeze"]["resgx545"].startswith("eea6d2a")


def test_stage_a_rows_as_planned():
    names = [r["name"] for r in TA]
    assert names[:2] == ["c0a-k", "c1a-c"] and names[2] == "f0a-w"
    ns = sorted(int(score.group_of(n)[1:]) for n in names if n[0] in "fh" and n.endswith("-w")
                and score.group_of(n) != "h157")
    assert sorted(set(ns)) == list(range(16))                  # sa0-sa15
    two = {0, 1, 2, 3, 5, 7, 15}
    assert all(ns.count(n) == (2 if n in two else 1) for n in range(16))
    assert names.count("h157a-w") == names.count("h157b-w") == 1
    for g in ("c2", "p"):
        for rep in "ab":
            assert [n for n in names if n.startswith(g + rep + "-")] == \
                [f"{g}{rep}-w"] + ([f"{g}{rep}-x"] if g == "p" else []) + [f"{g}{rep}-r"]
    assert [n for n in names if n.startswith("q")] == ["qa-w", "qa-x", "qa-r"]
    # the second replicate runs the two-replicate groups reversed
    ga = [score.group_of(n) for n in names if n.split("-")[0].endswith("a")]
    gb = [score.group_of(n) for n in names if n.split("-")[0].endswith("b")]
    dedup = lambda xs: [x for i, x in enumerate(xs) if not i or xs[i - 1] != x]  # noqa: E731
    assert dedup(gb) == [g for g in reversed(dedup(ga)) if g in set(gb)]
    for i, r in enumerate(TA):
        if r["name"].endswith(("-r", "-x")):
            assert "noreset" in r["knobs"] and TA[i - 1]["name"].split("-")[0] == r["name"].split("-")[0]
        else:
            assert "noreset" not in r["knobs"]
    sets = {n: r["set"] for n, r in zip(names, TA)}
    assert {sets[n] for n in names if n[0] == "f"} == {"fit"}
    assert {sets[n] for n in names if n[0] == "h"} == {"heldout"}
    assert sets["pa-r"] == sets["pb-r"] == "heldout" and sets["qa-r"] == "fit"


def test_stage_t_rows_as_planned():
    names = [r["name"] for r in TT]
    assert names[0] == "ca-t"
    groups = {}
    for n in names:
        groups.setdefault(n.split("-")[0], []).append(n.split("-")[1])
    assert groups["ca"] == groups["cb"] == ["t", "u"]
    for rep in "ab":
        assert groups["t1" + rep] == groups["t2" + rep] == ["t", "x", "u"]
        assert groups["t3" + rep] == ["t", "u"]
    assert groups["t4a"] == ["t", "x", "u"] and "t4b" not in groups
    by = {r["name"]: r for r in TT}
    assert by["t2a-x"]["tool"] == "t10" and "--temps 8" in by["t4a-x"]["args"]
    assert "/k.bin" in by["t1a-x"]["args"]
    for n, r in by.items():
        if n.endswith("-u"):
            assert ("noreset" in r["knobs"]) == (not n.startswith("t3")), n
            assert r["set"] == ("control" if n[0] == "c" else "heldout")


def test_controls_read_what_they_produce_and_are_frozen():
    for tab, pred in ((TA, PA), (TT, PT)):
        for r in tab:
            if r["set"] != "control":
                continue
            assert set(r["reads"]) <= score.producible(r), r["name"]
            assert set(pred[r["name"]]) == set(r["reads"]), r["name"]
            assert all(set(v) == {"H-REF"} for v in pred[r["name"]].values())


def test_hypotheses_differ_on_held_out_rows():
    held = [r["name"] for r in TT if r["set"] == "heldout"]
    pats = {m: tuple(PT[n]["cat"][m] for n in held) for m in score.T_FULL}
    assert len(set(pats.values())) == 3
    p = [r["name"] for r in TA if r["name"] in ("pa-r", "pb-r")]
    assert {PA[n]["cat"]["H-ONEJOB"] for n in p} == {"PREV"}
    assert {PA[n]["cat"]["H-UNTILWRITE"] for n in p} == {"M"}
    for n in ("h2a-w", "h15b-w"):
        assert PA[n]["pos"]["H-FIXED4"] == "S0" and PA[n]["pos"]["H-SHIFT"].startswith("S0+")
