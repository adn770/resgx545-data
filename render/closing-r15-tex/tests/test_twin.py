# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing15/plan/rank-round15.md sections 2 and 3,
r15-tex per R15-1 (a) and R15-5 (a), as README.md "Deviations" adapts them): the stages in run
order with their job counts (chain 18, ty 15), every row a fill probe carrying the flags its premise
needs (E934: --coords and --pixels; --scratch-pages 32 on every ty row, E1039's), the tool t10 on
module B60AB0B4, safe class with `#limit 0`, the controls first in each stage with `reads:pixels`.
Section 3's premise checks for r15-tex: every chain inside the scratch (test_gen.py) and every
32 x 32 type row with its mode 0 reference right before it."""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"chain": 18, "ty": 15}
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
    assert not any("gate" in v or "on_stop" in v for v in CFG["stages"].values())
    assert {s: len(rows(s)) for s in COUNTS} == COUNTS
    assert sum(COUNTS.values()) == 33
    assert list(CFG["tools"]) == ["t10"]
    t = CFG["tools"]["t10"]
    assert t["path"] == "sgxfive-test-t10" and t["sha256"].startswith("9bedc2d6")
    assert t["source"].startswith("a581c06bb24d") and t["source_sha256"].startswith("23e1fa76")
    assert t["recipe"] == "data:render/closing-r10-st1/lead/build_tool10.sh"
    assert CFG["health_tool"] == "t10" and CFG["prefix"] == "r15t" and CFG["name"] == "r15-tex"
    assert CFG["srcversion"] == "B60AB0B475DD1E8972419B5"
    assert not CFG["knobs"] and CFG["min_free_mb"] >= 200
    assert CFG["freeze"]["resgx545"].startswith("158bdc5")
    assert CFG["freeze"]["data"].startswith("cddc7b60b")
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["tool"] == "t10" and r["risk"] == "safe"
            assert (r["set"] == "control") == (r["knobs"] == ["reads:pixels"])
            if r["set"] != "control":
                assert r["knobs"] == ["-"] and r["set"] == "heldout"
        sets = [r["set"] for r in rows(s)]
        assert sets[:2] == ["control", "control"] and "control" not in sets[2:]


def test_probe_rows():
    for s in COUNTS:
        for r in rows(s):
            a = r["a"]
            assert a[:5] == PROBE, r["name"]
            assert a[-1] == f'"$S/bins/{r["name"]}.bin"'
            if s == "ty":
                assert a[5:7] == ["--scratch-pages", "32"] and len(a) == 8, r["name"]
            else:
                assert len(a) == 6, r["name"]          # 16 pages: every chain inside (test_gen)
            assert os.path.exists(os.path.join(KP, "bins", r["name"] + ".bin"))


def test_plan_rows():
    names = {s: [r["name"] for r in rows(s)] for s in COUNTS}
    assert names["chain"] == [
        "chain-ctl32", "chain-ctl128", "chain-1x32-lw", "chain-1x32-lh", "chain-32x1-lw",
        "chain-32x1-lh", "chain-32x1-b33", "chain-h32x16-lw", "chain-h32x16-lh",
        "chain-h16x64-lw", "chain-h16x64-lh", "chain-h32x16-mf", "chain-64x32-lw",
        "chain-256x32-lw", "chain-256x32-lb", "chain-1d-lw", "chain-1d-lh", "chain-1d-max3"]
    assert names["ty"] == [
        "ty-ctl", "ty-ty1u4r", "ty-16-ty1-u5", "ty-16-ty1-u6", "ty-16-ty1-u7", "ty-16-ty4-u5",
        "ty-16-ty4-u6", "ty-16-ty4-u7", "ty-16-ty1-n16", "ty-32-ty1-u0", "ty-32-ty1-u4",
        "ty-32-ty3-u0", "ty-32-ty3-u4", "ty-32-ty4-u0", "ty-32-ty4-u4"]
    # the plan's groups: 1D 3, a side of 1 5, 16-bit 5, long sides 3, controls 2 (chain);
    # 32 x 32 6, modes 5 to 7 6, H-NAME16 1, controls 2 (ty)
    groups = lambda p: sum(n.startswith(p) for n in names["chain"])  # noqa: E731
    assert [groups("chain-1d"), groups("chain-1x32") + groups("chain-32x1"), groups("chain-h"),
            groups("chain-64x32") + groups("chain-256x32"), groups("chain-ctl")] == [3, 5, 5, 3, 2]
    tg = lambda p: sum(n.startswith(p) for n in names["ty"])  # noqa: E731
    assert [tg("ty-32-"), tg("ty-16-") - 1, tg("ty-16-ty1-n16"), 2] == [6, 6, 1, 2]
    for n in names["ty"]:
        if n.startswith("ty-32-") and n.endswith("-u4"):
            assert names["ty"][names["ty"].index(n) - 1] == n[:-1] + "0"


def test_no_row_names_a_forbidden_option():
    for s in COUNTS:
        for r in rows(s):
            assert not re.search(r"--kreg|--kpoke|--clkgate|--trc-hazard|--fault\b|--refill",
                                 r["args"])
            assert "/tmp" not in r["args"]
