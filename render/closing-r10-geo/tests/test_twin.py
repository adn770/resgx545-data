# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing10/seeds/exp-seeds-r10.md sections 7, 9 and
12, session S10-geo, decision R10-3 (a), as README.md "Deviations" adapts them): the stages in run
order with their job counts, and every row carrying the flags and words its premise needs (E934: a
premise without its flag is a stop)."""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"pivot": 37, "bgw": 18, "q139c": 6}
LAYER = ["dbg:render_bg_layer=Y", "dbg:render_bg_src=0x3e800000"]


def rows(stage):
    out = []
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, risk, knobs, tool, args = ln.rstrip("\n").split("|", 5)
            out.append(dict(name=name, set=st, risk=risk, knobs=knobs.split(), tool=tool,
                            args=args, a=args.split()))
    return out


def opt(r, o):
    return r["a"][r["a"].index(o) + 1]


def test_stages_and_counts():
    assert list(CFG["stages"]) == list(COUNTS)
    assert {s: len(rows(s)) for s in COUNTS} == COUNTS
    assert sum(COUNTS.values()) == 61
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["risk"] == "safe" and r["a"][0] == "tri" and "expectdiff" in r["knobs"]
            assert (r["set"] == "control") == any(w.startswith("reads:") for w in r["knobs"])
            assert not any(w.startswith("expect") and w != "expectdiff" for w in r["knobs"])


def test_pivot_rows():
    rs = rows("pivot")
    assert rs[0]["name"] == "piv-ctl" and rs[0]["set"] == "control"
    assert "--tri-unit" not in rs[0]["a"]
    assert opt(rs[0], "--tri-v") == "4066,8385,7356,9765,536870912,11776"     # E684's far21d0
    for r in rs:
        a = r["a"]
        assert r["tool"] == "t4" and "--pixels" in a and "--keep-going" in a
        assert opt(r, "--width") == opt(r, "--height") == opt(r, "--max-width") == "64"
        v = [int(t) for t in opt(r, "--tri-v").split(",")]
        assert len(v) == 6 and all(-(1 << 30) <= t < 1 << 30 for t in v)
        if r["set"] != "control":
            assert opt(r, "--tri-unit") == "5" and max(abs(t) for t in v) >= 1 << 28
    assert [r["set"] for r in rs[1:]].count("replicate") == 3


def test_bgw_rows():
    rs = rows("bgw")
    assert [r["name"] for r in rs if r["set"] == "control"] == ["bgw-ctl", "bgw-ctl-end"]
    assert rs[0]["name"] == "bgw-ctl" and rs[-1]["name"] == "bgw-ctl-end"
    words = {}
    for r in rs:
        assert r["tool"] == "t9" and r["knobs"][:2] == LAYER
        assert r["a"][:6] == ["tri", "--bg-layer", "--pixels", "--keep-going", "--dump-render", "$W"]
        p = [x for x in r["a"] if x.startswith("1:bg:")]
        if r["set"] == "control":
            assert not p
            continue
        assert len(p) == 1 and r["a"].count("--kpoke-render") == 1
        w, v = p[0][5:].split("=")
        words.setdefault(int(w), []).append(int(v, 16))
    assert sorted(words) == [9, 11, 12, 13, 14]
    assert {w: len(v) for w, v in words.items()} == {9: 2, 11: 4, 12: 4, 13: 2, 14: 4}
    for w, vs in words.items():
        assert 0 not in vs and 0x3f800000 not in vs and 0xffffffff not in vs   # E973's values


def test_q139c_rows():
    rs = rows("q139c")
    assert [r["set"] for r in rs] == ["control", "control", "replicate", "replicate", "heldout", "heldout"]
    for r in rs:
        a = r["a"]
        assert r["tool"] == "t4" and "needhash" in r["knobs"]
        assert a[:3] == ["tri", "--tri-full", "--pixels"]
        assert opt(r, "--dump-render") == '"$W"' and "--keep-going" in a and opt(r, "--wait-ms") == "20000"
        w, h = opt(r, "--width"), opt(r, "--height")
        assert opt(r, "--max-width") == w and opt(r, "--max-height") == h
        pk = re.findall(r"--kpoke-render (\S+)", r["args"])
        assert (r["set"] == "control") == (not pk)
        if r["set"] == "control":
            assert r["knobs"] == ["expectdiff", "needhash", "reads:hash,dump"]
        else:
            assert len(pk) == 1 and pk[0].startswith("1:ta:144=0x")


def test_no_row_names_a_forbidden_option():
    forbid = set(CFG["forbid_options"]) | {"--kreg", "--clkgate", "--trc-hazard", "--kpoke", "--isp2"}
    for s in COUNTS:
        for r in rows(s):
            assert not forbid & set(r["a"]), r["name"]
            assert not re.search(r"--tri-unit [0-4]\b", r["args"])
