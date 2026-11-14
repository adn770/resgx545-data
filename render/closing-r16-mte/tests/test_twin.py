# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing16/plan/rank-round16.md sections 2 "r16-mte"
and 3, decision R16-4 (a); README.md "Deviations"): one stage rclip of 15 jobs on t10, the gate row
first with E348's clear-clip formula, its no-clip twin second, the empty-clip row last with
`on_stop = "end"`; every row carrying the flags its premise needs (E934): `probe --tri pixel`,
`--pixels` (the image is the reading), `--tri-full` on every full-target row, `--blk-add 7=C0,C1`
on every clip row and on no other; every partial row parting H-TILECLIP from H-FLIP (the plan's
row-origin rival) and H-EXCL on at least 256 pixels."""
import os
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import model as M  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def rows():
    out = []
    for ln in open(os.path.join(KP, "tables", "rclip.txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, risk, knobs, tool, args = ln.rstrip("\n").split("|", 5)
            out.append(dict(name=name, set=st, risk=risk, knobs=knobs.split(), tool=tool,
                            args=args, a=args.split()))
    return out


def opt(r, o):
    return r["a"][r["a"].index(o) + 1]


def test_one_stage_15_jobs_on_stop_end():
    assert list(CFG["stages"]) == ["rclip"]
    assert CFG["stages"]["rclip"].get("on_stop") == "end"
    rs = rows()
    assert len(rs) == 15
    head = open(os.path.join(KP, "tables", "rclip.txt")).read().splitlines()[:2]
    assert head == ["#stage rclip", "#limit 0"]                     # any fault or hang stops
    for r in rs:
        assert r["risk"] == "safe" and r["tool"] == "t10"
        assert (r["set"] == "control") == any(w.startswith("reads:") for w in r["knobs"])
        assert not any(w in ("expectfault", "expectdiff", "soft", "gate", "noreset") or
                       w.startswith(("expect:", "dbg:", "idle:")) for w in r["knobs"])
    assert list(CFG["tools"]) == ["t10"]
    t = CFG["tools"]["t10"]
    assert t["sha256"].startswith("9bedc2d6") and t["source"].startswith("a581c06")
    assert CFG["knobs"] == {} and CFG["prefix"] == "r16m"
    assert CFG["srcversion"] == "B60AB0B475DD1E8972419B5"


def test_order_gate_first_empty_last():
    rs = rows()
    assert [r["name"] for r in rs[:2]] == ["g-clear-64", "g-twin-64"]
    assert [r["set"] for r in rs[:2]] == ["control", "control"]
    assert all(r["set"] == "heldout" for r in rs[2:])
    assert rs[-1]["name"] == "z128-empty"
    # the gate's clip words are E348's formula for the clear's block at 64 x 64
    assert opt(rs[0], "--blk-add") == "7=0x%08x,0x%08x" % (0x80000000 | (64 - 1) // 32, (64 - 1) // 16)
    assert opt(rs[0], "--blk-add") == "7=0x80000001,0x00000003"       # E348's table, base row
    assert "--blk-add" not in rs[1]["a"]
    assert [a for a in rs[0]["a"] if a != "--blk-add" and not a.startswith("7=")] == rs[1]["a"]
    # E348's viewport row's triangle clip, at its own 64 x 64
    vp = [r for r in rs if r["name"] == "vp64-e348"][0]
    assert opt(vp, "--blk-add") == "7=0x80010001,0x00010003"


def test_every_row_carries_its_premise_flags():
    for r in rows():
        a, m = r["a"], M.row(r["name"])
        assert a[:3] == ["probe", "--tri", "pixel"] and "--pixels" in a
        assert opt(r, "--temps") == "32" and a[-1] == '"$S/bins/pix_green.bin"'
        assert (opt(r, "--width"), opt(r, "--height")) == (str(m["w"]), str(m["h"]))
        assert ("--tri-full" in a) == m["full"]
        assert a.count("--blk-add") == (1 if m["clip"] else 0)
        if m["clip"]:
            bit, words = opt(r, "--blk-add").split("=")
            assert bit == "7" and tuple(int(v, 16) for v in words.split(",")) == m["clip"]


def test_rows_of_the_plan():
    rs = {r["name"]: M.row(r["name"]) for r in rows()}
    sizes = {(m["w"], m["h"]) for m in rs.values()}
    assert {(64, 64), (128, 128), (256, 256), (100, 60)} == sizes
    words = {n: M.clip_words(*m["clip"]) for n, m in rs.items() if m["clip"]}
    # column ranges of one tile and of two at each of 64, 128, 256 (the plan's six)
    for s in (64, 128, 256):
        cols = {w[2] - w[1] + 1 for n, w in words.items() if n.startswith("p%d" % s)}
        assert cols == {1, 2}, (s, cols)
    # enable clear with a partial range, set with the full range
    assert words["e128-off"][0] == 0 and words["e128-on-full"] == (1, 0, 3, 0, 7)
    # four macrotiles at 256 x 256 (n = 2: boundaries at tile column 4, tile row 8)
    m = words["m256-c34-r59"]
    assert m[1] < 4 <= m[2] and m[3] < 8 <= m[4]
    # the straddling triangle and the empty clip use the default (not full) triangle
    assert not rs["s128-tri"]["full"] and not rs["z128-empty"]["full"]


def test_partial_rows_part_the_rivals_on_256_pixels():
    part = [n for n in M.NAMES if M.partial(M.row(n))]
    assert len(part) == 10
    for n in part:
        r = M.row(n)
        f = M.predict(r, M.FROZEN)
        for rival in (("H-FLIP", "H-BG", "H-EN"), ("H-EXCL", "H-BG", "H-EN")):
            assert M.parts(f, M.predict(r, rival)) >= 256, (n, rival)
        for rival in M.RIVALS:                               # every rival but the enable's
            if rival[2] == "H-EN":
                assert M.parts(f, M.predict(r, rival)) >= 256, (n, rival)


def test_enable_and_empty_rows_part_their_rivals():
    r = M.row("e128-off")
    f = M.predict(r, M.FROZEN)
    for rival in (("H-TILECLIP", "H-BG", "H-ALWAYS"), ("H-TILECLIP", "H-BG", "H-OFFDROP")):
        assert M.parts(f, M.predict(r, rival)) >= 256
    z = M.row("z128-empty")
    f = M.predict(z, M.FROZEN)
    assert "G" not in f and "g" not in f                      # no pixel of the object is kept
    assert M.parts(f, M.predict(z, ("H-NOCLIP", "H-BG", "H-EN"))) >= 256
    assert M.parts(f, M.predict(z, ("H-TILECLIP", "H-UNTOUCHED", "H-EN"))) >= 256
    assert M.parts(f, M.predict(z, ("H-FLIP", "H-BG", "H-EN"))) > 0


def test_no_row_names_a_forbidden_option():
    forbid = set(CFG["forbid_options"]) | {"--kreg", "--clkgate", "--trc-hazard", "--kpoke"}
    for r in rows():
        assert not forbid & set(r["a"]), r["name"]
