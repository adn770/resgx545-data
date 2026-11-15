# SPDX-License-Identifier: MIT
"""r20-zls's offline tests: the generator is current and session.toml agrees with it; the argv
twin (every row against the plan's premises: E934's flags, --depth-ctl-next on every geometry
depth row, zr's refill and its premise word, zc-geo = E1081's dz-a-nl28-1); the hooks' awk reader
equals the scorer's on kept outputs and the mock's; the scorer's pieces on kept records they must
hold on and must fail on (E1081's dza rows, E1082's zs rows, E489's rampx pair)."""
import os
import re
import shlex
import struct
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "mock"))
sys.dont_write_bytecode = True
import plan as PL  # noqa: E402
import pins  # noqa: E402
import score as SC  # noqa: E402
import world as WO  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
R19 = "data:render/closing-r19-dpm/out/20261114-224724/"
LAY = "data:zls/store-layout-dumps/dumps/"


def argv(r):
    a = shlex.split(r["args"].replace("$W", "/w").replace("$HOME", "/h"))
    i = a.index("--")
    return a[:i], os.path.basename(a[i + 1]), a[i + 2:]


def val(a, o):
    return a[a.index(o) + 1]


def dw(pin):
    return SC.dwords(pins.blob(pin))


def test_generator_current():
    r = subprocess.run([sys.executable, os.path.join(KP, "gen/plan.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_session_toml_agrees():
    T = PL.tables()
    assert list(CFG["stages"]) == list(PL.STAGES)
    assert sorted(CFG["extra_knobs"]) == PL.extra_knobs(T)
    assert set(PL.knob_values(T, "render_pb_pages")) <= set(CFG["knobs"]["render_pb_pages"]["values"])
    assert CFG["knobs"]["render_final_pb_pages"] == {"default": "0", "values": ["0"]}
    assert CFG["srcversion"] == "E0CC40275493F8AEAD8180B" and CFG["prefix"] == "r20z"
    assert CFG["tools"]["rt"].get("wraps") is True
    assert CFG["tools"]["t18b"]["sha256"].startswith("58e79855")
    assert {r["tool"] for rs in T.values() for r in rs} == {"rt"}
    assert sum(len(v) for v in T.values()) == 18
    assert {s: len(v) for s, v in T.items()} == {"zc": 3, "zr": 8, "zm": 3, "zq": 4}
    assert CFG["stages"]["zc"].get("on_stop") == "end"
    for st, dep in PL.GATES.items():
        assert CFG["stages"][st].get("gate") and dep == "zc"
    for o in ("--refill", "--move", "--geometry", "--final-pb-pages", "--depth-ctl-next"):
        assert o not in CFG["forbid_options"]


def test_argv_twin():
    for st, rs in PL.tables().items():
        names = [r["name"] for r in rs]
        assert len(set(names)) == len(names)
        for r in rs:
            pre, tool, a = argv(r)
            assert pre == ["0", PL.LEAD, PL.RT] and tool == "sgxfive-test-t18b"
            assert "0x0480-0x0490" in PL.RT.split(",")
            words = r["knobs"].split()
            assert r["risk"] == "safe" and "expectdiff" in words
            assert any(w.startswith("dbg:render_pb_pages=") for w in words)
            geo = "--geometry" in a
            assert geo == r["geo"]
            if geo:
                assert val(a, "--final-pb-pages") == "0x100" and val(a, "-n") == "2"
                assert val(a, "--geometry") == "1"
                for k in PL.PREMISE.split():
                    assert k in words, r["name"]
                if "--depth" in a:
                    assert val(a, "--depth-ctl-next") == val(a, "--depth-ctl"), r["name"]
            else:
                assert val(a, "-n") == "1" and "dbg:render_pb_pages=0x422" in words
            if r["set"] == "control":
                assert any(w.startswith("reads:") for w in words), r["name"]
            for o in ("--dump-render", "--words", "--depth-dump"):
                if o in a:
                    assert val(a, o) == "/w", (r["name"], o)
            if st == "zr":
                assert val(a, "--refill") == "2:depth=0x3e800000" and "ctl:refill=1" in words
                assert val(a, "--depth-fill") == "0x3f800000" and "--depth-store" in a
                assert val(a, "--depth-pages") == "0x340"
                assert ("--move" in a) == (r["move"] == 96)
                if "--move" in a:
                    assert val(a, "--move") == "2:96,0"
            else:
                assert "--refill" not in a and "ctl:refill=1" not in words
            if st == "zm":
                assert val(a, "--move") == "2:96,0" and "--depth" not in a
            if st == "zq":
                assert "--tri-full" in a and val(a, "--tri-z") == "0.25,0.75,0.25"
                assert PL.g_of(int(val(a, "--depth-ctl"), 16)) == r["g"]
        sets = [r["set"] for r in rs]
        n = sets.count("control")
        assert sets[:n] == ["control"] * n


def test_zc_geo_is_e1081_row():
    """zc-geo's tool command is r19-dpm's dz-a-nl28-1 byte for byte (only rt's list grew)."""
    t = pins.blob("data:render/closing-r19-dpm/tables/dza.txt").decode()
    old = next(ln for ln in t.splitlines() if ln.startswith("dz-a-nl28-1|"))
    new = next(r for r in PL.tables()["zc"] if r["name"] == "zc-geo")
    assert old.split("|")[5].split(" -- ", 1)[1] == new["args"].split(" -- ", 1)[1]
    assert PL.tables()["zc"][0]["name"] == "zc-geo"


def test_regimes_e625():
    """E625's raise on this session's P (U 19 triangle, 49 ramp) and on r19's kept jobs."""
    assert [PL.raised(p, PL.U_TRI) for p in (0x28, 0x2C, 0x30)] == [True, True, False]
    assert [PL.raised(p, PL.U_RAMP) for p in (0x28, 0x30, 0x44, 0x4C)] == [True, True, False, False]
    assert all(p - PL.D_OFF < PL.U_RAMP for p in (0x44, 0x4C))     # the ramp still overflows
    assert dw(R19 + "dza/dz-a-nl28-1.ta3d.1.bin.gz")[38] != 0
    assert dw(R19 + "dza/dz-a-nl30.ta3d.1.bin.gz")[38] == 0


def test_marker_fills_unique():
    fills = re.findall(r"--depth(?:-store)?-fill (0x[0-9a-f]+)",
                       " ".join(r["args"] for rs in PL.tables().values() for r in rs))
    fills = [f for f in fills if f != "0x3f800000"]
    assert len(fills) == len(set(fills))


# ---- the hooks' reader, twinned -----------------------------------------------------------------
def awk_words(text, tmp):
    p = os.path.join(tmp, "x.out")
    open(p, "w").write(text)
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; rd_words "$1"', "_", p],
                       capture_output=True, text=True, timeout=60)
    return dict(w.split("=", 1) for w in r.stdout.split())


KEPT_TXT = [R19 + "dza/dz-a-nl28-1.txt.gz", R19 + "dza/dz-a-nl30.txt.gz",
            R19 + "dzl/dz-ac-nl.txt.gz", R19 + "dzl/dz-ac-ld.txt.gz"]


def test_hooks_twin_kept(tmp_path):
    w = {}
    for pin in KEPT_TXT:
        t = pins.blob(pin).decode(errors="replace")
        w[pin.split("/")[-1]] = SC.words(t)
        assert awk_words(t, str(tmp_path)) == w[pin.split("/")[-1]], pin
    # zc-geo's control holds on its r19 run (E1081: equal reports, one partial render) and fails
    # on the 0x30 row (the store after the final differs); the -n 1 controls' sidx (E628)
    assert w["dz-a-nl28-1.txt.gz"]["ssame"] == "1" and w["dz-a-nl28-1.txt.gz"]["nparts"] == "1"
    assert w["dz-a-nl30.txt.gz"]["ssame"] == "0"
    assert w["dz-ac-nl.txt.gz"]["sidx"] == "0" and w["dz-ac-ld.txt.gz"]["sidx"] == "1"
    assert "refill" not in w["dz-a-nl28-1.txt.gz"]


def mock_text(args, world, knobs, tmp):
    os.environ["FAKE_DBGREAL"] = str(tmp)
    for k, v in knobs.items():
        open(os.path.join(tmp, k), "w").write(v + "\n")
    a = WO.answer("t18b", args, world)
    regs = ("0x0480", "0x0484", "0x0488", "0x0624", "0x0658", "0x0724")
    rows = WO.timeline("t18b", [int(x, 16) for x in regs], args, 0, world)
    return a, a["out"] + "timeline: regs %s samples %d\n" % (" ".join(regs), len(rows)) + "".join(
        "tl %d %s\n" % (i, " ".join("%08x" % v for v in r)) for i, r in enumerate(rows))


def test_hooks_twin_mock(tmp_path):
    for rs in PL.tables().values():
        for r in rs:
            _, _, a = argv(r)
            kn = dict(w[4:].split("=", 1) for w in r["knobs"].split() if w.startswith("dbg:"))
            for world in ({"model"}, {"finalovf"}, {"norefill"}):
                _, t = mock_text(a, world, kn, str(tmp_path))
                w = SC.words(t)
                assert awk_words(t, str(tmp_path)) == w, r["name"]
                if world == {"model"}:
                    if r["set"] == "control":
                        keys = next(k for k in r["knobs"].split() if k.startswith("reads:"))
                        assert set(keys[6:].split(",")) <= set(w) <= SC.producible(r) | {"inplace"}
                    for k in r["knobs"].split():
                        if k.startswith("ctl:"):
                            kk, v = k[4:].split("=")
                            assert w.get(kk) == v, (r["name"], k, w)


def test_mock_refuses_what_t18b_refuses(tmp_path):
    os.environ["FAKE_DBGREAL"] = str(tmp_path)
    ok = argv(PL.tables()["zr"][0])[2]
    assert WO.answer("t18b", ok, {"model"})["rc"] in (0, 1)
    nonext = [x for x in ok]
    nonext[nonext.index("-n") + 1] = "1"
    for b in (ok + ["--refill", "1:depth=0x0"], ok + ["--bg-layer"], nonext,
              [x for x in ok if x != "--depth"], ok + ["--move", "3:1,1"]):
        assert WO.answer("t18b", b, {"model"})["rc"] == 2, b


# ---- the scorer on kept records -----------------------------------------------------------------
def test_window_and_mask_on_kept():
    """E465's layout and the library's triangle: on r19's dz-a-nl30 store after the final (not
    raised, no load: the scene's depth) every inside dword is 0.5 and every outside one 1.0."""
    s2 = dw(R19 + "dza/dz-a-nl30.depth-store.2.bin.gz")
    bad = sum(1 for i, e in SC.window(0) if i < len(s2) and
              ((e == 1 and s2[i] != PL.HALF) or (e == 0 and s2[i] != PL.ONE)))
    assert bad == 0
    assert len({i for i, _ in SC.window(0)}) == PL.W * PL.H
    assert max(i for i, _ in SC.window(0)) < PL.DPAGES * 1024


def test_move_is_three_tiles():
    """T2 (96 px right) is T1's dwords moved by 3 * 512 (the in-tile index kept)."""
    a = {i: e for i, e in SC.window(0)}
    for i, e in SC.window(96):
        if e and i - 3 * 512 >= 0 and (i // 512) % 34 >= 3:
            assert a.get(i - 3 * 512) == e


def test_zr_forms_on_kept():
    """E1081's raised no-load row (0x28): the store after the final is render 1's (H-NOSTORE's
    form holds, H-LOADBASE's and H-HOSTBITS's fail); the 0x30 no-load row: H-HOSTBITS's form holds, H-NOSTORE's
    fails (the signs); the 0x30 load row stored indices, not 0.25: H-HOSTBITS (load) fails."""
    s1, s2 = dw(R19 + "dza/dz-a-nl28-1.depth-store.1.bin.gz"), dw(R19 + "dza/dz-a-nl28-1.depth-store.2.bin.gz")
    off, n = SC.off_counts(s1, s2, 0, False)
    assert n > 700000 and off["NOSTORE"] == 0
    assert off["LOADBASE"] and off["HOSTBITS"]
    assert off["STOREBASE"] == 0          # unsigned indices, no 1.0: it is H-NOSTORE's form here
    s1, s2 = dw(R19 + "dza/dz-a-nl30.depth-store.1.bin.gz"), dw(R19 + "dza/dz-a-nl30.depth-store.2.bin.gz")
    off, _ = SC.off_counts(s1, s2, 0, False)
    assert off["HOSTBITS"] == 0 and off["NOSTORE"] > 0
    assert off["STOREBASE"] == 0          # |store.1| with T at 0.5: the forms agree here
    off, _ = SC.off_counts(s1, dw(R19 + "dza/dz-a-ld30.depth-store.2.bin.gz"), 0, True)
    assert off["HOSTBITS"] > 0


def test_zr_forms_differ_on_a_synthetic_raised_row():
    """The four forms differ on a raised no-load row with the move (plan 3b): a store.1 as the
    partial render would leave it (signed 0.5 in T1, signed 1.0 elsewhere, zeros in rows 0-11)."""
    n = PL.DPAGES * 1024
    s1 = [0] * n
    for i, e in SC.window(0):
        s1[i] = 0 if i < PL.ROW12 else (0xBF000000 if e == 1 else 0xBF800000)
    forms = {
        "LOADBASE": [PL.QUARTER] * n,
        "NOSTORE": list(s1),
        "STOREBASE": [v & 0x7FFFFFFF for v in s1],
        "HOSTBITS": [PL.ONE] * n,
    }
    for i, e in SC.window(96):
        if e == 1:
            forms["HOSTBITS"][i] = PL.HALF
            if forms["STOREBASE"][i] == PL.ONE:
                forms["STOREBASE"][i] = PL.HALF
    for name, s2 in forms.items():
        off, _ = SC.off_counts(s1, s2, 96, False)
        assert off[name] == 0, name
        assert all(v > 0 for k, v in off.items() if k != name), (name, off)


def test_zregs_cannot_tell_without_the_registers():
    """r19's timelines have no 0x0480: zregs is cannot tell, never PASS."""
    t = pins.blob(R19 + "dza/dz-a-nl28-1.txt.gz").decode(errors="replace")
    col, _ = SC.timeline(t)
    assert "0x0480" not in col
    w = pins.blob(R19 + "dza/dz-a-nl28-1.words.1.txt.gz").decode()
    assert SC.zls_word(w) == 0x0017110C        # rd:53 0x480: bit 4 clear (E169)
    assert SC.tool_addrs(t) == (0x3E001000, 0x3E311000)


def test_tri_line_on_kept():
    c = SC.tri_line(pins.blob(R19 + "dza/dz-a-nl30.txt.gz").decode(errors="replace"), 2)
    assert c == dict(tri=207456, bg=559008, other=19968, win=0, wout=19968, wedge=0)
    assert SC.t1_minus_t2(96) > 0


def test_zq_forms_on_kept():
    """H-NR-PLAIN's G 33 form holds on a store without a partial render (r19's -n 1 ramp control)
    and fails on the raised 0x30 final (E1082's zero row), where H-AFTERPR holds; RULE holds on
    E489's pair and fails on the 0x30 finals (E1020, E1082)."""
    sg, z = SC.g33_plain(dw(R19 + "zsc/zs-c33.depth.1.bin.gz"))
    assert sg == 0 and z == 0
    sg, z = SC.g33_plain(dw(R19 + "zs/zs-30-g33.depth.2.bin.gz"))
    assert z > 0
    hit, tot = SC.rule_hits(dw(LAY + "fit-1024x768-G1-rampx.bin.gz"),
                            dw(LAY + "fit-1024x768-G33-rampx.bin.gz"))
    assert hit == tot > 60000
    hit, tot = SC.rule_hits(dw(R19 + "zs/zs-30-g1.depth.2.bin.gz"), dw(R19 + "zs/zs-30-g33.depth.2.bin.gz"))
    assert hit < tot


def test_pins_declared():
    want = set(CFG["freeze"]["pins"])
    assert pins.READ <= want, sorted(pins.READ - want)
