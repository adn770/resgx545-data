# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing14/plan/rank-round14.md sections 2 and 3,
r14-tex per R14-1 (a), as README.md "Deviations" adapts them): the stages in run order with their
job counts (srgb4 13, addr5 14), and every row carrying the flags its premise needs (E934: a
premise without its flag is a stop). Section 3's premise checks for r14-tex: the scratch covers
every rival's farthest read (test_gen.py) and every type row has its mode 0 reference right before
it; the corner rows map 32 pages with the texture at page 12; the tri rows carry T0 bit 27 and bit
9 and smp2dreplace, the alpha rows the r11 template."""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"srgb4": 13, "addr5": 14}
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
    assert sum(COUNTS.values()) == 27
    assert list(CFG["tools"]) == ["t10"]
    t = CFG["tools"]["t10"]
    assert t["path"] == "sgxfive-test-t10" and t["sha256"].startswith("9bedc2d6")
    assert t["source"].startswith("a581c06bb24d") and t["source_sha256"].startswith("23e1fa76")
    assert CFG["health_tool"] == "t10" and CFG["prefix"] == "r14t" and CFG["name"] == "r14-tex"
    assert CFG["srcversion"] == "B60AB0B475DD1E8972419B5"
    assert not CFG["knobs"]
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["tool"] == "t10" and r["risk"] == "safe"
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


def test_plan_rows():
    names = {s: [r["name"] for r in rows(s)] for s in COUNTS}
    assert names["srgb4"] == ["srgb4-ctl", "srgb4-trir", "srgb4-b2x1", "srgb4-t1125", "srgb4-t15",
                              "srgb4-t175", "srgb4-t1984", "srgb4-t025", "srgb4-t12",
                              "srgb4-tdark", "srgb4-ax", "srgb4-ay", "srgb4-axy"]
    assert names["addr5"] == ["addr5-ctl", "addr5-bduv5", "addr5-8x8-uv5", "addr5-32x32-uv5",
                              "addr5-128x32-uv5", "addr5-32x128-uv5", "addr5-128x128-uv5",
                              "addr5-ty1-u0", "addr5-ty1-u4", "addr5-ty3-u0", "addr5-ty3-u4",
                              "addr5-ty4-u0", "addr5-ty4-u4", "addr5-256x32-uv5"]
    sets = {r["name"]: r["set"] for s in COUNTS for r in rows(s)}
    assert [n for n, st in sets.items() if st == "control"] == [
        "srgb4-ctl", "srgb4-trir", "srgb4-b2x1", "addr5-ctl", "addr5-bduv5"]
    assert [n for n, st in sets.items() if st == "replicate"] == [
        "addr5-ty1-u0", "addr5-ty3-u0", "addr5-ty4-u0"]


def t_word(name, reg):
    text = open(os.path.join(KP, "bins", name + ".s")).read()
    return int(re.search(rf"mov {reg}, #0x([0-9a-f]+)", text).group(1), 16)


def test_srgb_words():
    for r in rows("srgb4"):
        n = r["name"]
        if n in ("srgb4-ctl", "srgb4-trir"):
            continue                                  # the published bins (test_gen.py)
        assert t_word(n, "r20") >> 27 & 1, n          # T0 bit 27: sRGB
        text = open(os.path.join(KP, "bins", n + ".s")).read()
        if n.startswith("srgb4-t"):
            assert t_word(n, "r20") >> 9 & 1 and "smp2dreplace" in text, n
            assert t_word(n, "r20") >> 21 & 0x3F == 0x3F, n      # top: the LOD is the operand
        else:
            assert "o0, r11" in text and "o0, r10" not in text, n


def test_addr_rows():
    for r in rows("addr5"):
        n, a = r["name"], r["a"]
        if n == "addr5-bduv5" or n.endswith("-u0"):    # E565's and E567's programs: 16 pages
            assert len(a) == 6, n
            continue
        assert a[5:7] == ["--scratch-pages", "32"], n
        if n.endswith("-uv5"):
            assert "mov r22, #0x5cafc000" in open(os.path.join(KP, "bins", n + ".s")).read()
            t0 = t_word(n, "r20")
            assert t0 >> 6 & 7 == 5 and t0 >> 3 & 7 == 5, n
        if n.endswith("-u4"):
            ref = [x["name"] for x in rows("addr5")]
            assert ref[ref.index(n) - 1] == n[:-1] + "0"   # its reference right before it
            assert t_word(n, "r20") >> 6 & 7 == 4


def test_no_row_names_a_forbidden_option():
    for s in COUNTS:
        for r in rows(s):
            assert not re.search(r"--kreg|--kpoke|--clkgate|--trc-hazard|--fault\b", r["args"])
            assert "/tmp" not in r["args"]
