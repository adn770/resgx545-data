# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing16/plan/rank-round16.md sections 2 and 3,
r16-usse per R16-1 (a) and R16-5 (a), as README.md "Deviations" adapts them): the stages in run
order with their job counts (uadd 7, utest 20, urpt 3), every row a fill probe `probe --temps 32 FILE` of
a program of ours on the tool t10 (module B60AB0B4), safe class with `#limit 0`, the controls first
in each stage with `reads:scratch` (urpt one, E521's again), the lane rows with the o join last in
utest, the write-mask rows a stage of their own, the session's last (on_stop = "end"), every program 1 to 256 words (PROBE_MAX_WORDS) and named
without a dot (probe_read cuts the label at the first one)."""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"uadd": 7, "utest": 20, "urpt": 3}
PROBE = ["probe", "--temps", "32"]


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
    assert CFG["stages"]["uadd"] == {"alarm": 900}
    assert CFG["stages"]["utest"] == {"alarm": 1200}
    assert CFG["stages"]["urpt"] == {"alarm": 600, "on_stop": "end"}
    assert {s: len(rows(s)) for s in COUNTS} == COUNTS
    assert list(CFG["tools"]) == ["t10"]
    t = CFG["tools"]["t10"]
    assert t["path"] == "sgxfive-test-t10" and t["sha256"].startswith("9bedc2d6")
    assert t["source"].startswith("a581c06bb24d") and t["source_sha256"].startswith("23e1fa76")
    assert t["recipe"] == "data:render/closing-r10-st1/lead/build_tool10.sh"
    assert CFG["health_tool"] == "t10" and CFG["prefix"] == "r16u" and CFG["name"] == "r16-usse"
    assert CFG["srcversion"] == "B60AB0B475DD1E8972419B5"
    assert not CFG["knobs"] and CFG["min_free_mb"] >= 200 and not CFG["outdir_opts"]
    assert CFG["freeze"]["resgx545"].startswith("b2b5288")
    assert CFG["freeze"]["data"].startswith("62cb03b36")
    assert CFG["files"]["laptop"] == ["bins/*.bin"]
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["tool"] == "t10" and r["risk"] == "safe"
            assert (r["set"] == "control") == (r["knobs"] == ["reads:scratch"])
            if r["set"] != "control":
                assert r["knobs"] == ["-"] and r["set"] == "heldout"
        sets = [r["set"] for r in rows(s)]
        nc = 1 if s == "urpt" else 2
        assert sets[:nc] == ["control"] * nc and "control" not in sets[nc:]


def test_probe_rows():
    for s in COUNTS:
        for r in rows(s):
            assert r["a"] == PROBE + [f'"$S/bins/{r["name"]}.bin"'], r["name"]
            assert "." not in r["name"] and len(r["name"]) < 64
            size = os.path.getsize(os.path.join(KP, "bins", r["name"] + ".bin"))
            assert size and size % 8 == 0 and size <= 256 * 8, (r["name"], size)


def test_plan_rows():
    names = {s: [r["name"] for r in rows(s)] for s in COUNTS}
    assert names["uadd"] == ["u-ctl-e521", "u-ctl-e498", "u-imm1", "u-imm127", "u-c56", "u-i0",
                             "u-sa0"]
    assert names["urpt"] == ["u-ctl-rpt", "u-rpt2", "u-rpt4"]
    forms = ["shl", "shr", "asr", "or7", "rol7", "iadd32", "iaddu32"]
    assert names["utest"] == (["t-ctl-and-a", "t-ctl-and-o"]
                              + [f"t-{f}-{j}" for f in forms for j in "ao"]
                              + ["t-iadd8-a", "t-iadd16-a", "t-iadd8-o", "t-iadd16-o"])
    # the plan's groups: immediates 2, a constant 1, destinations 2, repeats 2, controls 2 (uadd);
    # shifts 3, #7 forms 2, sums 2 (each with both joins), lanes 2 + 2 raw-o last, controls 2
    u = names["uadd"] + names["urpt"][1:]
    assert [sum(n.startswith(p) for n in u) for p in ("u-imm", "u-c56", "u-i0", "u-sa0",
                                                      "u-rpt", "u-ctl")] == [2, 1, 1, 1, 2, 2]


def test_no_row_names_a_forbidden_option():
    for s in COUNTS:
        for r in rows(s):
            assert not re.search(r"--kreg|--kpoke|--clkgate|--trc-hazard|--fault\b|--refill|--tri\b"
                                 r"|--pds|--place|--late|--low", r["args"])
            assert "/tmp" not in r["args"]
