#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: S2 end to end against a mock laptop, every gate and every stop rule.  Nothing touches the laptop.

The real scripts run: run/stage_s2.sh and run/s2.sh with ssh, scp, sudo, sha256sum and python3 shims (tests/shims),
the laptop runner run/s2_run.py with the fake fwtask_run (tests/mockfw: a simulated EDM, scenarios by MOCK_SCENARIO)
and the fake tool (tests/fake_tool.py), the scorer score/score_s2.py.  Output and gates go to a temporary directory
(S2_OUT, S2_GATES), never to out/ or gates/.  Needs a current freeze (run/freeze_s2.sh freeze).

    ../pixel-faults/.venv/bin/python tests/run_mock.py [-k SUBSTRING]
"""
import json
import os
import re
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

S2 = pathlib.Path(__file__).resolve().parent.parent
PY = str(S2.parent / "pixel-faults/.venv/bin/python")
FAIL, RAN = [], []
ONLY = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
BASE = pathlib.Path(tempfile.mkdtemp(prefix="s2mock-"))


def ok(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def env_for(name, scenario="", sysdebug=True):
    w = BASE / name
    mock, home, out, gates = w / "mock", w / "home", w / "out", w / "gates"
    for d in (mock / "dbg", home, out, gates):
        d.mkdir(parents=True, exist_ok=True)
    if sysdebug:                                   # what `sudo -n ... /sys/kernel/debug/dri/*/sgx` finds (shim)
        (mock / "sysdebug" / "dri" / "0" / "sgx").mkdir(parents=True, exist_ok=True)
    gt = home / "sgxfive-test"                     # the landed gate's tool (/home/jtorra/sgxfive-test)
    gt.write_text((S2 / "tests" / "fake_tool.py").read_text())
    gt.chmod(0o755)
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo"):
        (mock / "dbg" / f).write_text("")
    (mock / "dbg" / "hold_recovery").write_text("N")
    (mock / "dbg" / "render_pb_pages").write_text("0x00000422")
    (mock / "srcv").write_text("MOCKSRCV\n")
    (mock / "kmsg").write_text("")
    tool = home / "sgxfive-test-s1"
    tool.write_text((S2 / "tests" / "fake_tool.py").read_text())
    tool.chmod(0o755)
    e = dict(os.environ)
    e.update({"PATH": f"{S2 / 'tests' / 'shims'}:{os.environ['PATH']}", "MOCK_DIR": str(mock), "MOCK_HOME": str(home),
              "MOCK_PY": PY, "MOCK_SCENARIO": scenario, "S2_MOCK_ROOT": "1",
              "S2_FWTASK_DIR": str(S2 / "tests" / "mockfw"), "S2_KMSG": str(mock / "kmsg"),
              "S2_SRCV_PATH": str(mock / "srcv"), "S2_OUT": str(out), "S2_GATES": str(gates),
              "S2_HEALTH": str(S2 / "tests" / "fake_health.sh"), "PY": PY, "SGX_LOCAL_ENV": "/nonexistent",
              "SGX_TARGET_HOST": "mock@laptop"})
    return w, e


def sh(cmd, e, timeout=600):
    r = subprocess.run(cmd, env=e, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def stage(e):
    return sh(["bash", str(S2 / "run" / "stage_s2.sh")], e)


def session(e, *args):
    return sh(["bash", str(S2 / "run" / "s2.sh")] + list(args), e)


def runner(e, st, w):
    return sh([PY, str(w / "home" / "s2" / "run" / "s2_run.py"), st, "--tool", str(w / "home" / "sgxfive-test-s1"),
               "--out", str(w / "home" / "s2-out")], e)


def open_gate(w, g, run="test-run"):
    """For stop-rule tests of a later stage only: play the scorer's gate (the gate tests below use the scorer), with
    the run id of a stage.json of that stage on both sides, as the scorer and the runner require."""
    for d in (w / "home" / "s2-out" / g, w / "out" / g):
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "stage.json").exists() or json.loads((d / "stage.json").read_text()).get("run") != run:
            (d / "stage.json").write_text(json.dumps({"stage": g, "run": run, "exit": 0, "jobs_run": []}))
    line = f"GATE {g} OPEN run={run} (test)\n"
    (w / "home" / "s2" / "gates" / f"{g}.gate").write_text(line)
    (w / "gates" / f"{g}.gate").write_text(line)


def rec(w, st, job):
    p = w / "out" / st / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def laprec(w, st, job):
    p = w / "home" / "s2-out" / st / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def trace(w):
    p = w / "mock" / "trace"
    return p.read_text().splitlines() if p.exists() else []


TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def run_tests():
    for fn in TESTS:
        if ONLY and ONLY not in fn.__name__:
            continue
        RAN.append(fn.__name__)
        t = time.time()
        print(f"--- {fn.__name__}")
        try:
            fn()
        except Exception as ex:      # a test that crashes is a failure, not a skip
            ok(False, f"{fn.__name__} raised {ex!r}")
        print(f"    ({time.time() - t:.1f} s)")


@test
def t_full_session():
    w, e = env_for("full")
    rc, o = stage(e)
    ok(rc == 0 and "staged" in o, f"staging (rc {rc})")
    rc, o = session(e)
    ok(rc == 0 and o.rstrip().endswith("S2 done"), f"the whole session passes on the default mock (rc {rc})")
    for st in (S2 / "stages.txt").read_text().split():
        s = (w / "out" / f"score-{st}.txt")
        txt = s.read_text() if s.exists() else ""
        ok("SUMMARY:" in txt, f"{st}: one SUMMARY line: {[l for l in txt.splitlines() if l.startswith('SUMMARY')][:1]}")
    for g in ("e1c", "e2r", "e4c", "e4h", "e4l", "e5c"):
        ok((w / "gates" / f"{g}.gate").read_text().startswith(f"GATE {g} OPEN"), f"gate {g} opened by the scorer")
    sc = (w / "out" / "score-e1j.txt").read_text()
    ok("Q033 H1" in sc, "e1j decides H1 on the mock's reversed words")
    m = re.search(r"explained H1 (\d+)/(\d+)", sc)
    ok(bool(m) and m.group(1) == m.group(2) and int(m.group(2)) > 0,
       f"run 1: the count byte pa1[31:24] is not read as event bits ({m.group(0) if m else 'no line'})")
    sc = (w / "out" / "score-e1c.txt").read_text()
    ok("q50k: 0 entries" in sc and "held" in sc.split("q50k:")[1].splitlines()[0],
       "run 1: the window-1 filter at K = 5 (q50k) logs nothing")
    ok(len(re.findall(r"^kick[-r0-9]*: .*kick held", sc, re.M)) == 3, "run 1: the kick control (fit: S2 run 1) held 3/3")
    ok(len(re.findall(r"^kick[-r0-9]*: .*pa2 phase held", sc, re.M)) == 3 and
       len(re.findall(r"^kick[-r0-9]*: .*count \+1 held", sc, re.M)) == 3,
       "run 1: the held-out kick predictions (pa2 phase, count step) are scored")
    sc = (w / "out" / "score-e5c.txt").read_text()
    ok(sc.count(": QUEUED") == 3, "run 1: e5c finds the kick by its words (pa0 0, pa1 bit 8), not by pa1 bit 24")
    sc = (w / "out" / "score-e4h.txt").read_text()
    ok("'ONE'" in sc or "ONE" in sc, "e4h classifies the mock's one-pending ticks as ONE")
    sc = (w / "out" / "score-e5t.txt").read_text()
    ok("QUEUED" in sc, "e5t: the held triangle's events at the exit read QUEUED")
    sudo = (w / "mock" / "sudo.log").read_text().splitlines()
    runs = [l for l in sudo if "s2_run.py" in l]
    ok(len(runs) == 9 and all(l.startswith("sudo python3 ") for l in runs),
       f"every stage ran under sudo -n python3 ({len(runs)} runner calls)")
    k = (w / "mock" / "kmsg").read_text()
    ok(k.count("resgx545 s2 case ") == sum(len(json.loads((S2 / 'tables' / f'{s}.json').read_text())["jobs"])
                                          for s in (S2 / 'stages.txt').read_text().split()), "one case marker a job")
    r = rec(w, "e1j", "partial")
    ok(r and r["knobs_readback"]["render_pb_pages"] == "0x00000030" and r["knobs_restored"]["render_pb_pages"] == "0x00000422",
       "render_pb_pages written, read back, put back (marked in the kernel log)")
    tr = trace(w)
    i_page = max(i for i, l in enumerate(tr) if l.endswith("page tri100-r3"))
    i_rel = max(i for i, l in enumerate(tr) if "wr hold_recovery N" in l)
    ok(i_page < i_rel, "e5t: the page is read before hold_recovery is released")


@test
def t_dry_run():
    w, e = env_for("dry")
    e["SGX_DRY_RUN"] = "1"
    rc, o = session(e)
    ok(rc == 40 and "GATE e1c is not open" in o, f"dry run prints e1c then refuses e1j without the gate (rc {rc})")


@test
def t_gate_e1c_noise():
    w, e = env_for("noise", "noise")
    stage(e)
    rc, o = session(e)
    ok(rc == 40 and not (w / "out" / "e1j").exists(), f"a quiet control that logs closes the e1c gate; e1j never ran (rc {rc})")
    ok("CLOSED" in (w / "gates" / "e1c.gate").read_text(), "e1c.gate says CLOSED")


@test
def t_gate_e2r_sa66():
    w, e = env_for("sa66", "sa66bad")
    stage(e)
    open_gate(w, "e1c")
    rc, o = session(e, "--from", "e2r")
    ok(rc == 40 and not (w / "out" / "e2w").exists() and not (w / "home" / "s2-out" / "e2w").exists(),
       f"sa66 not 0x01061a70: the gate stays closed and the writer is never armed (rc {rc})")
    tr = trace(w)
    ok(not any("pa_write" in l for l in tr), "pa_write never armed")
    rc, o = runner(e, "e2w", w)
    ok(rc == 1 and "gate of e2r is not open" in o, f"the laptop runner itself refuses e2w without the open gate (rc {rc})")


@test
def t_stop_e2w_tick():
    w, e = env_for("tick", "tickstop_on_write")
    stage(e)
    open_gate(w, "e1c")
    rc, o = session(e, "--from", "e2r")
    st = json.loads((w / "out" / "e2w" / "stage.json").read_text())
    ok(rc == 4 and st["jobs_run"] == ["ctl", "w67-1"], f"the tick stops after the first write: stop at once, "
       f"no second attempt (rc {rc}, ran {st['jobs_run']})")
    ok(rec(w, "e2w", "w67-1")["class"] in ("tickstop", "notdone"), "the write job is classed a stop")
    tr = trace(w)
    ok(tr[-2:] == [tr[-2].split()[0] + " reset", tr[-1].split()[0] + " gate"] or any(l.endswith(" reset") for l in tr[-3:]),
       "after the stop: reset and gate")


@test
def t_gate_e4c_jitter():
    w, e = env_for("jitter", "jitter")
    stage(e)
    open_gate(w, "e1c")
    open_gate(w, "e2r")
    rc, o = session(e, "--from", "e4c")
    ok(rc == 40 and not (w / "out" / "e4h").exists(), f"stamps off the grid close the e4c gate (rc {rc})")


@test
def t_gate_e4h_nohold():
    w, e = env_for("nohold", "nohold")
    stage(e)
    for g in ("e1c", "e2r"):
        open_gate(w, g)
    rc, o = session(e, "--from", "e4c")
    sc = (w / "out" / "score-e4h.txt").read_text() if (w / "out" / "score-e4h.txt").exists() else ""
    ok(rc == 40 and "knob did not act" in sc and not (w / "out" / "e4l").exists(),
       f"a hold that takes no time is void (the knob), the e4h gate closes, row 5 never runs (rc {rc})")


@test
def t_stop_e4h_notdone():
    w, e = env_for("never", "never_done")
    stage(e)
    open_gate(w, "e4c")
    rc, o = runner(e, "e4h", w)
    ok(rc == 4 and laprec(w, "e4h", "h10k")["class"] == "notdone", f"a hold that never ends stops the stage (rc {rc})")
    ok(laprec(w, "e4h", "h10k-r2") is None, "nothing after it")


@test
def t_gate_e5c_control():
    w, e = env_for("e5ctl", "lost_in_e5c")
    stage(e)
    for g in ("e1c", "e2r"):
        open_gate(w, g)
    rc, o = session(e, "--from", "e4c")
    sc = (w / "out" / "score-e5c.txt").read_text() if (w / "out" / "score-e5c.txt").exists() else ""
    ok(rc == 40 and "NOT reproduced" in sc and not (w / "out" / "e5t").exists(),
       f"the 100 ms control not reproducing e4l closes e5c's gate: no triangle (rc {rc})")


@test
def t_stop_e5c_badlog():
    w, e = env_for("e5bad", "badlog@kick100")
    stage(e)
    for g in ("e1c", "e2r"):
        open_gate(w, g)
    rc, o = session(e, "--from", "e4c")
    ok(rc == 4 and not (w / "out" / "e5t").exists(), f"a stop in E5's first rows ends S2 before the triangle (rc {rc})")


@test
def t_e5c_kick_lost():
    w, e = env_for("kicklost", "kick_lost")
    stage(e)
    open_gate(w, "e4l")
    rc, o = runner(e, "e5c", w)
    shutil.copytree(w / "home" / "s2-out" / "e5c", w / "out" / "e5c", dirs_exist_ok=True)
    shutil.copytree(w / "home" / "s2-out" / "e5c", w / "out" / "e4l", dirs_exist_ok=True)   # any e4l: not the point
    k = (laprec(w, "e5c", "kick100") or {}).get("kick", {})
    ok(rc == 0 and laprec(w, "e5c", "kick100")["class"] == "kick-timeout", f"a lost kick is a result, not a stop (rc {rc})")
    ok(k.get("errno") == 110 and "no MISCINFO_READY" in k.get("text", ""),
       f"review 2: the read's TimeoutError is caught, errno and text recorded ({k})")
    sys.path.insert(0, str(S2 / "score"))
    import score_s2
    _, _, txt = score_s2.score("e5c", w / "out" / "e5c")
    ok("LOST" in txt, "the scorer reads it as LOST")


@test
def t_e5t_stuck():
    w, e = env_for("stuck", "tool_hang_in_hold")
    stage(e)
    open_gate(w, "e5c")
    rc, o = runner(e, "e5t", w)
    r = laprec(w, "e5t", "tri100")
    ok(rc == 0 and r["class"] == "stuck" and len(r["page"]) == 1024 and laprec(w, "e5t", "tri100-r2") is None,
       f"a held triangle that does not complete: page kept, reset, the row not repeated, stage ends (rc {rc})")
    tr = trace(w)
    ip = max(i for i, l in enumerate(tr) if l.endswith("page tri100"))
    ih = max(i for i, l in enumerate(tr) if "wr hold_recovery N" in l)
    ir = max(i for i, l in enumerate(tr) if l.endswith(" reset"))
    ok(ip < ih < ir, "page read, then hold_recovery N, then the reset")


@test
def t_stop_fatal():
    w, e = env_for("fatal", "fatal@fill")
    stage(e)
    open_gate(w, "e1c")
    rc, o = runner(e, "e1j", w)
    tr = trace(w)
    ok(rc == 3 and not any(l.endswith(" reset") for l in tr), f"a watchdog line: exit 3, no reset, nothing touched (rc {rc})")


@test
def t_stop_trigfail_keeps_page():
    w, e = env_for("trigfail", "tool_fail")
    stage(e)
    open_gate(w, "e1c")
    rc, o = runner(e, "e1j", w)
    r = laprec(w, "e1j", "fill")
    ok(rc == 4 and r["class"] == "trigfail" and isinstance(r.get("page"), list) and len(r["page"]) == 1024
       and (w / "home" / "s2-out" / "e1j" / "fill.dmesg").exists(),
       f"a failed client job stops; its page and kernel-log slice are kept anyway (rc {rc})")


@test
def t_stop_noreturn():
    w, e = env_for("noret", "tool_sleep")
    e["S2_TOOL_TIMEOUT_S"] = "1"
    stage(e)
    open_gate(w, "e1c")
    rc, o = runner(e, "e1j", w)
    ok(rc == 6 and not any(l.endswith(" reset") for l in trace(w)), f"a tool that does not return: exit 6, no reset (rc {rc})")


@test
def t_stop_knob():
    w, e = env_for("knob", "knob_stuck")
    stage(e)
    open_gate(w, "e1c")
    rc, o = runner(e, "e1j", w)
    ok(rc == 9, f"a knob that does not read back stops (rc {rc})")


@test
def t_stop_arm():
    w, e = env_for("arm", "armfail")
    stage(e)
    rc, o = runner(e, "e1c", w)
    ok(rc == 4 and "arm not ok" in o, f"an unhealthy arm stops (rc {rc})")
    ok(any(l.endswith(" reset") for l in trace(w)), "review 3: an unhealthy arm is followed by the reset and gate")


@test
def t_preflight():
    w, e = env_for("pre")
    stage(e)
    e2 = dict(e)
    e2.pop("S2_MOCK_ROOT")
    rc, o = runner(e2, "e1c", w)
    ok(os.geteuid() == 0 or (rc == 1 and "not root" in o), f"the runner refuses to run unprivileged (rc {rc})")
    t = w / "home" / "s2" / "tables" / "e1c.json"
    orig = t.read_text()
    t.write_text(orig + " ")
    rc, o = runner(e, "e1c", w)
    t.write_text(orig)
    ok(rc == 1 and "not the frozen file" in o, f"a table that is not the frozen one is refused (rc {rc})")
    (w / "mock" / "dbg" / "hold_recovery").write_text("Y")
    rc, o = runner(e, "e1c", w)
    (w / "mock" / "dbg" / "hold_recovery").write_text("N")
    ok(rc == 1 and "defaults" in o, f"hold_recovery not N at the start is refused (rc {rc})")
    rc, o = runner(e, "e4l", w)
    ok(rc == 1 and "gate of e4h is not open" in o, f"e4l without the e4h gate is refused on the laptop (rc {rc})")


@test
def t_scorer_void():
    sys.path.insert(0, str(S2 / "score"))
    import score_s2
    w, e = env_for("void")
    stage(e)
    rc, o = runner(e, "e2r", w)
    d = w / "home" / "s2-out" / "e2r"
    ok(rc == 0, "a clean e2r to damage")
    good, _, txt = score_s2.score("e2r", d)
    ok(good and "H-D read side held" in txt, "the undamaged e2r opens its gate")
    r = json.loads((d / "read.json").read_text())
    r["page"] = r["page"][:500]                             # truncated
    (d / "read.json").write_text(json.dumps(r))
    good, why, txt = score_s2.score("e2r", d)
    ok(not good and "NODATA (no page, or a truncated page)" in txt, "a truncated page is void and the gate closes")
    r2 = json.loads((d / "read-r2.json").read_text())
    r2["page"][64 + 8] = 0xDEADC0DE                         # an area dword not written
    (d / "read-r2.json").write_text(json.dumps(r2))
    good, why, txt = score_s2.score("e2r", d)
    ok("an area still holds INITFILL" in txt, "an INITFILL dword is void")
    r3 = json.loads((d / "read-r3.json").read_text())
    r3["run"] = "old-run"                                    # a file of an earlier run
    (d / "read-r3.json").write_text(json.dumps(r3))
    good, why, txt = score_s2.score("e2r", d)
    ok("NODATA (no record kept)" in txt and "cannot tell" in txt, "a record of an earlier run is not read; cannot tell")
    empty = w / "empty"
    empty.mkdir()
    for st in (S2 / "stages.txt").read_text().split():
        good, why, txt = score_s2.score(st, empty)
        ok(not good and "cannot tell" in txt.splitlines()[-1], f"{st} on no data: {txt.splitlines()[-1][:80]}")


@test
def t_predictions_can_fail():
    """The outcomes the frozen predictions do not favour are read as such (each prediction can fail)."""
    sys.path.insert(0, str(S2 / "score"))
    import score_s2
    for scen, st, gate, want in (("h2", "e1j", "e1c", "Q033 H2"), ("lost", "e4h", "e4c", "'LOST', 'LOST', 'LOST'"),
                                 ("noalias", "e2w", "e2r", "alias holds for the PDS words only"),
                                 ("sa66bad", "e2r", None, "sa66 prediction 0 of 3")):
        w, e = env_for(f"pf-{scen}-{st}", scen)
        stage(e)
        if gate:
            open_gate(w, gate)
        rc, o = runner(e, st, w)
        _, _, txt = score_s2.score(st, w / "home" / "s2-out" / st)
        summ = txt.splitlines()[-1]
        ok(rc == 0 and want in summ, f"{scen}: {summ[:110]}")


def resets(w):
    return sum(1 for l in trace(w) if l.endswith(" reset"))


@test
def t_review1_stale_gate():
    w, e = env_for("r1")
    stage(e)
    rc, o = session(e, "--only", "e2r")
    g = (w / "gates" / "e2r.gate").read_text()
    st = json.loads((w / "out" / "e2r" / "stage.json").read_text())
    ok(rc == 0 and g.startswith("GATE e2r OPEN") and f"run={st['run']}" in g, f"the gate line carries the run id ({g.strip()})")
    e2 = dict(e)
    e2["MOCK_SCENARIO"] = "armfail"
    rc, o = session(e2, "--only", "e2r")
    g2 = (w / "gates" / "e2r.gate").read_text()
    ok(rc != 0 and not g2.startswith("GATE e2r OPEN"), f"a stopped rerun of e2r leaves no OPEN gate ({g2.strip()})")
    (w / "home" / "s2" / "gates" / "e2r.gate").write_text("GATE e2r OPEN run=an-old-run\n")
    rc, o = runner(e, "e2w", w)
    ok(rc == 1 and "run" in o and not any("pa_write" in l for l in trace(w)),
       f"a gate of another run of e2r does not arm pa_write (rc {rc})")


@test
def t_review3_stop_paths():
    w, e = env_for("r3a", "armdirty")
    stage(e)
    rc, o = runner(e, "e1c", w)
    ok(rc == 4 and resets(w) >= 1, f"a dirty page after the arm: stop with reset and gate (rc {rc}, resets {resets(w)})")
    w, e = env_for("r3b", "boom@q50")
    stage(e)
    rc, o = runner(e, "e1c", w)
    st = json.loads((w / "home" / "s2-out" / "e1c" / "stage.json").read_text())
    cases = (w / "home" / "s2-out" / "e1c" / "cases.tsv").read_text()
    ok(rc in (4, 5) and st["exit"] == rc and resets(w) >= 1 and laprec(w, "e1c", "q50") is not None
       and "\nq50\t" in cases, f"a non-Stop exception after the arm: record, cases row, reset, exit {rc}")
    w, e = env_for("r3c", "knob_stuck")
    stage(e)
    open_gate(w, "e1c")
    rc, o = runner(e, "e1j", w)
    ok(rc == 9 and resets(w) >= 1 and laprec(w, "e1j", "partial") is not None,
       f"a knob stop (9) is followed by the reset, and the job's record is kept (rc {rc})")


@test
def t_review4_dmesg():
    w, e = env_for("r4a", "ringfull,badlog@fill")
    stage(e)
    open_gate(w, "e1c")
    rc, o = runner(e, "e1j", w)
    r = laprec(w, "e1j", "fill") or {}
    ok(rc == 4 and r.get("class") == "unhealthy", f"a full ring buffer: the job's slice is taken from its marker "
       f"(rc {rc}, class {r.get('class')})")
    w, e = env_for("r4b", "latebad")
    stage(e)
    rc, o = session(e, "--only", "e1c")
    ok(rc == 38 and not (w / "out" / "score-e1c.txt").exists(), f"a bad line in the stage's kernel.log stops before "
       f"scoring (rc {rc})")


@test
def t_review7_restore():
    w, e = env_for("r7a", "restore_bad")
    stage(e)
    open_gate(w, "e2r")
    rc, o = runner(e, "e2w", w)
    ok(rc == 4 and (laprec(w, "e2w", "restore67") or {}).get("class") == "restorefail",
       f"a restore whose read-back differs stops (rc {rc})")
    w, e = env_for("r7b", "ctl_nosa67")
    stage(e)
    open_gate(w, "e2r")
    rc, o = runner(e, "e2w", w)
    ok(rc == 4 and (laprec(w, "e2w", "restore67") or {}).get("class") == "restorefail",
       f"a skipped restore stops (rc {rc})")
    w, e = env_for("r7c", "restore_bad")
    stage(e)
    rc, o = session(e, "--from", "e2r")
    ok(rc == 4 and "WARNING" in o and "sa67" in o, f"s2.sh warns that sa67/sa68 may still hold the marker (rc {rc})")


@test
def t_review8_hashes():
    w, e = env_for("r8")
    stage(e)
    lp = w / "home" / "s2" / "LAPTOP.sha256"
    orig = lp.read_text()
    lp.write_text(orig + "0" * 64 + "  extra\n")
    rc, o = session(e, "--only", "e1c")
    lp.write_text(orig)
    ok(rc == 21 and not (w / "out" / "e1c").exists(), f"the laptop's LAPTOP.sha256 differs: no stage runs (rc {rc})")
    rc, o = runner(e, "e2r", w)
    sys.path.insert(0, str(S2 / "score"))
    import score_s2
    d = w / "home" / "s2-out" / "e2r"
    good, _, _ = score_s2.score("e2r", d)
    env = json.loads((d / "env.json").read_text())
    env["table_sha256"] = "0" * 64
    (d / "env.json").write_text(json.dumps(env))
    good2, why, txt = score_s2.score("e2r", d)
    ok(good and not good2 and "env.json" in txt.splitlines()[-1], f"scoring refuses a stage whose env.json hashes are "
       f"not the Mac's files ({txt.splitlines()[-1][:90]})")


@test
def t_review9_prereq():
    w, e = env_for("r9a")
    (w / "home" / "sgxfive-test").chmod(0o644)
    rc, o = stage(e)
    ok(rc != 0 and "sgxfive-test" in o, f"staging refuses without /home/jtorra/sgxfive-test (rc {rc})")
    w, e = env_for("r9b", sysdebug=False)
    rc, o = stage(e)
    ok(rc != 0, f"staging refuses without an sgx debugfs directory found as root (rc {rc})")
    w, e = env_for("r9c")
    stage(e)
    (w / "home" / "sgxfive-test").chmod(0o644)
    rc, o = runner(e, "e1c", w)
    ok(rc == 1 and "sgxfive-test" in o, f"the runner's preflight checks the gate tool too (rc {rc})")


@test
def t_review10_controls():
    sys.path.insert(0, str(S2 / "score"))
    import score_s2
    for scen, st, gate in (("misdispatch", "e1j", "e1c"), ("sa66bad_ctl", "e2w", "e2r"), ("nohold_noevents", "e5t", "e5c")):
        w, e = env_for(f"r10-{scen}", scen)
        stage(e)
        open_gate(w, gate)
        rc, o = runner(e, st, w)
        _, _, txt = score_s2.score(st, w / "home" / "s2-out" / st)
        summ = txt.splitlines()[-1]
        ok("cannot tell (instrument control failed" in summ, f"review 10, {scen}: {summ[:110]}")


@test
def t_guard_catches():
    w = BASE / "guard"
    shutil.copytree(S2, w / "s2", ignore=shutil.ignore_patterns("out", "__pycache__", "s2mock-*"))
    g = w / "s2" / "run" / "guard_s2.sh"
    rc, o = sh(["bash", str(g)], dict(os.environ))
    ok(rc == 0, "the guard is clean on the tree as it is")
    cases = [("run/s2.sh", 'ssh "$T" "cat /sys/kernel/debug/dri/0/sgx/regs"\n', "unprivileged debugfs"),
             ("run/stage_s2.sh", "until false; do :; done\n", "wait loop"),
             ("run/s2.sh", "export S2_MOCK_ROOT=1\n", "test-only override"),
             ("run/stage_s2.sh", "rm -f out/x\n", "forbidden word"),
             ("asm/ring_e1.s", "        mov sa65, r4\n", "sa64, sa65 or sa66"),
             ("asm/pa_read.s", "        mov sa70, r4\n", "an sa write"),
             ("asm/ring_hold.s", "        str r4, #69, drc0\n", "str in"),
             ("run/s2_run.py", "    while True:\n        pass\n", "while loop in the runner"),
             ("score/score_s2.py", "\nimport os\nos.remove('x')\n", "forbidden word in the Python code"),
             ("run/s2_run.py", "\nFR.sh('echo 1 > /sys/kernel/debug/dri/0/sgx/kreg_write')\n", "forbidden word in the Python code")]
    for f, line, want in cases:
        p = w / "s2" / f
        orig = p.read_text()
        p.write_text(orig + line)
        rc, o = sh(["bash", str(g)], dict(os.environ))
        p.write_text(orig)
        ok(rc == 1 and want in o, f"the guard catches: {want} ({f})")


def main():
    r = subprocess.run([str(S2 / "run" / "freeze_s2.sh"), "verify"], capture_output=True, text=True)
    if r.returncode:
        print("the freeze does not verify: run run/freeze_s2.sh freeze first\n" + r.stdout)
        return 2
    print(f"work dir (kept for inspection): {BASE}")
    run_tests()
    print(f"{len(RAN)} tests, {len(FAIL)} failed" + (f": {FAIL}" if FAIL else ""))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
