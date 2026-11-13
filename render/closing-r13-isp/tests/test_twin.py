# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing13/plan/rank-round13.md sections 2 and 3,
session r13-isp, decisions R13-1 (a) and R13-2 (a), as README.md "Deviations" adapts them): the
stages in run order with their job counts, and every row carrying the flags and words its premise
needs (E934: a premise without its flag is a stop):
  q201      every row `--cmd 16=0x000000NN` (byte 0 only) and the vtx-coords program
            (--vtx-coords 2, the vtxuse slot vtx_coords.bin), probe --tri pixpds:12, 64 x 64
  q261/far  every row `--tri-unit` and six coordinates in int32; far last, in ascending distance"""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"q201": 23, "q261": 16, "far": 8}


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
    assert list(CFG["stages"]) == ["q201", "q261", "far"]          # far last (R13-2 a)
    assert {s: len(rows(s)) for s in COUNTS} == COUNTS
    assert sum(COUNTS.values()) == 47
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["risk"] == "safe" and r["tool"] == "t10"
            assert (r["set"] == "control") == any(w.startswith("reads:") for w in r["knobs"])
            assert not any(w in ("expectfault", "soft", "gate") or w.startswith(("expect:", "dbg:"))
                           for w in r["knobs"])
    assert list(CFG["tools"]) == ["t10"]
    t = CFG["tools"]["t10"]
    assert t["sha256"].startswith("9bedc2d6") and t["source"].startswith("a581c06")


def test_q201_rows():
    rs = rows("q201")
    assert [r["set"] for r in rs].count("control") == 5
    assert [r["name"] for r in rs if r["set"] == "control"] == [
        "q201-88-cset-x", "q201-88-cset-y", "q201-26-src0-x", "q201-26-src0-y", "q201-88-cset-x-end"]
    assert rs[-1]["name"] == "q201-88-cset-x-end"
    tris, bytes0 = set(), {}
    for r in rs:
        a = r["a"]
        assert a[:3] == ["probe", "--tri", "pixpds:12"] and "--pixels" in a
        assert opt(r, "--width") == opt(r, "--height") == "64" and opt(r, "--temps") == "32"
        assert opt(r, "--vtx-coords") == "2"
        assert '--slot vtxuse="$S/bins/vtx_coords.bin"' in r["args"]
        cm = re.findall(r"--cmd (\S+)", r["args"])
        assert len(cm) == 1 and re.fullmatch(r"16=0x000000[0-9a-f]{2}", cm[0]), cm
        b = int(cm[0][3:], 16)
        prog = "cset" if r["a"][-1] == '"$S/bins/cset.bin"' else "src0"
        assert r["a"][-1] in ('"$S/bins/cset.bin"', '"$S/bins/pos.bin"')
        comp = "x" if '--slot pixel="$S/bins/pix_pa0.bin"' in r["args"] else "y"
        assert '--slot pixel="$S/bins/pix_pa%d.bin"' % (comp == "y") in r["args"]
        assert r["name"].startswith("q201-%02x-%s-%s" % (b, prog, comp))
        bytes0.setdefault(b, set()).add((prog, comp))
        tris.add(opt(r, "--tri-v"))
    assert len(tris) == 1
    v = [int(t) for t in tris.pop().split(",")]
    assert v != [8 * 256, 8 * 256, 56 * 256, 20 * 256, 20 * 256, 56 * 256]   # not the default triangle
    full = {(p, c) for p in ("src0", "cset") for c in ("x", "y")}
    assert sorted(bytes0) == [0x0F, 0x26, 0x3C, 0x5A, 0x88, 0xF0]
    for b in (0x0F, 0x26, 0x3C, 0x5A, 0xF0):
        assert bytes0[b] == full
    assert bytes0[0x88] == {("cset", "x"), ("cset", "y")}


def test_tri_rows():
    for s in ("q261", "far"):
        for r in rows(s):
            a = r["a"]
            assert a[:5] == ["tri", "--keep-going", "--wait-ms", "20000", "--width"]
            assert "--pixels" in a and "expectdiff" in r["knobs"]
            w = opt(r, "--width")
            assert opt(r, "--height") == opt(r, "--max-width") == opt(r, "--max-height") == w
            assert 0 <= int(opt(r, "--tri-unit")) <= 20                     # the premise flag
            v = [int(t) for t in opt(r, "--tri-v").split(",")]
            assert len(v) == 6 and all(-(1 << 31) <= t < (1 << 31) for t in v)   # int32
    q = rows("q261")
    assert [r["name"] for r in q if r["set"] == "control"] == ["q261-ctl-far21", "q261-ctl-x24p"]
    assert q[0]["name"] == "q261-ctl-far21" and q[-1]["name"] == "q261-ctl-x24p"
    assert [opt(r, "--width") for r in q].count("128") == 3
    assert opt(q[0], "--tri-v") == "4066,8385,7356,9765,536870912,11776"        # E684's far21d0
    assert opt(q[-1], "--tri-v") == "200,296,304,1720,536870912,134217728"     # E979's far-x24p


def test_far_ascending_and_last():
    rs = rows("far")
    assert [r["set"] for r in rs] == ["control", "replicate"] + ["heldout"] * 6
    dist = []
    for r in rs[1:]:
        u = int(opt(r, "--tri-unit"))
        v = [int(t) for t in opt(r, "--tri-v").split(",")]
        dist.append(max(abs(t) for t in v) / (1 << u))
    assert dist == sorted(dist) and dist[0] == 2 ** 25
    assert [int(d).bit_length() - 1 for d in dist[1:]] == [26, 26, 28, 28, 30, 30]
    assert all(opt(r, "--tri-unit") == "0" for r in rs[2:])


def test_no_row_names_a_forbidden_option():
    forbid = set(CFG["forbid_options"]) | {"--kreg", "--clkgate", "--trc-hazard", "--kpoke"}
    for s in COUNTS:
        for r in rows(s):
            assert not forbid & set(r["a"]), r["name"]
