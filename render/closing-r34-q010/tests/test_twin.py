# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the table against the plan (closing29/plan/rank-round34.md section 3.1) and
the session build rules: one safe stage (#limit 0, no expectfault, no kreg, no dbg knob, no
pre:miscinfo), 32 jobs; the in-session references first, then triples L, X, R in the plan's order
with the second replicates reversed; every X is the health pair's own argv (kit/lib_kit.sh
health_ok: `$ht fill`, `$ht tri` with the session's health tool) or the plain copy; T6's triangle
alone is noreset and follows its fill; the idle words are T4's 60 s and T5's 120 s on R; every
control reads keys its row produces and has frozen predictions for each of them; every held-out
row is a copy without the load whose frozen hash is KEPT or CLEARED under each hypothesis."""
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
T = K.table(KP, "c")
BY = {r["name"]: r for r in T}
LOAD = "--poke xfer:17^=0x1"
R_ARGS = "copy --every-value --pixels --poke tex:1=0x7d03f01f --poke tex:0^=0x90"
BT601 = " --poke xfer:18=0x950095 --poke xfer:19=0x95 --poke xfer:20=0x10203ce --poke xfer:21=0x39800cc --poke xfer:22=0"
ZEROS = "".join(f" --poke xfer:{k}=0" for k in range(18, 23))


def test_one_safe_stage_of_32_jobs():
    assert list(CFG["stages"]) == ["c"]
    assert CFG["stages"]["c"].get("class") is None and not CFG["stages"]["c"].get("gate")
    assert CFG["stages"]["c"].get("on_stop") == "end"
    head = open(os.path.join(KP, "tables", "c.txt")).read().splitlines()
    assert "#limit 0" in head
    assert len(T) == 32
    for r in T:
        assert r["risk"] == "safe"
        for w in r["knobs"]:
            assert not w.startswith(("expectfault", "kreg:", "dbg:", "pre:", "after", "grp:", "soft")), r["name"]
    assert not CFG["knobs"] and not CFG["kregs"]
    assert CFG["srcversion"] == "7CE8E38EDB97FC5EA4F6C90" and CFG["prefix"] == "r34q"
    assert CFG["health_tool"] == "t10" and CFG["host_key_alias"] == "cedar"


def test_order_triples_and_reversed_replicates():
    names = [r["name"] for r in T]
    assert names[:2] == ["z0-ld", "z0-rd"]
    trip = []
    for n in names[2:]:
        t = n.split("-")[0]
        if not trip or trip[-1] != t:
            trip.append(t)
    assert trip == ["t0a", "t1a", "t2a", "t3a", "t4", "t5", "t6", "t3b", "t2b", "t1b", "t0b"]
    for t in trip:
        rows = [n for n in names if n.split("-")[0] == t]
        assert rows[0] == t + "-ld" and rows[-1] == t + "-rd", t
        xs = [BY[n]["args"] for n in rows[1:-1]]
        want = {"t0": [], "t1": ["fill"], "t2": ["tri"], "t3": ["copy --every-value --pixels"], "t4": [],
                "t5": [], "t6": ["fill", "tri"]}[t[:2]]
        assert xs == want, t


def test_loads_reads_and_the_x_jobs():
    for r in T:
        n, a = r["name"], r["args"]
        if n.endswith("-ld"):
            assert r["tool"] == "t30" and a == R_ARGS + " " + LOAD + (ZEROS if n == "z0-ld" else BT601), n
        elif n.endswith("-rd"):
            assert r["tool"] == "t30" and a == R_ARGS and LOAD not in a, n
            assert "expectdiff" in r["knobs"]
        else:
            assert r["set"] == "between"
            assert (r["tool"], a) in (("t10", "fill"), ("t10", "tri"), ("t30", "copy --every-value --pixels")), n
    # the health pair's argv, as the kit runs it (bare fill, then bare tri, the health tool)
    lib = open(os.path.join(KP, "kit", "lib_kit.sh")).read()
    assert re.search(r'"\$ht" fill >', lib) and re.search(r'"\$ht" tri >', lib)


def test_noreset_and_idle_words():
    nr = [r["name"] for r in T if "noreset" in r["knobs"]]
    assert nr == ["t6-xt"]
    names = [r["name"] for r in T]
    assert names[names.index("t6-xt") - 1] == "t6-xf"
    idle = {r["name"]: w for r in T for w in r["knobs"] if w.startswith("idle:")}
    assert idle == {"t4-rd": "idle:60", "t5-rd": "idle:120"}


def test_controls_read_what_they_produce_and_are_frozen():
    p = K.predictions(KP, "c")
    ctl = [r for r in T if r["set"] == "control"]
    assert [r["name"] for r in ctl] == [n for n in (r["name"] for r in T)
                                        if n.endswith("-ld") or n in ("z0-rd", "t0a-rd", "t0b-rd")]
    for r in ctl:
        assert set(r["reads"]) == {"job", "hash"} <= score.producible(r), r["name"]
        assert set(p[r["name"]]) == {"job", "hash"}
        want = score.CLEARED_HASH if r["name"].startswith("z0") else score.KEPT_HASH
        assert p[r["name"]]["hash"] == {"H-REF": want} and p[r["name"]]["job"] == {"H-REF": "ok"}


def test_heldout_rows_and_hypotheses():
    p = K.predictions(KP, "c")
    held = [r["name"] for r in T if r["set"] == "heldout"]
    assert held == ["t1a-rd", "t2a-rd", "t3a-rd", "t4-rd", "t5-rd", "t6-rd", "t3b-rd", "t2b-rd", "t1b-rd"]
    for n in held:
        for m in score.FULL:
            assert p[n]["hash"][m] in score.WORD
    clr = {m: {n for n in held if p[n]["hash"][m] == score.CLEARED_HASH} for m in score.FULL}
    assert clr == {"H-FILL": {"t1a-rd", "t1b-rd", "t6-rd"}, "H-TRI": {"t2a-rd", "t2b-rd", "t6-rd"},
                   "H-BOTH": {"t1a-rd", "t1b-rd", "t2a-rd", "t2b-rd", "t6-rd"}, "H-NONE": set()}
    assert {n for n in held if "H-IDLE" in p[n]["hash"]} == {"t4-rd", "t5-rd"}
    assert {n for n in held if "H-COPYNL" in p[n]["hash"]} == {"t3a-rd", "t3b-rd"}
    # every hypothesis is distinct on held-out rows
    pats = {m: tuple(p[n]["hash"][m] for n in held) for m in score.FULL}
    assert len(set(pats.values())) == len(pats)
