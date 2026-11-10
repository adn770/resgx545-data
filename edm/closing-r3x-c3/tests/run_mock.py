#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: C3 end to end against a mock laptop.  Nothing touches the laptop.

The real scripts run on a COPY of this directory (so that the pinned tool hash can be the fake tool's and the freeze can be redone
there): run/stage_c3.sh and run/c3.sh with ssh, scp, sudo, sha256sum, python3 and dmesg shims (tests/shims), the laptop runner
run/c3_run.py with the fake fwtask_run (tests/mockfw: a simulated EDM, scenarios by MOCK_SCENARIO), the fake tool
(tests/fake_tool.py), the scorer score/score_c3.py.  Output goes to a temporary directory.

    ../../closing/pixel-faults/.venv/bin/python tests/run_mock.py [-k SUBSTRING]
"""
import hashlib
import importlib
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
R3 = pathlib.Path(__file__).resolve().parent.parent
PY = str(R3.parent.parent / "closing/pixel-faults/.venv/bin/python")
FAIL, RAN = [], []
ONLY = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
BASE = pathlib.Path(tempfile.mkdtemp(prefix="c3mock-"))
STAGES = (R3 / "stages.txt").read_text().split()
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
    dst = BASE / name / "c3"
    shutil.copytree(R3, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "*.pyc", "debug"))
    (dst / "debug").mkdir()
    h = hashlib.sha256((dst / "tests" / "fake_tool.py").read_bytes()).hexdigest()
    (dst / "TOOL.sha256").write_text(f"{h}  /home/jtorra/sgxfive-test-s1b\n")
    rc, o = sh([str(dst / "run" / "freeze_c3.sh"), "freeze"], cwd=str(dst))
    assert rc == 0, o
    return dst


def env_for(name, scenario="", copy=None):
    w = BASE / name
    c = copy or copy_tree(name)
    mock, home, out = w / "mock", w / "home", w / "out"
    for d in (mock / "dbg", home, out):
        d.mkdir(parents=True, exist_ok=True)
    dri = mock / "sysdebug" / "dri"                       # the device's three names, as on the laptop
    (dri / "0").mkdir(parents=True, exist_ok=True)
    for n_, tgt in (("0/sgx", "../../../dbg"), ("128", "0"), ("0000:00:02.0", "0")):
        if not (dri / n_).exists():
            os.symlink(tgt, dri / n_)
    for t in ("sgxfive-test", "sgxfive-test-s1b"):        # the landed gate's tool and the pinned health tool
        p = home / t
        p.write_text((c / "tests" / "fake_tool.py").read_text())
        p.chmod(0o755)
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo"):
        (mock / "dbg" / f).write_text("")
    (mock / "dbg" / "hold_recovery").write_text("N")
    (mock / "dbg" / "render_pb_pages").write_text("0x00000422")
    (mock / "srcv").write_text("MOCKSRCV\n")
    (mock / "kmsg").write_text("")
    (mock / "uptime").write_text("123.45 456.78\n")
    (mock / "bootid").write_text("00000000-mock-boot-id\n")
    e = dict(os.environ)
    e.update({"PATH": f"{c / 'tests' / 'shims'}:{os.environ['PATH']}", "MOCK_DIR": str(mock), "MOCK_HOME": str(home),
              "MOCK_PY": PY, "MOCK_SCENARIO": scenario, "R3_MOCK_ROOT": "1", "R3_UPTIME": str(mock / "uptime"), "R3_BOOT_ID": str(mock / "bootid"), "R3_FWTASK_DIR": str(c / "tests" / "mockfw"),
              "R3_KMSG": str(mock / "kmsg"), "R3_SRCV_PATH": str(mock / "srcv"), "R3_DEBUGFS": str(mock / "dbg"),
              "R3_OUT": str(out), "PY": PY, "PYTHON": PY, "SGX_LOCAL_ENV": "/nonexistent", "SGX_TARGET_HOST": "mock@laptop",
              "PYTHONDONTWRITEBYTECODE": "1"})
    return w, e, c


def stage(e, c):
    return sh(["bash", str(c / "run" / "stage_c3.sh")], e)


def session(e, c, *args):
    return sh(["bash", str(c / "run" / "c3.sh")] + list(args), e)


def runner(e, w, st, extra=()):
    return sh([PY, str(w / "home" / "r3xc3" / "run" / "c3_run.py"), st, "--tool", str(w / "home" / "sgxfive-test-s1b"),
               "--bins", str(w / "home" / "r3xc3" / "bins"), "--out", str(w / "home" / "r3xc3-out")] + list(extra), e)


def laprec(w, st, job):
    p = w / "home" / "r3xc3-out" / st / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def stage_json(w, st):
    return json.loads((w / "home" / "r3xc3-out" / st / "stage.json").read_text())


def trace(w):
    p = w / "mock" / "trace"
    return p.read_text().splitlines() if p.exists() else []


def resets(w):
    p = w / "mock" / "reset_count"
    return int(p.read_text()) if p.exists() else 0


def score_txt(w, st):
    p = w / "out" / f"score-{st}.txt"
    return p.read_text() if p.exists() else ""


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


def staged(name, scenario=""):
    w, e, c = env_for(name, scenario)
    rc, o = stage(e, c)
    assert rc == 0, o
    return w, e, c


# ---- static -----------------------------------------------------------------------------------------------------------
@test
def t_freeze_and_guard():
    rc, o = sh([str(R3 / "run" / "freeze_c3.sh"), "verify"])
    ok(rc == 0 and "files verified" in o, f"the frozen files of this directory verify ({o.strip().splitlines()[-1] if o.strip() else ''})")
    rc, o = sh([str(R3 / "run" / "guard_c3.sh")], dict(os.environ, PYTHON=PY))
    ok(rc == 0 and "guard: clean" in o, f"guard_c3.sh is clean ({o.strip()[-60:]})")


@test
def t_guard_catches():
    c = copy_tree("guard")
    e = dict(os.environ, PYTHON=PY)

    def guard_with(path, old, new, label):
        p = c / path
        orig = p.read_text()
        p.write_text(orig.replace(old, new) if old else orig + new)
        rc, o = sh([str(c / "run" / "guard_c3.sh")], e)
        p.write_text(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")
    guard_with("run/c3.sh", "", "\nset -f\n", "set -f in a script (it breaks the globs that keep dumps)")
    guard_with("run/c3.sh", "", "\nwhile true; do sleep 1; done\n", "a wait loop in a shell script")
    guard_with("run/c3.sh", "", "\ncat /sys/kernel/debug/dri/0/sgx/regs\n", "unprivileged debugfs access")
    guard_with("run/c3.sh", "", "\nreboot\n", "a reboot")
    guard_with("run/c3.sh", "", "\necho 1 > $D/kpoke\n", "a kpoke write")
    guard_with("run/c3.sh", "", "\necho $R3_KMSG\n", "a test-only override in a laptop-driving script")
    guard_with("run/c3_run.py", "os.open(KMSG, os.O_WRONLY | os.O_APPEND)", "open(KMSG, 'a')", "the kernel log opened in Python's append mode")
    guard_with("run/c3_run.py", "\ndef sha(p):", "\nwhile False:\n    pass\n\n\ndef sha(p):", "a while loop in the runner")
    guard_with("run/c3_run.py", "captured(FR.cmd_arm, a)", "captured(FR.cmd_arm, a)\n        FR.kreg_write(0x0814, 1)", "a register write in the runner")
    guard_with("run/c3_run.py", "captured(FR.cmd_reset)\n        g = captured", "captured(FR.cmd_reset)\n        FR.wait_state(None, 1)\n        g = captured", "a polling command in the runner")
    guard_with("run/c3_run.py", "        self.armed = False\n        return bool", "        FR.wr(\"render_pb_pages\", \"0x30\")\n        self.armed = False\n        return bool", "a debugfs write off the allow-list")
    guard_with("run/c3_run.py", "        self.armed = False\n        return bool", "        FR.sh(\"echo 1 > /tmp/x\")\n        self.armed = False\n        return bool", "a shell command off the allow-list")
    guard_with("asm/start.s", "", "\n        mov sa100, r4\n", "an sa write in start.s (the blob no longer matches)")
    guard_with("asm/start.s", "", "\n        str #517, r4\n", "a str in the task source")
    guard_with("asm/start.s", "", "\n        ldr r1, #7, drc0\n", "an ldr of another register in the task source")
    guard_with("tables/c3.json", '"arm": "slots=0x1 entry=0"', '"arm": "slots=0x1 entry=0 trc=3"', "a trc in the arm line")
    guard_with("tables/c3.json", '"stop_budget": 0', '"stop_budget": 1', "a stop budget of 1")
    guard_with("tables/c3.json", '"perturb": "reset"', '"perturb": "reload"', "a perturbation that is not its row's")


@test
def t_pick_debugfs_and_kmsg():
    old = dict(os.environ)
    kf = BASE / "kmsg_flags"
    kf.write_text("older\n")
    os.environ.update({"MOCK_DIR": str(BASE), "R3_FWTASK_DIR": str(R3 / "tests" / "mockfw"), "R3_KMSG": str(kf)})
    try:
        sys.modules.pop("c3_run", None)
        sys.path.insert(0, str(R3 / "run"))
        c3 = importlib.import_module("c3_run")
        import glob as g
        cands = ["/sys/kernel/debug/dri/0/sgx", "/sys/kernel/debug/dri/0000:00:02.0/sgx", "/sys/kernel/debug/dri/128/sgx"]
        have = {"all": set(cands), "no0": set(cands[1:]), "only128": {cands[2]}, "none": set()}
        real_glob, real_exists = g.glob, os.path.exists
        out = {}
        for k, files in have.items():
            g.glob = lambda pat, files=files: sorted(files) if "dri/*/sgx" in pat else real_glob(pat)
            os.path.exists = lambda p, files=files: (p.rsplit("/", 1)[0] in files) if p.endswith("/own_res") else real_exists(p)
            c3.glob.glob = g.glob
            out[k] = c3.pick_debugfs()
        g.glob, os.path.exists = real_glob, real_exists
        ok(out["all"][0] == cands[0] and len(out["all"][1]) == 3, "pick_debugfs: three names, dri/0 preferred, all three recorded")
        ok(out["no0"][0] == cands[1], "pick_debugfs: without dri/0 the first sorted name that holds own_res")
        ok(out["only128"][0] == cands[2] and out["none"][0] is None, "pick_debugfs: one name, or none (a preflight stop)")
        calls = []
        real = os.open
        c3.os.open = lambda p, fl, *a: (calls.append((p, fl)), real(p, fl, *a))[1]
        run = type("A", (), {"stage": "c3", "tool": "t", "bins": "b", "out": str(BASE / "o")})
        rn = c3.Runner(run)
        rn.mark("hello")
        c3.os.open = real
        ok(calls == [(str(kf), os.O_WRONLY | os.O_APPEND)], f"Runner.mark opens the kernel log with O_WRONLY | O_APPEND ({calls})")
        ok(kf.read_text().splitlines()[-1].startswith("resgx545 r3 hello ") and kf.read_text().startswith("older\n"),
           "Runner.mark appends one line and truncates nothing")
    finally:
        os.environ.clear()
        os.environ.update(old)
        sys.modules.pop("c3_run", None)


# ---- the session ------------------------------------------------------------------------------------------------------
@test
def t_full_session():
    w, e, c = env_for("full")
    rc, o = stage(e, c)
    ok(rc == 0 and "staged: ~/r3xc3" in o and "tool ok:" in o, f"staging into ~/r3xc3 (rc {rc})")
    ok("debugfs " in o and o.count("debugfs ") >= 3, "staging found the debugfs directories through dri/*/sgx (three names)")
    t0 = time.time()
    rc, o = session(e, c)
    el = time.time() - t0
    ok(rc == 0 and o.rstrip().endswith("C3 done"), f"the whole C3 session passes on the default mock (rc {rc}, {el:.0f} s)")
    if rc != 0:
        print(o[-1500:])
    sc = score_txt(w, "c3")
    ok("SUMMARY:" in sc, "one SUMMARY line")
    ok("c3: kept 13 of 13 read jobs, stops 0" in sc and "controls failed none" in sc, "13 of 13 jobs kept, no stop, no failed control")
    ok("H-KEEP supported" in sc and "H-SET refuted" in sc, "the default world: H-KEEP supported for p2/p3")
    ok("refuted" in sc and "H-ALL" in sc, "the default world refutes H-ALL (r20/r21 survive nothing)")
    t = json.loads((c / "tables" / "c3.json").read_text())
    km = (w / "mock" / "kmsg").read_text()
    ok(km.count("resgx545 r3 case ") == 13 and km.count("resgx545 r3 class ") == 13, "one case marker and one class marker a job (13)")
    sj = stage_json(w, "c3")
    ok(sj["exit"] == 0 and sj["stops"] == 0 and sj["jobs_run"] == [j["name"] for j in t["jobs"]] and set(sj["classes"].values()) == {"ok"},
       "stage.json: exit 0, no stop, the 13 jobs in the frozen order, all ok")
    sudo = (w / "mock" / "sudo.log").read_text().splitlines()
    runs = [x for x in sudo if "c3_run.py" in x]
    ok(len(runs) == 1 and runs[0].startswith("sudo python3 ") and "/r3xc3/run/" in runs[0], f"the stage ran from ~/r3xc3 under sudo -n python3 ({len(runs)} runner call)")
    health = [x for x in sudo if "/sys/kernel/debug" in x]
    ok(len(health) >= 1 and all(x.startswith("sudo ") for x in health), f"every debugfs access of the scripts went through sudo -n ({len(health)} calls)")
    tr = trace(w)
    wrs = sorted({x.split()[2] for x in tr if " wr " in x})
    ok(set(wrs) <= {"own_code", "own_arm", "load", "boot", "reset"}, f"the runner wrote only allow-listed debugfs files: {wrs}")
    ok((w / "mock" / "dbg" / "hold_recovery").read_text().strip() == "N" and int((w / "mock" / "dbg" / "render_pb_pages").read_text(), 0) == 0x422,
       "no knob was touched")
    arms = [x for x in tr if x.split(" ", 1)[1].startswith("arm ")]
    ok(len(arms) == 1 + 3 + 3, f"one arm at the start, one a reload job (3), one a reset job (3): {len(arms)} arms")
    nres = len([x for x in tr if x.endswith(" reset")])
    ok(nres == 3 + 1, f"three reset jobs and the end reset: {nres} resets")
    nf = len([x for x in tr if " fill " in x or x.split(" ", 1)[1].startswith("fill ")])
    ok(nf == 3, f"one client fill a fill job (3), none elsewhere ({nf})")
    last = [i for i, x in enumerate(tr) if x.endswith(" reset")][-1]
    ok(tr[-1].endswith(" gate") or last > len(tr) - 6, "the session ends with the reset and the gate")
    env = json.loads((w / "home" / "r3xc3-out" / "c3" / "env.json").read_text())
    ok(env["srcversion_loaded"] == env["srcversion_installed"] and env["uptime"].startswith("123.45") and env["boot_id"].startswith("0000"),
       "env.json: srcversion loaded = installed, the uptime and the boot id of the preflight are kept")
    r = laprec(w, "c3", "r2")
    ok(r["rdB"]["ran"] and r["perturb"]["kind"] == "reset" and r["perturb"]["reset"]["ok"] and r["perturb"]["arm"]["ok"],
       "an R job: the reset, then the arm, then the host's reader (rdB)")
    ok(laprec(w, "c3", "s0")["writer"]["issued"] is False, "S0 has no writer")
    rc, o = stage(e, c)
    ok(rc == 0, "restaging after the session works")


def one(name, scenario, stage_only=True):
    w, e, c = env_for(name, scenario)
    rc, o = stage(e, c)
    assert rc == 0, o
    rc, o = session(e, c)
    return w, e, c, rc, o


@test
def t_worlds():
    w, e, c, rc, o = one("w_all", "all")
    sc = score_txt(w, "c3")
    ok(rc == 0 and "H-KEEP, its r20/r21 row only (both kept after a reload or a reset): FAILED in 6 of 6" in sc and "H-ALL, its r20/r21 row only (both kept after a reload or a reset): held in all 6" in sc,
       f"the world where r20/r21 survive: H-ALL held, H-KEEP refuted (rc {rc})")
    w, e, c, rc, o = one("w_set", "set")
    sc = score_txt(w, "c3")
    ok(rc == 0 and "H-SET supported" in sc and "H-KEEP refuted" in sc, f"the world with p2 = p3 = 1 at the next entry: H-SET supported (rc {rc})")
    w, e, c, rc, o = one("w_s0", "s0_zero")
    ok(rc == 0 and "not informative" in score_txt(w, "c3"), "sa100 = sa127 = 0 at S0: the scorer says their persistence is not informative")


# ---- stops --------------------------------------------------------------------------------------------------------------
@test
def t_stop_ends_the_stage():
    w, e, c = staged("stop_f2", "stop_f2")
    rc, o = session(e, c)
    ok(rc == 8, f"a tick stop (budget 0) ends the stage: exit 8 (rc {rc})")
    sj = stage_json(w, "c3")
    ok(sj["exit"] == 8 and sj["stops"] == 1 and sj["classes"]["f2"] == "stop" and "f3" not in sj["jobs_run"] and "l1" not in sj["jobs_run"],
       f"the stage ended at f2; f3 and the reload and reset jobs did not run ({sj['jobs_run']})")
    rec = laprec(w, "c3", "f2")
    ok(rec.get("sig") and len(rec["sig"]["samples"]) == 2 and rec["sig"]["samples"][0]["regs"].get("0x8") == 0xccfa0,
       "the stop record holds two register samples (the signature) taken before the reset")
    tr = trace(w)
    ids = [i for i, x in enumerate(tr) if x.endswith(" reset")]
    first_dump = next(i for i, x in enumerate(tr) if x.endswith(" dump"))
    ok(ids and first_dump < [i for i in ids if i > first_dump][0], "the signature dump was taken BEFORE the reset that follows the stop")
    ok(resets(w) >= 1 and tr[-1].endswith(" gate"), "reset and gate were done after the stop")
    ok("stops 1 ['f2']" in score_txt(w, "c3") and "[f2: busy (E537)]" in score_txt(w, "c3"), "the scorer reports the stop and its E537 match")
    ok("a tick stop ends the stage" in o or "stage c3 exited 8" in o or "STOP" in o, "the driver stopped the session")
    w, e, c = staged("stop_pend", "stop_f2,sig_pending")
    rc, o = session(e, c)
    ok("[f2: idle-pending]" in score_txt(w, "c3"), "an idle-pending stop is classed idle-pending")
    w, e, c = staged("stop_l1", "stop_l1,sig_empty")
    rc, o = session(e, c)
    ok(rc == 8 and "[l1: idle-empty]" in score_txt(w, "c3"), f"a stop in an L job (rc {rc}), classed idle-empty")


@test
def t_stop_after_a_perturbation():
    w, e, c = staged("stop_reload", "stop_reload")
    rc, o = session(e, c)
    ok(rc == 4 and resets(w) >= 1, f"a reload that leaves the tick stopped: the arm is not ok, exit 4, reset done (rc {rc})")
    ok(stage_json(w, "c3")["exit"] == 4 and "gate" in trace(w)[-1], "the stage ended with reset and gate")


@test
def t_reader_and_void():
    w, e, c = staged("nr", "noreader")
    rc, o = session(e, c)
    ok(rc == 0, f"the reader never runs but the tick is kept: not a stop, the stage finishes (rc {rc})")
    ok(set(stage_json(w, "c3")["classes"].values()) <= {"noreader", "ok"} and stage_json(w, "c3")["classes"]["n1"] == "noreader" and "cannot tell" in score_txt(w, "c3"),
       "noreader jobs are cannot-tell")
    w, e, c = staged("wf", "writefail")
    rc, o = session(e, c)
    ok("n1: NODATA (the sa63 read-back" in score_txt(w, "c3"), "a write that did not take is void")


@test
def t_cleanup_stops():
    w, e, c = staged("fatal", "fatal@f1")
    rc, o = session(e, c)
    ok(rc == 3 and resets(w) == 0, f"a watchdog line stops all laptop work: exit 3, no reset (rc {rc}, resets {resets(w)})")
    w, e, c = staged("armfail", "armfail")
    rc, o = session(e, c)
    ok(rc == 4 and resets(w) >= 1, f"an arm that is not healthy: exit 4, reset done (rc {rc})")
    w, e, c = staged("gatefail", "gatefail")
    rc, o = session(e, c)
    ok(rc == 5, f"a gate that is not exact after the stage: exit 5 (rc {rc})")
    w, e, c = staged("unhealthy", "unhealthy")
    rc, o = session(e, c)
    ok(rc in (4, 5), f"an unhealthy GPU after a job stops (rc {rc})")
    w, e, c = staged("boom", "boom@n2")
    rc, o = session(e, c)
    ok(rc in (4, 5) and (w / "home/r3xc3-out/c3/n2.json").exists(), f"an exception in a job still writes its record (rc {rc})")
    w, e, c = staged("badlog", "badlog@l2")
    rc, o = session(e, c)
    ok(rc in (4, 5) and laprec(w, "c3", "l2")["class"] == "unhealthy", f"a hung line in a job's log: unhealthy, the stage stops (rc {rc})")
    w, e, c = staged("fillfail", "fillfail")
    rc, o = session(e, c)
    ok(rc == 4 and resets(w) >= 1 and "f1" in stage_json(w, "c3")["jobs_run"], f"a client fill that is not exact: exit 4, reset done (rc {rc})")
    w, e, c = staged("latebad", "latebad")
    rc, o = session(e, c)
    ok(rc == 38, f"a hung line in the stage's kernel log after the run stops the session (rc {rc})")
    w, e, c = staged("toolfail", "tool_fail")
    rc, o = session(e, c)
    ok(rc != 0, f"the health tool failing ends the session (rc {rc})")


@test
def t_preflight_refusals():
    w, e, c = staged("pre")
    (w / "mock" / "srcv").write_text("OTHERSRCV\n")
    rc, o = runner(e, w, "c3")
    ok(rc == 1 and "the loaded module is not the installed one" in o, f"srcversion loaded != installed: exit 1 (rc {rc})")
    (w / "mock" / "srcv").write_text("MOCKSRCV\n")
    tool = w / "home" / "sgxfive-test-s1b"
    tool.write_text(tool.read_text() + "\n# changed\n")
    rc, o = runner(e, w, "c3")
    ok(rc == 1 and "pinned" in o, f"a tool that is not the pinned one: exit 1 (rc {rc})")
    tool.write_text((c / "tests" / "fake_tool.py").read_text())
    dbg = w / "mock" / "dbg" / "xfer_sync"
    (w / "mock" / "dbg" / "reset").rename(w / "mock" / "dbg" / "reset.gone")
    rc, o = runner(e, w, "c3")
    ok(rc == 1 and "no debugfs reset" in o, f"a debugfs file the stage needs is missing: exit 1 (rc {rc})")
    (w / "mock" / "dbg" / "reset.gone").rename(w / "mock" / "dbg" / "reset")
    tb = w / "home" / "r3xc3" / "tables" / "c3.json"
    orig = tb.read_text()
    tb.write_text(orig + " ")
    rc, o = runner(e, w, "c3")
    ok(rc == 1 and "is not the frozen file" in o, f"a table that is not the frozen file: exit 1 (rc {rc})")
    lp = w / "home" / "r3xc3" / "LAPTOP.sha256"

    def rehash(t):
        tb.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
        h = hashlib.sha256(tb.read_bytes()).hexdigest()
        lp.write_text("\n".join(f"{h}  tables/c3.json" if x.endswith("tables/c3.json") else x for x in lp.read_text().splitlines()) + "\n")
    t = json.loads(orig)
    t["jobs"][3]["perturb"] = "fill"
    rehash(t)
    rc, o = runner(e, w, "c3")
    ok(rc == 7 and "is not row" in o, f"a job whose perturbation is not its row's: exit 7 (rc {rc})")
    t = json.loads(orig)
    t["jobs"].append(dict(t["jobs"][1], name="x7", row="A7"))
    rehash(t)
    rc, o = runner(e, w, "c3")
    ok(rc == 7 and "approved rows" in o, f"a table with a row from another session: exit 7 (rc {rc})")
    t = json.loads(orig)
    t["stop_budget"] = 1
    rehash(t)
    rc, o = runner(e, w, "c3")
    ok(rc == 7 and "stop budget" in o, f"a stop budget of 1: exit 7 (rc {rc})")
    ok(resets(w) == 0, "no preflight refusal touched the GPU")
    rc, o = session(e, c)
    ok(rc == 21, f"a laptop whose LAPTOP.sha256 is not this freeze's: the driver refuses (rc {rc})")


@test
def t_laptop_limits_in_trace():
    """Every write the runner does through the mock, over a whole default session: no kreg, no clock register, no knob."""
    w, e, c = staged("limits")
    rc, o = session(e, c)
    tr = trace(w)
    bad = [x for x in tr if re.search(r" wr (kreg|kregnow|kpoke|alias_skip|trc_hazard|render_pb_pages|hold_recovery)", x)]
    ok(rc == 0 and not bad, f"no kreg, kpoke, knob or trc write in the whole trace ({len(tr)} lines)")
    arms = [x for x in tr if " wr own_arm " in x and not x.endswith(" wr own_arm 0")]
    ok(arms and all(x.endswith(" wr own_arm slots=0x1 entry=0") for x in arms), f"every arm line is the allow-listed one ({sorted({x.split(' wr ')[1] for x in arms})})")
    codes = [x for x in tr if " wr own_code " in x]
    ok(len(codes) == 7, f"the blob is written once an arm (7)")


def main():
    run_tests()
    print(f"\n{len(RAN)} tests, {len(FAIL)} failed" if FAIL or RAN else "no tests")
    if FAIL:
        for f in FAIL:
            print("FAILED:", f)
    else:
        shutil.rmtree(BASE, ignore_errors=True)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
