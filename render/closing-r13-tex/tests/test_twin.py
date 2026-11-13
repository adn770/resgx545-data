# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing13/plan/rank-round13.md sections 2 and 3,
r13-tex per R13-1 (a), as README.md "Deviations" adapts them): the stages in run order with their
job counts, and every row carrying the flags its premise needs (E934: a premise without its flag is
a stop). Section 3's premise check for r13-tex: scratch pages cover every rival's farthest read
(test_gen.py) and every bit-14 row is followed by its reference; addr4 rows map 32 pages with the
texture at page 12; sb12 rows carry the eot slot, --sideband with bit 12 and the moved row
--tri-v."""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"srgb3": 9, "addr4": 12, "t3c": 16, "sb12": 16}
PROBE = ["probe", "--temps", "32", "--coords", "--pixels"]
TRI = ["probe", "--tri", "pixel", "--pixels", '--slot', 'eot="$S/bins/eot_plain.bin"',
       "--sideband"]


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
    assert sum(COUNTS.values()) == 53
    assert CFG["tools"].keys() == {"t10", "t10p"}
    for t in ("t10", "t10p"):        # one binary, two names (README.md "Deviations")
        assert CFG["tools"][t]["path"] == "sgxfive-test-t10"
        assert CFG["tools"][t]["sha256"] == CFG["tools"]["t10"]["sha256"]
        assert CFG["tools"][t]["built_from"] == CFG["tools"]["t10"]["built_from"]
    assert "source" not in CFG["tools"]["t10p"] and CFG["tools"]["t10p"]["no_source"]
    assert CFG["tools"]["t10"]["sha256"].startswith("9bedc2d6")
    assert CFG["tools"]["t10"]["source"].startswith("a581c06bb24d")
    assert CFG["health_tool"] == "t10" and CFG["prefix"] == "r13t"
    assert CFG["srcversion"] == "B60AB0B475DD1E8972419B5"
    assert not CFG["knobs"]
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["tool"] == ("t10" if s == "sb12" else "t10p") and r["risk"] == "safe"
            assert (r["set"] == "control") == (r["knobs"] == ["reads:pixels"])
            if r["set"] != "control":
                assert r["knobs"] == ["-"]
        assert rows(s)[0]["set"] == "control"


def test_probe_rows():
    for s in ("srgb3", "addr4", "t3c"):
        for r in rows(s):
            a = r["a"]
            assert a[:5] == PROBE, r["name"]
            assert a[-1] == f'"$S/bins/{r["name"]}.bin"'
            assert len(a) in (6, 8)
            if len(a) == 8:
                assert a[5] == "--scratch-pages" and 16 < int(a[6]) <= 64
            assert os.path.exists(os.path.join(KP, "bins", r["name"] + ".bin"))
    for r in rows("addr4"):
        if r["name"] == "addr4-bduv5":                 # E565's program: base 0, 16 pages
            assert len(r["a"]) == 6
            continue
        assert r["a"][5:7] == ["--scratch-pages", "32"], r["name"]
        if r["name"] != "addr4-ctl":
            text = open(os.path.join(KP, "bins", r["name"] + ".s")).read()
            assert "mov r22, #0x5cafc000" in text, r["name"]


def test_plan_rows():
    names = {s: [r["name"] for r in rows(s)] for s in COUNTS}
    assert names["srgb3"] == ["srgb3-ctl", "srgb3-an27", "srgb3-x1", "srgb3-x2", "srgb3-y1",
                              "srgb3-y2", "srgb3-sub2", "srgb3-tri", "srgb3-x1r"]
    assert names["addr4"][:2] == ["addr4-ctl", "addr4-bduv5"]
    assert sorted(names["addr4"][2:]) == sorted(
        [f"addr4-{s}-u{m}" for s in ("32x64", "8x64", "128x32") for m in (4, 6)]
        + ["addr4-64x16-uv5", "addr4-16x64-uv5", "addr4-32x64-u7", "addr4-32x64-u4-h16"])
    t3 = names["t3c"]
    assert t3[0] == "t3c-ctl" and t3[1:8] == [f"t3c-b11-l{L}" for L in range(7)]
    assert t3[-2:] == ["t3c-b14bl", "t3c-b14bl-ref"]       # the bit-14 row, then its reference
    sb = names["sb12"]
    assert sb[:2] == ["sb12-ctl-m8", "sb12-rep-m0-c0"]
    assert sb[2:8] == [f"sb12-m{m}-c0" for m in range(1, 7)]
    assert sb[8:15] == [f"sb12-m{m}-c1" for m in range(7)]
    assert sb[15] == "sb12-mv-m0-c0"


def t_word(name, reg):
    text = open(os.path.join(KP, "bins", name + ".s")).read()
    return int(re.search(rf"mov {reg}, #0x([0-9a-f]+)", text).group(1), 16)


def test_t3_words():
    for r in rows("t3c")[1:]:
        t3 = t_word(r["name"], "r23")
        if r["name"].startswith("t3c-b14bl"):
            assert bool(t3 >> 14 & 1) == (not r["name"].endswith("-ref")), r["name"]
            continue
        want = {"b11": 0, "b12": 3, "b10": 2}[re.match(r"t3c-(b1[0-2])", r["name"]).group(1)]
        assert t3 >> 11 & 3 == want, r["name"]
        text = open(os.path.join(KP, "bins", r["name"] + ".s")).read()
        assert "smp2dreplace" in text
    assert t_word("t3c-b11-nomip", "r20") >> 21 & 0x3F == 0
    assert t_word("t3c-b12-m3", "r20") >> 17 & 15 == 3
    assert t_word("t3c-b12-m5", "r20") >> 17 & 15 == 5


def test_srgb_words():
    for r in rows("srgb3")[2:]:
        assert t_word(r["name"], "r20") >> 27 & 1, r["name"]      # T0 bit 27: sRGB
    assert t_word("srgb3-tri", "r20") >> 9 & 1                    # mip interpolation
    assert "smp2dreplace" in open(os.path.join(KP, "bins/srgb3-tri.s")).read()


def test_sb_rows():
    for r in rows("sb12"):
        a = r["a"]
        assert a[:7] == TRI, r["name"]
        sb = int(a[7], 0)
        if r["name"] == "sb12-ctl-m8":
            assert sb == 0x208
        else:
            assert sb & ~0x1F == 0x1200 and sb & 0x1F <= 6, r["name"]
            assert sb & 0x1F == int(re.search(r"m(\d)-c", r["name"]).group(1))
        moved = "--tri-v" in a
        assert moved == (r["name"] == "sb12-mv-m0-c0")
        if moved:
            assert a[8:10] == ["--tri-v", "3072,3072,15360,6144,6144,15360"]
        assert a[-1] == f'"$S/bins/sb-c{r["name"][-1] if r["name"][-2] == "c" else 0}.bin"'


def test_no_row_names_a_forbidden_option():
    for s in COUNTS:
        for r in rows(s):
            assert not re.search(r"--kreg|--kpoke|--clkgate|--trc-hazard|--fault\b", r["args"])
            assert "/tmp" not in r["args"]
