# SPDX-License-Identifier: MIT
"""r19-dpm's offline tests: the generator is current and session.toml agrees with it; the argv
twin (every row against the plan's premises: E934's flags, --depth-ctl-next on every geometry
depth row, no --ctx2 or --bg-layer with --geometry, the medium rows last and soft); the hooks'
awk reader equals the scorer's on kept outputs and the mock's; the scorer's pieces on kept
records they must hold on and must fail on (E628's dl controls, Q045's A2 statistic, E1020's
q107 rule)."""
import os
import re
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
C26 = "data:dpm/partial-model-batch/dumps/depth-safe.c26/"
C1 = "data:dpm/partial-model-batch/dumps/depth-safe.c1/"
LAY = "data:zls/store-layout-dumps/dumps/"


def argv(r):
    a = shlex.split(r["args"].replace("$W", "/w").replace("$HOME", "/h"))
    i = a.index("--")
    return a[:i], os.path.basename(a[i + 1]), a[i + 2:]


def test_generator_current():
    r = subprocess.run([sys.executable, os.path.join(KP, "gen/plan.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_session_toml_agrees():
    T = PL.tables()
    assert list(CFG["stages"]) == list(PL.STAGES)
    assert sorted(CFG["extra_knobs"]) == PL.extra_knobs(T)
    for k in ("render_pb_pages", "render_bg_layer", "render_bg_src"):
        assert set(PL.knob_values(T, k)) <= set(CFG["knobs"][k]["values"]), k
    assert CFG["knobs"]["render_final_pb_pages"] == {"default": "0", "values": ["0"]}
    assert CFG["srcversion"] == "E0CC40275493F8AEAD8180B" and CFG["prefix"] == "r19d"
    assert CFG["tools"]["rt"].get("wraps") is True
    assert "tadata_fill" in CFG["debugfs"]
    assert sum(len(v) for v in T.values()) == 42


def test_argv_twin():
    for st, rs in PL.tables().items():
        names = [r["name"] for r in rs]
        assert len(set(names)) == len(names)
        for r in rs:
            pre, tool, a = argv(r)
            assert pre == ["0", PL.LEAD, PL.RT] and r["tool"] == "rt"
            words = r["knobs"].split()
            geo = "--geometry" in a
            assert ("--final-pb-pages" in a) == geo == (tool == "sgxfive-test-t18b" and st != "ldb")
            if geo:
                assert a[a.index("--final-pb-pages") + 1] == "0x100" and a[a.index("-n") + 1] == "2"
                for k in PL.PREMISE.split():
                    assert k in words, r["name"]
                assert "--ctx2" not in a and "--bg-layer" not in a
                if "--depth" in a:                       # the host must not refill before render 2
                    assert "--depth-ctl-next" in a, r["name"]
            if "--depth" in a or geo:
                assert "expectdiff" in words, r["name"]
            if "--bg-layer" in a:
                assert "dbg:render_bg_layer=Y" in words and "dbg:render_bg_src=0x3e800000" in words
                assert a[a.index("-n") + 1] == "1" and tool == "sgxfive-test-t10"
            if tool == "sgxfive-test-t10":
                assert not {"--final-pb-pages", "--tadata-fill-render"} & set(a)
            if r["set"] == "control":
                assert any(w.startswith("reads:") for w in words), r["name"]
            assert any(w.startswith("dbg:render_pb_pages=") for w in words), r["name"]
            for o in ("--dump-render", "--words", "--depth-dump"):
                if o in a:
                    assert a[a.index(o) + 1] == "/w", (r["name"], o)
        # controls first in their stage
        sets = [r["set"] for r in rs]
        if "control" in sets:
            assert sets[:sets.count("control")] == ["control"] * sets.count("control")
    assert CFG["stages"]["dza"].get("gate") and CFG["stages"]["zs"].get("gate")
    assert PL.GATES == {"dza": "dzl", "zs": "zsc"}


def test_ld_zero_rows_last_medium_soft():
    rs = PL.tables()["ld"]
    zero = [i for i, r in enumerate(rs) if "--tadata-fill-render" in r["args"]]
    assert zero == list(range(len(rs) - 4, len(rs)))
    for i in zero:
        r = rs[i]
        assert r["risk"] == "medium" and "soft" in r["knobs"].split()
        assert "--tadata-fill-render 2:6:0" in r["args"]
        tw = next(x for x in rs if x["name"] == r["twin"])
        assert tw["args"] + " --tadata-fill-render 2:6:0" == r["args"] and tw["p"] == r["p"]
    for r in rs:
        if "--tadata-fill-render" not in r["args"]:
            assert r["risk"] == "safe"


def test_other_stages_safe():
    for st in PL.STAGES[1:]:
        assert {r["risk"] for r in PL.tables()[st]} == {"safe"}


def test_marker_fills_unique():
    fills = re.findall(r"--depth(?:-store)?-fill (0x[0-9a-f]+)",
                       " ".join(r["args"] for rs in PL.tables().values() for r in rs))
    assert len(fills) == len(set(fills))


def test_rd_and_zs_controls_words():
    for r in PL.tables()["rd"]:
        a = argv(r)[2]
        assert PL.g_of(int(a[a.index("--depth-ctl") + 1], 16)) == r["g1"]
        assert PL.g_of(int(a[a.index("--depth-ctl-next") + 1], 16)) == r["g2"]
    assert {(r["g1"], r["g2"]) for r in PL.tables()["rd"]} == {(33, 1), (1, 33)}
    for r in PL.tables()["dzl"] + PL.tables()["dza"]:
        if r.get("form") == "dl":
            a = argv(r)[2]
            assert int(a[a.index("--depth-ctl") + 1], 16) == r["ctl"]
    assert PL.g_of(PL.E336) == 1 and PL.E336 & 0x4002 == 0x4002


# ---- the hooks' reader, twinned -----------------------------------------------------------------
def awk_words(text, tmp):
    p = os.path.join(tmp, "x.out")
    open(p, "w").write(text)
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; rd_words "$1"', "_", p],
                       capture_output=True, text=True, timeout=60)
    return dict(w.split("=", 1) for w in r.stdout.split())


KEPT_TXT = [C26 + "dl-z05-noload-0x422.txt.gz", C26 + "dl-z05-load-0x422.txt.gz",
            C26 + "dl-z05-noload-0x28.txt.gz", C1 + "dp-z05-g1-0x28-r1.txt.gz",
            C1 + "dp-z05-g1-0x30-r1.txt.gz"]


def test_hooks_twin_kept(tmp_path):
    for pin in KEPT_TXT:
        t = pins.blob(pin).decode(errors="replace")
        assert awk_words(t, str(tmp_path)) == SC.words(t), pin


def mock_text(tool, args, world, knobs, tmp):
    os.environ["FAKE_DBGREAL"] = str(tmp)
    for k, v in knobs.items():
        open(os.path.join(tmp, k), "w").write(v + "\n")
    a = WO.answer(tool, args, world)
    rows = WO.timeline(tool, [int(x, 16) for x in ("0x0624", "0x0658", "0x0724")], args, 0, world)
    return a["out"] + "timeline: regs 0x0624 0x0658 0x0724 samples %d\n" % len(rows) + "".join(
        "tl %d %s\n" % (i, " ".join("%08x" % v for v in r)) for i, r in enumerate(rows))


def test_hooks_twin_mock(tmp_path):
    for rs in PL.tables().values():
        for r in rs:
            _, tool, a = argv(r)
            kn = dict(w[4:].split("=", 1) for w in r["knobs"].split() if w.startswith("dbg:"))
            for world in ({"model"}, {"finalovf"}):
                t = mock_text({"sgxfive-test-t18b": "t18b"}.get(tool, "t10"), a, world, kn,
                              str(tmp_path))
                w = SC.words(t)
                assert awk_words(t, str(tmp_path)) == w, r["name"]
                if world == {"model"} and r["set"] == "control":   # every key it reads
                    keys = next(k for k in r["knobs"].split() if k.startswith("reads:"))
                    assert set(keys[6:].split(",")) <= set(w), (r["name"], w)
                if world == {"model"}:      # the mock's model world meets every row's ctl: words
                    for k in r["knobs"].split():
                        if k.startswith("ctl:"):
                            kk, v = k[4:].split("=")
                            assert w.get(kk) == v, (r["name"], k, w)


# ---- the scorer on kept records -----------------------------------------------------------------
def test_sidx_on_e628_controls():
    """The dz-a controls' reading on E628's kept -n 1 0x422 cells (it holds), and on the no-load
    0x28 cell (an overflowing job stores indices: a no-load control reading it would fail)."""
    w = {p.split("/")[-1]: SC.words(pins.blob(p).decode(errors="replace")) for p in KEPT_TXT[:3]}
    assert w["dl-z05-noload-0x422.txt.gz"]["sidx"] == "0"
    assert w["dl-z05-load-0x422.txt.gz"]["sidx"] == "1"
    assert w["dl-z05-noload-0x28.txt.gz"]["sidx"] == "1"
    assert w["dl-z05-noload-0x28.txt.gz"]["ovf1"] == "1"
    assert w["dl-z05-noload-0x422.txt.gz"]["ovf1"] == "0"


def state_sum(tadata, off):
    d = SC.dwords(tadata)
    return sum(d[off // 4 + 2 * i] >> 16 for i in range(16))


def a2(name):
    t = pins.blob(C1 + name + ".txt.gz").decode(errors="replace")
    col, rows = SC.timeline(t)
    prs, peaks = SC.runs(rows, col)
    tot = state_sum(pins.blob(C1 + name + ".tri.1.tadata.bin.gz"), 0x6000)
    raised = SC.dwords(pins.blob(C1 + name + ".ta3d.1.bin.gz"))[38] == 0x20
    return tot, prs[0], peaks[-1], raised


def test_ldb_statistic_on_kept_jobs():
    """Q045's A2 on two kept 11.38 jobs: R-PEAK holds on the raised 0x28 job (48 of 48 then) and
    R-THR on the 0x30 job that is not raised (28 of 28); each fails the other's rule."""
    tot, thr0, peak, raised = a2("dp-z05-g1-0x28-r1")
    assert raised and tot == peak - 1 and tot != thr0 - 1
    tot, thr0, peak, raised = a2("dp-z05-g1-0x30-r1")
    assert not raised and tot == thr0 - 1


def test_runs_is_dpm_raise():
    m = pins.module("data:vdm/verification-1141ta/recompute/dpm_raise.py", "dpm_raise")
    t = pins.blob(C1 + "dp-z05-g1-0x28-r1.txt.gz").decode(errors="replace")
    col, rows = SC.timeline(t)
    regs = sorted(col, key=col.get)
    assert SC.runs(rows, col) == m.runs(regs, [[0] + r for r in rows])


def test_q107_rule_holds_and_fails_on_kept():
    """E1020: RULE holds on a 1024x768 store without a partial render (E489's G 1 / G 33 rampx
    pair) and fails on an overflowed G 1 store (dp-ramp 0x28)."""
    g1 = SC.dwords(pins.blob(LAY + "fit-1024x768-G1-rampx.bin.gz"))
    g33 = SC.dwords(pins.blob(LAY + "fit-1024x768-G33-rampx.bin.gz"))
    hit, tot = SC.rule_hits(g1, g33)
    assert hit == tot and tot > 60000
    g1 = SC.dwords(pins.blob(C26 + "dp-ramp-g1-0x28-r1.depth.1.bin.gz"))
    g33 = SC.dwords(pins.blob(C26 + "dp-ramp-g33-0x28-r1.depth.1.bin.gz"))
    hit, tot = SC.rule_hits(g1, g33)
    assert hit < tot


def test_g_layout_on_kept():
    """rd's reading on kept stores: a G 33 dump writes past slot 126, a G 1 dump does not."""
    for name, g in (("dp-ramp-g33-0x28-r1", 33), ("dp-ramp-g1-0x28-r1", 1)):
        d = SC.dwords(pins.blob(C26 + name + ".depth.1.bin.gz"))
        fill = next(int(x, 16) for x in re.findall(
            r"--depth-fill (0x[0-9a-f]+)", pins.blob(C26 + "cases.tsv").decode())
            if any(ln.startswith(name + "\t") and x in ln
                   for ln in pins.blob(C26 + "cases.tsv").decode().splitlines()))
        assert SC.g_layout(d, fill) == g, name


def test_pins_declared():
    want = set(CFG["freeze"]["pins"])
    assert pins.READ <= want, sorted(pins.READ - want)
