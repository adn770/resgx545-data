# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing29/plan/rank-round34.md 3.2, R34-1 (a),
R34-4 (a), as README.md "Deviations" adapts it): the stages in run order with their job counts,
every row a safe t10 `probe --tri pixel --pixels` of E031's / E385's form carrying the flags its
premise needs (E934): --cmd on word 11 alone (pixelbe, include/uapi/sgxfive_drm.h at a581c06),
--sideband 0x200 | mode with bits 11 and 12 and 8:6 clear (E383: bit 11 faults), pack mode 14
never (E031: it faults), the ramp rows with E385's pixpds (12 data dwords), vtxuse and
--vtx-coords 2. Premise checks: every bit-25 and every low-byte row follows its mode's reference
in the same stage; 22, 26 and 34 have a second reference after the bit-25 row."""
import os
import re
import shlex
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import q044 as Q  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"s0": 7, "p1": 118, "p2": 68, "pw": 5}
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
    o = {}
    i = len(HEAD)
    while i < len(a) - 1:
        o.setdefault(a[i], []).append(a[i + 1])
        i += 2
    return o


def test_stages_and_counts():
    assert list(CFG["stages"]) == list(COUNTS)
    assert {s: len(rows(s)) for s in COUNTS} == COUNTS
    assert sum(COUNTS.values()) == 198
    assert CFG["tools"].keys() == {"t10"}
    assert CFG["tools"]["t10"]["sha256"].startswith("9bedc2d6")
    assert CFG["tools"]["t10"]["source"].startswith("a581c06bb24d")
    assert CFG["health_tool"] == "t10" and CFG["prefix"] == "r34p" and CFG["name"] == "r34-q044"
    assert CFG["srcversion"] == "7CE8E38EDB97FC5EA4F6C90"
    assert CFG["host_key_alias"] == "cedar"
    assert not CFG["knobs"] and not CFG["kregs"]
    assert CFG["freeze"]["resgx545"].startswith("5745c8d")
    assert CFG["stages"]["s0"]["on_stop"] == "end"
    for s in ("p1", "p2", "pw"):
        assert CFG["stages"][s]["gate"] is True
    assert all(CFG["stages"][s].get("class", "safe") == "safe" for s in COUNTS)


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
            assert a[-1] in ("$S/bins/colour.bin", "$S/bins/ramp.bin"), r
            o = opts(a[:-1])
            assert set(o) <= {"--cmd", "--sideband", "--slot", "--vtx-coords"}, r
            assert len(o["--cmd"]) == 1 and o["--cmd"][0].startswith("11=0x"), r
            word = int(o["--cmd"][0][3:], 16)
            assert word & ~0x02000FFF == 0, r          # only the bits the register takes (E251)
            sb = int(o["--sideband"][0], 16)
            assert sb & ~0x3F == 0x200 and sb & 0x3F != 14, r
            slots = dict(x.split("=", 1) for x in o["--slot"])
            if a[-1].endswith("ramp.bin"):
                assert slots == {"eot": "$S/bins/eot_plain.bin",
                                 "pixpds": "$S/bins/pds_iter_xy.bin:12",
                                 "vtxuse": "$S/bins/vtx_coords.bin"}, r
                assert o["--vtx-coords"] == ["2"]
            else:
                assert slots == {"eot": "$S/bins/eot_plain.bin"} and "--vtx-coords" not in o


def test_modes_run_and_left_out():
    p1 = {int(r["name"][4:6]) for r in rows("p1") if r["name"].startswith("p1-m")}
    pw = {int(r["name"][4:6]) for r in rows("pw") if r["name"].startswith("pw-m")}
    assert p1 | pw == set(range(4, 64)) - {14}
    assert pw == {12, 13} and not p1 & pw
    every = [r for s in COUNTS for r in rows(s)]
    assert not [r for r in every if int(opts(r["a"][:-1])["--sideband"][0], 16) & 0x3F == 14]


def test_references_precede_their_rows():
    for s in ("p1", "p2", "pw"):
        seen = set()
        for r in rows(s):
            m = re.match(rf"^{s}-m(\d\d)-(\w+)$", r["name"])
            if not m:
                continue
            mode, what = int(m.group(1)), m.group(2)
            if what == "ref":
                seen.add(mode)
                continue
            assert mode in seen, r["name"]
            o = opts(r["a"][:-1])
            assert int(o["--sideband"][0], 16) & 0x3F == mode, r["name"]
    names = [r["name"] for r in rows("p1")]
    for m in Q.REPEAT2:
        i = names.index(f"p1-m{m:02d}-b25")
        assert names[i - 1] == f"p1-m{m:02d}-ref" and names[i + 1] == f"p1-m{m:02d}-ref2"
    names = [r["name"] for r in rows("p2")]
    assert names.index("p2-m26-ref2") == names.index("p2-m26-wf80") + 1


def test_the_bit25_and_word_values():
    for s in ("p1", "pw"):
        for r in rows(s):
            w = int(opts(r["a"][:-1])["--cmd"][0][3:], 16)
            assert w == (Q.B25 if r["name"].endswith("-b25") else Q.W080), r["name"]
    for r in rows("p2"):
        w = int(opts(r["a"][:-1])["--cmd"][0][3:], 16)
        if r["name"].endswith(("-ref", "-ref2")):
            assert w == Q.W080
        elif "-m04-e" in r["name"]:
            assert w == int(r["name"][-2:], 16) and w in Q.EQ
        else:
            assert w == int(r["name"].rsplit("-w", 1)[1], 16)
