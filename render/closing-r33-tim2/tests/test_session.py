# SPDX-License-Identifier: MIT
"""r33-tim2's offline tests: the generator is current; the argv twin (every row a plain 64 x 64
triangle of t10 under regtimeline, t1 on 0x012c, 0x0804 and 0x0acc, t1d on 0x0acc alone; no
knob); the hooks' reader equals the scorer's on synthetic timelines built on r30-evst2's kept
rows and on r32-misc's kept snapshots; the hook's stops; the scorer on synthetic kept
directories that must decide each pair both ways (a free-running count against a write in the
window, 399 against 400 counts a us, a spread against a fixed phase) and must refuse to decide
(no change, no pre-change rate)."""
import gzip
import os
import random
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
E2 = "data:render/closing-r30-evst2/out/20261116-132348/e2/"
M2 = "data:render/closing-r32-misc/out/20261116-185655/m2/"
TRI = ["tri", "--width", "64", "--height", "64"]
COLS = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n"


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


# ---- synthetic timelines on kept rows ---------------------------------------------------------
def synth(base, rate=398.98, phase=123456, write_at=None, step=4800, regs3=True, late=0.02,
          seed=1, nochange=False, stopped=False, lead_step=1213):
    """r30-evst2's kept text with its timeline resampled over 60 ms (the tool starting 5 ms in,
    the change 25 ms in), every LEAD_STEP ns before the tool starts and every STEP ns after (the
    spacing E1131 measured), CR_EVENT_STATUS and CR_CACHE_CTRL carried (NOCHANGE: CR_CACHE_CTRL kept at its
    first word), 0x0acc a count of RATE a us that reads PHASE at the change (reloading to
    400000; from WRITE_AT ns after the change reloaded once more; STOPPED: 0, as after POWER
    IDLE); a share LATE of the samples read 3 us late, as a preempted read would be."""
    tl = SC.timeline(base)
    rows = tl["rows"]
    rnd = random.Random(seed)
    tcc = [t for t, v in rows if v[2] != rows[0][1][2]][0]
    out, j, t = [], 0, tcc - 25_000_000

    def tim(x):
        if stopped:
            return 0
        c = phase - rate * (x - tcc) / 1000.0
        if write_at is not None and x >= tcc + write_at:
            c = 400000 - rate * (x - tcc - write_at) / 1000.0
        return 0x01000000 | int(c % 400000)
    while t < tcc + 35_000_000:
        while j + 1 < len(rows) and rows[j + 1][0] <= t:
            j += 1
        v = list(rows[j][1])
        if nochange:
            v[2] = rows[0][1][2]
        x = t + (3000 if rnd.random() < late else 0)
        out.append(f"tl {t} {v[1]:08x} {v[2]:08x} {tim(x):08x}" if regs3 else
                   f"tl {t} {tim(x):08x}")
        t += lead_step if t < tcc - 20_000_000 else step
    regs = "0x012c 0x0804 0x0acc" if regs3 else "0x0acc"
    hdr = (f"timeline: regs {regs} samples {len(out)} seconds 0.06 start "
           f"{tcc - 25_000_000 + 5_000_000} end {tcc + 90_000_000} rc 0")
    return base.split("timeline:")[0] + hdr + "\n" + "\n".join(out) + "\n"


def corrupt(text, word="00ffffff"):
    """The timeline's 100th sample with 0x0acc WORD."""
    head, _, tail = text.partition("timeline: regs")
    ls = tail.split("\n")
    p = ls[100].split()
    ls[100] = " ".join(p[:-1] + [word])
    return head + "timeline: regs" + "\n".join(ls)


def test_generated_current():
    assert subprocess.run([sys.executable, os.path.join(KP, "gen/make.py"), "--check"]).returncode == 0


def test_stages_and_counts():
    assert list(CFG["stages"]) == ["t1", "t1d"] == list(MK.STAGES)
    rows = table_rows()
    assert len(rows) == 15 and sum(1 for r in rows if r["stage"] == "t1") == 11
    assert all(CFG["stages"][s].get("class", "safe") == "safe" for s in CFG["stages"])
    assert all(CFG["stages"][s]["on_stop"] == "end" for s in CFG["stages"])


def test_argv_twin():
    for r in table_rows():
        argv = shlex.split(r["args"])
        assert r["tool"] == "rt" and r["risk"] == "safe", r
        want = (["0.06", "0.005", "0x012c,0x0804,0x0acc"] if r["stage"] == "t1" else
                ["0.04", "0.005", "0x0acc"])
        assert argv[:3] == want and argv[3] == "--", r
        assert argv[4] == "$HOME/sgxfive-test-t10" and argv[5:] == TRI, r
        assert not [w for w in r["knobs"] if w != "-" and not w.startswith("reads:")], r


def test_controls_frozen_and_rows_split():
    for st in CFG["stages"]:
        pr = SC.frozen(st)
        for r in SC.K.table(KP, st):
            mine = {(q, s) for c, q, _, _, s in pr if c == r["name"]}
            ctl = {q for q, s in mine if s == "control"}
            if r["set"] == "control":
                assert set(r["reads"]) == {"diff", "ivl", "ten"} and set(r["reads"]) <= ctl
                assert ctl <= SC.producible(r) and set(r["reads"]) <= SC.producible(r)
            else:
                assert not ctl
            assert ("rate", "held") in mine and ("period", "held") in mine, r
            if st == "t1":
                assert ("wmed", "held") in mine and ("as120", "held") in mine, r
    # both readings of each decisive pair are frozen, and they do not overlap
    for st in CFG["stages"]:
        got = {(c, q, m): v for c, q, v, m, _ in SC.frozen(st)}
        for c in {k[0] for k in got}:
            for q, a, b in (("rate", "H-TIM-399", "H-TIM-400"), ("period", "H-TIM-399",
                            "H-TIM-400"), ("as120", "H-TIM-LINE", "H-TIM-WRITE"),
                            ("tccspread", "H-TIM-ASYNC", "H-TIM-SYNC")):
                if (c, q, a) in got:
                    lo1, hi1 = (float(x) for x in got[(c, q, a)].split(".."))
                    lo2, hi2 = (float(x) for x in got[(c, q, b)].split(".."))
                    assert hi1 <= lo2 or hi2 <= lo1, (c, q)


def test_the_snapshot_model_source_is_r32_misc_s_kept_snapshots():
    """0x0acc in a kit snapshot is a running count (208 of 208 kept, post hoc): r32-misc m2-01."""
    s0, s9 = blob(M2 + "m2-01.snap0.regs.gz"), blob(M2 + "m2-01.snap9.regs.gz")
    a = SC.analyse("diff: 0 of 4096 pixels\n", s0, s9)
    assert (a["ten0"], a["ten9"]) == (1, 1)
    assert SC.reg(s0, "0x0acc") == 0x01041c73


def test_the_scorer_reads_r30_evst2_s_change_and_bit_26():
    """e2-01: the change, then bit 26 39.1 us later, 5.0 us wide (E1120); e2-02: no bit 26."""
    a = SC.analyse(synth(blob(E2 + "e2-01.txt.gz")))
    assert a["ccn"] == 1 and a["ccword"] == "0x1000ffff"
    assert 38 <= a["d26"] <= 41 and 4 <= a["w26"] <= 7
    assert a["rate"] == pytest.approx(398.98, abs=0.05) and a["nline"] >= 50
    assert a["period"] == pytest.approx(400000 / 398.98, abs=0.2)
    assert a["wmed"] <= 50 and a["as120"] <= 50 and abs(a["rcc"]) <= 50 and a["ten"] == 1
    assert 0 <= 123456 - a["lcc"] <= 399 * 4.8 + 50 and a["lead"] == 1213 and a["job"] == 4800
    assert a["tover"] == 0 and a["tnoen"] == 0 and 398500 <= a["tmax"] <= 399999
    b = SC.analyse(synth(blob(E2 + "e2-02.txt.gz")))
    assert "d26" not in b and b["wn"] >= 24        # the 120 us window, 4.8 us a sample


def test_a_write_in_the_window_and_a_400_mhz_rate_are_told_apart():
    base = blob(E2 + "e2-01.txt.gz")
    a = SC.analyse(synth(base, write_at=10_000))
    assert a["as120"] >= 2000 and a["rate"] == pytest.approx(398.98, abs=0.05)
    b = SC.analyse(synth(base, rate=400.0))
    assert b["rate"] == pytest.approx(400.0, abs=0.05)
    assert b["period"] == pytest.approx(1000.0, abs=0.2) and b["wmed"] <= 50


def test_a_late_read_at_the_change_moves_only_rcc():
    """E1131's t1-08: the change sample read about 74 us late; the line, not that sample, carries
    the window."""
    base = synth(blob(E2 + "e2-01.txt.gz"), late=0.0)
    tl = SC.timeline(base)
    c = tl["regs"].index(0x0804)
    i = next(j for j, (_, v) in enumerate(tl["rows"]) if v[c] != tl["rows"][0][1][c])
    t, v = tl["rows"][i]
    late = (v[2] & 0xffffff) - 29478
    bad = base.replace(f"tl {t} {v[0]:08x} {v[1]:08x} {v[2]:08x}",
                       f"tl {t} {v[0]:08x} {v[1]:08x} {0x01000000 | late % 400000:08x}")
    a, b = SC.analyse(base), SC.analyse(bad)
    assert abs(b["rcc"] + 29478) <= 50 and b["lcc"] == a["lcc"] and b["as120"] == a["as120"]
    assert b["wmed"] <= 50


def test_the_reload_word_is_a_running_count():
    """E1131's t1-c2 read 0x01061a80 once: bits 23:0 at most 400000, not below it."""
    assert SC.running(0x01061a80) and not SC.running(0x01061a81) and not SC.running(0x00061a80)


def hook(tmp, name, out, snap0=None, snap9=None, fn="rd_words", stage="t1"):
    for f, t in ((f"{name}.out", out), ("snap0.regs", snap0), ("snap9.regs", snap9)):
        p = os.path.join(tmp, f)
        if t is None:
            if os.path.exists(p):
                os.remove(p)
        else:
            open(p, "w").write(t)
    r = subprocess.run(["bash", "-c", f'JW="{tmp}"; PREFIX=r33u; RUN=1-2; STAGE={stage}; '
                        f'. "{KP}/run/hooks.sh"; {fn} {name}'],
                       capture_output=True, text=True, check=True)
    if fn == "rd_words":
        return dict(ln.split("=", 1) for ln in r.stdout.split())
    return r.stdout.strip()


def test_hooks_twin_on_kept_and_synthetic(tmp_path):
    s0, s9 = blob(M2 + "m2-01.snap0.regs.gz"), blob(M2 + "m2-01.snap9.regs.gz")
    base = blob(E2 + "e2-01.txt.gz")
    bad = s0.replace("reg 0x0acc 0x01041c73", "reg 0x0acc 0x0106a000")
    for text, sn in ((synth(base), s0), (synth(base, regs3=False), s9), (corrupt(synth(base)), bad),
                     (synth(base, stopped=True), s0), (synth(base, phase=399999.5, rate=0.0), s0)):
        w = hook(str(tmp_path), "x", text, sn, sn)
        a = SC.analyse(text, sn, sn)
        for k in ("diff", "ivl", "ten", "ten0", "ten9"):
            assert str(a[k]) == w[k], (k, a[k], w[k])
        assert w["cut"] == "0" and w["tlrc"] == "0"
    assert hook(str(tmp_path), "x", corrupt(synth(base)))["ten"] == "0"
    assert hook(str(tmp_path), "x", corrupt(synth(base), "0106a000"))["ten"] == "0"
    assert hook(str(tmp_path), "x", corrupt(synth(base), "01061a81"))["ten"] == "0"
    assert hook(str(tmp_path), "x", corrupt(synth(base), "01061a80"))["ten"] == "1"
    assert hook(str(tmp_path), "x", synth(base), bad)["ten0"] == "0"
    # the mock's timeline: TOTAL 0, the stored rows' step
    mk = "diff: 0 of 4096 pixels\ntimeline: regs 0x0acc samples 3 seconds 0 start 0 end 0 rc 0\n" \
         "tl 0 01040000\ntl 1000 0103fe71\ntl 2000 0103fce2\n"
    w = hook(str(tmp_path), "x", mk)
    assert w["ivl"] == "1000" == str(SC.analyse(mk)["ivl"]) and w["ten"] == "1"
    assert "ten0" not in w


def test_hook_check_stops(tmp_path):
    rt = synth(blob(E2 + "e2-01.txt.gz"))
    t = str(tmp_path)
    assert hook(t, "x", rt, fn="hook_check") == ""
    assert "wrong pixels" in hook(t, "x", rt.replace("diff: 0 of", "diff: 3 of"), fn="hook_check")
    assert "renders ok" in hook(t, "x", rt.replace("tri: 1 renders ok", ""), fn="hook_check")
    notl = rt.split("timeline: regs")[0]
    assert "no regtimeline sample" in hook(t, "x", notl, fn="hook_check")
    assert "cut" in hook(t, "x", rt + "tl 1 2\n", fn="hook_check")
    assert "rc 1" in hook(t, "x", rt.replace(" rc 0\n", " rc 1\n", 1), fn="hook_check")


def snap(v=0x01041c73):
    return f"sgxfive regs 1\nreg 0x0804 0x0000ffff\nreg 0x0acc 0x{v:08x}\n"


def kept_dir(tmp, stage, phases=None, **kw):
    """A kept directory of every row of STAGE: a synthetic timeline (r30-evst2's e2-01 or e2-02
    under it, the count from PHASES), the snapshots, the controls' readings."""
    import gzip as gz
    d = os.path.join(tmp, stage)
    os.makedirs(d)
    rows = SC.K.table(KP, stage)
    lines, reads = [], ["name\tkeys\treading\n"]
    bases = (blob(E2 + "e2-01.txt.gz"), blob(E2 + "e2-02.txt.gz"))
    for i, r in enumerate(rows):
        n = r["name"]
        ph = phases[i % len(phases)] if phases else 37_000 * i + 5000
        text = synth(bases[i % 2], phase=ph, regs3=stage == "t1", seed=i, **kw)
        lines.append(f"{n}\t{stage}\t{r['set']}\tsafe\t{' '.join(r['knobs'])}\t{r['tool']}\t"
                     f"{r['args']}\t0\tok\t-\t-\t1\n")
        for suf, t in ((".txt", text), (".snap0.regs", snap()), (".snap9.regs", snap())):
            open(os.path.join(d, n + suf + ".gz"), "wb").write(gz.compress(t.encode()))
        if r["set"] == "control":
            a = SC.analyse(text, snap(), snap())
            reads.append(f"{n}\t{','.join(r['reads'])}\t"
                         + " ".join(f"{q}={a.get(q)}" for q in r["reads"]) + "\n")
    open(os.path.join(d, "cases.tsv"), "w").write(COLS + "".join(lines))
    open(os.path.join(d, "void.tsv"), "w").write(COLS)
    open(os.path.join(d, "readings.tsv"), "w").write("".join(reads))
    return d


def summary(stage, d):
    controls, per_model, lines = SC.verdicts(stage, d)
    return controls, {m: SC.SK.headline(m, controls, rows) for m, rows in per_model.items()}, \
        lines


def held(s, m):
    return s[m].startswith(f"{m} (")


def test_the_scorer_holds_the_free_running_model(tmp_path):
    for st in ("t1", "t1d"):
        controls, s, _ = summary(st, kept_dir(str(tmp_path), st))
        assert all(controls.values()), controls
        for m in ("H-TIM-EN", "H-TIM-RANGE", "H-TIM-RELOAD", "H-TIM-399"):
            assert held(s, m), (st, m, s[m])
        assert "not supported" in s["H-TIM-400"] and "not supported" in s["H-TIM-24"], s
    controls, s, _ = summary("t1", kept_dir(str(tmp_path / "x"), "t1"))
    for m in ("H-TIM-LINE", "H-TIM-ASYNC", "H-CC-ONE", "H-CC-LAT", "H-SPACING"):
        assert held(s, m), (m, s[m])
    assert "not supported" in s["H-TIM-WRITE"] and "not supported" in s["H-TIM-SYNC"], s


def test_the_scorer_holds_the_alternatives(tmp_path):
    controls, s, _ = summary("t1", kept_dir(str(tmp_path), "t1", rate=400.0, write_at=8000,
                                            phases=[100_000, 104_000, 98_000]))
    assert all(controls.values())
    for m in ("H-TIM-400", "H-TIM-WRITE", "H-TIM-SYNC"):
        assert held(s, m), (m, s[m])
    for m in ("H-TIM-399", "H-TIM-LINE", "H-TIM-ASYNC"):
        assert "not supported" in s[m], (m, s[m])


def test_the_scorer_cannot_tell_without_a_change(tmp_path):
    """No CR_CACHE_CTRL change in the timeline (the change after the sampling): no window."""
    d = kept_dir(str(tmp_path), "t1", nochange=True)
    controls, s, lines = summary("t1", d)
    assert s["H-TIM-LINE"].startswith("cannot tell"), s
    assert s["H-TIM-ASYNC"].startswith("cannot tell"), s
    assert any("premise" in ln for ln in lines if ln.startswith("ROW t1-01"))


def test_a_control_fails_on_a_stopped_timer(tmp_path):
    d = kept_dir(str(tmp_path), "t1d", stopped=True)
    controls, s, _ = summary("t1d", d)
    assert False in controls.values(), controls
    assert s["H-TIM-399"].startswith("controls FAILED"), s


def test_the_scorer_reads_exactly_its_declared_files(tmp_path):
    import sessioncheck
    for st in ("t1", "t1d"):
        d = kept_dir(str(tmp_path), st)
        probs = sessioncheck.kept_problems(d, SC.REQUIRED[st], sessioncheck.kept_classes(d),
                                           lambda: SC.read_files(st, d))
        assert probs == [], probs
