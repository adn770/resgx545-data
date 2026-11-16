# SPDX-License-Identifier: MIT
"""r32-misc's offline tests: the generator is current; the argv twin (every row a plain 64 x 64
triangle of t10, m2's under regtimeline on 0x0804 and 0x0b14; the word on every held row, never
on the no-word controls); the hooks' reader equals the scorer's on r31-cc's kept rows and on
synthetic ones, and counts the served kicks before snap0 as the kernel logs them (r31-cc's
kernel.log: one a reset); the hook's stops; the scorer on kept records it must hold on (r31-cc's
c1-01 as a no-word control) and on synthetic kept directories it must decide both ways (snap0
0x0000ffff: H-CC-FW held, H-CC-HW FAILED; 0x1000ffff the reverse) and must refuse to decide (the
read not served, the triangle not setting bit 28)."""
import gzip
import os
import shlex
import subprocess
import sys
import tomllib

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import make as MK  # noqa: E402
import score as SC  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
R31 = "data:render/closing-r31-cc/out/20261116-144402/"
TRI = ["tri", "--width", "64", "--height", "64"]
COLS = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n"
MI_OK = "GETMISCINFO answered after 151 us\ncore rev         0x0001000d ok\nall values match\n"
MI_BAD = ("GETMISCINFO answered after 151 us\ncore rev         0x0001000c MISMATCH\n"
          "                 expected 0x0001000d\nMISMATCHES\n")


def blob(pin):
    assert pin in CFG["freeze"]["pins"], pin
    path = pin.partition(":")[2]
    r = subprocess.run(["git", "-C", DATA, "show", f"{CFG['freeze']['data']}:{path}"],
                       capture_output=True, timeout=60, check=True)
    return (gzip.decompress(r.stdout) if path.endswith(".gz") else r.stdout).decode()


def table_rows():
    out = []
    for st in CFG["stages"]:
        out += [dict(r, stage=st) for r in SC.K.table(KP, st)]
    return out


def test_generated_current():
    assert subprocess.run([sys.executable, os.path.join(KP, "gen/make.py"), "--check"]).returncode == 0


def test_stages_and_counts():
    assert list(CFG["stages"]) == ["m1", "m2"] == list(MK.STAGES)
    rows = table_rows()
    assert len(rows) == 11
    assert all(CFG["stages"][s].get("class", "safe") == "safe" for s in CFG["stages"])
    assert all(CFG["stages"][s]["on_stop"] == "end" for s in CFG["stages"])
    assert sum(1 for r in rows if "pre:miscinfo" in r["knobs"]) == 9


def test_argv_twin():
    for r in table_rows():
        argv = shlex.split(r["args"])
        if r["tool"] == "t10":
            assert argv == TRI, r
        else:
            assert r["tool"] == "rt" and r["stage"] == "m2", r
            assert argv[:3] == ["1.5", "0.5", "0x0804,0x0b14"] and argv[3] == "--", r
            assert argv[4] == "$HOME/sgxfive-test-t10" and argv[5:] == TRI, r
        assert r["risk"] == "safe"
        assert not [w for w in r["knobs"] if w.startswith(("dbg:", "kreg:", "expect"))], r
        assert "noreset" not in r["knobs"]
        if r["set"] == "held":
            assert "pre:miscinfo" in r["knobs"], r


def test_controls_frozen_and_rows_split():
    for st in CFG["stages"]:
        pr = SC.frozen(st)
        for r in SC.K.table(KP, st):
            mine = {(q, s) for c, q, _, _, s in pr if c == r["name"]}
            if r["set"] == "control":
                keys = {q for q, s in mine if s == "control"}
                assert keys == set(r["reads"]), r
                assert keys <= SC.producible(r), r
                if "pre:miscinfo" not in r["knobs"]:
                    assert {"cache", "cache9", "kicks"} <= keys
            else:
                assert all(s == "held" for _, s in mine) and ("cache", "held") in mine, r
    # both readings of the decisive quantity are frozen, and they disagree
    for c, q, v, m, s in SC.frozen("m1"):
        if q == "cache" and m == "H-CC-FW":
            assert v == "0x0000ffff"
        if q == "cache" and m == "H-CC-HW":
            assert v == "0x1000ffff"


def test_the_control_premises_are_r31_cc_s_kept_rows():
    """A no-word control after the kit's reset: snap0 0x0000ffff, snap9 0x1000ffff, one served
    boot kick before snap0 (r31-cc c1-01, E1122)."""
    s0, s9 = blob(R31 + "c1/c1-01.snap0.regs.gz"), blob(R31 + "c1/c1-01.snap9.regs.gz")
    a = SC.analyse(blob(R31 + "c1/c1-01.txt.gz"), s0, s9)
    assert (a["diff"], a["cache"], a["cache9"]) == (0, "0x0000ffff", "0x1000ffff")
    log = blob(R31 + "c1/kernel.log")
    run = log.split("resgx545 r31c snap c1-01 0 ")[1].split()[2]
    assert SC.kicks(log, "c1-01", prefix="r31c", run=run) == 1
    # one boot answer a reset over the whole stage, 130 to 285 us over r31-cc (H-MI-LAT's source)
    assert log.count("SGX boot: kicking the EDM") == log.count("answered after") == 13
    us = [int(x.split(" answered after ")[1].split()[0]) for x in log.splitlines()
          if " answered after " in x]
    assert 100 <= min(us) and max(us) <= 400


def hook(tmp, name, out, snap0=None, snap9=None, mi=None, dmesg=None, fn="rd_words",
         stage="m1", run="1-2"):
    for f, t in ((f"{name}.out", out), ("snap0.regs", snap0), ("snap9.regs", snap9),
                 ("miscinfo.out", mi), ("dmesg.all", dmesg)):
        p = os.path.join(tmp, f)
        if t is None:
            if os.path.exists(p):
                os.remove(p)
        else:
            open(p, "w").write(t)
    r = subprocess.run(["bash", "-c", f'JW="{tmp}"; PREFIX=r32m; RUN={run}; STAGE={stage}; '
                        f'. "{KP}/run/hooks.sh"; {fn} {name}'],
                       capture_output=True, text=True, check=True)
    if fn == "rd_words":
        return dict(ln.split("=", 1) for ln in r.stdout.split())
    return r.stdout.strip()


def boot(n=1):
    return ("x kernel: SGX boot: kicking the EDM\nx kernel: SGX boot: EDM up after 150 us\n"
            + "x kernel: SGX firmware: core 545 rev 0x1000d, DDK 1.7.17 build 862890, answered "
            "after 142 us\n" * n)


def test_hooks_twin_on_kept_and_synthetic(tmp_path):
    s0, s9 = blob(R31 + "c1/c1-01.snap0.regs.gz"), blob(R31 + "c1/c1-01.snap9.regs.gz")
    for pin in (R31 + "c1/c1-01.txt.gz", R31 + "c2/c2-01.txt.gz"):
        text = blob(pin)
        w = hook(str(tmp_path), "x", text, s0, s9)
        a = SC.analyse(text, s0, s9)
        assert int(w["diff"]) == a["diff"] and w["cache"] == a["cache"]
        assert w["cache9"] == a["cache9"]
        if "ivl" in a:
            assert int(w["ivl"]) == a["ivl"] and w["cut"] == "0" and w["tlrc"] == "0"
    # the kicks before snap0: the boot's alone, or the boot's and the word's
    for n, mi in ((1, None), (2, MI_OK)):
        d = ("x resgx545 r32m snap old 0 0x0 0x0 1-2\n" + boot(1) + "x resgx545 r32m case old\n"
             + boot(n) + "x resgx545 r32m snap x 0 0x00080000 0x0 1-2\nx resgx545 case x 1-2\n"
             + boot(1))
        w = hook(str(tmp_path), "x", "diff: 0 of 4096 pixels\n", s0, s9, mi, d)
        assert w["kicks"] == str(n) == str(SC.kicks(d, "x", run="1-2"))
        assert ("mi" in w) == (mi is not None)
    w = hook(str(tmp_path), "x", "diff: 0 of 4096 pixels\n", mi=MI_BAD)
    assert w["mi"] == "0" and "kicks" not in w and "cache" not in w


def test_hook_check_stops(tmp_path):
    ok = blob(R31 + "c1/c1-01.txt.gz")
    rt = blob(R31 + "c2/c2-01.txt.gz")
    t = str(tmp_path)
    assert hook(t, "x", ok, fn="hook_check") == ""
    assert "wrong pixels" in hook(t, "x", ok.replace("diff: 0 of", "diff: 3 of"), fn="hook_check")
    assert "renders ok" in hook(t, "x", ok.replace("tri: 1 renders ok", ""), fn="hook_check")
    assert hook(t, "x", rt, fn="hook_check", stage="m2") == ""
    notl = rt.split("timeline: regs")[0]
    assert hook(t, "x", notl, fn="hook_check") == ""
    assert "no regtimeline sample" in hook(t, "x", notl, fn="hook_check", stage="m2")
    cut = rt + "tl 1 2\n"
    assert "cut" in hook(t, "x", cut, fn="hook_check", stage="m2")


def snap(v):
    return f"sgxfive regs 1\nreg 0x0804 {v}\nreg 0x0c04 0x00080000\n"


def kept_dir(tmp, stage, cache="0x0000ffff", cache9="0x1000ffff", mi=MI_OK, kicks=(1, 2, 1),
             drop=()):
    """A kept directory of every row of STAGE: the job's text (r31-cc's), the snapshots, the
    word rows' miscinfo, the controls' readings (kicks as the no-word, word, no-word controls)."""
    import gzip as gz
    d = os.path.join(tmp, stage)
    os.makedirs(d)
    rows = SC.K.table(KP, stage)
    lines, reads = [], ["name\tkeys\treading\n"]
    text = blob(R31 + ("c1/c1-01.txt.gz" if stage == "m1" else "c2/c2-01.txt.gz"))
    k = iter(kicks)
    for r in rows:
        n, word = r["name"], "pre:miscinfo" in r["knobs"]
        if n in drop:
            continue
        lines.append(f"{n}\t{stage}\t{r['set']}\tsafe\t{' '.join(r['knobs'])}\t{r['tool']}\t"
                     f"{r['args']}\t0\tok\t-\t-\t1\n")
        for suf, t in ((".txt", text), (".snap0.regs", snap("0x0000ffff" if not word else cache)),
                       (".snap9.regs", snap("0x1000ffff" if not word else cache9))):
            open(os.path.join(d, n + suf + ".gz"), "wb").write(gz.compress(t.encode()))
        if word and mi is not None:
            open(os.path.join(d, n + ".miscinfo.gz"), "wb").write(gz.compress(mi.encode()))
        if r["set"] == "control":
            a = SC.analyse(text, snap("0x0000ffff" if not word else cache),
                           snap("0x1000ffff" if not word else cache9),
                           SC.K.miscinfo(d, n) if word else None)
            kv = {q: a.get(q) for q in r["reads"]}
            kv["kicks"] = next(k) if stage == "m1" else 2
            reads.append(f"{n}\t{','.join(r['reads'])}\t"
                         + " ".join(f"{q}={v}" for q, v in kv.items()) + "\n")
    open(os.path.join(d, "cases.tsv"), "w").write(COLS + "".join(lines))
    open(os.path.join(d, "void.tsv"), "w").write(COLS)
    open(os.path.join(d, "readings.tsv"), "w").write("".join(reads))
    return d


def summary(stage, d):
    controls, per_model, lines = SC.verdicts(stage, d)
    return controls, {m: SC.SK.headline(m, controls, rows) for m, rows in per_model.items()}, \
        lines


def test_the_scorer_holds_h_cc_fw_on_an_unchanged_snap0(tmp_path):
    for st in ("m1", "m2"):
        controls, s, _ = summary(st, kept_dir(str(tmp_path), st))
        assert all(controls.values()), controls
        assert s["H-CC-FW"].startswith("H-CC-FW (") and "not supported" in s["H-CC-HW"], s
        assert s["H-CC-ONE"].startswith("H-CC-ONE (") and s["H-MI-LAT"].startswith("H-MI-LAT (")
    controls, s, _ = summary("m2", kept_dir(str(tmp_path / "x"), "m2"))
    assert s["H-CC-LAT"].startswith("H-CC-LAT ("), s


def test_the_scorer_holds_h_cc_hw_on_a_set_snap0(tmp_path):
    controls, s, _ = summary("m1", kept_dir(str(tmp_path), "m1", cache="0x1000ffff"))
    assert all(controls.values())
    assert s["H-CC-HW"].startswith("H-CC-HW (") and "not supported" in s["H-CC-FW"], s


@pytest.mark.parametrize("kw", [dict(cache9="0x0000ffff"), dict(mi=MI_BAD)])
def test_the_scorer_cannot_tell_without_the_row_s_premises(tmp_path, kw):
    controls, s, lines = summary("m1", kept_dir(str(tmp_path), "m1", **kw))
    assert s["H-CC-FW"].startswith(("cannot tell", "controls FAILED")), s
    assert s["H-CC-HW"].startswith(("cannot tell", "controls FAILED")), s
    assert any("premise" in ln for ln in lines if ln.startswith("ROW m1-01"))


@pytest.mark.parametrize("kicks", [(0, 2, 1), (1, 1, 1), (1, 2, 2)])
def test_a_control_fails_on_a_kick_count_the_kernel_did_not_log(tmp_path, kicks):
    controls, s, _ = summary("m1", kept_dir(str(tmp_path), "m1", kicks=kicks))
    assert False in controls.values(), controls
    assert s["H-CC-FW"].startswith("controls FAILED"), s


def test_the_scorer_reads_exactly_its_declared_files(tmp_path):
    import sessioncheck
    for st in ("m1", "m2"):
        d = kept_dir(str(tmp_path), st)
        probs = sessioncheck.kept_problems(d, SC.REQUIRED[st], sessioncheck.kept_classes(d),
                                           lambda: SC.read_files(st, d))
        assert probs == [], probs
