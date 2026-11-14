# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing15/plan/rank-round15.md sections 2 and 3,
session r15-isp, row zcut (Q241); closing15/DECISIONS-R15.md: safe class only, no tool change), as
README.md "Deviations" adapts it: the one stage with its 11 jobs in run order and every row
carrying the flags and words its premise needs (E934):
  zcut   E1045's form (--depth --depth-ctl 0x00171014 --depth-fill 0xdeadbeef --depth-dump,
         ISP word 0 0x01c00200 by --poke blk:1, --tri-v six int32 in 1/256 px, --tri-z, --pixels)
         on every depth row; E065's rows (--poke blk:1^=V on the library triangle, --pixels);
         the controls first, E065's bits 16 and 17 last; on_stop = "end" """
import os
import struct
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def rows():
    out = []
    for ln in open(os.path.join(KP, "tables", "zcut.txt")):
        if ln.strip() and not ln.startswith("#"):
            name, st, risk, knobs, tool, args = ln.rstrip("\n").split("|", 5)
            out.append(dict(name=name, set=st, risk=risk, knobs=knobs.split(), tool=tool, args=args,
                            a=args.replace("'", "").split()))
    return out


def opt(r, o):
    return r["a"][r["a"].index(o) + 1]


def test_stage_and_order():
    assert list(CFG["stages"]) == ["zcut"] and CFG["stages"]["zcut"].get("on_stop") == "end"
    assert CFG["tools"]["t10"]["sha256"].startswith("9bedc2d6") and list(CFG["tools"]) == ["t10"]
    assert CFG["tools"]["t10"]["source"].startswith("a581c06")
    head = open(os.path.join(KP, "tables", "zcut.txt")).read().splitlines()[:2]
    assert head == ["#stage zcut", "#limit 0"]
    rs = rows()
    assert [r["name"] for r in rs] == ["zcut-ctl-zhi", "zcut-ctl-zlo", "zcut-ctl-b15", "zcut-hi1", "zcut-hi2",
                                       "zcut-hi3", "zcut-lo1", "zcut-lo2", "zcut-lo3", "zcut-b16", "zcut-b17"]
    assert [r["set"] for r in rs] == ["control"] * 3 + ["heldout"] * 8
    assert len(rs) == 11


def test_every_row_has_its_flags():
    for r in rows():
        assert r["risk"] == "safe" and r["tool"] == "t10"
        assert "expectdiff" in r["knobs"] and "--pixels" in r["a"]
        assert (r["set"] == "control") == any(w.startswith("reads:") for w in r["knobs"])
        assert not any(w in ("expectfault", "soft", "gate", "noreset") or w.startswith(("expect:", "dbg:", "idle:"))
                       for w in r["knobs"])
        assert r["a"][:4] == ["tri", "--keep-going", "--wait-ms", "20000"]


def test_depth_rows_are_e1045s_form():
    for r in rows()[:2] + rows()[3:9]:
        assert (opt(r, "--width"), opt(r, "--height")) == ("80", "40")
        assert (opt(r, "--max-width"), opt(r, "--max-height")) == ("80", "40")
        assert "--depth" in r["a"] and opt(r, "--depth-ctl") == "0x00171014"
        assert opt(r, "--depth-fill") == "0xdeadbeef" and opt(r, "--depth-dump") == '"$W"'
        assert "--tri-unit" not in r["a"]
        pk = [r["a"][i + 1] for i, t in enumerate(r["a"]) if t == "--poke"]
        assert pk == ["blk:1=0x01c00200"]                              # compare always, the depth written
        v = [int(t) for t in opt(r, "--tri-v").split(",")]
        z = [float(t) for t in opt(r, "--tri-z").split(",")]
        assert len(v) == 6 and all(-(1 << 31) <= t < (1 << 31) for t in v) and len(z) == 3
        assert all(-1 <= t <= 2 for t in z)
        assert (min(z) < 0 or max(z) > 1)                              # every depth row cuts
    rs = {r["name"]: r for r in rows()}
    assert opt(rs["zcut-ctl-zhi"], "--tri-v") == opt(rs["zcut-ctl-zlo"], "--tri-v") == "0,0,40960,0,0,20480"
    assert opt(rs["zcut-ctl-zhi"], "--tri-z") == "1.25,0.25,1.25"        # E1045's wind-zhi
    assert opt(rs["zcut-ctl-zlo"], "--tri-z") == "0.25,-0.75,0.25"       # E1045's wind-zlo
    for n in ("zcut-hi1", "zcut-hi2", "zcut-hi3"):
        z = [float(t) for t in opt(rs[n], "--tri-z").split(",")]
        assert max(z) == 1.25 and z.count(1.25) == 1 and min(z) >= 0
    for n in ("zcut-lo1", "zcut-lo2", "zcut-lo3"):
        z = [float(t) for t in opt(rs[n], "--tri-z").split(",")]
        assert min(z) == -0.25 and z.count(-0.25) == 1 and max(z) <= 1


def test_e065_rows_are_the_library_triangle_with_a_flip():
    rs = {r["name"]: r for r in rows()}
    for n, bit in (("zcut-ctl-b15", 15), ("zcut-b16", 16), ("zcut-b17", 17)):
        r = rs[n]
        assert not {"--width", "--height", "--depth", "--tri-v", "--tri-z"} & set(r["a"])
        pk = [r["a"][i + 1] for i, t in enumerate(r["a"]) if t == "--poke"]
        assert pk == ["blk:1^=0x%x" % (1 << bit)]                        # E065's xor, 'blk:1^=0x8000'
    assert [r["name"] for r in rows()][-2:] == ["zcut-b16", "zcut-b17"]    # last, after every cut row


def test_controls_read_what_their_rows_print():
    rs = {r["name"]: r for r in rows()}
    reads = {n: [w for w in rs[n]["knobs"] if w.startswith("reads:")][0] for n in rs if rs[n]["set"] == "control"}
    assert reads == {"zcut-ctl-zhi": "reads:job,drawn,depth_changed", "zcut-ctl-zlo": "reads:job,drawn,depth_changed",
                     "zcut-ctl-b15": "reads:job,drawn,hash"}


def test_no_row_names_a_forbidden_option():
    forbid = set(CFG["forbid_options"]) | {"--kreg", "--clkgate", "--trc-hazard", "--kpoke"}
    for r in rows():
        assert not forbid & set(r["a"]), r["name"]
        assert "--fault" not in r["a"] and "--tri-unit" not in r["a"]


def f32(u):
    return struct.unpack("<f", struct.pack("<I", int(u, 0)))[0]
