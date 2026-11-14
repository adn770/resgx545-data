# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing16/plan/rank-round16.md sections 2 and 3,
r16-tex per R16-7 (a) and DECISIONS-R16.md, as README.md "Deviations" adapts them): one stage ty,
15 jobs (the control, 14 type rows), every row a fill probe carrying the flags its premise needs
(E934: --coords and --pixels; --scratch-pages 32), the tool t10 on module B60AB0B4, safe class with
`#limit 0`, the control first with `reads:pixels`. Section 3's premise check for r16-tex: every type
row has its mode 0 reference at its size (the row before it, or the shared reference of its size
for modes 5 to 7)."""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
PROBE = ["probe", "--temps", "32", "--coords", "--pixels", "--scratch-pages", "32"]
NAMES = ["ty-ty1u4r",
         "ty-08-ty1-u0", "ty-08-ty1-u4", "ty-08-ty1-u5", "ty-08-ty4-u0", "ty-08-ty4-u4",
         "ty-64-ty1-u0", "ty-64-ty1-u4", "ty-64-ty1-u5", "ty-64-ty1-u6", "ty-64-ty1-u7",
         "ty-64-ty4-u0", "ty-64-ty4-u4", "ty-6416-ty1-u0", "ty-6416-ty1-u4"]


def rows():
    out = []
    for ln in open(os.path.join(KP, "tables", "ty.txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, risk, knobs, tool, args = ln.rstrip("\n").split("|", 5)
            out.append(dict(name=name, set=st, risk=risk, knobs=knobs.split(), tool=tool,
                            args=args, a=args.split()))
    return out


def test_stage_and_count():
    assert list(CFG["stages"]) == ["ty"]
    assert not any("gate" in v or "on_stop" in v for v in CFG["stages"].values())
    assert [r["name"] for r in rows()] == NAMES and len(NAMES) == 15
    assert list(CFG["tools"]) == ["t10"]
    t = CFG["tools"]["t10"]
    assert t["path"] == "sgxfive-test-t10" and t["sha256"].startswith("9bedc2d6")
    assert t["source"].startswith("a581c06bb24d") and t["source_sha256"].startswith("23e1fa76")
    assert t["recipe"] == "data:render/closing-r10-st1/lead/build_tool10.sh"
    assert CFG["health_tool"] == "t10" and CFG["prefix"] == "r16t" and CFG["name"] == "r16-tex"
    assert CFG["srcversion"] == "B60AB0B475DD1E8972419B5"
    assert not CFG["knobs"] and CFG["min_free_mb"] >= 200
    assert CFG["freeze"]["resgx545"].startswith("b2b5288")
    assert CFG["freeze"]["data"].startswith("62cb03b36")
    head = open(os.path.join(KP, "tables", "ty.txt")).read().splitlines()[:2]
    assert head == ["#stage ty", "#limit 0"]
    for r in rows():
        assert r["tool"] == "t10" and r["risk"] == "safe"
        assert (r["set"] == "control") == (r["knobs"] == ["reads:pixels"])
        if r["set"] != "control":
            assert r["knobs"] == ["-"] and r["set"] == "heldout"
    sets = [r["set"] for r in rows()]
    assert sets[0] == "control" and "control" not in sets[1:]


def test_probe_rows():
    for r in rows():
        assert r["a"][:-1] == PROBE, r["name"]
        assert r["a"][-1] == f'"$S/bins/{r["name"]}.bin"'
        assert os.path.exists(os.path.join(KP, "bins", r["name"] + ".bin"))


def test_every_type_row_has_its_mode0_reference():
    names = [r["name"] for r in rows()]
    for n in names:
        if n == "ty-ty1u4r" or n.endswith("-u0"):
            continue
        ref = re.sub(r"-u\d$", "-u0", n)
        assert ref in names and names.index(ref) < names.index(n), n
        if n.endswith("-u4"):
            assert names.index(ref) == names.index(n) - 1, n    # the reference right before
    # the plan's groups: 8 x 8 and 64 x 64, types 1 and 4, mode 4 with reference (8); 64 x 16
    # type 1 with reference (2); modes 6 and 7 at 64 x 64 (2); mode 5 at 8 x 8 and 64 x 64 (2)
    g = lambda p: sum(n.startswith(p) for n in names)  # noqa: E731
    assert [g("ty-08-ty1-u0") + g("ty-08-ty1-u4") + g("ty-08-ty4") + g("ty-64-ty1-u0")
            + g("ty-64-ty1-u4") + g("ty-64-ty4"), g("ty-6416"),
            g("ty-64-ty1-u6") + g("ty-64-ty1-u7"), g("ty-08-ty1-u5") + g("ty-64-ty1-u5")] == [
        8, 2, 2, 2]


def test_no_row_names_a_forbidden_option():
    for r in rows():
        assert not re.search(r"--kreg|--kpoke|--clkgate|--trc-hazard|--fault\b|--refill|--blk-add",
                             r["args"])
        assert "/tmp" not in r["args"]
