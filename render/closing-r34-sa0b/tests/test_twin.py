# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the table against the plan (closing29/plan/rank-round34.md section 3.6, the
lead's sketch: an iaddu32 to sa0 in a fill's pixel task, readers after noreset, idle:S for several
S, a debugfs reset and other jobs between, every reader held out, controls) and the session build
rules: one safe stage (#limit 0, no expectfault, no kreg, no dbg knob, no pre:miscinfo), 54 jobs;
the first row after the stage-begin health is a W; the second replicate is the first reversed;
every X is the health pair's own argv or the colour job; every control reads keys its row
produces and is frozen for each of them; every hypothesis differs from its rivals on held-out
rows."""
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
T = K.table(KP, "s")
BY = {r["name"]: r for r in T}
P = K.predictions(KP, "s")


def groups(rep):
    out = []
    for r in T:
        t = r["name"].split("-")[0]
        if t.endswith(rep) and (not out or out[-1] != t):
            out.append(t)
    return out


def test_one_safe_stage_of_54_jobs():
    assert list(CFG["stages"]) == ["s"]
    assert CFG["stages"]["s"].get("class") is None and not CFG["stages"]["s"].get("gate")
    assert CFG["stages"]["s"].get("on_stop") == "end"
    head = open(os.path.join(KP, "tables", "s.txt")).read().splitlines()
    assert "#limit 0" in head
    assert len(T) == 54
    for r in T:
        assert r["risk"] == "safe"
        for w in r["knobs"]:
            assert not w.startswith(("expectfault", "kreg:", "dbg:", "pre:", "after", "grp:", "soft",
                                     "expect")), r["name"]
    assert not CFG["knobs"] and not CFG["kregs"]
    assert CFG["srcversion"] == "7CE8E38EDB97FC5EA4F6C90" and CFG["prefix"] == "r34t"
    assert CFG["health_tool"] == "t10" and CFG["host_key_alias"] == "cedar"
    assert CFG["tools"]["t30"]["sha256"].startswith("b5ea288d")


def test_order_and_reversed_replicates():
    ga = [g[:-1] for g in groups("a")]
    gb = [g[:-1] for g in groups("b")]
    assert ga == ["nr", "rs", "i10", "i60", "i120", "k3", "fl", "tr", "ptr", "pk3", "pfl",
                  "pk3r"]
    assert gb == list(reversed(ga))
    assert [r["name"] for r in T][:27] == [r["name"] for r in T if r["name"].split("-")[0][-1] == "a"]
    assert T[0]["name"] == "nra-w"                      # the first row after the health is a W


def test_rows_of_each_group():
    for r in T:
        n, g = r["name"], r["name"].split("-")[0][:-1]
        a = r["args"]
        if n.endswith("-w"):
            assert r["set"] == "control" and r["tool"] == "t30" and r["knobs"] == ["reads:sa,top"]
            assert re.fullmatch(r'probe --temps 32 "\$S/bins/w-5a0c0[ab]0[1-9]\.bin"', a)
        elif n.endswith("-r"):
            assert r["set"] == "heldout" and a == 'probe --temps 32 "$S/bins/r.bin"'
        elif n.endswith("-p"):
            assert r["set"] == ("fit" if g == "ptr" else "heldout")
            assert a == 'probe --temps 32 "$S/bins/p.bin"'
        else:
            assert n.endswith("-x")
            assert (r["tool"], a) in (("t10", "fill"), ("t10", "tri"),
                                      ("t30", 'probe --temps 32 "$S/bins/k.bin"')), n
            assert (r["set"] == "control") == (r["tool"] == "t30")
    # the health pair's argv, as the kit runs it (bare fill, then bare tri, the health tool)
    lib = open(os.path.join(KP, "kit", "lib_kit.sh")).read()
    assert re.search(r'"\$ht" fill >', lib) and re.search(r'"\$ht" tri >', lib)
    # every writer's marker is its own
    ms = [r["args"] for r in T if r["name"].endswith("-w")]
    assert len(ms) == len(set(ms)) == 16


def test_noreset_reset_and_idle_words():
    idle = {r["name"]: w for r in T for w in r["knobs"] if w.startswith("idle:")}
    assert idle == {f"i{s}{rep}-r": f"idle:{s}" for s in (10, 60, 120) for rep in "ab"}
    reset_readers = {r["name"] for r in T if r["set"] in ("heldout", "fit")
                     and "noreset" not in r["knobs"]}
    assert reset_readers == {"rsa-r", "rsb-r", "pk3ra-p", "pk3rb-p"}
    for i, r in enumerate(T):
        n = r["name"]
        if n.endswith("-w"):
            assert "noreset" not in r["knobs"]
        if n.endswith("-x") and not n.startswith("p"):
            assert "noreset" in r["knobs"], n
        if n.endswith("-x") and n.startswith("p"):
            assert "noreset" not in r["knobs"], n
        if r["set"] in ("heldout", "fit"):
            assert i > 0 and T[i - 1]["name"].split("-")[0] == n.split("-")[0]


def test_controls_read_what_they_produce_and_are_frozen():
    for r in T:
        if r["set"] != "control":
            continue
        assert set(r["reads"]) == {"sa", "top"} <= score.producible(r), r["name"]
        assert set(P[r["name"]]) == {"sa", "top"}
        assert set(P[r["name"]]["sa"]) == {"H-REF"}


def test_hypotheses_on_held_out_rows():
    held = [r["name"] for r in T if r["set"] == "heldout"]
    rrows = [n for n in held if not n.startswith("p")]
    prows = [n for n in held if n.startswith("p")]
    assert len(rrows) == 16 and len(prows) == 6
    pats = {m: tuple(P[n]["cat"][m] for n in rrows) for m in score.FULL_A}
    assert len(set(pats.values())) == 3
    for n in rrows:
        g = n.split("-")[0][:-1]
        between = g in ("k3", "fl", "tr")
        assert P[n]["cat"]["H-PERSIST"] == "M" and P[n]["cat"]["H-COLOUR"] == "PREV"
        assert P[n]["cat"]["H-ONEJOB"] == ("PREV" if between else "M")
        assert ("H-RESET" in P[n]["cat"]) == (g == "rs")
        assert ("H-IDLE" in P[n]["cat"]) == (g in ("i10", "i60", "i120"))
    for n in prows + ["ptra-p", "ptrb-p"]:
        assert P[n]["cat"]["H-PREV"] == "PREV" and P[n]["cat"]["H-FIXED"] == "TRI"
        assert ("H-RESETP" in P[n]["cat"]) == n.startswith("pk3r")
