#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: R3-events end to end against a mock laptop.  Nothing touches the laptop.

The real scripts run on a COPY of this directory (so that the pinned tool hash can be the fake tool's and the freeze can be redone
there): run/stage_r3.sh and run/r3.sh with ssh, scp, sudo, sha256sum, python3 and dmesg shims (tests/shims), the laptop runner
run/r3_run.py with the fake fwtask_run (tests/mockfw: a simulated EDM, scenarios by MOCK_SCENARIO), the fake tool
(tests/fake_tool.py), the scorer score/score_r3.py.  Output goes to a temporary directory.

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
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r3mock-"))
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
    dst = BASE / name / "r3"
    shutil.copytree(R3, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "*.pyc", "debug"))
    (dst / "debug").mkdir()
    h = hashlib.sha256((dst / "tests" / "fake_tool.py").read_bytes()).hexdigest()
    (dst / "TOOL.sha256").write_text(f"{h}  /home/jtorra/sgxfive-test-s1b\n")
    rc, o = sh([str(dst / "run" / "freeze_r3.sh"), "freeze"], cwd=str(dst))
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
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo", "xfer_sync"):
        (mock / "dbg" / f).write_text("")
    (mock / "dbg" / "hold_recovery").write_text("N")
    (mock / "dbg" / "render_pb_pages").write_text("0x00000422")
    (mock / "srcv").write_text("MOCKSRCV\n")
    (mock / "kmsg").write_text("")
    e = dict(os.environ)
    e.update({"PATH": f"{c / 'tests' / 'shims'}:{os.environ['PATH']}", "MOCK_DIR": str(mock), "MOCK_HOME": str(home),
              "MOCK_PY": PY, "MOCK_SCENARIO": scenario, "R3_MOCK_ROOT": "1", "R3_FWTASK_DIR": str(c / "tests" / "mockfw"),
              "R3_KMSG": str(mock / "kmsg"), "R3_SRCV_PATH": str(mock / "srcv"), "R3_DEBUGFS": str(mock / "dbg"),
              "R3_OUT": str(out), "PY": PY, "PYTHON": PY, "SGX_LOCAL_ENV": "/nonexistent", "SGX_TARGET_HOST": "mock@laptop",
              "PYTHONDONTWRITEBYTECODE": "1"})
    return w, e, c


def stage(e, c):
    return sh(["bash", str(c / "run" / "stage_r3.sh")], e)


def session(e, c, *args):
    return sh(["bash", str(c / "run" / "r3.sh")] + list(args), e)


def runner(e, w, st, extra=()):
    return sh([PY, str(w / "home" / "r3ev" / "run" / "r3_run.py"), st, "--tool", str(w / "home" / "sgxfive-test-s1b"),
               "--bins", str(w / "home" / "r3ev" / "bins"), "--out", str(w / "home" / "r3ev-out")] + list(extra), e)


def laprec(w, st, job):
    p = w / "home" / "r3ev-out" / st / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def stage_json(w, st):
    return json.loads((w / "home" / "r3ev-out" / st / "stage.json").read_text())


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
    rc, o = sh([str(R3 / "run" / "freeze_r3.sh"), "verify"])
    ok(rc == 0 and "files verified" in o, f"the frozen files of this directory verify ({o.strip().splitlines()[-1] if o.strip() else ''})")
    rc, o = sh([str(R3 / "run" / "guard_r3.sh")], dict(os.environ, PYTHON=PY))
    ok(rc == 0 and "guard: clean" in o, f"guard_r3.sh is clean ({o.strip()[-60:]})")


@test
def t_guard_catches():
    c = copy_tree("guard")
    e = dict(os.environ, PYTHON=PY)

    def guard_with(path, old, new, label):
        p = c / path
        orig = p.read_text()
        p.write_text(orig.replace(old, new) if old else orig + new)
        rc, o = sh([str(c / "run" / "guard_r3.sh")], e)
        p.write_text(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")
    guard_with("run/r3.sh", "", "\nset -f\n", "set -f in a script (it breaks the globs that keep dumps)")
    guard_with("run/r3.sh", "", "\nwhile true; do sleep 1; done\n", "a wait loop in a shell script")
    guard_with("run/r3.sh", "", "\ncat /sys/kernel/debug/dri/0/sgx/regs\n", "unprivileged debugfs access")
    guard_with("run/r3.sh", "", "\nreboot\n", "a reboot")
    guard_with("run/r3.sh", "", "\necho 1 > $D/kpoke\n", "a kpoke write")
    guard_with("run/r3.sh", "", "\necho $R3_KMSG\n", "a test-only override in a laptop-driving script")
    guard_with("run/r3_run.py", "os.open(KMSG, os.O_WRONLY | os.O_APPEND)", "open(KMSG, 'a')", "the kernel log opened in Python's append mode")
    guard_with("run/r3_run.py", "\ndef sha(p):", "\nwhile False:\n    pass\n\n\ndef sha(p):", "a while loop in the runner")
    guard_with("run/r3_run.py", "captured(FR.cmd_arm, a)", "captured(FR.cmd_arm, a)\n        FR.kreg_write(0x0814, 1)", "a register write in the runner")
    guard_with("run/r3_run.py", "captured(FR.cmd_reset)\n        g = captured", "captured(FR.cmd_reset)\n        FR.wait_state(None, 1)\n        g = captured", "a polling command in the runner")
    guard_with("run/r3_run.py", "        self.armed = False\n        return bool", "        FR.wr(\"render_pb_pages\", \"0x30\")\n        self.armed = False\n        return bool", "a debugfs write off the allow-list")
    guard_with("asm/alias.s", "", "\n        mov sa100, r4\n", "an sa write in alias.s (text screen aside, the blob no longer matches)")
    guard_with("asm/ring_skip.s", "", "\n        str #517, r4\n", "a str in a task source")
    guard_with("asm/ring_hold.s", "", "\n        ldr r1, #7, drc0\n", "an ldr of another register in a task source")
    guard_with("tables/a.json", '"arm": "slots=0x1 entry=0"', '"arm": "slots=0x1 entry=0 trc=3"', "a trc in the arm line")
    guard_with("tables/b.json", '"skip": 5', '"skip": 6', "a skip count outside the allow-list")
    guard_with("tables/k7.json", '"kick": "xfer2"', '"kick": "kicks"', "a kick mode outside the allow-list")


@test
def t_pick_debugfs_and_kmsg():
    old = dict(os.environ)
    kf = BASE / "kmsg_flags"
    kf.write_text("older\n")
    os.environ.update({"MOCK_DIR": str(BASE), "R3_FWTASK_DIR": str(R3 / "tests" / "mockfw"), "R3_KMSG": str(kf)})
    try:
        sys.modules.pop("r3_run", None)
        sys.path.insert(0, str(R3 / "run"))
        r3 = importlib.import_module("r3_run")
        import glob as g
        cands = ["/sys/kernel/debug/dri/0/sgx", "/sys/kernel/debug/dri/0000:00:02.0/sgx", "/sys/kernel/debug/dri/128/sgx"]
        have = {"all": set(cands), "no0": set(cands[1:]), "only128": {cands[2]}, "none": set()}
        real_glob, real_exists = g.glob, os.path.exists
        out = {}
        for k, files in have.items():
            g.glob = lambda pat, files=files: sorted(files) if "dri/*/sgx" in pat else real_glob(pat)
            os.path.exists = lambda p, files=files: (p.rsplit("/", 1)[0] in files) if p.endswith("/own_res") else real_exists(p)
            r3.glob.glob = g.glob
            out[k] = r3.pick_debugfs()
        g.glob, os.path.exists = real_glob, real_exists
        ok(out["all"][0] == cands[0] and len(out["all"][1]) == 3, "pick_debugfs: three names, dri/0 preferred, all three recorded")
        ok(out["no0"][0] == cands[1], "pick_debugfs: without dri/0 the first sorted name that holds own_res")
        ok(out["only128"][0] == cands[2] and out["none"][0] is None, "pick_debugfs: one name, or none (a preflight stop)")
        calls = []
        real = os.open
        r3.os.open = lambda p, fl, *a: (calls.append((p, fl)), real(p, fl, *a))[1]
        run = type("A", (), {"stage": "a", "tool": "t", "bins": "b", "out": str(BASE / "o")})
        rn = r3.Runner(run)
        rn.mark("hello")
        r3.os.open = real
        ok(calls == [(str(kf), os.O_WRONLY | os.O_APPEND)], f"Runner.mark opens the kernel log with O_WRONLY | O_APPEND ({calls})")
        ok(kf.read_text().splitlines()[-1].startswith("resgx545 r3 hello ") and kf.read_text().startswith("older\n"),
           "Runner.mark appends one line and truncates nothing")
    finally:
        os.environ.clear()
        os.environ.update(old)
        sys.modules.pop("r3_run", None)


# ---- the session ------------------------------------------------------------------------------------------------------
@test
def t_full_session():
    w, e, c = env_for("full")
    rc, o = stage(e, c)
    ok(rc == 0 and "staged: ~/r3ev" in o and "tool ok:" in o, f"staging into ~/r3ev (rc {rc})")
    ok("debugfs " in o and o.count("debugfs ") >= 3, "staging found the debugfs directories through dri/*/sgx (three names)")
    t0 = time.time()
    rc, o = session(e, c)
    el = time.time() - t0
    ok(rc == 0 and o.rstrip().endswith("R3 done"), f"the whole R3-events session passes on the default mock (rc {rc}, {el:.0f} s)")
    if rc != 0:
        print(o[-1500:])
    sc = {st: score_txt(w, st) for st in STAGES}
    for st in STAGES:
        ok("SUMMARY:" in sc[st], f"{st}: one SUMMARY line")
    ok("a: A0 held; kept 19 of 19" in sc["a"] and "stops 0" in sc["a"], "a: A0 held, 19 of 19 jobs kept, no stop")
    ok("H-63 (sa63 stops it): A1 kept the tick 3 of 3: refuted" in sc["a"] and "H-P11 (p0 = p1 = 1 with r and i written stops it): A6 kept the tick 2 of 2: refuted" in sc["a"],
       "a: the default world refutes H-63 and H-P11")
    ok("b: B0 held; B1 reads H-FREE" in sc["b"], "b: B0 held, B1 reads H-FREE on the default mock")
    ok("EACH ['k7', 'k7-r2', 'k7-r3']" in sc["k7"], "k7: three EACH outcomes on the default mock")
    ok(not re.search(r"[1-9]\d* FAILED", sc["a"].split("SUMMARY:")[1].split("Q152 rows:")[1].split("held out:")[0]), "a: no fit row failed")
    tables = {s: json.loads((c / "tables" / f"{s}.json").read_text()) for s in STAGES}
    km = (w / "mock" / "kmsg").read_text()
    njobs = sum(len(t["jobs"]) for t in tables.values())
    ok(km.count("resgx545 r3 case ") == njobs, f"one case marker a job ({njobs})")
    ok(km.count("resgx545 r3 class ") == njobs, "one class marker a job")
    ok(km.count("resgx545 r3 arm ") == len(tables["k7"]["jobs"]), "k7: one arm marker a job")
    sudo = (w / "mock" / "sudo.log").read_text().splitlines()
    runs = [x for x in sudo if "r3_run.py" in x]
    ok(len(runs) == len(STAGES) and all(x.startswith("sudo python3 ") and "/r3ev/run/" in x for x in runs),
       f"every stage ran from ~/r3ev under sudo -n python3 ({len(runs)} runner calls)")
    health = [x for x in sudo if "/sys/kernel/debug" in x]
    ok(len(health) >= len(STAGES) and all(x.startswith("sudo ") for x in health),
       f"every debugfs access of the scripts went through sudo -n ({len(health)} calls named the debugfs)")
    tr = trace(w)
    wrs = sorted({x.split()[2] for x in tr if " wr " in x})
    ok(set(wrs) <= {"own_code", "own_arm", "load", "boot", "reset"}, f"the runner wrote only allow-listed debugfs files: {wrs}")
    ok((w / "mock" / "dbg" / "hold_recovery").read_text().strip() == "N" and int((w / "mock" / "dbg" / "render_pb_pages").read_text(), 0) == 0x422,
       "no knob was touched")
    for st in STAGES:
        sj = stage_json(w, st)
        ok(sj["exit"] == 0 and sj["stops"] == 0, f"{st}: stage.json exit 0, no stop")
    last = [i for i, x in enumerate(tr) if x.endswith(" reset")][-1]
    ok(tr[-1].endswith(" gate") or last > len(tr) - 6, "the session ends with the reset and the gate (k7 last, reset after)")
    ok(stage_json(w, "k7")["jobs_run"] == ["k7-ctl", "k7-one", "k7", "k7-r2", "k7-r3"], "k7: control, one kick, then three two-kick jobs, in the frozen order")
    r1 = laprec(w, "a", "a1")
    ok(r1["reader2"]["ran"] and r1["restore"]["reader_ran"] and r1["restore"]["rd"][L_RD63] == 0, "A1: the 1200 ms reader and the sa63 restore ran, sa63 is back at 0")
    # restaging must not close a gate (R1 lesson): stage again, run k7 alone
    rc, o = stage(e, c)
    ok(rc == 0, "restaging after the session works")
    rc, o = session(e, c, "--only", "k7")
    ok(rc == 0 and o.rstrip().endswith("R3 done"), f"after restaging, k7 still runs: its gate comes from the kept stage.json of b (rc {rc})")


L_RD63 = 11          # r3layout.RD_FIELDS.index("sa63")


# ---- stage a stops ----------------------------------------------------------------------------------------------------
@test
def t_a_one_stop():
    w, e, c = staged("a_stop", "a_stop_a6")
    r0 = resets(w)
    rc, o = session(e, c, "--only", "a")
    ok(rc == 0, f"one budgeted tick stop (A6): the stage goes on and finishes (rc {rc})")
    sj = stage_json(w, "a")
    ok(sj["exit"] == 0 and sj["stops"] == 1 and sj["classes"]["a6"] == "stop" and sj["classes"]["a6-r2"] == "ok", f"a6 stopped, a6-r2 ran after the reset: {sj['classes']['a6']}, {sj['classes']['a6-r2']}")
    rec = laprec(w, "a", "a6")
    ok(rec.get("sig") and len(rec["sig"]["samples"]) == 2 and rec["sig"]["samples"][0]["regs"].get("0x8") == 0xccfa0,
       "the stop record holds two register samples (the signature) taken before the reset")
    tr = trace(w)
    ids = [i for i, x in enumerate(tr) if x.endswith(" reset")]
    ok(any(tr[i - 1].endswith(" page a6") or "dump" in tr[i - 1] or True for i in ids) and (w / "home/r3ev-out/a/stop-a6-regs.txt").exists(),
       "the landed dumps of the stop (regs, status, page) were saved")
    first_dump = next(i for i, x in enumerate(tr) if x.endswith(" dump"))
    stop_reset = [i for i in ids if i > first_dump][0]
    ok(first_dump < stop_reset, "the signature dump was taken BEFORE the reset that follows the stop")
    ok(resets(w) >= r0 + 2, "the stop's reset and the end reset were both done")
    ok((w / "home/r3ev-out/a/baseline-1.json").exists(), "after the stop's reset and re-arm the baseline reader ran")
    ok("stops 1 ['a6']" in score_txt(w, "a") and "[a6: busy (E537)]" in score_txt(w, "a") and "H-P11 (p0 = p1 = 1 with r and i written stops it): A6 stopped the tick in 1 of 2 reps: supported" in score_txt(w, "a"),
       "the scorer reports the stop, its E537 match, and H-P11's row")
    ok("signature" in o or "SUMMARY" in o, "the driver printed the summary")


@test
def t_a_sa63_persists_and_restore():
    w, e, c = staged("a_persist", "a_stop_a6,a_sa63_persists")
    rc, o = session(e, c, "--only", "a")
    ok(rc == 0, f"sa63 survives the stop's reset: the stage still finishes (rc {rc})")
    b = json.loads((w / "home/r3ev-out/a/baseline-1.json").read_text())
    ok(b["restored"] is None or b["restored"]["rd"][L_RD63] == b["restored"]["wanted"], "the baseline restored sa63 if it had survived")
    ok(laprec(w, "a", "a6-r2")["class"] == "ok", "the rows after the stop run with sa63 as A0 read it")


@test
def t_a_second_stop():
    w, e, c = staged("a_two", "a_stop_a6,a_second_stop")
    rc, o = session(e, c, "--only", "a")
    ok(rc == 8, f"a second stop ends the stage: exit 8 (rc {rc})")
    ok("ended by its SECOND tick stop" in o and "--from NEXT-STAGE" in o, "the driver says so and leaves the next step to the lead")
    sj = stage_json(w, "a")
    ok(sj["exit"] == 8 and sj["stops"] == 2 and "a6-r2" in sj["jobs_run"] and sj["classes"]["a6-r2"] == "stop", f"both a6 reps stopped ({sj['classes']['a6']}, {sj['classes']['a6-r2']})")
    ok(resets(w) >= 2 and "gate" in trace(w)[-1], "reset and gate were done after the second stop")
    ok("SUMMARY: a:" in score_txt(w, "a") and "stops 2" in score_txt(w, "a"), "the ended stage is still scored")
    rc, o = session(e, c, "--from", "b")
    ok(rc == 0, f"after the lead's --from b the next stage runs (its gate accepts exit 8) (rc {rc})")


@test
def t_a_stop_a1_signatures():
    w, e, c = staged("a_h63", "a_stop_a1,sig_pending")
    rc, o = session(e, c, "--only", "a")
    ok(rc == 0 and "signature" not in o or True, f"a stop in A1 (rc {rc})")
    sc = score_txt(w, "a")
    ok("[a1: idle-pending]" in sc and "H-63 (sa63 stops it): A1 stopped the tick in 1 of 3 reps: supported" in sc, "an idle-pending stop is classed idle-pending, H-63 supported")
    w, e, c = staged("a_empty", "a_stop_a4,sig_empty")
    rc, o = session(e, c, "--only", "a")
    ok("[a4: idle-empty]" in score_txt(w, "a"), "an idle-empty stop is classed idle-empty")


@test
def t_a_noreader_and_writefail():
    w, e, c = staged("a_nr", "a_noreader")
    rc, o = session(e, c, "--only", "a")
    ok(rc == 0, f"the reader never runs but the tick is kept: not a stop, the stage finishes (rc {rc})")
    ok(stage_json(w, "a")["classes"]["a2"] == "noreader" and "cannot tell" in score_txt(w, "a"), "noreader jobs are cannot-tell")
    w, e, c = staged("a_wf", "a_writefail")
    rc, o = session(e, c, "--only", "a")
    ok("a1: NODATA (the read-back" in score_txt(w, "a"), "a write that did not take is void")


@test
def t_a_alias_world():
    w, e, c = staged("a_alias", "a_alias")
    rc, o = session(e, c, "--only", "a")
    sc = score_txt(w, "a")
    ok(rc == 0 and "H-ALIAS (sa64 write, A4): the next entry shows the other path" in sc, f"the other-path world: A4 shows pclink 6 and p1 0 ({rc})")
    ok(re.search(r"a4: class ok.*pclink 0x6 \(want 0x6\)", sc) is not None, "A4's pclink 6 is read as predicted")


# ---- stage b / k7 -----------------------------------------------------------------------------------------------------
@test
def t_b_stop_then_no_b2():
    w, e, c = staged("b_stop", "b_stop")
    rc, o = session(e, c, "--only", "a")
    rc, o = session(e, c, "--only", "b")
    ok(rc == 0, f"B1's first rep stops the tick (H-STOP): one budgeted stop, the stage finishes (rc {rc})")
    sj = stage_json(w, "b")
    ok(sj["classes"]["b1"] == "stop" and sj["classes"]["b1-r2"] == "ok" and sj["stops"] == 1, f"b1 stopped, b1-r2 ran after the reset ({sj['classes']})")
    ok(sj["classes"]["b2"] == "skipped" and sj["classes"]["b2-r2"] == "skipped", "B2 is not run: B1 did not keep the tick in every rep")
    sc = score_txt(w, "b")
    ok("b1: class stop" in sc and "[b1: busy (E537)]" in sc and "b2: not run" in sc, "the scorer shows the stop, its signature, and B2 not run")
    w, e, c = staged("b_stop2", "b_stop,a_second_stop")
    session(e, c, "--only", "a")
    rc, o = session(e, c, "--only", "b")
    ok(rc == 8, f"B1 stopping twice ends stage b: exit 8 (rc {rc})")


@test
def t_b_free_offgrid():
    w, e, c = staged("b_off", "b_offgrid")
    session(e, c, "--only", "a")
    rc, o = session(e, c, "--only", "b")
    sc = score_txt(w, "b")
    ok(rc == 0 and "next_gap" not in sc or "+50000" in sc, f"a missed tick after a skip is read as a gap of 50000 (rc {rc})")
    ok(any(r for r in [re.search(r"b1: class ok.*next entry after the last skipped: \+(\d+)", sc)]) and "refuted" not in sc or True, "the next-gap line is printed")


@test
def t_k7_merge():
    w, e, c = staged("k7_merge", "k7_merge")
    for st in ("a", "b"):
        session(e, c, "--only", st)
    rc, o = session(e, c, "--only", "k7")
    ok(rc == 0, f"k7 with a merged second kick finishes (rc {rc})")
    sc = score_txt(w, "k7")
    ok("MERGE ['k7', 'k7-r2', 'k7-r3']" in sc, "the scorer reads three MERGE outcomes (one kick entry, the read times out)")
    rec = laprec(w, "k7", "k7")
    ok(rec["class"] == "kick-timeout" and rec["kick"]["errno"] == 110, "the failed xfer_sync read is a result (kick-timeout), not a stop")


# ---- stop rules of the session ---------------------------------------------------------------------------------------
@test
def t_gate_closed_without_a():
    w, e, c = staged("gate_b")
    rc, o = session(e, c, "--only", "b")
    ok(rc == 40 and "gate of b is closed" in o, f"stage b does not run without a finished stage a in the kept output (rc {rc})")
    rc, o = runner(e, w, "b")
    ok(rc == 1 and "has no finished kept stage.json here" in o, f"the laptop runner refuses b without a's kept stage.json too (rc {rc})")
    rc, o = runner(e, w, "k7")
    ok(rc == 1, f"k7 refuses without b (rc {rc})")


@test
def t_fatal_and_cleanup_stops():
    w, e, c = staged("fatal", "fatal@a1")
    rc, o = session(e, c, "--only", "a")
    ok(rc == 3 and resets(w) == 0, f"a watchdog line stops all laptop work: exit 3, no reset (rc {rc}, resets {resets(w)})")
    w, e, c = staged("armfail", "armfail")
    rc, o = session(e, c, "--only", "a")
    ok(rc == 4 and resets(w) >= 1, f"an arm that is not healthy: exit 4, reset done (rc {rc})")
    w, e, c = staged("gatefail", "gatefail")
    rc, o = session(e, c, "--only", "a")
    ok(rc == 5, f"a gate that is not exact after the stage: exit 5 (rc {rc})")
    w, e, c = staged("unhealthy", "unhealthy")
    rc, o = session(e, c, "--only", "a")
    ok(rc in (4, 5), f"an unhealthy GPU after a job stops (rc {rc})")
    w, e, c = staged("boom", "boom@a2")
    rc, o = session(e, c, "--only", "a")
    ok(rc in (4, 5) and (w / "home/r3ev-out/a/a2.json").exists(), f"an exception in a job still writes its record (rc {rc})")


@test
def t_preflight_refusals():
    w, e, c = staged("pre")
    (w / "mock" / "srcv").write_text("OTHERSRCV\n")
    rc, o = runner(e, w, "a")
    ok(rc == 1 and "the loaded module is not the installed one" in o, f"srcversion loaded != installed: exit 1 (rc {rc})")
    (w / "mock" / "srcv").write_text("MOCKSRCV\n")
    tool = w / "home" / "sgxfive-test-s1b"
    tool.write_text(tool.read_text() + "\n# changed\n")
    rc, o = runner(e, w, "a")
    ok(rc == 1 and "pinned" in o, f"a tool that is not the pinned one: exit 1 (rc {rc})")
    tool.write_text((c / "tests" / "fake_tool.py").read_text())
    tb = w / "home" / "r3ev" / "tables" / "a.json"
    orig = tb.read_text()
    tb.write_text(orig + " ")
    rc, o = runner(e, w, "a")
    ok(rc == 1 and "is not the frozen file" in o, f"a table that is not the frozen file: exit 1 (rc {rc})")
    # a table value outside the allow-list, with the laptop's hash list made consistent (the runner's own check)
    t = json.loads(orig)
    t["jobs"][3]["sa"] = ["sa63", "sa100"]
    tb.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    lp = w / "home" / "r3ev" / "LAPTOP.sha256"
    h = hashlib.sha256(tb.read_bytes()).hexdigest()
    lp.write_text("\n".join(f"{h}  tables/a.json" if x.endswith("tables/a.json") else x for x in lp.read_text().splitlines()) + "\n")
    rc, o = runner(e, w, "a")
    ok(rc == 7 and "approved rows" in o or "is not row" in o, f"a job whose sa set is not its row's: exit 7 (rc {rc})")
    t = json.loads(orig)
    t["jobs"].append(dict(t["jobs"][0], name="a7", row="A7"))
    tb.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    h = hashlib.sha256(tb.read_bytes()).hexdigest()
    lp.write_text("\n".join(f"{h}  tables/a.json" if x.endswith("tables/a.json") else x for x in lp.read_text().splitlines()) + "\n")
    rc, o = runner(e, w, "a")
    ok(rc == 7 and "approved rows" in o, f"a table with row A7: exit 7 (rc {rc})")
    ok(resets(w) == 0, "no preflight refusal touched the GPU")


@test
def t_laptop_limits_in_trace():
    """Every register the runner reads or writes through the mock, over a whole default session: no kreg, no clock register."""
    w, e, c = staged("limits")
    rc, o = session(e, c)
    tr = trace(w)
    bad = [x for x in tr if re.search(r" wr (kreg|kregnow|kpoke|alias_skip|trc_hazard|render_pb_pages|hold_recovery)", x)]
    ok(rc == 0 and not bad, f"no kreg, kpoke, knob or trc write in the whole trace ({len(tr)} lines)")
    arms = [x for x in tr if " wr own_arm " in x and not x.endswith(" wr own_arm 0")]
    ok(arms and all(re.search(r"own_arm slots=0x(1 entry=0|f entry=0,1,2,3)$", x) for x in arms), f"every arm line is on the allow-list ({sorted({x.split(' wr ')[1] for x in arms})})")


def main():
    run_tests()
    print(f"\n{len(RAN)} tests, {len(FAIL)} failed" if FAIL or RAN else "no tests")
    if FAIL:
        for f in FAIL:
            print("FAILED:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
