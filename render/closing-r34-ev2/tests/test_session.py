# SPDX-License-Identifier: MIT
"""r34-ev2's offline tests: the generator and the fit are current; the argv twin (the plan's rows:
42 jobs, every one safe, read only, under regtimeline, one of three forms, each control's premise
read from snap0 or a calibration of the same register set); the session lint is clean; the
hooks' reader equals the scorer's on the kept rows the hypotheses are frozen from; the scorer on
kept rows it must hold on and must fail on; the gate on synthetic calibrations."""
import gzip
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import fit as FIT  # noqa: E402
import make as MK  # noqa: E402
import score as SC  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
PY = sys.executable
COLS = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n"


def knobs(r):
    k = r["knobs"]
    return k.split() if isinstance(k, str) else list(k)


def table_rows():
    out = []
    for st in CFG["stages"]:
        out += [dict(r, stage=st) for r in SC.K.table(KP, st)]
    return out


# ---- generated files --------------------------------------------------------------------------
def test_generator_current():
    assert MK.main(["make.py", "--check"]) == 0


def test_fit_current_and_pinned():
    assert set(FIT.pins()) <= set(CFG["freeze"]["pins"])
    assert FIT.main(["fit.py", "--check"]) == 0


def test_lint_clean():
    r = subprocess.run([PY, "kit/session.py", "lint", "."], cwd=KP, capture_output=True,
                       text=True, timeout=120)
    assert r.returncode == 0 and r.stdout.strip() == "lint: clean", r.stdout + r.stderr


# ---- the argv twin ----------------------------------------------------------------------------
def test_stages_and_counts():
    assert list(CFG["stages"]) == ["e0", "e1", "c0", "d1", "d1s", "p0", "p1"]
    want = {"e0": 6, "e1": 30, "c0": 3, "d1": 10, "d1s": 10, "p0": 2, "p1": 10}
    rows = table_rows()
    assert {s: sum(r["stage"] == s for r in rows) for s in want} == want
    assert len(rows) == 71          # 61 run: d1 and d1s exclude each other
    for st in CFG["stages"]:
        text = open(os.path.join(KP, "tables", st + ".txt")).read()
        assert "#limit 0\n" in text
        assert CFG["stages"][st].get("class") != "flagged"
    assert {s for s, v in CFG["stages"].items() if v.get("gate")} == set(SC.GATES)


def test_rows_are_the_plan():
    regs = MK.REGS
    probe = ('"$HOME/sgxfive-test-t10" probe --tri pixel --width 3072 --height 2048 '
             '--vertices 1500 "$S/bins/p1139-green.bin"')
    forms = {probe, '"$HOME/sgxfive-test-t30" copy',
             '"$HOME/sgxfive-test-t30" copy --width 256 --height 256 --src-stride 1024 '
             '--dst-stride 1024'}
    for r in table_rows():
        assert r["risk"] == "safe" and r["tool"] == "rt"
        head, _, cmd = r["args"].partition(" -- ")
        assert head == f"0 0.005 {regs[r['stage']]}"
        assert cmd in forms
        words = knobs(r)
        assert "expectfault" not in words and "after" not in words
        assert not any(w.startswith(("kreg:", "idle:", "pre:")) or w == "noreset" for w in words)
        pb = [w for w in words if w.startswith("dbg:")]
        if cmd == probe:
            assert len(pb) == 1 and pb[0][len("dbg:render_pb_pages="):] in MK.PR
            assert "expect:rc3-overflow" in words
        else:
            assert not pb and "expect:rc3-overflow" not in words
        if r["stage"] in ("e0", "c0", "p0"):
            assert r["set"] == "control" and "ivl" in r["reads"]
    # every row of a calibration form a later control cites
    for st, cal in SC.GATES.items():
        need = {SC.form(r["args"]) for r in SC.K.table(KP, st) if r["set"] == "control"}
        have = [SC.form(r["args"]) for r in SC.K.table(KP, cal)]
        assert all(have.count(f) >= 2 for f in need), (st, need, have)
    # the knob's values: the five kept sizes, the module's default first
    k = CFG["knobs"]["render_pb_pages"]
    assert k["default"] == "0x422" and set(k["values"]) == set(MK.PR)


def test_every_held_row_has_a_rival_or_a_bound():
    preds = {st: SC.frozen(st) for st in CFG["stages"]}
    models = {m for p in preds.values() for (_, _, _, m, s) in p if s != "control"}
    for a, b in (("H-OOM-SMALL", "H-OOM-CHANCE"), ("H-C18-LARGE", "H-C18-ANY"),
                 ("H-B2PR", "H-B2-NONE"),
                 ("H-B4-ONE", "H-B4-PR"), ("H-B3-LONG", "H-B3-SHORT"),
                 ("H-PC-ONCE", "H-PC-RENDER")):
        assert a in models and b in models
    for st, p in preds.items():
        for case, q, v, m, s in p:
            if s == "control" and q.startswith("reg:") and q != "reg:0x0748":
                assert v == "@snap0"
            if s == "control" and q == "ivl":
                assert v == f"@cal:{SC.GATES[st]}"


# ---- the hooks' reader against the scorer's on kept rows -------------------------------------
def kept(pin):
    assert pin in CFG["freeze"]["pins"], pin
    return FIT.blob(pin.partition(":")[2])


def rd_words(text):
    d = tempfile.mkdtemp(prefix="r34ev.", dir=os.path.join(KP, "debug"))
    try:
        open(os.path.join(d, "j.out"), "w").write(text)
        r = subprocess.run(["bash", "-c", f'. "{KP}/run/hooks.sh"; JW="{d}"; rd_words j'],
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr
        return dict(w.split("=", 1) for w in r.stdout.split() if "=" in w)
    finally:
        shutil.rmtree(d)


KEPT = [FIT.R13 + "pr2-c0-1.txt.gz", FIT.R13 + "pr2-c4-2.txt.gz", FIT.R15 + "pr4-c0-1.txt.gz",
        FIT.R15 + "pr4-c7-1.txt.gz", FIT.EV + "tl-copy-r2-1.txt.gz",
        FIT.EV + "tl-partial-r7-2.txt.gz"]


@pytest.mark.parametrize("path", KEPT)
def test_hook_twin(path):
    text = kept("data:" + path)
    a, h = SC.analyse(text), rd_words(text)
    for k in ("ivl", "img", "diff", "r012c", "r0118", "r0660", "r0748",
              "b0n", "b1n", "b2n", "b3n", "b4n"):
        assert (str(a[k]) if k in a else None) == h.get(k), (k, a.get(k), h.get(k))
    assert h["cut"] == "0" and int(h["tl"]) > 0


def test_hook_copy_text():
    t = ("programs asm\njob: ok\ntarget: 64x32 hash 0x9b1c0be484ac0d25\ndiff: 0 of 2048 pixels\n"
         "copy: ok, 64x32 from (0, 0) to (0, 0)\n"
         "timeline: regs 0x012c samples 100 seconds 0 start 5000000 end 60000 rc 0\n"
         "tl 0 20000000\n")
    h, a = rd_words(t), SC.analyse(t)
    assert h["diff"] == "0" and h["cok"] == "1" and h["probe"] == "0" and h["ivl"] == "600"
    assert a["diff"] == 0 and a["cok"] == 1 and a["ivl"] == 600 and "ovl" not in a


# ---- the scorer on kept rows ------------------------------------------------------------------
def held(q, v, a):
    return SC.inside(a.get(q), v)


def test_scorer_holds_on_its_fit():
    c42 = SC.analyse(kept("data:" + FIT.R13 + "pr2-c4-2.txt.gz"))
    assert held("oom", "1..1000000", c42) and held("gbl", "0", c42) and held("thr", "0", c42)
    assert held("pcn", "0..1", c42) and held("pcfin", "0x200c0", c42)
    assert held("img", str(MK.IMG["0xe2"]), c42)
    c01 = SC.analyse(kept("data:" + FIT.R13 + "pr2-c0-1.txt.gz"))
    assert held("oom", "0", c01) and held("pcfin", "0x70305", c01)
    p71 = SC.analyse(kept("data:" + FIT.R15 + "pr4-c7-1.txt.gz"))
    assert held("b2wmax", "0..7000", dict(p71, b2wmax=p71["b2max"]))
    assert p71["b2n"] >= 1 and held("b4n", "1", p71) and held("b4ms", "150..240", p71)
    assert held("b3max", "20000..60000", p71) and held("b1n", "10..28", p71)
    p01 = SC.analyse(kept("data:" + FIT.R15 + "pr4-c0-1.txt.gz"))
    assert held("b2n", "0", p01) and held("b3max", "0..10000", p01) and held("b4ms", "15..26", p01)
    cp = SC.analyse(kept("data:" + FIT.EV + "tl-copy-r2-1.txt.gz"))
    assert held("e18", "0", cp) and held("e0", "0", cp) and held("s2words", "1", cp)


def test_scorer_fails_where_it_must():
    # a fill ends with bit 18: H-COPY must fail on it, H-COPY-END hold
    fl = SC.analyse(kept("data:" + FIT.EV + "tl-fill-r2-1.txt.gz"))
    assert held("e18", "0", fl) is False and held("e18", "1..1000000", fl)
    # a job that does not overflow: H-OOM-SET fails; r13-dpm's 7.5 us sampler sees no bit 2 clear
    c01 = SC.analyse(kept("data:" + FIT.R13 + "pr2-c0-1.txt.gz"))
    assert held("oom", "1..1000000", c01) is False
    # a partial job of E547's -n 2 form has two TAs: H-B4-ONE fails on it
    pr = SC.analyse(kept("data:" + FIT.EV + "tl-partial-r7-2.txt.gz"))
    assert held("b4n", "1", pr) is False
    # a 4 us pulse is not 8 us wide: bit 1's 136 us episode of E547's tl-partial-r2-2 fails
    assert held("w1max", "0..8000", SC.analyse(kept("data:" + FIT.EV +
                                                    "tl-partial-r2-2.txt.gz"))) is False


# ---- controls and the gate on synthetic kept directories -------------------------------------
def tl_text(regs, rows, end, samples, extra=""):
    out = extra + "timeline: regs %s samples %d seconds 0 start 5000000 end %d rc 0\n" % (
        " ".join(regs), samples, end)
    return out + "".join("tl %d %s\n" % (t, " ".join("%08x" % x for x in v)) for t, v in rows)


def write_stage(root, stage, ivls, first=0x20000000, snap=0x20000000, img=1748705):
    d = os.path.join(root, stage)
    os.makedirs(d)
    cases, reads = COLS, "name\tstage\treading\n"
    for r in SC.K.table(KP, stage):
        n, f = r["name"], SC.form(r["args"])
        regs = r["args"].split()[2].split(",")
        rows = [(0, [first if x == "0x012c" else 0x1f if x == "0x0748" else 0x400
                     if x == "0x0118" else 2 for x in regs])]
        if "0x0748" in regs:
            rows.append((ivls[f] * 10, [0x1f]))
        ivl = ivls[f]
        extra = ("probe p1139-green: o0 mixed 0xff203040 x1 0xff00ff00 x%d\n" % img
                 if f == "ovf" else "diff: 0 of 2048 pixels\ncopy: ok, 64x32\n")
        t = tl_text(regs, rows, ivl * 1000, 1000, extra)
        if r["set"] == "control":
            reads += f"{n}\t{stage}\tivl={ivl}" + (" b2n=0" if "0x0748" in regs else "") + "\n"
        open(os.path.join(d, n + ".txt"), "w").write(t)
        snapt = "sgxfive regs 1\nreg 0x012c 0x%08x\nreg 0x0118 0x00000400\nreg 0x0660 " \
                "0x00000002\n" % snap
        open(os.path.join(d, n + ".snap0.regs"), "w").write(snapt)
        cases += "\t".join([n, stage, r["set"], "safe", " ".join(knobs(r)), "rt", r["args"], "0", "ok",
                            "-", "-", "1"]) + "\n"
    open(os.path.join(d, "cases.tsv"), "w").write(cases)
    open(os.path.join(d, "void.tsv"), "w").write("name\treason\n")
    open(os.path.join(d, "readings.tsv"), "w").write(reads)
    return d


def test_gate_and_controls(tmp_path):
    root = str(tmp_path)
    write_stage(root, "e0", {"ovf": 640, "copy": 560, "lcopy": 580})
    ok, why = SC.gate("e1", [root])
    assert ok, why
    d = write_stage(root, "e1", {"ovf": 650, "copy": 570, "lcopy": 600})
    ctl, _, lines = SC.verdicts("e1", d, (root,))
    assert all(ctl.values()), lines
    # an interval outside the calibration's window, or a first sample not snap0's, fails
    shutil.rmtree(d)
    d = write_stage(root, "e1", {"ovf": 1650, "copy": 570, "lcopy": 600})
    ctl, _, _ = SC.verdicts("e1", d, (root,))
    assert ctl["e1-c0a"] is False and ctl["e1-cp1"] is True
    shutil.rmtree(d)
    d = write_stage(root, "e1", {"ovf": 650, "copy": 570, "lcopy": 600}, first=0x24000000)
    ctl, _, _ = SC.verdicts("e1", d, (root,))
    assert not any(ctl.values())
    # no calibration: the gate is shut
    assert not SC.gate("p1", [root])[0]
    # c0's median opens exactly one of d1 and d1s
    for ivl, d1, d1s in ((3500, True, False), (4200, False, True), (15000, False, False)):
        shutil.rmtree(os.path.join(root, "c0"), ignore_errors=True)
        write_stage(root, "c0", {"ovf": ivl})
        assert (SC.gate("d1", [root])[0], SC.gate("d1s", [root])[0]) == (d1, d1s), ivl


def test_gate_shuts_on_a_failed_calibration_control(tmp_path):
    root = str(tmp_path)
    write_stage(root, "e0", {"ovf": 640, "copy": 560, "lcopy": 580}, first=0x20000002)
    ok, why = SC.gate("e1", [root])
    assert not ok and "FAILED" in why


def test_stage_readings():
    t = {r["name"]: r for r in SC.K.table(KP, "e1")}
    allr = {}
    for n, r in t.items():
        pb, f = SC.pb_of(r), SC.form(r["args"])
        a = {"mt": 1 if pb in SC.SMALL else 0, "e18": 1 if f == "lcopy" else 0}
        allr[n] = (r, a)
    agg, _ = SC.stage_readings("e1", allr)
    assert agg == dict(mtbig=0, c18plain=0, c18large=6, c18both=0, c18gap=6)
    pre = SC.frozen("e1")
    st = {(m, q): SC.inside(agg[q], v) for c, q, v, m, s in pre if c == "e1-all"}
    assert st[("H-OOM-SMALL", "mtbig")] and st[("H-OOM-CHANCE", "mtbig")] is False
    assert st[("H-C18-LARGE", "c18large")] and st[("H-C18-ANY", "c18gap")] is False
    # one row at 0x2b6 missing: cannot tell
    del allr["e1-p11"]
    assert "mtbig" not in SC.stage_readings("e1", allr)[0]


def test_oom_small_is_r34_evs_reading():
    """H-OOM-SMALL is frozen from r34-ev's kept rows (E1137): bit 1 at 0xe2 and 0x82 in 6 of 6,
    at 0x2b6 and 0x1c2 in 0 of 5."""
    pbs = {"p1": "0x2b6", "p2": "0x1c2", "p4": "0xe2", "p7": "0x82"}
    got = {}
    for n in FIT.R34_ROWS:
        tag = n.split("-")[-1][:2]
        if tag in pbs and n.split("/")[0] in ("e1", "e2"):
            a = SC.analyse(kept("data:" + FIT.R34 + n + ".txt.gz"))
            got.setdefault(pbs[tag], []).append(a["mt"] > 0)
    assert got["0xe2"].count(True) + got["0x82"].count(True) == 6
    assert sum(got["0x2b6"] + got["0x1c2"]) == 0 and len(got["0x2b6"] + got["0x1c2"]) == 5
