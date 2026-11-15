# SPDX-License-Identifier: MIT
"""r23-dpm's offline tests: the generator is current and session.toml agrees with it; the argv
twin (every row against the plan's premises: E934's flags, the reload files and --keep-target on
rl, --ctx2-geometry with the kept copies on og, E1093's zl form on zn, the controls byte for byte
the kept rows they repeat); E442's programs are the bytes E442 ran; the hooks' awk reader equals
the scorer's on kept outputs and the mock's; the scorer's pieces on the kept records they must
hold on and must fail on (E1089's zm rows, E1087's own1 copies, E1093's zl rows)."""
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
R21 = "data:render/closing-r21-zls/out/20261115-140052/"
R19 = "data:render/closing-r19-own1b/out/20261114-230658/own1/"
E442 = "data:dpm/partial-reload/dpm-partial-reload-green/bins/"


def argv(r):
    a = shlex.split(r["args"].replace("$W", "/w").replace("$HOME", "/h").replace("$S", "/s"))
    if r["tool"] != "rt":
        return [], r["tool"], a
    i = a.index("--")
    return a[:i], os.path.basename(a[i + 1]), a[i + 2:]


def val(a, o):
    return a[a.index(o) + 1]


def dw(pin):
    return SC.dwords(pins.blob(pin))


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/plan.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_session_toml_agrees():
    T = PL.tables()
    assert list(CFG["stages"]) == list(PL.STAGES)
    assert sorted(CFG["extra_knobs"]) == PL.extra_knobs(T)
    assert PL.knob_values(T, "render_pb_pages") == CFG["knobs"]["render_pb_pages"]["values"]
    assert PL.knob_values(T, "render_keep") == ["1"]
    assert CFG["knobs"]["render_final_pb_pages"] == {"default": "0", "values": ["0"]}
    assert CFG["knobs"]["render_keep"]["default"] == "0"
    assert CFG["srcversion"] == "E0CC40275493F8AEAD8180B" and CFG["prefix"] == "r23d"
    assert CFG["health_tool"] == "t10"
    assert CFG["tools"]["rt"].get("wraps") is True
    assert CFG["tools"]["t22b"]["sha256"].startswith("2ae2800a")
    assert CFG["tools"]["t22b"]["built_from"].startswith("b2b6bc0d44fc")
    assert {r["tool"] for rs in T.values() for r in rs} == {"rt", "t22b"}
    assert {s: len(v) for s, v in T.items()} == {"rl": 10, "og": 6, "zn": 5}
    assert not any(d.get("gate") or d.get("on_stop") for d in CFG["stages"].values())
    assert CFG["files"]["laptop"] == ["bins/*.bin"]
    for o in ("--refill", "--move", "--geometry", "--final-pb-pages", "--depth-ctl-next",
              "--bg-pds", "--bg-pixel", "--keep-target", "--ctx2-geometry", "--kept-copy"):
        assert o not in CFG["forbid_options"]
    assert "--bg-layer" in CFG["forbid_options"] and "--overlap" in CFG["forbid_options"]


def test_built_line_and_recipe():
    """lead/ holds the round 22 laptop recipe and its built line, byte copies of closing22/k22."""
    built = open(os.path.join(KP, "lead/TOOL22b.built")).read().split()
    t = CFG["tools"]["t22b"]
    assert built[0] == t["sha256"] and built[2] == t["built_from"].split(":")[0]
    assert built[4] == t["built_sha256"] == t["source_sha256"]
    rec = open(os.path.join(KP, "lead/build_tool22b_laptop.sh")).read()
    assert f"COMMIT={built[2]}" in rec and f"SRCSHA={built[4]}" in rec
    assert t["recipe"] == "data:render/closing-r23-dpm/lead/build_tool22b_laptop.sh"


def test_e442_programs_are_e442s_bytes():
    for f in ("pds_bg_pos.bin", "bg_reload_1024.bin"):
        assert open(os.path.join(KP, "bins", f), "rb").read() == pins.blob(E442 + f), f
    assert os.path.getsize(os.path.join(KP, "bins/pds_bg_pos.bin")) == 15 * 4   # 12 data + 3 code


def test_argv_twin():
    for st, rs in PL.tables().items():
        names = [r["name"] for r in rs]
        assert len(set(names)) == len(names)
        for r in rs:
            pre, tool, a = argv(r)
            words = r["knobs"].split()
            assert r["risk"] == "safe"
            assert not any(w.startswith(("expectfault", "expecthang", "#limit", "soft",
                                         "noreset")) for w in words)
            assert any(w.startswith("dbg:render_pb_pages=") for w in words)
            assert tool == ("sgxfive-test-t22b" if r["tool"] == "rt" else "t22b")
            if r["set"] == "control":
                assert any(w.startswith("reads:") for w in words), r["name"]
            for o in ("--dump-render", "--words", "--depth-dump", "--kept-copy"):
                if o in a:
                    assert val(a, o) == "/w", (r["name"], o)
            if st in ("rl", "zn"):
                assert pre == ["0", PL.LEAD, PL.RT] and "expectdiff" in words
                assert "--regs" in a and val(a, "--regs") == "0x0600-0x0750"
            if "--geometry" in a:
                assert val(a, "-n") == "2" and val(a, "--geometry") == "1"
                assert val(a, "--final-pb-pages") == "0x100" and val(a, "--move") == "2:96,0"
                for k in PL.PREMISE.split():
                    assert k in words, r["name"]
                assert PL.overflows(r["p"]), r["name"]
            if st == "rl":
                assert "--depth" not in a and "--poke" not in a
                if r["name"] != "rl-c1":
                    assert val(a, "--keep-target") == "2" and "--geometry" in a
                assert ("--bg-pds" in a) == ("--bg-pixel" in a) == r["reload"]
                if r["reload"]:
                    assert val(a, "--bg-pds") == "/s/bins/pds_bg_pos.bin:12"
                    assert val(a, "--bg-pixel") == "/s/bins/bg_reload_1024.bin"
            if st == "og":
                assert pre == [] and "expectdiff" not in words and "dbg:render_keep=1" in words
                assert val(a, "--ctx2-geometry") == "1" and "--close-first-early" in a
                assert val(a, "--kpoke-render") == f"1:ta:7^=0x{r['flag']:x}"
                assert "--final-pb-pages" not in a and "--overlap" not in a
            if st == "zn":
                assert "ctl:refill=1" in words and val(a, "--refill") == "2:depth=0x3f400000"
                assert val(a, "--depth-ctl-next") == val(a, "--depth-ctl") == hex(r["ctl"])
                assert val(a, "--depth-pages") == "0x340" and "--depth-store" in a
                assert val(a, "--poke") == "blk:1=0x00400200"
        sets = [r["set"] for r in rs]
        n = sets.count("control")
        assert sets[:n] == ["control"] * n


def test_controls_and_forms_repeat_kept_rows():
    """rl-c2 is E1089's zm-28 (t18b -> t22b) plus --keep-target 2; every rl row is that form plus
    the reload; og's rows are E1087's own1 rows plus --ctx2-geometry 1; zn's rows are E1093's zl
    form with t22b and their own markers."""
    zm = pins.blob("data:render/closing-r20-zls/tables/zm.txt").decode().splitlines()
    old = next(ln for ln in zm if ln.startswith("zm-28|")).split("|")
    T = {r["name"]: r for rs in PL.tables().values() for r in rs}
    t18, t22 = '"$HOME/sgxfive-test-t18b"', '"$HOME/sgxfive-test-t22b"'
    assert T["rl-c2"]["args"] == old[5].replace(t18, t22).replace(
        " --move", " --keep-target 2 --move")
    assert T["rl-c2"]["knobs"] == old[3] + " reads:ovf1,ovf2,thr,chg,red2"
    assert T["rl-28-a"]["args"] == old[5].replace(t18, t22).replace(
        " --move", f" {PL.RELOAD} --keep-target 2 --move")
    own = pins.blob("data:render/closing-r19-own1b/tables/own1.txt").decode().splitlines()
    for n, o in (("og-4", "o1-4"), ("og-c-a", "o1-c-a"), ("og-p200", "o1-p200")):
        old = next(ln for ln in own if ln.startswith(o + "|")).split("|")
        assert T[n]["args"] == old[5] + " --ctx2-geometry 1", n
        assert T[n]["knobs"].replace(" reads:ovf1,kept,gsize", "") == old[3].replace(
            " reads:ovf,kept,size", "")
    zl = pins.blob("data:render/closing-r21-zls/tables/zl.txt").decode().splitlines()
    for n, o in (("zn-c", "zl-2e-nl"), ("zn-2e-ld", "zl-2e-ld")):
        old = next(ln for ln in zl if ln.startswith(o + "|")).split("|")
        a = old[5].replace(t18, t22)
        mk = a.split("--depth-store-fill ")[1].split()[0]
        assert T[n]["args"].split("--depth-store-fill ")[0] == a.split("--depth-store-fill ")[0]
        assert T[n]["args"].split("--depth-store-fill ")[1].split(" ", 1)[1] == \
            a.split("--depth-store-fill ")[1].split(" ", 1)[1], n
        assert mk != T[n]["args"].split("--depth-store-fill ")[1].split()[0]
        assert T[n]["knobs"].startswith(old[3])


def test_regimes_e625():
    """E625's raise and overflow for the triangle (U 19): rl raised at 0x28 and 0x2c, not at 0x30
    and 0x34; zn's P all overflow and none is raised (0x38 would not overflow); kept regimes."""
    rl = {r["name"]: r["raised"] for r in PL.tables()["rl"] if r["geo"]}
    assert rl == {"rl-c2": True, "rl-28-a": True, "rl-28-b": True, "rl-2c-a": True,
                  "rl-2c-b": True, "rl-30-a": False, "rl-30-b": False, "rl-34-a": False,
                  "rl-34-b": False}
    assert [r["raised"] for r in PL.tables()["zn"]] == [False] * 5
    assert all(PL.overflows(r["p"]) for r in PL.tables()["zn"])
    assert not PL.overflows(0x38) and PL.overflows(0x34)
    assert dw(R20 + "zm/zm-28.ta3d.1.bin.gz")[38] != 0
    assert dw(R20 + "zm/zm-30.ta3d.1.bin.gz")[38] == 0
    assert dw(R21 + "zl/zl-2e-ld.ta3d.1.bin.gz")[38] == 0


def test_marker_fills_unique():
    import re
    fills = re.findall(r"--depth-store-fill (0x[0-9a-f]+)",
                       " ".join(r["args"] for rs in PL.tables().values() for r in rs))
    assert len(fills) == len(set(fills)) == 5


# ---- the hooks' reader, twinned -----------------------------------------------------------------
def awk_words(text, tmp):
    p = os.path.join(tmp, "x.out")
    open(p, "w").write(text)
    r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; rd_words "$1"', "_", p],
                       capture_output=True, text=True, timeout=60)
    return dict(w.split("=", 1) for w in r.stdout.split())


KEPT_TXT = [R20 + "zm/zm-28.txt.gz", R20 + "zm/zm-30.txt.gz", R21 + "zl/zl-2e-ld.txt.gz",
            R19 + "o1-c-a.txt.gz", R19 + "o1-4.txt.gz"]


def test_hooks_twin_kept(tmp_path):
    w = {}
    for pin in KEPT_TXT:
        t = pins.blob(pin).decode(errors="replace")
        k = pin.split("/")[-1]
        w[k] = SC.words(t)
        assert awk_words(t, str(tmp_path)) == w[k], pin
    a = w["zm-28.txt.gz"]
    assert (a["ovf1"], a["ovf2"], a["thr"]) == ("1", "0", "0xde")
    assert w["zm-30.txt.gz"]["tri1"] == "156048"
    assert w["zl-2e-ld.txt.gz"]["refill"] == "1"
    assert (w["o1-c-a.txt.gz"]["kept"], w["o1-c-a.txt.gz"]["fsize"]) == ("2", "24576")
    assert w["o1-c-a.txt.gz"]["ovf1"] == "0" and "gsize" not in w["o1-c-a.txt.gz"]


def test_hooks_read_t22bs_new_lines(tmp_path):
    """t22b's keep line (test_cli_reload.py's format) and the copy after the second context's
    geometry kick, as kept_copy() prints them."""
    t = ("tri 1024x768 #1: overflowed, 162544 triangle, 0 background, 623888 other; wrong 0 "
         "inside, 0 outside, 0 at edges; 0 if flipped; guard 0; background ours, not checked\n"
         "tri 1024x768 #2: target kept, 207456 pixels changed, colours 0xdeadbeef 478976, "
         "0xffff0000 207456, 0xff00ff00 100000; guard 0\n"
         "tri: render_kept after the second context's geometry kick, before its closing render 1: "
         "/w/kept.geo.1.bin (24576 bytes)\n"
         "tri: render_kept after the second context's render 1: /w/kept.1.bin (0 bytes)\n")
    w = SC.words(t)
    assert awk_words(t, str(tmp_path)) == w
    assert (w["ovf1"], w["ovf2"], w["chg"], w["red2"], w["tri1"], w["oth1"]) == (
        "1", "0", "207456", "207456", "162544", "623888")
    assert (w["kept"], w["gsize"], w["fsize"]) == ("1", "24576", "0")
    kl = SC.keep_line(t)
    assert kl[0] == 207456 and kl[1][PL.GREEN] == 100000 and kl[2] == 0
    assert SC.rl_models(kl)["H-RELOAD"][0] is True and SC.rl_models(kl)["H-REPAINT"][0] is False


def mock_text(r, world, tmp):
    os.environ["FAKE_DBGREAL"] = str(tmp)
    os.environ["FAKE_DIR"] = str(tmp)
    kn = dict(w[4:].split("=", 1) for w in r["knobs"].split() if w.startswith("dbg:"))
    for k, v in kn.items():
        open(os.path.join(tmp, k), "w").write(v + "\n")
    a = shlex.split(r["args"].replace("$W", str(tmp)).replace("$HOME", "/h").replace("$S", KP))
    if r["tool"] == "rt":
        a = a[a.index("--") + 2:]
    ans = WO.answer("t22b", a, world)
    txt = ans.get("out", "")
    if r["tool"] == "rt":
        regs = ("0x0480", "0x0484", "0x0488", "0x0624", "0x0658", "0x0724")
        rows = WO.timeline("t22b", [int(x, 16) for x in regs], a, 0, world)
        txt += "timeline: regs %s samples %d\n" % (" ".join(regs), len(rows)) + "".join(
            "tl %d %s\n" % (i, " ".join("%08x" % v for v in x)) for i, x in enumerate(rows))
    return ans, txt


def test_hooks_twin_mock(tmp_path):
    for rs in PL.tables().values():
        for r in rs:
            for world in ({"model"}, {"alt"}, {"finalovf"}, {"geoempty"}):
                ans, t = mock_text(r, world, str(tmp_path))
                assert ans.get("rc", 0) in (0, 1), (r["name"], ans.get("err"))
                w = SC.words(t)
                assert awk_words(t, str(tmp_path)) == w, r["name"]
                if world == {"model"}:
                    if r["set"] == "control":
                        keys = next(k for k in r["knobs"].split() if k.startswith("reads:"))
                        assert set(keys[6:].split(",")) <= set(w) <= SC.producible(r), (
                            r["name"], w)
                    for k in r["knobs"].split():
                        if k.startswith("ctl:"):
                            kk, v = k[4:].split("=")
                            assert w.get(kk) == v, (r["name"], k, w)


def test_mock_refuses_what_t22b_refuses(tmp_path):
    os.environ["FAKE_DBGREAL"] = str(tmp_path)
    T = {r["name"]: r for rs in PL.tables().values() for r in rs}

    def a_of(n):
        r = T[n]
        a = shlex.split(r["args"].replace("$W", str(tmp_path)).replace("$HOME", "/h")
                        .replace("$S", KP))
        return a[a.index("--") + 2:] if r["tool"] == "rt" else a

    rl, og = a_of("rl-28-a"), a_of("og-c-a")
    assert WO.answer("t22b", rl, {"model"})["rc"] in (0, 1)
    bad = [rl + ["--bg-layer"], rl + ["--keep-target", "3"], rl + ["--ctx2"],
           rl[:rl.index("--bg-pixel") + 1] + ["/nonexistent.bin"] + rl[rl.index("--bg-pixel") + 2:],
           og + ["--final-pb-pages", "0x100"], [x for x in og if x != "--ctx2"],
           og[:og.index("--ctx2-geometry")] + ["--ctx2-geometry", "2"]]
    for b in bad:
        assert WO.answer("t22b", b, {"model"})["rc"] == 2, b


# ---- the scorer on kept records -----------------------------------------------------------------
def test_rl_control_c2_on_kept_e1089():
    """rl-c2's frozen colours are E1089's zm-28 final (207456 triangle, 578976 background, wrong
    0): with the target kept every pixel changes (render 1 had no red or 0xff000080)."""
    t = pins.blob(R20 + "zm/zm-28.txt.gz").decode(errors="replace")
    n = SC.tri_line(t, 2)
    assert (n["tri"], n["bg"], n["other"], n["win"], n["wout"]) == (PL.T_PIX, PL.BG_PIX, 0, 0, 0)
    n1 = SC.tri_line(t, 1)
    assert n1["tri"] + n1["bg"] + n1["other"] == PL.NPIX


def test_rl_models_part():
    """H-RELOAD and H-REPAINT part on synthetic keep lines and never both hold."""
    rel = (207456, {PL.RED: 207456, PL.GREEN: 90000, PL.SENT: 488976}, 0, 0)
    rep = (297456, {PL.RED: 207456, PL.SENT: 578976}, 0, 0)
    nav = (786432, {PL.RED: 207456, PL.NAVY: 578976}, 0, 0)
    more = (207456, {PL.RED: 207456, PL.GREEN: 90000, PL.SENT: 488970}, 1, 0)
    for kl, want in ((rel, (True, False)), (rep, (False, True)), (nav, (False, True)),
                     (more, (False, False))):
        m = SC.rl_models(kl)
        assert (m["H-RELOAD"][0], m["H-REPAINT"][0]) == want, kl
    assert SC.rl_models(None)["H-RELOAD"][0] is None


def test_og_owner_words_on_kept_e1087():
    """E1087's o1-c-a holds the four words after the second render and none after the close;
    o1-4 (flag 0x4) none: the og forms on the kept copies."""
    a = SC.owner_words(pins.blob(R19 + "o1-c-a.kept.1.bin.gz"))
    c = SC.owner_words(pins.blob(R19 + "o1-c-a.kept.closed.1.bin.gz"))
    f = SC.owner_words(pins.blob(R19 + "o1-4.kept.1.bin.gz"))
    assert a == (4, []) and c == (0, []) and f == (0, [])
    assert SC.owner_words(b"") is None and SC.owner_words(None) is None


class Kept:
    """A kept row of r21-zls, read from its pins (the scorer's Run interface)."""

    def __init__(self, name):
        self.p = R21 + f"zl/{name}"

    def dump(self, n, suffix):
        return pins.blob(self.p + suffix + ".gz")


def test_zn_forms_on_kept_e1093():
    """E1093's zl-2e-ld (not raised, load bits; the fit row's repeat) holds H-LOADNODRAW and fails
    H-HOSTBITS (post hoc, frozen here); zl-2e-nl (zn-c's form) holds the no-load control form and
    fails H-LOADNODRAW's."""
    tot = SC.hi_total()
    s2 = SC.dwords(Kept("zl-2e-ld").dump("x", ".depth-store.2.bin"))
    off, n = SC.hi_forms(s2, 96, PL.R75, True)
    assert n == tot and off["LOADNOTEST"] == 0 and off["LOADTEST"] > 0
    s2 = SC.dwords(Kept("zl-2e-nl").dump("x", ".depth-store.2.bin"))
    off, n = SC.hi_forms(s2, 96, PL.R75, False)
    assert n == tot and off["HOSTBITS"] == 0 and off["LOADNOTEST"] > 0


def test_pins_declared():
    want = set(CFG["freeze"]["pins"])
    assert pins.READ <= want, sorted(pins.READ - want)
