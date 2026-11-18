# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing29/plan/rank-round35.md 3.3, R35-1 (a),
R35-4 (a), as README.md "Deviations" adapts it): the stages in run order with their job counts,
every row a safe t10 `probe --tri pixel --pixels` of the colour or ramp form carrying the flags its
premise needs (E934): --cmd on word 11 alone, --sideband 0x200 | mode with bits 11 and 8:6 clear
(E383), pack modes 14, 22, 26, 34 never, the ramp rows with E385's pixpds (12 data dwords),
vtxuse and --vtx-coords 2; every stage but s0 starts with its mode 0 reference; r3's rows follow
their mode's reference."""
import os
import re
import shlex
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import pk as Q  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"s0": 9, "r1": 15, "r2": 41, "r3": 20, "pw": 7}
HEAD = ["probe", "--temps", "32", "--pixels", "--tri", "pixel", "--width", "64", "--height", "64"]


def rows(stage):
    out = []
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, risk, knobs, tool, args = ln.rstrip("\n").split("|", 5)
            out.append(dict(name=name, set=st, risk=risk, knobs=knobs.split(), tool=tool,
                            args=args, a=shlex.split(args)))
    return out


def opts(a):
    o, i = {}, len(HEAD)
    while i < len(a) - 1:
        o.setdefault(a[i], []).append(a[i + 1])
        i += 2
    return o


def test_stages_and_counts():
    assert list(CFG["stages"]) == list(COUNTS)
    assert {s: len(rows(s)) for s in COUNTS} == COUNTS
    assert sum(COUNTS.values()) == 92
    assert CFG["tools"].keys() == {"t10"}
    assert CFG["tools"]["t10"]["sha256"].startswith("9bedc2d6")
    assert CFG["tools"]["t10"]["source"].startswith("a581c06bb24d")
    assert CFG["health_tool"] == "t10" and CFG["prefix"] == "r35p" and CFG["name"] == "r35-pk"
    assert CFG["srcversion"] == "7CE8E38EDB97FC5EA4F6C90"
    assert CFG["host_key_alias"] == "cedar"
    assert not CFG["knobs"] and not CFG["kregs"]
    assert CFG["freeze"]["resgx545"].startswith("eea6d2a")
    assert CFG["stages"]["s0"]["on_stop"] == "end"
    for s in ("r1", "r2", "r3", "pw"):
        assert CFG["stages"][s]["gate"] is True
    assert all(CFG["stages"][s].get("class", "safe") == "safe" for s in COUNTS)
    assert list(CFG["stages"])[-1] == "pw"


def test_every_row():
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        assert rows(s)[0]["set"] == "control"
        for r in rows(s):
            a = r["a"]
            assert r["tool"] == "t10" and r["risk"] == "safe", r
            assert (r["set"] == "control") == (r["knobs"] == ["reads:pixels"]), r
            if r["set"] != "control":
                assert r["knobs"] == ["-"], r
            assert a[:len(HEAD)] == HEAD, r
            assert a[-1] in ("$S/bins/colour.bin", "$S/bins/ramp_xy.bin"), r
            o = opts(a[:-1])
            assert set(o) <= {"--cmd", "--sideband", "--slot", "--vtx-coords"}, r
            assert len(o["--cmd"]) == 1 and o["--cmd"][0].startswith("11=0x"), r
            word = int(o["--cmd"][0][3:], 16)
            assert word & ~0x020000FF == 0, r
            sb = int(o["--sideband"][0], 16)
            assert sb & ~0x3F == 0x200 and sb & 0x3F not in (14, 22, 26, 34), r
            slots = dict(x.split("=", 1) for x in o["--slot"])
            if a[-1].endswith("ramp_xy.bin"):
                assert slots == {"eot": "$S/bins/eot_plain.bin",
                                 "pixpds": "$S/bins/pds_iter_xy.bin:12",
                                 "vtxuse": "$S/bins/vtx_coords.bin"}, r
                assert o["--vtx-coords"] == ["2"]
            else:
                assert slots == {"eot": "$S/bins/eot_plain.bin"} and "--vtx-coords" not in o
                assert r["set"] == "control" and word == 0x80


def test_modes_and_references():
    for s in ("r1", "r2", "r3", "pw"):
        assert rows(s)[0]["name"] == f"{s}-m00-ref"
        assert rows(s)[0]["a"][-1].endswith("ramp_xy.bin")
    r2 = {int(r["name"][4:6]) for r in rows("r2")[1:]}
    assert r2 == set(Q.ARGB40) and len(r2) == 40
    r1 = [int(r["name"][4:6]) for r in rows("r1")[1:]]
    assert r1 == list(Q.R1_MODES) + list(reversed(Q.R1_MODES))
    seen = set()
    for r in rows("r3"):
        m = re.match(r"^r3-m(\d\d)-(ref|w([0-9a-f]{8})-[ab])$", r["name"])
        assert m, r["name"]
        mode = int(m.group(1))
        if m.group(2) == "ref":
            seen.add(mode)
        else:
            assert mode in seen and int(m.group(3), 16) in Q.R3_WORDS
    assert {int(r["name"][4:6]) for r in rows("pw")[1:]} == {12, 13}
