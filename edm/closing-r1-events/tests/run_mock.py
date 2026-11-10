#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: R1-events end to end against a mock laptop.  Nothing touches the laptop.

The real scripts run on a COPY of this directory (so that the pinned tool hash can be the fake tool's and the freeze can be
redone there): run/stage_r1.sh and run/r1.sh with ssh, scp, sudo, sha256sum, python3 and dmesg shims (tests/shims), the laptop
runner run/r1_run.py with the fake fwtask_run (tests/mockfw: a simulated EDM, scenarios by MOCK_SCENARIO), the fake tool
(tests/fake_tool.py), the fake regtimeline (tests/fake_rt.py), the scorer score/score_r1.py.  Output and gates go to a
temporary directory.  The directory itself must be frozen (run/freeze_r1.sh verify is test 1).

    ../../closing/pixel-faults/.venv/bin/python tests/run_mock.py [-k SUBSTRING]
"""
import ast
import hashlib
import importlib
import inspect
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
R1 = pathlib.Path(__file__).resolve().parent.parent
PY = str(R1.parent.parent / "closing/pixel-faults/.venv/bin/python")
LANDED = pathlib.Path.home() / "src/resgx545/tools/fwtask/fwtask_run.py"
FAIL, RAN = [], []
ONLY = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r1mock-"))
STAGES = (R1 / "stages.txt").read_text().split()
TESTS = []


def ok(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def test(fn):
    TESTS.append(fn)
    return fn


def sh(cmd, e=None, timeout=900, cwd=None):
    r = subprocess.run(cmd, env=e or dict(os.environ), capture_output=True, text=True, timeout=timeout, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def copy_tree(name):
    """A private copy of this directory, with its own pinned tool hash (the fake tool's) and its own freeze."""
    dst = BASE / name / "r1"
    shutil.copytree(R1, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "*.pyc"))
    h = hashlib.sha256((dst / "tests" / "fake_tool.py").read_bytes()).hexdigest()
    (dst / "TOOL.sha256").write_text(f"{h}  /home/jtorra/sgxfive-test-s1b\n")
    rc, o = sh([str(dst / "run" / "freeze_r1.sh"), "freeze"], cwd=str(dst))
    assert rc == 0, o
    return dst


def env_for(name, scenario="", copy=None):
    w = BASE / name
    c = copy or copy_tree(name)
    mock, home, out, gates = w / "mock", w / "home", w / "out", w / "gates"
    for d in (mock / "dbg", home, out, gates):
        d.mkdir(parents=True, exist_ok=True)
    dri = mock / "sysdebug" / "dri"                       # the device's three names, as on the laptop
    (dri / "0").mkdir(parents=True, exist_ok=True)
    for n_, tgt in (("0/sgx", "../../../dbg"), ("128", "0"), ("0000:00:02.0", "0")):
        if not (dri / n_).exists():
            os.symlink(tgt, dri / n_)
    for t in ("sgxfive-test", "sgxfive-test-s1b"):        # the landed gate's tool and the pinned job tool
        p = home / t
        p.write_text((c / "tests" / "fake_tool.py").read_text())
        p.chmod(0o755)
    if not (home / "regtimeline").exists():
        os.symlink(c / "tests" / "fake_rt.py", home / "regtimeline")
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo"):
        (mock / "dbg" / f).write_text("")
    (mock / "dbg" / "hold_recovery").write_text("N")
    (mock / "dbg" / "render_pb_pages").write_text("0x00000422")
    (mock / "dbg" / "buf09").write_bytes(bytes(236))
    (mock / "srcv").write_text("MOCKSRCV\n")
    (mock / "kmsg").write_text("")
    e = dict(os.environ)
    e.update({"PATH": f"{c / 'tests' / 'shims'}:{os.environ['PATH']}", "MOCK_DIR": str(mock), "MOCK_HOME": str(home),
              "MOCK_PY": PY, "MOCK_SCENARIO": scenario, "R1_MOCK_ROOT": "1", "R1_FWTASK_DIR": str(c / "tests" / "mockfw"),
              "R1_KMSG": str(mock / "kmsg"), "R1_SRCV_PATH": str(mock / "srcv"), "R1_DEBUGFS": str(mock / "dbg"),
              "R1_OUT": str(out), "R1_GATES": str(gates), "PY": PY, "SGX_LOCAL_ENV": "/nonexistent",
              "SGX_TARGET_HOST": "mock@laptop", "PYTHONDONTWRITEBYTECODE": "1"})
    return w, e, c


def stage(e, c):
    return sh(["bash", str(c / "run" / "stage_r1.sh")], e)


def session(e, c, *args):
    return sh(["bash", str(c / "run" / "r1.sh")] + list(args), e)


def runner(e, w, st, extra=()):
    return sh([PY, str(w / "home" / "r1ev" / "run" / "r1_run.py"), st, "--tool", str(w / "home" / "sgxfive-test-s1b"),
               "--rt", str(w / "home" / "regtimeline"), "--bins", str(w / "home" / "r1ev" / "bins"),
               "--out", str(w / "home" / "r1ev-out")] + list(extra), e)


def laprec(w, st, job):
    p = w / "home" / "r1ev-out" / st / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def trace(w):
    p = w / "mock" / "trace"
    return p.read_text().splitlines() if p.exists() else []


def stage_json(w, st):
    return json.loads((w / "home" / "r1ev-out" / st / "stage.json").read_text())


def open_gate(w, c, g="d0", run="test-run"):
    """For stop-rule tests of d1 only: play the scorer's gate with a stage.json of that run on the laptop."""
    d = w / "home" / "r1ev-out" / g
    d.mkdir(parents=True, exist_ok=True)
    (d / "stage.json").write_text(json.dumps({"stage": g, "run": run, "exit": 0, "jobs_run": []}))
    (w / "home" / "r1ev" / "gates").mkdir(parents=True, exist_ok=True)
    (w / "home" / "r1ev" / "gates" / f"{g}.gate").write_text(f"GATE {g} OPEN run={run} (test)\n")


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
            import traceback
            traceback.print_exc()
            ok(False, f"{fn.__name__} raised {ex!r}")
        print(f"    ({time.time() - t:.1f} s)")


# ---- static -----------------------------------------------------------------------------------------------------------
@test
def t_freeze_and_guard():
    rc, o = sh([str(R1 / "run" / "freeze_r1.sh"), "verify"])
    ok(rc == 0 and "files verified" in o, f"the frozen files of this directory verify ({o.strip().splitlines()[-1] if o.strip() else ''})")
    rc, o = sh([str(R1 / "run" / "guard_r1.sh")], dict(os.environ, PYTHON=PY))
    ok(rc == 0 and "guard: clean" in o, f"guard_r1.sh is clean ({o.strip()[-60:]})")


@test
def t_guard_catches():
    c = copy_tree("guard")
    e = dict(os.environ, PYTHON=PY)

    def guard_with(path, old, new, label):
        p = c / path
        orig = p.read_text()
        p.write_text(orig.replace(old, new) if old else orig + new)
        rc, o = sh([str(c / "run" / "guard_r1.sh")], e)
        p.write_text(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")
    guard_with("run/r1.sh", "", "\nset -f\n", "set -f in a script (it breaks the globs that keep dumps)")
    guard_with("run/r1.sh", "", "\nwhile true; do sleep 1; done\n", "a wait loop in a shell script")
    guard_with("run/r1.sh", "", "\ncat /sys/kernel/debug/dri/0/sgx/regs\n", "unprivileged debugfs access")
    guard_with("run/r1.sh", "", "\nreboot\n", "a reboot")
    guard_with("run/r1.sh", "", "\necho 1 > $D/kpoke\n", "a kpoke write")
    guard_with("run/r1_run.py", "os.open(KMSG, os.O_WRONLY | os.O_APPEND)", "open(KMSG, 'a')", "the kernel log opened in Python's append mode")
    guard_with("run/r1_run.py", "\ndef sha(p):", "\nwhile False:\n    pass\n\n\ndef sha(p):", "a while loop in the runner")
    guard_with("run/r1_run.py", "FR.cmd_arm, a)", "FR.cmd_arm, a)\n        FR.kreg_write(0x0814, 1)", "a register write in the runner")
    guard_with("run/r1_run.py", "FR.cmd_reset)\n        g = captured", "FR.cmd_reset)\n        FR.wait_state(None, 1)\n        g = captured", "a polling command in the runner")
    guard_with("asm/ring_e1.s", "", "\n        mov sa65, r4\n", "an sa write in the task source")
    guard_with("asm/ring_e1.s", "", "\n        str r1, #0x0814, r2\n", "a str in the task source")
    guard_with("asm/loop-b8-i53.s", "", "\nldr r1, #0x144, drc0\n", "an ldr in a loop program")
    guard_with("tables/k.json", '"arm": "slots=0xf entry=0,1,2,3"', '"arm": "slots=0xf entry=0,1,2,3 trc=3"', "a trc in the arm line")
    guard_with("tables/t.json", '"hold_recovery": "Y"', '"hold_recovery": "Z"', "a knob value outside the allow-list")


@test
def t_pick_debugfs():
    sys.path.insert(0, str(R1 / "tests" / "mockfw"))
    e = {"MOCK_DIR": str(BASE), "R1_FWTASK_DIR": str(R1 / "tests" / "mockfw"), "R1_KMSG": str(BASE / "k")}
    old = dict(os.environ)
    os.environ.update(e)
    (BASE / "dbg_dummy").mkdir(exist_ok=True)
    try:
        sys.modules.pop("r1_run", None)
        sys.path.insert(0, str(R1 / "run"))
        r1 = importlib.import_module("r1_run")
        import glob as g
        cands = ["/sys/kernel/debug/dri/0/sgx", "/sys/kernel/debug/dri/0000:00:02.0/sgx", "/sys/kernel/debug/dri/128/sgx"]
        have = {"all": set(cands), "no0": set(cands[1:]), "only128": {cands[2]}, "none": set()}
        real_glob, real_exists = g.glob, os.path.exists
        out = {}
        for k, files in have.items():
            g.glob = lambda pat, files=files: sorted(files) if "dri/*/sgx" in pat else real_glob(pat)
            os.path.exists = lambda p, files=files: (p.rsplit("/", 1)[0] in files) if p.endswith("/own_res") else real_exists(p)
            r1.glob.glob = g.glob
            out[k] = r1.pick_debugfs()
        g.glob, os.path.exists = real_glob, real_exists
        ok(out["all"][0] == cands[0] and len(out["all"][1]) == 3, "pick_debugfs: three names, dri/0 preferred, all three recorded")
        ok(out["no0"][0] == cands[1], "pick_debugfs: without dri/0 the first sorted name that holds own_res")
        ok(out["only128"][0] == cands[2] and out["none"][0] is None, "pick_debugfs: one name, or none (a preflight stop)")
    finally:
        os.environ.clear()
        os.environ.update(old)
        sys.modules.pop("r1_run", None)


@test
def t_kmsg_flags():
    """The marker is written with os.open(path, os.O_WRONLY | os.O_APPEND), not Python's "a" mode (EINVAL on /dev/kmsg)."""
    old = dict(os.environ)
    kf = BASE / "kmsg_flags"
    kf.write_text("older\n")
    os.environ.update({"MOCK_DIR": str(BASE), "R1_FWTASK_DIR": str(R1 / "tests" / "mockfw"), "R1_KMSG": str(kf)})
    try:
        sys.modules.pop("r1_run", None)
        sys.path.insert(0, str(R1 / "run"))
        r1 = importlib.import_module("r1_run")
        calls = []
        real = os.open
        r1.os.open = lambda p, fl, *a: (calls.append((p, fl)), real(p, fl, *a))[1]
        run = type("A", (), {"stage": "k", "tool": "t", "rt": "r", "bins": "b", "out": str(BASE / "o")})
        rn = r1.Runner(run)
        rn.mark("hello")
        r1.os.open = real
        ok(calls == [(str(kf), os.O_WRONLY | os.O_APPEND)], f"Runner.mark opens the kernel log with O_WRONLY | O_APPEND ({calls})")
        ok(kf.read_text().splitlines()[-1].startswith("resgx545 r1 hello ") and kf.read_text().startswith("older\n"),
           "Runner.mark appends one line and truncates nothing")
    finally:
        os.environ.clear()
        os.environ.update(old)
        sys.modules.pop("r1_run", None)


@test
def t_scratch_arm_matches_landed():
    """The scratch arm is the landed cmd_arm with the runner's GETMISCINFO left out or doubled, statement for statement."""
    def names(src, fn_name):
        tree = ast.parse(src)
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn_name)
        out = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                f = n.func
                nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "?")
                out.append((n.lineno, n.col_offset, nm))
        return [x[2] for x in sorted(out)]
    landed = [n for n in names(LANDED.read_text(), "cmd_arm") if n != "emit"]
    scratch = names((R1 / "run" / "r1_run.py").read_text(), "arm_scratch")
    it = iter(scratch)
    sub = all(any(x == y for y in it) for x in landed)        # the landed calls, in order, inside the scratch ones
    extra = [n for n in scratch if n not in landed]
    ok(sub, "arm_scratch makes every call of the landed cmd_arm, in the landed order")
    ok(extra == [] and scratch.count("miscinfo") == 3 and landed.count("miscinfo") == 1,
       f"the only addition is the variant's GETMISCINFO calls (landed 1, scratch {scratch.count('miscinfo')} in source: the "
       f"standard one, and two more for extra2); other new calls: {extra}")
    sa = (R1 / "run" / "r1_run.py").read_text()
    ok("FR.cmd_arm, a) if variant == \"std\"" in sa, "the standard arm (K0, K1, K4-K6, every D job) is the landed cmd_arm itself")


# ---- the session ------------------------------------------------------------------------------------------------------
@test
def t_full_session():
    w, e, c = env_for("full")
    rc, o = stage(e, c)
    ok(rc == 0 and "staged: ~/r1ev" in o and "tool ok:" in o, f"staging into ~/r1ev (rc {rc})")
    ok("debugfs " in o and o.count("debugfs ") >= 3, "staging found the debugfs directories through dri/*/sgx (three names)")
    t0 = time.time()
    rc, o = session(e, c)
    el = time.time() - t0
    ok(rc == 0 and o.rstrip().endswith("R1 done"), f"the whole R1-events session passes on the default mock (rc {rc}, {el:.0f} s)")
    if rc != 0:
        print(o[-1500:])
    sc = {}
    for st in STAGES:
        s = w / "out" / f"score-{st}.txt"
        txt = s.read_text() if s.exists() else ""
        sc[st] = txt
        ok("SUMMARY:" in txt, f"{st}: one SUMMARY line")
    ok("controls held" in sc["k"] and "held out:" in sc["k"] and "fit:" in sc["k"], "k: controls held, fit and held-out rows tallied apart")
    ok(not re.search(r"[1-9]\d* FAILED", sc["k"].split("SUMMARY:")[1]), "k: no frozen row failed on the default model (H-KW)")
    ok("T0 control held" in sc["t"] and "T1 True/False" in sc["t"].replace("T1 (True, False)", "T1 True/False"), "t: T0 held; the instruction-count model holds on T1")
    ok((w / "gates" / "d0.gate").read_text().startswith("GATE d0 OPEN"), "gate d0 opened by the scorer")
    ok("H-RAISE favoured" in sc["d1"], "d1: H-RAISE favoured on the default model")
    tables = {s: json.loads((c / "tables" / f"{s}.json").read_text()) for s in STAGES}
    km = (w / "mock" / "kmsg").read_text()
    njobs = sum(len(t["jobs"]) for t in tables.values())
    ok(km.count("resgx545 r1 case ") == njobs, f"one case marker a job ({njobs})")
    ok(km.count("resgx545 r1 class ") == njobs, "one class marker a job")
    ok(km.count("resgx545 r1 arm ") == len(tables["k"]["jobs"]), "k: one arm marker a job")
    sudo = (w / "mock" / "sudo.log").read_text().splitlines()
    runs = [x for x in sudo if "r1_run.py" in x]
    ok(len(runs) == len(STAGES) and all(x.startswith("sudo python3 ") and "/r1ev/run/" in x for x in runs),
       f"every stage ran from ~/r1ev under sudo -n python3 ({len(runs)} runner calls)")
    health = [x for x in sudo if "/sys/kernel/debug" in x]
    ok(len(health) >= len(STAGES) and all(x.startswith("sudo ") for x in health),
       f"every debugfs access of the scripts went through sudo -n ({len(health)} calls named the debugfs)")
    tr = trace(w)
    bad = [x for x in tr if re.search(r" wr (kreg|kregnow|kpoke|alias_skip|trc_hazard)", x)]
    wrs = sorted({x.split()[2] for x in tr if " wr " in x})
    ok(not bad and set(wrs) <= {"own_code", "own_arm", "load", "boot", "reset", "render_pb_pages", "hold_recovery"},
       f"the runner wrote only allow-listed debugfs files: {wrs}")
    ok((w / "mock" / "dbg" / "hold_recovery").read_text().strip() == "N" and
       int((w / "mock" / "dbg" / "render_pb_pages").read_text(), 0) == 0x422, "the knobs are back at their defaults")
    # the arm variants as the kernel log shows them (the K0 count, offline premise 0e)
    idents = {j["name"]: laprec(w, "k", j["name"])["ident_after_arm"] for j in tables["k"]["jobs"]}
    ok([idents[n] for n in ("k0", "k0-r2", "k1", "k2", "k3", "k4", "k5", "k6-fill")] == [2, 2, 2, 1, 4, 2, 2, 2],
       f"GETMISCINFO answers in the arm path: std 2, nomisc 1, extra2 4 ({idents})")
    r5 = laprec(w, "k", "k5")
    ok(len(r5["warm_kicks"]) == 254 and len(r5["kicks"]) == 4 and r5["ident_total"] == 260 and r5["ccbctl_after"][0] == 4,
       f"k5: 254 + 4 kicks, 260 answers, ccbctl[0] wrapped to 4 ({r5['ccbctl_after']})")
    d1 = laprec(w, "d1", "d2-0x320")
    ok(len(d1["dump_files"]) == 2 and (w / "home" / "r1ev-out" / "d1" / "d2-0x320.dump" / "probe.param.bin").exists(),
       "d1: the render dumps are kept in NAME.dump/ (no glob lost them)")
    ok((w / "home" / "r1ev-out" / "d1" / "d2-0x320.tool.txt.gz").exists() and "d2-0x320" in " ".join(
        p.name for p in (w / "out" / "d1").iterdir()), "d1: the regtimeline output and the dumps were copied back")
    env = json.loads((w / "home" / "r1ev-out" / "d1" / "env.json").read_text())
    ok(len(env["debugfs_candidates"]) >= 1 and env["tool_sha256"] == (c / "TOOL.sha256").read_text().split()[0],
       "env.json records the debugfs candidates and the pinned tool's sha256")
    t6 = laprec(w, "t", "t6-hang")
    ok(t6["snap1_status2"] == 0x480 and t6["knobs_readback"]["hold_recovery_after"] == "N", "t6-hang: 0x480 held, hold_recovery put back (read back N)")
    ok((w / "home" / "r1ev-out" / "t" / "t0-b8-53.dmesg").exists() and (w / "out" / "t" / "t0-b8-53.dmesg").exists(),
       "t: per-job dmesg slices kept and copied back")
    tw = laprec(w, "t", "t0-b8-53")
    ok(tw["status2_pre"] == 0x400 and tw["status2_post"] == 0x400, "t0-b8-53: the job's own pre and post samples are in its record")


@test
def t_dry_run_and_gate_order():
    w, e, c = env_for("dry")
    e["SGX_DRY_RUN"] = "1"
    rc, o = session(e, c)
    ok(rc == 40 and all(f"r1_run.py {s} " in o for s in ("k", "t", "d0")) and "--rt ~/regtimeline" in o
       and "health_remote.sh" in o and "GATE d0 is not open: d1 does not run" in o,
       f"dry run prints the k, t and d0 commands, then refuses d1 without the gate (rc {rc})")
    e2 = dict(e)
    e2.pop("SGX_DRY_RUN")
    rc, o = session(e2, c, "--only", "d1")
    ok(rc == 40 and "GATE d0 is not open" in o, f"d1 does not run without d0's open gate (rc {rc})")


# ---- stop rules and scenarios (the runner directly) --------------------------------------------------------------------
def staged(name, scenario, st=None):
    w, e, c = env_for(name, scenario)
    rc, o = stage(e, c)
    assert rc == 0, o
    return w, e, c


@test
def t_stops():
    cases = [("fatal", "fatal@k0", "k", 3, "a watchdog line in the kernel log stops at once"),
             ("boom", "boom@k0", "k", 4, "an exception after the arm is a cleanup stop"),
             ("armfail", "armfail", "k", 4, "an arm that is not healthy stops"),
             ("unhealthy", "unhealthy", "t", 5, "an unhealthy GPU after a job stops; the reset cannot restore health: exit 5"),
             ("toolfail", "tool_fail", "t", 4, "a failed probe stops (trigfail)"),
             ("gatefail", "gatefail", "k", 5, "a gate that is not exact after the stage is exit 5"),
             ("badlog", "badlog@k0", "k", 4, "a hung line in a job's kernel-log slice stops"),
             ("knobstuck", "knob_stuck", "d0", 9, "a knob that reads back wrong stops with exit 9")]
    for name, sc, st, want, what in cases:
        w, e, c = staged("stop_" + name, sc)
        rc, o = runner(e, w, st)
        ok(rc == want, f"{what} (exit {rc}, wanted {want})")
        tr = trace(w)
        if want == 3:
            ok(not any(x.endswith(" reset") for x in tr), "after a fatal log line nothing else touches the GPU (no reset)")
        elif want in (4, 5, 9):
            ok(any(x.endswith(" reset") for x in tr) and any(x.endswith(" gate") for x in tr), "after a stop: dump, reset, gate")
    w, e, c = staged("stop_noreturn", "tool_sleep")
    e["R1_TOOL_TIMEOUT_S"] = "1"
    rc, o = runner(e, w, "d0")
    ok(rc == 6, f"a tool that does not return stops with exit 6 and nothing else touches the GPU (exit {rc})")
    ok(not any(x.endswith(" gate") for x in trace(w)[-3:]), "after a no-return stop no gate or reset is run")
    # preflight refusals
    w, e, c = staged("pre_tool", "")
    (w / "home" / "sgxfive-test-s1b").write_text("#!/bin/sh\necho changed\n")
    rc, o = runner(e, w, "k")
    ok(rc == 1 and "not the pinned" in o, f"a tool that is not the pinned one is refused (exit {rc})")
    w, e, c = staged("pre_table", "")
    tp = w / "home" / "r1ev" / "tables" / "k.json"
    tp.write_text(tp.read_text().replace('"warm": 254', '"warm": 255'))
    rc, o = runner(e, w, "k")
    ok(rc == 1 and "not the frozen file" in o, f"a table that is not the frozen one is refused (exit {rc})")
    w, e, c = staged("pre_bin", "")
    bp = w / "home" / "r1ev" / "bins" / "loop-b8-i53.bin"
    bp.write_bytes(bp.read_bytes() + b"\0")
    rc, o = runner(e, w, "t")
    ok(rc == 1 and "loop-b8-i53.bin is not the frozen file" in o, f"a loop program that is not the frozen one is refused (exit {rc})")
    w, e, c = staged("pre_gate", "")
    rc, o = runner(e, w, "d1")
    ok(rc == 1 and "gate of d0 is not open" in o, f"d1 without d0's gate is refused by the runner too (exit {rc})")
    w, e, c = staged("pre_gate2", "")
    open_gate(w, c, run="other")
    (w / "home" / "r1ev-out" / "d0" / "stage.json").write_text(json.dumps({"stage": "d0", "run": "different", "exit": 0}))
    rc, o = runner(e, w, "d1")
    ok(rc == 1 and "not of its last run" in o, f"a gate of another run of d0 is refused (exit {rc})")
    w, e, c = staged("pre_knob", "")
    (w / "mock" / "dbg" / "hold_recovery").write_text("Y")
    rc, o = runner(e, w, "k")
    ok(rc == 1 and "knobs not at their defaults" in o, f"knobs that are not at their defaults are refused (exit {rc})")
    w, e, c = staged("pre_files", "")
    (w / "mock" / "dbg" / "buf09").unlink()
    rc, o = runner(e, w, "d0")
    ok(rc == 1 and "no debugfs buf09" in o, f"a driver without the debugfs file a stage needs is refused (exit {rc})")


@test
def t_scenarios_k():
    for sc, check_fn, what in (
            ("k_sat", lambda txt: "refuted ['H-KW" in txt or "FAILED" in txt, "k_sat: the saturating byte refutes H-KW on the 254 + 4 kicks"),
            ("k_fw2", lambda txt: "FAILED" in txt, "k_fw2: a byte that is 2 whatever the host sent refutes K = 1 on nomisc"),
            ("k5_timeout", lambda txt: "cannot tell" in txt, "k5_timeout: a kick that times out is a result, cannot tell, the stage goes on")):
        w, e, c = staged("k_" + sc, sc)
        rc, o = runner(e, w, "k")
        ok(rc == 0, f"{sc}: the runner finishes (exit {rc})")
        ok(laprec(w, "k", "k5") is not None, f"{sc}: k5 recorded")
        if sc == "k5_timeout":
            ok(laprec(w, "k", "k5")["class"] == "kick-timeout", "k5_timeout: the class is kick-timeout, not a stop")
        rc2, o2 = sh([PY, str(c / "score" / "score_r1.py"), "k", str(w / "home" / "r1ev-out" / "k")], e)
        ok(rc2 == 0 or "REFUSING" in o2, f"{sc}: scored")
        # the scorer refuses unless the freeze verifies: it is the copy's freeze, which holds
        ok("SUMMARY:" in o2 and check_fn(o2), what)


@test
def t_scenarios_t():
    for sc, want in (("t_iter", "H-ITER"), ("t_time", "H-TIME")):
        w, e, c = staged("t_" + sc, sc)
        rc, o = runner(e, w, "t")
        ok(rc == 0, f"{sc}: the runner finishes the 56 jobs (exit {rc})")
        sys.path.insert(0, str(c / "score"))
        for m in [m for m in sys.modules if m in ("score_r1", "r1layout")]:
            sys.modules.pop(m)
        import score_r1
        Sg = score_r1.Stage("t", w / "home" / "r1ev-out" / "t")
        score_r1.score_t(Sg)
        v = Sg.verdicts
        if sc == "t_iter":
            ok(v["T1"] == (False, True) and v["T3"] == (False, True), f"{sc}: the scorer reads H-ITER ({v['T1']}, {v['T3']})")
        else:
            ok(v["T3"] == (True, False) and v["T4"] == (True, False), f"{sc}: the scorer reads H-TIME ({v['T3']}, {v['T4']})")
        sys.path.pop(0)
        for m in [m for m in sys.modules if m in ("score_r1", "r1layout")]:
            sys.modules.pop(m)
    w, e, c = staged("t_dirty", "pre_dirty")
    rc, o = runner(e, w, "t")
    ok(rc == 5 and "reset before the job is not ok" in o and laprec(w, "t", "t0-b8-53") is not None,
       f"pre_dirty: a reset that leaves CR_EVENT_STATUS2 at 0x440 stops the stage before any tool runs; its own reset cannot clear it either: exit {rc}")
    ok(laprec(w, "t", "t0-b8-53")["class"] != "ok" and "tool_out" not in laprec(w, "t", "t0-b8-53"),
       "pre_dirty: the job's record is written (class not ok), no probe ran on a dirty register")


@test
def t_scenarios_d():
    for sc, want in (("h_thresh", "H-THRESH favoured"), ("h_never", "H-NEVER")):
        w, e, c = staged("d_" + sc, sc)
        rc, o = runner(e, w, "d0")
        ok(rc == 0, f"{sc}: d0 runs (exit {rc})")
        rc2, o2 = sh([PY, str(c / "score" / "score_r1.py"), "d0", str(w / "home" / "r1ev-out" / "d0"), "--gates", str(w / "gates"), "--gate"], e)
        ok(rc2 == 0 and "GATE d0 OPEN" in o2, f"{sc}: the d0 controls hold and the gate opens (rc {rc2})")
        sh(["cp", str(w / "gates" / "d0.gate"), str(w / "home" / "r1ev" / "gates" / "d0.gate")])
        rc, o = runner(e, w, "d1")
        ok(rc == 0, f"{sc}: d1 runs (exit {rc})")
        rc2, o2 = sh([PY, str(c / "score" / "score_r1.py"), "d1", str(w / "home" / "r1ev-out" / "d1")], e)
        ok(want in o2, f"{sc}: the summary reads '{want}'")
    w, e, c = staged("d_big4", "d_big4")
    rc, o = runner(e, w, "d0")
    rc2, o2 = sh([PY, str(c / "score" / "score_r1.py"), "d0", str(w / "home" / "r1ev-out" / "d0"), "--gates", str(w / "gates"), "--gate"], e)
    sh(["cp", str(w / "gates" / "d0.gate"), str(w / "home" / "r1ev" / "gates" / "d0.gate")])
    rc, o = runner(e, w, "d1")
    rec = laprec(w, "d1", "d2-0x320")
    ok(rec is not None and rec["page"][16 + 3] > 0 and rec["page"][512 + 8 * 11] == 1,
       "d_big4: slot 3's twelve rungs fill and the drop counter (dword 19) counts the rest")


@test
def t_scorer_refuses_unfrozen():
    w, e, c = staged("unfrozen", "")
    rc, o = runner(e, w, "k")
    (c / "score" / "score_r1.py").write_text((c / "score" / "score_r1.py").read_text() + "\n# changed\n")
    rc2, o2 = sh([PY, str(c / "score" / "score_r1.py"), "k", str(w / "home" / "r1ev-out" / "k")], e)
    ok(rc2 == 3 and "REFUSING" in o2, f"the scorer refuses unless the freeze verifies (rc {rc2})")
    rc3, o3 = session(e, c, "--only", "k")
    ok(rc3 == 20 and "FROZEN FILES CHANGED" in o3, f"the driver refuses a changed frozen file (rc {rc3})")


def main():
    run_tests()
    print(f"\n{len(RAN)} tests, {len(FAIL)} failed" if True else "")
    for f in FAIL:
        print("  FAILED:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
