# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the argv twin of the plan (closing10/rank/rank-round10.md, R10-A to R10-F as
README.md "Deviations" adapts them): the stages in run order with their job counts, and every row
carrying the flags and words its premise needs (E934: a premise without its flag is a stop)."""
import os
import re
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COUNTS = {"dcmp": 31, "zov": 11, "zbits": 11, "isp0x": 6, "sb": 18, "win0": 14}


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


def opts(r, o):
    return [r["a"][i + 1] for i, x in enumerate(r["a"]) if x == o]


def test_stages_and_counts():
    assert list(CFG["stages"]) == list(COUNTS)
    assert {s: len(rows(s)) for s in COUNTS} == COUNTS
    assert sum(COUNTS.values()) == 91
    for s in COUNTS:
        head = open(os.path.join(KP, "tables", s + ".txt")).read().splitlines()[:2]
        assert head == [f"#stage {s}", "#limit 0"]
        for r in rows(s):
            assert r["tool"] == "t4" and r["risk"] == "safe"
            assert (r["set"] == "control") == any(w.startswith("reads:") for w in r["knobs"])
            assert "expectfault" not in r["knobs"]


def tri_common(r):
    a = r["a"]
    assert a[:4] == ["tri", "--keep-going", "--wait-ms", "20000"]
    assert "expectdiff" in r["knobs"], r["name"]
    w, h = int(opt(r, "--width")), int(opt(r, "--height"))
    assert opt(r, "--max-width") == str(w) and opt(r, "--max-height") == str(h)
    assert "--depth" in a and opt(r, "--depth-dump") == '"$W"'
    ctl = int(opt(r, "--depth-ctl"), 16)
    return w, h, ctl


def test_dcmp_rows():
    for r in rows("dcmp"):
        w, h, ctl = tri_common(r)
        assert (w, h, ctl) == (64, 32, 0x0017500E)            # E977's z243 control word
        assert {"--tri-full", "--depth-store", "--pixels"} <= set(r["a"])
        z = opt(r, "--tri-z")
        assert z in ("0.5,0.5,0.5", "0,0,0") and (z == "0,0,0") == r["name"].startswith("z0-")
        (p,) = opts(r, "--poke")
        isp = int(p.split("=")[1], 16)
        assert p.startswith("blk:1=") and isp & ~(7 << 22) == 0x200
        assert r["name"] == "z243-ctl" or isp >> 22 == int(r["name"].rsplit("-m", 1)[1])
    names = [r["name"] for r in rows("dcmp") if r["set"] == "control"]
    assert names == ["z243-ctl", "eq-m0", "eq-m7"]


def test_zov_rows():
    for r in rows("zov"):
        w, h, ctl = tri_common(r)
        tx = -(-w // 32)
        assert w % 32 == 0 and h % 16 == 0                     # whole tiles: no edge band
        g = ctl >> 3 & 0x1FF
        assert ctl & ~(0x1FF << 3) & ~(7 << 24) == 0x00171004 and not ctl & 0x6002
        if r["set"] == "control":
            assert g == tx - 1 and ctl >> 24 & 7 == 0
        else:
            assert g < tx - 1 and g == int(r["name"].split("-g")[1].split("-")[0])
            assert ctl >> 24 & 7 == (1 if r["name"].endswith("-f1") else 0)
        assert opt(r, "--tri-v") == f"0,0,{512 * w},0,0,{512 * h}"
        assert opts(r, "--poke") == ["blk:1=0x00400200"]


def test_zbits_and_isp0x_rows():
    for r in rows("zbits") + rows("isp0x"):
        w, h, ctl = tri_common(r)
        load = "load" in r["name"]
        assert (w, h) == ((64, 32) if load else (80, 40))
        assert ("--depth-store" in r["a"]) == load and ("--pixels" in r["a"]) == load
        assert (ctl >> 3 & 0x1FF) == (1 if load else 2)
        assert opts(r, "--poke")[0].startswith("blk:1=")
    by = {r["name"]: int(opt(r, "--depth-ctl"), 16) for r in rows("zbits")}
    assert by["zb-all-f0"] == 0xF8E68014 and by["zb-set-f0"] == 0xF8F79014
    assert by["zb-clr-f0"] == 0x00060014 and by["zb-all-load"] == 0xF8E6C00E
    assert {n: c & 1 for n, c in by.items() if n.startswith("zb-b0")} == {
        "zb-b0-f0": 1, "zb-b0-f1": 1, "zb-b0-f2": 1, "zb-b0-load": 1}
    pk = {r["name"]: opts(r, "--poke") for r in rows("isp0x")}
    assert pk["x-ctl"] == ["blk:1=0x00400200"]
    assert pk["x-w0b15"] == ["blk:1=0x00408200"] and pk["x-w0b17"] == ["blk:1=0x00420200"]
    assert pk["x-w1b3"] == ["blk:1=0x00400200", "blk:2^=0x8"]
    assert pk["x-w1b23"] == ["blk:1=0x00400200", "blk:2^=0x800000"]
    assert not any("0x00440200" in p for v in pk.values() for p in v)  # bit 18: E065's fault


def test_sb_rows():
    for r in rows("sb"):
        a = r["a"]
        assert a[:4] == ["probe", "--tri", "pixel", "--pixels"]
        assert opt(r, "--slot") == 'eot="$S/bins/eot_plain.bin"'
        sb = int(opt(r, "--sideband"), 16)
        assert sb & 0x200 and not sb & 0x1800                  # bits 11, 12: not run (faults)
        assert sb & 0x1F in ((8,) if r["set"] == "control" else (20, 27))
        assert sb >> 6 & 7 <= 3 and a[-1] == f'"$S/bins/sb-c{r["name"][-1]}.bin"'


def test_win0_rows():
    for r in rows("win0"):
        a = r["a"]
        assert "dbg:render_rgn_arrays=1" in r["knobs"], r["name"]
        assert a[:5] == ["probe", "--tri", "pixpds:12", "--temps", "32"]
        assert {"--tri-full", "--pixels"} <= set(a) and a[-1] == '"$S/bins/pos.bin"'
        cmd = dict(c.split("=") for c in opts(r, "--cmd"))
        assert cmd["10"] == cmd["16"] == "0xeaa26e26"
        mode = int(cmd["13"], 16)
        assert mode >> 31 and (mode & 3) == (1 if "m1" in r["name"] else 0)
        ax = r["name"][-1]
        assert opt(r, "--slot") == f'pixel="$S/bins/pix_pa{0 if ax == "x" else 1}.bin"'
    assert CFG["knobs"]["render_rgn_arrays"] == {"default": "0", "values": ["0", "1"]}
    assert list(CFG["stages"])[-1] == "win0"


def test_no_row_names_a_forbidden_option():
    for s in COUNTS:
        for r in rows(s):
            assert not re.search(r"--kreg|--kpoke|--fault\b|--isp2|--aa4", r["args"]), r["name"]
