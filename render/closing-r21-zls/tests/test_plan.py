# SPDX-License-Identifier: MIT
"""r21-zls's offline tests: the generator is current and session.toml agrees with it; the argv
twin (every row against the plan's premises: E934's flags, --depth-ctl-next on every depth row,
the refill and its premise word, zc-r25 = E1088's zr-28-nl-1 and zc-nl = r20's zc-nl byte for
byte); the hooks' awk reader equals the scorer's on kept outputs and the mock's; the scorer's
pieces on the kept records they must hold on and must fail on (E1088's zr rows, E1082's zs rows,
E1090's zq rows)."""
import os
import shlex
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
R20 = "data:render/closing-r20-zls/out/20261115-080705/"
R19 = "data:render/closing-r19-dpm/out/20261114-224724/"


def argv(r):
    a = shlex.split(r["args"].replace("$W", "/w").replace("$HOME", "/h"))
    i = a.index("--")
    return a[:i], os.path.basename(a[i + 1]), a[i + 2:]


def val(a, o):
    return a[a.index(o) + 1]


def dw(pin):
    return SC.dwords(pins.blob(pin))


class Kept:
    """A kept row of r20-zls, read from its pins (the scorer's Run interface)."""

    def __init__(self, stage, name, words_from=None):
        self.p, self.wp = R20 + f"{stage}/{name}", words_from

    def done(self, n):
        return True

    def text(self, n, suffix=".txt"):
        p = self.wp if suffix == ".words.1.txt" and self.wp else self.p
        return pins.blob(p + suffix + ".gz").decode(errors="replace")

    def dump(self, n, suffix):
        return pins.blob(self.p + suffix + ".gz")

    def raised(self, n):
        return SC.dwords(self.dump(n, ".ta3d.1.bin"))[38] != 0


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/plan.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_session_toml_agrees():
    T = PL.tables()
    assert list(CFG["stages"]) == list(PL.STAGES)
    assert sorted(CFG["extra_knobs"]) == PL.extra_knobs(T)
    assert PL.knob_values(T, "render_pb_pages") == CFG["knobs"]["render_pb_pages"]["values"]
    assert CFG["knobs"]["render_final_pb_pages"] == {"default": "0", "values": ["0"]}
    assert CFG["srcversion"] == "E0CC40275493F8AEAD8180B" and CFG["prefix"] == "r21z"
    assert CFG["tools"]["rt"].get("wraps") is True
    assert CFG["tools"]["t18b"]["sha256"].startswith("58e79855")
    assert {r["tool"] for rs in T.values() for r in rs} == {"rt"}
    assert {s: len(v) for s, v in T.items()} == {"zc": 2, "zl": 7, "zw": 3, "zz": 4}
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
            words = r["knobs"].split()
            assert r["risk"] == "safe" and "expectdiff" in words
            assert not any(w.startswith(("expectfault", "expecthang", "#limit")) for w in words)
            assert any(w.startswith("dbg:render_pb_pages=") for w in words)
            assert "--geometry" in a and val(a, "-n") == "2" or r["name"] == "zc-nl"
            if "--geometry" in a:
                assert val(a, "--final-pb-pages") == "0x100" and val(a, "--geometry") == "1"
                for k in PL.PREMISE.split():
                    assert k in words, r["name"]
                assert val(a, "--depth-ctl-next") == val(a, "--depth-ctl"), r["name"]
                assert ("--refill" in a) == ("ctl:refill=1" in words) == (st != "zz")
            if "--refill" in a:
                rv = 0x3E800000 if r["name"] == "zc-r25" else PL.R75
                assert val(a, "--refill") == f"2:depth=0x{rv:x}" and r["refill"] == rv
                assert val(a, "--depth-fill") == "0x3f800000" and "--depth-store" in a
                assert val(a, "--depth-pages") == "0x340" and val(a, "--move") == "2:96,0"
                assert "--poke" in a and val(a, "--poke") == "blk:1=0x00400200"
            if r["set"] == "control":
                assert any(w.startswith("reads:") for w in words), r["name"]
            for o in ("--dump-render", "--words", "--depth-dump"):
                if o in a:
                    assert val(a, o) == "/w", (r["name"], o)
            if st == "zz":
                assert "--tri-full" in a and val(a, "--tri-z") == "0.25,0.75,0.25"
                assert PL.g_of(int(val(a, "--depth-ctl"), 16)) == 33 and "--move" not in a
        sets = [r["set"] for r in rs]
        n = sets.count("control")
        assert sets[:n] == ["control"] * n


def test_controls_are_r20_rows():
    """zc-r25's tool command and premise words are E1088's zr-28-nl-1 byte for byte, zc-nl's
    command r20's zc-nl; zc-r25 runs first."""
    zr = pins.blob("data:render/closing-r20-zls/tables/zr.txt").decode().splitlines()
    zc = pins.blob("data:render/closing-r20-zls/tables/zc.txt").decode().splitlines()
    old = next(ln for ln in zr if ln.startswith("zr-28-nl-1|")).split("|")
    new = PL.tables()["zc"][0]
    assert new["name"] == "zc-r25" and old[5] == new["args"]
    assert new["knobs"] == old[3] + " reads:ovf1,ovf2,thr,refill"
    old = next(ln for ln in zc if ln.startswith("zc-nl|")).split("|")
    assert old[5] == PL.tables()["zc"][1]["args"]


def test_regimes_e625():
    """E625's raise on this session's P (U 19 triangle, 49 ramp), the plan's table; the
    overflow of every kick; kept regimes."""
    zl = {r["name"]: r["raised"] for r in PL.tables()["zl"]}
    assert zl == {"zl-28-nl": True, "zl-24-nl": True, "zl-2a-ld": True, "zl-2c-nl": True,
                  "zl-2e-nl": False, "zl-2e-ld": False, "zl-34-nl": False}
    assert [r["raised"] for r in PL.tables()["zw"]] == [True, False, True]
    assert [r["raised"] for r in PL.tables()["zz"]] == [True, True, False, False]
    for st, u in (("zl", PL.U_TRI), ("zw", PL.U_TRI), ("zz", PL.U_RAMP)):
        assert all(r["p"] - PL.D_OFF < u for r in PL.tables()[st])
    assert dw(R20 + "zr/zr-28-nl-1.ta3d.1.bin.gz")[38] != 0
    assert dw(R20 + "zr/zr-30-nl.ta3d.1.bin.gz")[38] == 0


def test_marker_fills_unique():
    import re
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


KEPT_TXT = [R20 + "zr/zr-28-nl-1.txt.gz", R20 + "zr/zr-30-nl.txt.gz", R20 + "zc/zc-nl.txt.gz"]


def test_hooks_twin_kept(tmp_path):
    w = {}
    for pin in KEPT_TXT:
        t = pins.blob(pin).decode(errors="replace")
        w[pin.split("/")[-1]] = SC.words(t)
        assert awk_words(t, str(tmp_path)) == w[pin.split("/")[-1]], pin
    a = w["zr-28-nl-1.txt.gz"]
    assert (a["ovf1"], a["ovf2"], a["thr"], a["refill"]) == ("1", "0", "0xde", "1")
    assert w["zc-nl.txt.gz"]["ovf1"] == "0" and w["zc-nl.txt.gz"]["sidx"] == "0"


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
    ok = argv(PL.tables()["zl"][0])[2]
    assert WO.answer("t18b", ok, {"model"})["rc"] in (0, 1)
    nonext = list(ok)
    nonext[nonext.index("-n") + 1] = "1"
    for b in (ok + ["--refill", "1:depth=0x0"], ok + ["--bg-layer"], nonext,
              [x for x in ok if x != "--depth"], ok + ["--move", "3:1,1"]):
        assert WO.answer("t18b", b, {"model"})["rc"] == 2, b


# ---- the scorer on kept records -----------------------------------------------------------------
def test_zc_store_control_on_kept():
    """zc-r25's store control holds on E1088's zr-28-nl-1
    and fails on zr-30-nl (not raised: the scene's depth after the final)."""
    ok, t = SC.zc_store(Kept("zr", "zr-28-nl-1"), "x")
    assert ok is True, t
    assert "589824" in t
    ok, t = SC.zc_store(Kept("zr", "zr-30-nl"), "x")
    assert ok is False, t


def test_zregs2_on_kept():
    """H-OFFS holds on E1088's rows (the offsets rd:12 0x1000, rd:13 0x341000) and fails when the
    words are another row's (zc-geo's default-size store, rd:13 0x311000)."""
    for n in ("zr-28-nl-1", "zr-30-nl", "zr-28-e336"):
        ok, t = SC.zregs2(Kept("zr", n), "x")
        assert ok is True, (n, t)
    ok, t = SC.zregs2(Kept("zr", "zr-28-nl-1", words_from=R20 + "zc/zc-geo"), "x")
    assert ok is False, t


def test_prmask_on_kept():
    """H-PRMASK holds on E1088's four kept words (0x0017110c, 0x0017510e, 0x0011700a; zr-30-nl
    not raised); H-PR1419 fails on E336's word, where the two part; H-OTHER fails everywhere."""
    for n in ("zr-28-nl-1", "zr-28-ld", "zr-30-nl", "zr-28-e336"):
        v = SC.pr_verdicts(Kept("zr", n), "x", True)
        assert v["H-PRMASK"][0] is True and v["H-OTHER"][0] is False, (n, v)
    v = SC.pr_verdicts(Kept("zr", "zr-28-e336"), "x", True)
    assert v["H-PR1419"][0] is False
    assert SC.pr_verdicts(Kept("zr", "zr-28-ld"), "x", True)["H-PR1419"][0] is True
    v = SC.pr_verdicts(Kept("zr", "zr-28-nl-1"), "x", False)
    assert all(s is None for s, _ in v.values())
    # the words of another row (0x0017110c's timeline against E336's word): H-PRMASK fails
    v = SC.pr_verdicts(Kept("zr", "zr-28-nl-1", words_from=R20 + "zr/zr-28-e336"),
                       "x", True)
    assert v["H-PRMASK"][0] is False and v["H-OTHER"][0] is True
    assert SC.mask_holds(0x10, [0x10, 0x10, 0xC4010], PL.PRMASK) is False   # under 80 %


def test_zl_forms_on_kept():
    """At the kept refill 0.25 the two raised forms coincide and hold on E1088's raised row; the
    not-raised rows hold H-HOSTBITS (no load: T1 \\ T2 at 0.5 or 1.0; load: the 0.25 everywhere);
    H-HOSTBITS (no load) fails on the raised row (E1088: raised does not follow its bits)."""
    tot = sum(1 for i, _ in SC.window(0) if i >= PL.ROW12)
    s2 = dw(R20 + "zr/zr-28-nl-1.depth-store.2.bin.gz")
    off, n = SC.hi_forms(s2, 96, PL.QUARTER, False)
    assert n == tot and off["LOADTEST"] == off["LOADNOTEST"] == 0 and off["HOSTBITS"] > 0
    off, _ = SC.hi_forms(dw(R20 + "zr/zr-30-nl.depth-store.2.bin.gz"), 96, PL.QUARTER, False)
    assert off["HOSTBITS"] == 0 and off["LOADNOTEST"] > 0
    off, _ = SC.hi_forms(dw(R20 + "zr/zr-30-ld.depth-store.2.bin.gz"), 96, PL.QUARTER, True)
    assert off["HOSTBITS"] == 0


def test_zl_forms_differ_at_075():
    """At R 0.75 the three forms part on synthetic stores of each (plan 3b)."""
    n = PL.DPAGES * 1024
    lt, lnt, hb = [PL.R75] * n, [PL.R75] * n, [PL.ONE] * n
    for i, e1, e2 in SC.window2(96):
        if e2 == 1:
            lt[i] = hb[i] = PL.HALF
        elif e2 == 0 and e1 == 1:
            hb[i] = PL.HALF
    for name, s2 in (("LOADTEST", lt), ("LOADNOTEST", lnt), ("HOSTBITS", hb)):
        off, _ = SC.hi_forms(s2, 96, PL.R75, False)
        assert off[name] == 0, name
        assert all(v > 0 for k, v in off.items() if k != name), (name, off)
    off, _ = SC.hi_forms(lt, 96, PL.R75, True)
    assert off["HOSTBITS"] == 0


def test_zcount_on_kept():
    """H-ZCOUNT's frozen counts are E1082's raised zs rows and E1090's not-raised zq rows, window
    dwords only (the plan's 195584 counted the pad columns 32 and 33 as well: 11264 more)."""
    for pin, rs in ((R19 + "zs/zs-28-g33-1", True), (R19 + "zs/zs-30-g33", True),
                    (R20 + "zq/zq-44-g33", False), (R20 + "zq/zq-4c-g33", False)):
        d2 = dw(pin + ".depth.2.bin.gz")
        assert (dw(pin + ".ta3d.1.bin.gz")[38] != 0) == rs
        z, sg = SC.zcount(d2)
        assert (z, sg) == ((PL.ZC_RAISED if rs else PL.ZC_NOT), 0), pin
        assert sum(1 for i in range(PL.ROW12) if d2[i] == 0) - z == 11264


def test_window_hi():
    assert sum(1 for i, _ in SC.window(0) if i >= PL.ROW12) == PL.W * (PL.H - 192)
    assert max(i for i, _ in SC.window(0)) < PL.DPAGES * 1024


def test_pins_declared():
    want = set(CFG["freeze"]["pins"])
    assert pins.READ <= want, sorted(pins.READ - want)
