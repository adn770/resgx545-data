#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: S2b end to end against a mock laptop, every gate and every stop rule.  Nothing touches the laptop.

The real scripts run: run/stage_s2.sh and run/s2.sh with ssh, scp, sudo, sha256sum and python3 shims (tests/shims),
the laptop runner run/s2_run.py with the fake fwtask_run (tests/mockfw: a simulated EDM with S2 run 3's hold model,
scenarios by MOCK_SCENARIO) and the fake tool (tests/fake_tool.py), the scorer score/score_s2.py.  Output and gates
go to a temporary directory (S2_OUT, S2_GATES), never to out/ or gates/.  Needs a current freeze.

    ../pixel-faults/.venv/bin/python tests/run_mock.py [-k SUBSTRING]
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

S2 = pathlib.Path(__file__).resolve().parent.parent
PY = str(S2.parent / "pixel-faults/.venv/bin/python")
FAIL, RAN = [], []
ONLY = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
BASE = pathlib.Path(tempfile.mkdtemp(prefix="s2bmock-"))
STAGES = (S2 / "stages.txt").read_text().split()
LAP, LAPOUT = "s2b", "s2b-out"            # the laptop's directories of S2b


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
    for t in ("sgxfive-test", "sgxfive-test-s1"):  # the landed gate's tool and the job tool
        p = home / t
        p.write_text((S2 / "tests" / "fake_tool.py").read_text())
        p.chmod(0o755)
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo"):
        (mock / "dbg" / f).write_text("")
    (mock / "dbg" / "hold_recovery").write_text("N")
    (mock / "dbg" / "render_pb_pages").write_text("0x00000422")
    (mock / "srcv").write_text("MOCKSRCV\n")
    (mock / "kmsg").write_text("")
    e = dict(os.environ)
    e.update({"PATH": f"{S2 / 'tests' / 'shims'}:{os.environ['PATH']}", "MOCK_DIR": str(mock), "MOCK_HOME": str(home),
              "MOCK_PY": PY, "MOCK_SCENARIO": scenario, "S2_MOCK_ROOT": "1",
              "S2_FWTASK_DIR": str(S2 / "tests" / "mockfw"), "S2_KMSG": str(mock / "kmsg"),
              "S2_SRCV_PATH": str(mock / "srcv"), "S2_OUT": str(out), "S2_GATES": str(gates),
              "S2_HEALTH": str(S2 / "tests" / "fake_health.sh"), "PY": PY, "SGX_LOCAL_ENV": "/nonexistent",
              "SGX_TARGET_HOST": "mock@laptop"})
    return w, e


def sh(cmd, e, timeout=900):
    r = subprocess.run(cmd, env=e, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def stage(e):
    return sh(["bash", str(S2 / "run" / "stage_s2.sh")], e)


def session(e, *args):
    return sh(["bash", str(S2 / "run" / "s2.sh")] + list(args), e)


def runner(e, st, w):
    return sh([PY, str(w / "home" / LAP / "run" / "s2_run.py"), st, "--tool", str(w / "home" / "sgxfive-test-s1"),
               "--out", str(w / "home" / LAPOUT)], e)


def open_gate(w, g, run="test-run"):
    """For stop-rule tests of a later stage only: play the scorer's gate (the gate tests use the scorer), with the run
    id of a stage.json of that stage on both sides, as the scorer and the runner require."""
    for d in (w / "home" / LAPOUT / g, w / "out" / g):
        d.mkdir(parents=True, exist_ok=True)
        if not (d / "stage.json").exists() or json.loads((d / "stage.json").read_text()).get("run") != run:
            (d / "stage.json").write_text(json.dumps({"stage": g, "run": run, "exit": 0, "jobs_run": []}))
    line = f"GATE {g} OPEN run={run} (test)\n"
    (w / "home" / LAP / "gates" / f"{g}.gate").write_text(line)
    (w / "gates" / f"{g}.gate").write_text(line)


def laprec(w, st, job):
    p = w / "home" / LAPOUT / st / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def trace(w):
    p = w / "mock" / "trace"
    return p.read_text().splitlines() if p.exists() else []


def resets(w):
    return sum(1 for l in trace(w) if l.endswith(" reset"))


def score(st, d):
    sys.path.insert(0, str(S2 / "score"))
    import score_s2
    return score_s2.score(st, d)


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
    ok(rc == 0 and "staged: ~/s2b" in o, f"staging into ~/s2b (rc {rc})")
    rc, o = session(e)
    ok(rc == 0 and o.rstrip().endswith("S2 done"), f"the whole S2b session passes on the default mock (rc {rc})")
    for st in STAGES:
        s = w / "out" / f"score-{st}.txt"
        txt = s.read_text() if s.exists() else ""
        ok("SUMMARY:" in txt, f"{st}: one SUMMARY line: {[l for l in txt.splitlines() if l.startswith('SUMMARY')][:1]}")
    for g in ("e4c", "e4m", "e4l", "e5c"):
        ok((w / "gates" / f"{g}.gate").read_text().startswith(f"GATE {g} OPEN"), f"gate {g} opened by the scorer")
    sc = (w / "out" / "score-e4m.txt").read_text()
    ok("cap q = min(H, 4) held in 10 of 10 told" in sc, "e4m: the cap prediction held 10/10 on the mock's queue")
    ok("pa2 signature 10/10" in sc and "window count 10/10" in sc, "e4m: the pa2 signature and the window count 10/10")
    ok(all(f"m{H}: " in sc and f"H {H} (held {H})" in sc for H in (1, 2, 3, 4, 6)),
       "e4m: every hold held the designed number of ticks (exits mid-period)")
    sc = (w / "out" / "score-e4l.txt").read_text()
    ok("{90: ['PARTIAL(4)', 'PARTIAL(4)']}" in sc, "e4l: the 90-tick holds read PARTIAL(4)")
    sc = (w / "out" / "score-e5c.txt").read_text()
    ok(sc.count(": QUEUED") == 3 and "place in the drain" in sc, "e5c: three kicks QUEUED, their place in the drain")
    ok("control reproduced" in sc, "e5c: the 90-tick control reproduced e4l's class")
    sc = (w / "out" / "score-e5t.txt").read_text()
    ok("QUEUED" in sc, "e5t: the held triangle's events at the exit read QUEUED")
    sudo = (w / "mock" / "sudo.log").read_text().splitlines()
    runs = [l for l in sudo if "s2_run.py" in l]
    ok(len(runs) == len(STAGES) and all(l.startswith("sudo python3 ") and "/s2b/run/" in l for l in runs),
       f"every stage ran from ~/s2b under sudo -n python3 ({len(runs)} runner calls)")
    tables = [json.loads((S2 / "tables" / f"{s}.json").read_text()) for s in STAGES]
    k = (w / "mock" / "kmsg").read_text()
    ok(k.count("resgx545 s2 case ") == sum(len(t["jobs"]) for t in tables), "one case marker a job")
    ok(all(t["blob"] == "ring_hold" for t in tables) and not any(j["op"] == "pa" for t in tables for j in t["jobs"]),
       "S2b runs ring_hold only: no pa task, no sa write")
    tr = trace(w)
    i_page = max(i for i, l in enumerate(tr) if l.endswith("page tri90-r3"))
    i_rel = max(i for i, l in enumerate(tr) if "wr hold_recovery N" in l)
    ok(i_page < i_rel, "e5t: the page is read before hold_recovery is released")
    ok(not (w / "home" / "s2").exists() and not (w / "home" / "s2-out").exists(), "S2's laptop directories untouched")


@test
def t_dry_run():
    w, e = env_for("dry")
    e["SGX_DRY_RUN"] = "1"
    rc, o = session(e)
    ok(rc == 40 and "GATE e4c is not open" in o and "~/s2b/run/s2_run.py e4c" in o,
       f"dry run prints e4c (in ~/s2b) then refuses e4m without the gate (rc {rc})")


@test
def t_gate_e4c_jitter():
    w, e = env_for("jitter", "jitter")
    stage(e)
    rc, o = session(e)
    ok(rc == 40 and not (w / "out" / "e4m").exists(), f"stamps off the grid close the e4c gate (rc {rc})")


@test
def t_gate_e4m_nohold():
    w, e = env_for("nohold", "nohold")
    stage(e)
    rc, o = session(e)
    sc = (w / "out" / "score-e4m.txt").read_text() if (w / "out" / "score-e4m.txt").exists() else ""
    ok(rc == 40 and "knob did not act" in sc and not (w / "out" / "e4l").exists(),
       f"a hold that takes no time is void (the knob), the e4m gate closes, e4l never runs (rc {rc})")


@test
def t_stop_e4m_notdone():
    w, e = env_for("never", "never_done")
    stage(e)
    open_gate(w, "e4c")
    rc, o = runner(e, "e4m", w)
    ok(rc == 4 and laprec(w, "e4m", "m1")["class"] == "notdone" and laprec(w, "e4m", "m1-r2") is None,
       f"a hold that never ends stops the stage at once (rc {rc})")


@test
def t_predictions_can_fail():
    for scen, want in (("lost", "held in 0 of 10 told"), ("all", "held in 8 of 10 told")):
        w, e = env_for(f"pf-{scen}", scen)
        stage(e)
        open_gate(w, "e4c")
        rc, o = runner(e, "e4m", w)
        summ = score("e4m", w / "home" / LAPOUT / "e4m")[2].splitlines()[-1]
        ok(rc == 0 and want in summ, f"{scen}: the cap prediction fails where it should ({summ[:120]})")


@test
def t_gate_e5c_control():
    w, e = env_for("e5ctl", "lost_in_e5c")
    stage(e)
    rc, o = session(e)
    sc = (w / "out" / "score-e5c.txt").read_text() if (w / "out" / "score-e5c.txt").exists() else ""
    ok(rc == 40 and "NOT reproduced" in sc and not (w / "out" / "e5t").exists(),
       f"the 90-tick control not reproducing e4l closes e5c's gate: no triangle (rc {rc})")


@test
def t_stop_e5c_badlog():
    w, e = env_for("e5bad", "badlog@kick90")
    stage(e)
    rc, o = session(e)
    ok(rc == 4 and not (w / "out" / "e5t").exists(), f"a stop in E5's first rows ends S2b before the triangle (rc {rc})")


@test
def t_e5c_kick_lost():
    w, e = env_for("kicklost", "kick_lost")
    stage(e)
    open_gate(w, "e4l")
    rc, o = runner(e, "e5c", w)
    r = laprec(w, "e5c", "kick90") or {}
    k = r.get("kick", {})
    ok(rc == 0 and r.get("class") == "kick-timeout" and k.get("errno") == 110,
       f"a lost kick (TimeoutError) is a result, not a stop (rc {rc})")
    d = w / "home" / LAPOUT
    shutil.copytree(d / "e5c", w / "sc" / "e5c")
    shutil.copytree(d / "e5c", w / "sc" / "e4l")      # a reference that is not the point here
    ok("LOST" in score("e5c", w / "sc" / "e5c")[2], "the scorer reads it as LOST")


@test
def t_e5t_stuck():
    w, e = env_for("stuck", "tool_hang_in_hold")
    stage(e)
    open_gate(w, "e5c")
    rc, o = runner(e, "e5t", w)
    r = laprec(w, "e5t", "tri90")
    ok(rc == 0 and r["class"] == "stuck" and len(r["page"]) == 1024 and laprec(w, "e5t", "tri90-r2") is None,
       f"a held triangle that does not complete: page kept, reset, the row not repeated (rc {rc})")
    tr = trace(w)
    ip = max(i for i, l in enumerate(tr) if l.endswith("page tri90"))
    ih = max(i for i, l in enumerate(tr) if "wr hold_recovery N" in l)
    ir = max(i for i, l in enumerate(tr) if l.endswith(" reset"))
    ok(ip < ih < ir, "page read, then hold_recovery N, then the reset")


@test
def t_stop_paths():
    w, e = env_for("fatal", "fatal@m1")
    stage(e)
    open_gate(w, "e4c")
    rc, o = runner(e, "e4m", w)
    ok(rc == 3 and resets(w) == 0, f"a watchdog line: exit 3, no reset (rc {rc})")
    w, e = env_for("trigfail", "tool_fail")
    stage(e)
    open_gate(w, "e5c")
    rc, o = runner(e, "e5t", w)
    r = laprec(w, "e5t", "tri-nohold") or {}
    ok(rc == 4 and r.get("class") == "trigfail" and len(r.get("page") or []) == 1024 and resets(w) >= 1,
       f"a failed client job stops; page kept; reset (rc {rc})")
    w, e = env_for("noret", "tool_sleep")
    e["S2_TOOL_TIMEOUT_S"] = "1"
    stage(e)
    open_gate(w, "e5c")
    rc, o = runner(e, "e5t", w)
    ok(rc == 6 and resets(w) == 0, f"a tool that does not return: exit 6, no reset (rc {rc})")
    w, e = env_for("knob", "knob_stuck")
    stage(e)
    open_gate(w, "e5c")
    rc, o = runner(e, "e5t", w)
    ok(rc == 9 and resets(w) >= 1 and laprec(w, "e5t", "tri90") is not None,
       f"hold_recovery not read back: stop 9, reset, record kept (rc {rc})")
    w, e = env_for("arm", "armfail")
    stage(e)
    rc, o = runner(e, "e4c", w)
    ok(rc == 4 and resets(w) >= 1, f"an unhealthy arm: stop, reset (rc {rc})")
    w, e = env_for("dirty", "armdirty")
    stage(e)
    rc, o = runner(e, "e4c", w)
    ok(rc == 4 and resets(w) >= 1, f"a dirty page after the arm: stop, reset (rc {rc})")
    w, e = env_for("boom", "boom@nohold")
    stage(e)
    rc, o = runner(e, "e4c", w)
    st = json.loads((w / "home" / LAPOUT / "e4c" / "stage.json").read_text())
    ok(rc in (4, 5) and st["exit"] == rc and resets(w) >= 1 and laprec(w, "e4c", "nohold") is not None,
       f"a non-Stop exception after the arm: record, reset, exit {rc}")


@test
def t_kernel_log():
    w, e = env_for("ring", "ringfull,badlog@m1")
    stage(e)
    open_gate(w, "e4c")
    rc, o = runner(e, "e4m", w)
    ok(rc == 4 and (laprec(w, "e4m", "m1") or {}).get("class") == "unhealthy",
       f"a full ring buffer: the job's slice from its marker (rc {rc})")
    w, e = env_for("late", "latebad")
    stage(e)
    rc, o = session(e, "--only", "e4c")
    ok(rc == 38 and not (w / "out" / "score-e4c.txt").exists(), f"a bad line in kernel.log stops before scoring (rc {rc})")


@test
def t_gates_and_hashes():
    w, e = env_for("g")
    stage(e)
    rc, o = session(e, "--only", "e4c")
    g = (w / "gates" / "e4c.gate").read_text()
    st = json.loads((w / "out" / "e4c" / "stage.json").read_text())
    ok(rc == 0 and g.startswith("GATE e4c OPEN") and f"run={st['run']}" in g, f"the gate carries the run id ({g.strip()})")
    e2 = dict(e, MOCK_SCENARIO="armfail")
    rc, o = session(e2, "--only", "e4c")
    ok(rc != 0 and not (w / "gates" / "e4c.gate").read_text().startswith("GATE e4c OPEN"),
       "a stopped rerun leaves no OPEN gate")
    (w / "home" / LAP / "gates" / "e4c.gate").write_text("GATE e4c OPEN run=an-old-run\n")
    n_arm = sum(1 for l in trace(w) if " arm " in l)
    rc, o = runner(e, "e4m", w)
    ok(rc == 1 and sum(1 for l in trace(w) if " arm " in l) == n_arm, f"a gate of another run arms nothing (rc {rc})")
    lp = w / "home" / LAP / "LAPTOP.sha256"
    orig = lp.read_text()
    lp.write_text(orig + "0" * 64 + "  extra\n")
    rc, o = session(e, "--only", "e4c")
    lp.write_text(orig)
    ok(rc == 21, f"the laptop's LAPTOP.sha256 differs: no stage runs (rc {rc})")
    rc, o = runner(e, "e4c", w)
    d = w / "home" / LAPOUT / "e4c"
    good = score("e4c", d)[0]
    env = json.loads((d / "env.json").read_text())
    env["blob_sha256"] = "0" * 64
    (d / "env.json").write_text(json.dumps(env))
    good2, _, txt = score("e4c", d)
    ok(good and not good2 and "env.json" in txt.splitlines()[-1], "scoring refuses env.json hashes not the Mac's files")


@test
def t_preflight():
    w, e = env_for("pre")
    stage(e)
    e2 = dict(e)
    e2.pop("S2_MOCK_ROOT")
    rc, o = runner(e2, "e4c", w)
    ok(os.geteuid() == 0 or (rc == 1 and "not root" in o), f"the runner refuses to run unprivileged (rc {rc})")
    t = w / "home" / LAP / "tables" / "e4c.json"
    orig = t.read_text()
    t.write_text(orig + " ")
    rc, o = runner(e, "e4c", w)
    t.write_text(orig)
    ok(rc == 1 and "not the frozen file" in o, f"a table that is not the frozen one is refused (rc {rc})")
    (w / "mock" / "dbg" / "hold_recovery").write_text("Y")
    rc, o = runner(e, "e4c", w)
    (w / "mock" / "dbg" / "hold_recovery").write_text("N")
    ok(rc == 1 and "defaults" in o, f"hold_recovery not N at the start is refused (rc {rc})")
    rc, o = runner(e, "e4l", w)
    ok(rc == 1 and "gate of e4m is not open" in o, f"e4l without the e4m gate is refused on the laptop (rc {rc})")
    (w / "home" / "sgxfive-test").chmod(0o644)
    rc, o = runner(e, "e4c", w)
    ok(rc == 1 and "sgxfive-test" in o, f"the preflight checks the gate tool (rc {rc})")
    w, e = env_for("pre2", sysdebug=False)
    rc, o = stage(e)
    ok(rc != 0, f"staging refuses without an sgx debugfs directory found as root (rc {rc})")


@test
def t_scorer_void():
    w, e = env_for("void")
    stage(e)
    open_gate(w, "e4c")
    rc, o = runner(e, "e4m", w)
    d = w / "home" / LAPOUT / "e4m"
    good, _, txt = score("e4m", d)
    ok(rc == 0 and good, "a clean e4m to damage")
    r = json.loads((d / "m1.json").read_text())
    r["page"] = r["page"][:500]
    (d / "m1.json").write_text(json.dumps(r))
    good, _, txt = score("e4m", d)
    ok(not good and "m1: NODATA (no page, or a truncated page)" in txt, "a truncated page is void; the gate closes")
    r = json.loads((d / "m2.json").read_text())
    r["page"][33] = 0xDEADC0DE
    (d / "m2.json").write_text(json.dumps(r))
    ok("m2: NODATA" in score("e4m", d)[2], "a missing exit stamp is void")
    r = json.loads((d / "m3.json").read_text())
    r["run"] = "old"
    (d / "m3.json").write_text(json.dumps(r))
    ok("m3: NODATA (no record kept)" in score("e4m", d)[2], "a record of an earlier run is not read")
    empty = w / "empty"
    empty.mkdir()
    for st in STAGES:
        good, _, txt = score(st, empty)
        ok(not good and "cannot tell" in txt.splitlines()[-1], f"{st} on no data: {txt.splitlines()[-1][:70]}")


@test
def t_e5t_control():
    w, e = env_for("nhne", "nohold_noevents")
    stage(e)
    open_gate(w, "e5c")
    rc, o = runner(e, "e5t", w)
    summ = score("e5t", w / "home" / LAPOUT / "e5t")[2].splitlines()[-1]
    ok("cannot tell (instrument control failed" in summ, f"e5t's no-hold control failing: cannot tell ({summ[:90]})")


@test
def t_guard_catches():
    w = BASE / "guard"
    shutil.copytree(S2, w / "s2b", ignore=shutil.ignore_patterns("out", "__pycache__"))
    g = w / "s2b" / "run" / "guard_s2.sh"
    rc, o = sh(["bash", str(g)], dict(os.environ))
    ok(rc == 0, "the guard is clean on the tree as it is")
    cases = [("run/s2.sh", 'ssh "$T" "cat /sys/kernel/debug/dri/0/sgx/regs"\n', "unprivileged debugfs"),
             ("run/stage_s2.sh", "until false; do :; done\n", "wait loop"),
             ("run/s2.sh", "export S2_MOCK_ROOT=1\n", "test-only override"),
             ("run/stage_s2.sh", "rm -f out/x\n", "forbidden word"),
             ("asm/ring_hold.s", "        mov sa65, r4\n", "sa64, sa65 or sa66"),
             ("asm/ring_hold.s", "        mov sa70, r4\n", "an sa write"),
             ("asm/ring_hold.s", "        str r4, #69, drc0\n", "str in"),
             ("tables/e4m.json", '{"op": "pa"}\n', "ring_hold only"),
             ("run/s2_run.py", "    while True:\n        pass\n", "while loop in the runner"),
             ("score/score_s2.py", "\nimport os\nos.remove('x')\n", "forbidden word in the Python code")]
    for f, line, want in cases:
        p = w / "s2b" / f
        orig = p.read_text()
        p.write_text(orig + line)
        rc, o = sh(["bash", str(g)], dict(os.environ))
        p.write_text(orig)
        ok(rc == 1 and want in o, f"the guard catches: {want} ({f})")
    (w / "s2b" / "asm" / "pa_write.s").write_text("        mov sa67, r9\n")
    rc, o = sh(["bash", str(g)], dict(os.environ))
    ok(rc == 1 and "ring_hold.s only" in o, "the guard catches another source in asm/ (no pa_write in S2b)")


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
