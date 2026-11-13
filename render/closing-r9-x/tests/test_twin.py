# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing9/rank/rank-round9.md, R9-A to R9-E as
README.md "Deviations" adapts them): the stages in run order with their job counts, and every row
carrying the flags and words its premise needs (E934: a premise without its flag is a stop)."""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"t3": 19, "srgb": 8, "zls": 16, "zst": 12, "far": 11}


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
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["tool"] == "t4" and r["risk"] == "safe"
            assert (r["set"] == "control") == any(w.startswith("reads:") for w in r["knobs"])


def test_probe_rows():
    for s in ("t3", "srgb"):
        for r in rows(s):
            assert r["a"][:5] == ["probe", "--temps", "32", "--coords", "--pixels"], r["name"]
            assert r["a"][-1] == f'"$S/bins/{r["name"]}.bin"'
            assert os.path.exists(os.path.join(KP, "bins", r["name"] + ".bin"))


def test_tri_rows_premises():
    for s in ("zls", "zst", "far"):
        for r in rows(s):
            a = r["a"]
            assert a[:4] == ["tri", "--keep-going", "--wait-ms", "20000"]
            assert "expectdiff" in r["knobs"], r["name"]     # a drawn count other than the tool's
            assert "--isp2" not in a and "--tri-unit" not in a or opt(r, "--tri-unit") == "5"
            w, h = int(opt(r, "--width")), int(opt(r, "--height"))
            assert opt(r, "--max-width") == str(w) and opt(r, "--max-height") == str(h)
            if s == "far":
                continue
            ctl = int(opt(r, "--depth-ctl"), 16)
            assert opt(r, "--depth-dump") == '"$W"' and "--depth" in a
            assert ctl & 0x00171004 == 0x00171004            # E466's store bits
            assert (ctl >> 3 & 0x1FF) + 1 == -(-w // 32)     # pitch: the tiles across, no overlap
            assert opt(r, "--poke").startswith("blk:1=")     # the depth test and depth write
            assert opt(r, "--depth-fill").startswith("0x")
            fmt = ctl >> 24 & 7
            n = r["name"]
            if n.startswith("z242"):
                assert fmt == int(n[-1]) and not ctl & 0x6002 and "--tri-v" in a
            if n.startswith("z243"):
                assert ctl & 0x4002 == 0x4002 and "--depth-store" in a and "--pixels" in a
                assert fmt == (1 if "-f1-" in n else 2 if "-f2-" in n else 0)
            if n.startswith("z120"):
                assert ctl & 0x2002 == 0x2002 and not ctl & 0x4000
                assert {"--stencil", "--stencil-store"} <= set(a) and opt(r, "--stencil-fill") == "index"
                assert fmt == (0 if "ctl" in n else int(n[6]))


def test_far_rows():
    for r in rows("far"):
        a = r["a"]
        assert "--pixels" in a and opt(r, "--width") == "64" and opt(r, "--height") == "64"
        v = [int(t) for t in opt(r, "--tri-v").split(",")]
        assert len(v) == 6 and all(-(1 << 30) <= t < 1 << 30 for t in v)
        if r["name"] == "far-ctl":
            assert "--tri-unit" not in a and v == [4066, 8385, 7356, 9765, 536870912, 11776]
        else:
            assert opt(r, "--tri-unit") == "5" and max(abs(t) for t in v) >= 1 << 27


def test_no_row_names_a_forbidden_option():
    for s in COUNTS:
        for r in rows(s):
            assert not re.search(r"--kreg|--kpoke|--fault\b|--tri-unit 0\b", r["args"]), r["name"]
