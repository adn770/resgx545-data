# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing10/seeds/exp-seeds-r10.md, S10-tex per
R10-2 (a), sections 1 to 4 and 15, as README.md "Deviations" adapts them): the stages in run order
with their job counts, and every row carrying the flags its premise needs (E934: a premise without
its flag is a stop). Section 15's S10-tex checks: addr3 rows `--scratch-pages 32` and T2 page 12
(test_gen.py: every rival's read inside the mapping); t3b rows scratch pages >= the largest
rival's read + 1 page (test_gen.py); every bit-14 row followed by its `-ref`."""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"addr3": 11, "cube3": 16, "t3b": 15, "srgb2": 6}
PROBE = ["probe", "--temps", "32", "--coords", "--pixels"]


def rows(stage):
    out = []
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, risk, knobs, tool, args = ln.rstrip("\n").split("|", 5)
            out.append(dict(name=name, set=st, risk=risk, knobs=knobs.split(), tool=tool,
                            args=args, a=args.split()))
    return out


def test_stages_and_counts():
    assert list(CFG["stages"]) == list(COUNTS)
    assert {s: len(rows(s)) for s in COUNTS} == COUNTS
    assert sum(COUNTS.values()) == 48
    assert CFG["tools"].keys() == {"t4"} and CFG["tools"]["t4"]["path"] == "sgxfive-test-rgn4"
    assert CFG["tools"]["t4"]["source"].startswith("4623753f2cc5")
    assert not CFG["knobs"]
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["tool"] == "t4" and r["risk"] == "safe"
            assert (r["set"] == "control") == (r["knobs"] == ["reads:pixels"])
            if r["set"] != "control":
                assert r["knobs"] == ["-"]
        assert rows(s)[0]["set"] == "control"


def test_probe_rows():
    for s in COUNTS:
        for r in rows(s):
            a = r["a"]
            assert a[:5] == PROBE, r["name"]
            assert a[-1] == f'"$S/bins/{r["name"]}.bin"'
            assert len(a) in (6, 8)
            if len(a) == 8:
                assert a[5] == "--scratch-pages" and 16 < int(a[6]) <= 64
            assert os.path.exists(os.path.join(KP, "bins", r["name"] + ".bin"))
    assert all(r["a"][5:7] == ["--scratch-pages", "32"] for r in rows("addr3"))


def test_plan_rows():
    names = {s: [r["name"] for r in rows(s)] for s in COUNTS}
    assert names["addr3"] == ["addr3-ctl-u0", "addr3-u4-rep", "addr3-ns32x8-u4", "addr3-8x32-u4",
                              "addr3-16x64-u4", "addr3-64x16-u4", "addr3-64x64-u4",
                              "addr3-64x64-u6", "addr3-4x4-u4", "addr3-16x32-u5",
                              "addr3-32x16-u5"]
    cube = names["cube3"]
    assert cube[0] == "cube3-ctl-xn" and cube[-3:] == ["cube3-a2-replay", "cube3-edge-zx",
                                                       "cube3-edge-yx"]
    assert sorted(cube[1:13]) == sorted(f"cube3-{k}-{p}-{s}" for k in ("cc", "rr")
                                        for p in ("xy", "yz", "xz") for s in ("pn", "pp"))
    t3 = names["t3b"]
    assert t3[:3] == ["t3b-ctl", "t3b-b14ref", "t3b-u01"]
    for i in range(3, 15, 2):                        # every bit-14 row followed by its reference
        assert t3[i + 1] == t3[i] + "-ref"
    assert names["srgb2"] == ["srgb2-ctl", "srgb2-offgrid", "srgb2-k0b", "srgb2-sub", "srgb2-rand1",
                              "srgb2-rand2"]


def test_bit14_rows_set_bit14_and_refs_clear_it():
    for r in rows("t3b")[3:]:
        text = open(os.path.join(KP, "bins", r["name"] + ".s")).read()
        t3 = int(re.search(r"mov r23, #0x([0-9a-f]+)", text).group(1), 16)
        assert bool(t3 >> 14 & 1) == (not r["name"].endswith("-ref")), r["name"]


def test_no_row_names_a_forbidden_option():
    for s in COUNTS:
        for r in rows(s):
            assert not re.search(r"--kreg|--kpoke|--clkgate|--trc-hazard|--fault\b", r["args"])
            assert "/tmp" not in r["args"]
