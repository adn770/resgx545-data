# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing14/plan/rank-round14.md sections 2 and 3,
session r14-isp; decisions R14-1 (a), R14-2 (a), R14-3 (a) of closing14/DECISIONS-R14.md and the
user's: the poked-viewport rows are g14's last and stop it at the first job not ok, the int32 ends
are the session's last rows), as README.md "Deviations" adapts it: the stages in run order with
their job counts, and every row carrying the flags and words its premise needs (E934):
  wind    E998's form: --depth --depth-ctl 0x00171014 --depth-dump, ISP word 0 by --poke blk:1,
          the reversed order on the bit rows, --tri-z outside [0, 1] only on the z rows, --pixels
  g14     every row --tri-unit and six int32 coordinates, --pixels; the vp rows poke words 6 to 9
          (offset = scale, a float) and come last, after both controls
  clipr   the same; the int32 ends (+-2^31 at --tri-unit 0) last, after both controls;
          on_stop = "end" """
import os
import struct
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"wind": 8, "g14": 21, "clipr": 10}


def rows(stage):
    out = []
    for ln in open(os.path.join(KP, "tables", stage + ".txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, risk, knobs, tool, args = ln.rstrip("\n").split("|", 5)
            out.append(dict(name=name, set=st, risk=risk, knobs=knobs.split(), tool=tool, args=args, a=args.split()))
    return out


def opt(r, o):
    return r["a"][r["a"].index(o) + 1]


def opts(r, o):
    return [r["a"][i + 1] for i, t in enumerate(r["a"]) if t == o]


def f32(u):
    return struct.unpack("<f", struct.pack("<I", int(u, 0)))[0]


def test_stages_and_counts():
    assert list(CFG["stages"]) == ["wind", "g14", "clipr"]
    assert CFG["stages"]["clipr"].get("on_stop") == "end"
    assert {s: len(rows(s)) for s in COUNTS} == COUNTS
    assert sum(COUNTS.values()) == 39
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["risk"] == "safe" and r["tool"] == "t10"
            assert "expectdiff" in r["knobs"] and "--pixels" in r["a"]
            assert (r["set"] == "control") == any(w.startswith("reads:") for w in r["knobs"])
            assert not any(w in ("expectfault", "soft", "gate", "noreset") or w.startswith(("expect:", "dbg:", "idle:"))
                           for w in r["knobs"])
            assert r["a"][:3] == ["tri", "--keep-going", "--wait-ms"]
            w = opt(r, "--width")
            h = opt(r, "--height")
            assert opt(r, "--max-width") == w and opt(r, "--max-height") == h
    t = CFG["tools"]["t10"]
    assert list(CFG["tools"]) == ["t10"]
    assert t["sha256"].startswith("9bedc2d6") and t["source"].startswith("a581c06")


def test_wind_rows():
    rs = rows("wind")
    assert [r["set"] for r in rs] == ["control"] * 3 + ["heldout"] * 5
    for r in rs:
        assert (opt(r, "--width"), opt(r, "--height")) == ("80", "40")
        assert "--depth" in r["a"] and opt(r, "--depth-ctl") == "0x00171014"
        assert opt(r, "--depth-fill") == "0xdeadbeef" and opt(r, "--depth-dump") == '"$W"'
        assert "--tri-unit" not in r["a"]
        pk = opts(r, "--poke")
        assert len(pk) == 1 and pk[0].startswith("blk:1=")
    by = {r["name"]: r for r in rs}
    rev, fwd = "0,0,0,20480,40960,0", "0,0,40960,0,0,20480"
    for n in ("wind-ctl-rev", "wind-rev-b15", "wind-rev-b16", "wind-rev-b17"):
        assert opt(by[n], "--tri-v") == rev and opt(by[n], "--tri-z") == "1,1,0"
    for n, b in (("wind-rev-b15", 15), ("wind-rev-b16", 16), ("wind-rev-b17", 17), ("wind-ctl-b15", 15)):
        assert int(opts(by[n], "--poke")[0][6:], 0) == 0x00400200 | 1 << b
    assert opt(by["wind-ctl-b15"], "--tri-v") == fwd                     # E998's x-w0b15
    for n, z in (("wind-ctl-always", "1,0,1"), ("wind-zhi", "1.25,0.25,1.25"), ("wind-zlo", "0.25,-0.75,0.25")):
        assert opt(by[n], "--tri-v") == fwd and opt(by[n], "--tri-z") == z
        assert int(opts(by[n], "--poke")[0][6:], 0) == 0x01C00200     # always, the depth written
    for r in rs:                                  # a depth outside [0, 1] only on the z rows
        z = [float(t) for t in opt(r, "--tri-z").split(",")]
        assert all(-1 <= t <= 2 for t in z)
        assert (min(z) < 0 or max(z) > 1) == (r["name"] in ("wind-zhi", "wind-zlo"))


def tri_rows(stage):
    for r in rows(stage):
        assert 0 <= int(opt(r, "--tri-unit")) <= 20                 # the premise flag
        v = [int(t) for t in opt(r, "--tri-v").split(",")]
        assert len(v) == 6 and all(-(1 << 31) <= t < (1 << 31) for t in v)   # int32
        assert "--depth" not in r["a"] and "--tri-z" not in r["a"]
        yield r, v


def test_g14_rows():
    rs = rows("g14")
    list(tri_rows("g14"))
    names = [r["name"] for r in rs]
    assert names[0] == "g14-ctl-far21" and names[17] == "g14-ctl-t128"
    assert [r["set"] for r in rs].count("control") == 2
    assert opt(rs[0], "--tri-v") == "4066,8385,7356,9765,536870912,11776"        # E684's far21d0
    assert opt(rs[17], "--tri-v") == "400,592,608,3440,257450388,31020207"       # E1023's t128-1
    shapes = [(opt(r, "--width"), opt(r, "--height")) for r in rs[1:17]]
    assert shapes.count(("64", "64")) == 2 and shapes.count(("128", "128")) == 6
    assert shapes.count(("256", "256")) == 4 and shapes.count(("128", "64")) == 2 and shapes.count(("64", "128")) == 2
    vp = rs[18:]
    assert [r["name"] for r in vp] == ["g14-vp64-px", "g14-vp64-py", "g14-vp128-px"]
    for r in rs[:18]:
        assert "--poke" not in r["a"]
    for r, (w, val) in zip(vp, (("128", 32.0), ("128", 32.0), ("64", 64.0))):
        assert opt(r, "--width") == opt(r, "--height") == w
        pk = opts(r, "--poke")
        assert [p.split("=")[0] for p in pk] == ["blk:6", "blk:7", "blk:8", "blk:9"]
        assert [f32(p.split("=")[1]) for p in pk] == [val] * 4                # offset = scale, floats
        assert r["set"] == "heldout"


def test_clipr_rows():
    rs = rows("clipr")
    tv = list(tri_rows("clipr"))
    names = [r["name"] for r in rs]
    assert names == ["clipr-ctl-far21", "clipr-tie-a", "clipr-tie-b", "clipr-tie-c", "clipr-w4-d",
                     "clipr-w4-e", "clipr-w4-f", "clipr-ctl-x30p", "clipr-i32-x", "clipr-i32-y"]
    assert opt(rs[7], "--tri-v") == "6,9,10,54,1073741824,132369010"           # E1024's far-x30p
    for r, v in tv[1:4]:
        assert (opt(r, "--width"), opt(r, "--tri-unit")) == ("64", "8")
    for r, v in tv[4:7]:
        assert (opt(r, "--width"), opt(r, "--height")) == ("4096", "16")
    for r, v in tv[8:]:                           # the int32 ends, last
        assert opt(r, "--tri-unit") == "0" and opt(r, "--width") == "64"
    assert tv[8][1][4] == 2 ** 31 - 1 and tv[9][1][5] == -2 ** 31
    for r, v in tv[:8]:
        assert max(abs(t) >> int(opt(r, "--tri-unit")) for t in v) <= 2 ** 30      # E1024 reached 2^30


def test_no_row_names_a_forbidden_option():
    forbid = set(CFG["forbid_options"]) | {"--kreg", "--clkgate", "--trc-hazard", "--kpoke"}
    for s in COUNTS:
        for r in rows(s):
            assert not forbid & set(r["a"]), r["name"]
