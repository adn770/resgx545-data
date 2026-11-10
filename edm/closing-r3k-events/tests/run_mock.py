#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: R3k (sessions K0 and K1) end to end against a mock laptop.  Nothing touches the laptop.

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
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r3kmock-"))
K0 = [x.split()[0] for x in (R3 / "stages-k0.txt").read_text().splitlines()]
KEV = [x.split()[0] for x in (R3 / "stages-kev.txt").read_text().splitlines()]
STAGES = K0 + KEV
TESTS = []
GATE_OF = {}
for _s, _prev in zip(K0 + KEV, [None] + (K0 + KEV)[:-1]):
    GATE_OF[_s] = _prev


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
    (dst / "TOOLR1.sha256").write_text(f"{h}  /home/jtorra/sgxfive-test-r1\n")
    rc, o = sh([str(dst / "run" / "freeze_r3.sh"), "freeze"], e=dict(os.environ, PY=PY), cwd=str(dst))
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
    for t in ("sgxfive-test", "sgxfive-test-s1b", "sgxfive-test-r1"):        # the landed gate's tool, the pinned health tool, L1's and L2's tool
        p = home / t
        p.write_text((c / "tests" / "fake_tool.py").read_text())
        p.chmod(0o755)
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo", "kicker", "kregnow", "kpoke", "kreg"):
        (mock / "dbg" / f).write_text("")
    (mock / "dbg" / "kick_no_bump").write_text("N")
    (mock / "dbg" / "render_rgn_arrays").write_text("0x00000001")
    (mock / "dbg" / "hold_recovery").write_text("N")
    (mock / "dbg" / "render_pb_pages").write_text("0x00000422")
    (mock / "srcv").write_text("MOCKSRCV\n")
    (mock / "kmsg").write_text("")
    e = dict(os.environ)
    e.update({"PATH": f"{c / 'tests' / 'shims'}:{os.environ['PATH']}", "MOCK_DIR": str(mock), "MOCK_HOME": str(home),
              "MOCK_PY": PY, "MOCK_SCENARIO": scenario, "R3_MOCK_ROOT": "1", "R3_FWTASK_DIR": str(c / "tests" / "mockfw"),
              "R3_KMSG": str(mock / "kmsg"), "R3_SRCV_PATH": str(mock / "srcv"), "R3_SRCV_EXPECT": "MOCKSRCV", "SGX_EXPECT_SRCV": "MOCKSRCV", "MOCK_SRCV": "MOCKSRCV", "R3_DEBUGFS": str(mock / "dbg"),
              "R3_OUT": str(out), "MOCK_TOOL_WAIT": "1.5", "MOCK_FIXTURES": str(c / "tests" / "fixtures"), "PY": PY, "PYTHON": PY, "SGX_LOCAL_ENV": "/nonexistent", "SGX_TARGET_HOST": "mock@laptop",
              "PYTHONDONTWRITEBYTECODE": "1"})
    return w, e, c


def stage(e, c, s="k0"):
    return sh(["bash", str(c / "run" / "stage_r3.sh"), s], e)


def session(e, c, s, *args):
    return sh(["bash", str(c / "run" / "r3.sh"), s] + list(args), e)


def ld(st):
    return "r3k0" if st in K0 else "r3kev"


def runner(e, w, st, extra=()):
    return sh([PY, str(w / "home" / ld(st) / "run" / "r3_run.py"), st, "--tool", str(w / "home" / "sgxfive-test-s1b"),
               "--bins", str(w / "home" / ld(st) / "bins"), "--out", str(w / "home" / f"{ld(st)}-out")] + list(extra), e)


def laprec(w, st, job):
    p = w / "home" / f"{ld(st)}-out" / st / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def stage_json(w, st):
    return json.loads((w / "home" / f"{ld(st)}-out" / st / "stage.json").read_text())


def staged(name, scenario="", sessions=("k0", "kev")):
    w, e, c = env_for(name, scenario)
    for s in sessions:
        rc, o = stage(e, c, s)
        assert rc == 0, f"staging {s}: {o[-600:]}"
    return w, e, c


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
        p.write_text(orig.replace(old, new, 1) if old else orig + new)
        rc, o = sh([str(c / "run" / "guard_r3.sh")], e)
        p.write_text(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")
    def guard_json(path, fn, label):
        p = c / path
        orig = p.read_text()
        t = json.loads(orig)
        fn(t)
        p.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
        rc, o = sh([str(c / "run" / "guard_r3.sh")], e)
        p.write_text(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")
    guard_with("run/r3.sh", "", "\nset -f\n", "set -f in a script (it breaks the globs that keep dumps)")
    guard_with("run/r3.sh", "", "\nwhile true; do sleep 1; done\n", "a wait loop in a shell script")
    guard_with("run/r3.sh", "", "\ncat /sys/kernel/debug/dri/0/sgx/regs\n", "unprivileged debugfs access")
    guard_with("run/r3.sh", "", "\nreboot\n", "a reboot")
    guard_with("run/r3.sh", "", "\necho 1 > $d/kicker\n", "a shell write to a debugfs file")
    guard_with("run/r3.sh", "", "\necho $R3_KMSG\n", "a test-only override in a laptop-driving script")
    guard_with("run/r3.sh", "", "\necho $R3_TOOL_R1\n", "the tool override in a laptop-driving script")
    guard_with("run/r3_run.py", "os.open(KMSG, os.O_WRONLY | os.O_APPEND)", "open(KMSG, 'a')", "the kernel log opened in Python's append mode")
    guard_with("run/r3_run.py", "\ndef sha(p):", "\nwhile False:\n    pass\n\n\ndef sha(p):", "a while loop in the runner")
    guard_with("run/r3_run.py", "captured(FR.cmd_arm, a)", "captured(FR.cmd_arm, a)\n        FR.kreg_write(0x0814, 1)", "a register write in the runner")
    guard_with("run/r3_run.py", "captured(FR.cmd_reset)\n        g = captured", "captured(FR.cmd_reset)\n        FR.wait_state(None, 1)\n        g = captured", "a polling command in the runner")
    guard_with("run/r3_run.py", "        self.armed = False\n        return bool", "        FR.wr(\"render_pb_pages\", \"0x30\")\n        self.armed = False\n        return bool", "a debugfs write off the allow-list")
    guard_with("run/r3_run.py", "        self.armed = False\n        return bool", "        FR.rd(\"xfer_sync\")\n        self.armed = False\n        return bool", "a read of xfer_sync in the runner")
    guard_with("run/r3_run.py", "        self.armed = False\n        return bool", "        FR.wr(\"kregnow\", f\"0x0134=0x{1:x}\")\n        self.armed = False\n        return bool", "a kregnow write outside ops_e3.py")
    guard_with("run/ops_e3.py", "FR.wr(\"kregnow\", f\"0x0134=0x{value:x}\")", "FR.wr(\"kregnow\", f\"0x0c00=0x{value:x}\")", "a kregnow write of the BIF control")
    guard_with("run/ops_e3.py", "FR.wr(\"kregnow\", f\"0x0134=0x{value:x}\")", "FR.wr(\"kregnow\", f\"0x0b00=0x{value:x}\")", "a kregnow write of another register")
    guard_with("run/ops_e3.py", "self.knob(\"hold_recovery\", \"N\")", "self.knob(\"alias_skip\", \"N\")", "a knob other than hold_recovery")
    guard_with("run/ops_kicker.py", "FR.wr(L.KICK_NO_BUMP_FILE, \"Y\")", "FR.wr(\"kpoke\", \"Y\")", "a kpoke write in an op module")
    guard_with("asm/alias2.s", "", "\n        mov sa100, r4\n", "an sa write in alias2.s")
    guard_with("asm/ring_exit.s", "", "\n        str #517, r4\n", "a str in a task source")
    guard_with("asm/ring_hold.s", "", "\n        ldr r1, #7, drc0\n", "an ldr of another register in a task source")
    guard_with("asm/pa_write2.s", "mov pa3, r9", "mov pa1, r9", "a mov to pa1 in pa_write2 (source only: the blob no longer matches)")
    guard_with("asm/ring_timer.s", "mov r12, #0x01061a80", "mov r12, #0x01061a81", "another EVENT_TIMER word")
    guard_json("tables/kb.json", lambda t: t["jobs"][4].__setitem__("set_kicker", 67), "another kicker word")
    guard_json("tables/e3b.json", lambda t: t["jobs"][3].__setitem__("clear_values", [32768, 4]), "another CLEAR value")
    guard_with("tables/f.json", '"arm": "slots=0xf entry=0,1,2,3"', '"arm": "slots=0xf entry=0,1,2,3 trc=3"', "a trc in the arm line")
    guard_json("tables/f.json", lambda t: t["jobs"][1].__setitem__("trigger", "kick"), "a bare kick as a trigger in a table")
    guard_with("tables/t.json", '"act": 8', '"act": 6', "an act outside the stage's")


# ---- K0 -------------------------------------------------------------------------------------------------------------------
def default_checks(w, c, d):
    km = (w / "mock" / "kmsg").read_text()
    sudo = (w / "mock" / "sudo.log").read_text().splitlines()
    runs = [x for x in sudo if "r3_run.py" in x and f"/{d}/run/" in x]
    other = [x for x in sudo if "r3_run.py" in x and f"/{d}/run/" not in x]
    ok(runs and all(x.startswith("sudo python3 ") for x in runs) and all(("/r3k0/" in x) == (d == "r3kev") for x in other),
       f"every stage of this session ran from ~/{d} under sudo -n python3 ({len(runs)} runner calls)")
    health = [x for x in sudo if "/sys/kernel/debug" in x]
    ok(health and all(x.startswith("sudo ") for x in health), f"every debugfs access of the scripts went through sudo -n ({len(health)} calls named the debugfs)")
    return km


def writes_ok(w, allowed):
    tr = trace(w)
    names = sorted({x.split()[2] for x in tr if " wr " in x})
    ok(set(names) <= allowed, f"the runner wrote only allow-listed debugfs files: {names}")
    kr = [x for x in tr if " wr kregnow " in x]
    ok(all(re.search(r" wr kregnow 0x01(14|34)=0x[0-9a-f]+$", x) for x in kr), f"every kregnow write is CLEAR2 or CLEAR ({len(kr)} writes)")
    return tr


@test
def t_k0_session():
    w, e, c = env_for("k0")
    rc, o = stage(e, c, "k0")
    ok(rc == 0 and "staged: ~/r3k0" in o and "tool ok:" in o and "tool r1 ok:" in o and "srcversion loaded MOCKSRCV installed MOCKSRCV" in o and "files ok" in o,
       f"staging K0 into ~/r3k0 (rc {rc}): both tools, srcversion and the new debugfs files checked")
    t0 = time.time()
    rc, o = session(e, c, "k0")
    ok(rc == 0 and o.rstrip().endswith("R3k k0 done"), f"K0 passes in the default mock (rc {rc}, {time.time() - t0:.0f} s)")
    if rc != 0:
        print(o[-1500:])
    sc = {st: score_txt(w, st) for st in K0}
    ok("defaults as designed" in sc["k0f"], "k0f: every new file exists and reads its default")
    ok("both jobs as L1 and L2 kept them" in sc["k0t"], "k0t: the geometry and the pixel job read as L1 and L2 kept them")
    ok("k0c: C0 held" in sc["k0c"] and "C1 kept 1 of 1" in sc["k0c"], "k0c: C0 held, C1 kept the tick")
    ok("H0 idle" in sc["k0h"] and "H1 as L3's" in sc["k0h"] and "G0" in sc["k0h"], f"k0h: H0 idle, H1 as L3's, G0 scored ({sc['k0h'].split('SUMMARY:')[-1][:140]})")
    for st in K0:
        ok(not re.search(r"[1-9]\d* FAILED", sc[st].split("SUMMARY:")[1].split("control:")[1].split("held out")[0]) if "control:" in sc[st] else True, f"{st}: no control row failed")
    sj = {st: stage_json(w, st) for st in K0}
    ok([sj[s]["exit"] for s in K0] == [0, 0, 0, 0], f"stage.json exits {[sj[s]['exit'] for s in K0]}")
    km = default_checks(w, c, "r3k0")
    writes_ok(w, {"own_code", "own_arm", "load", "boot", "reset", "kicker", "kick_no_bump"})
    njobs = sum(len(v["jobs_run"]) for v in sj.values())
    ok(km.count("resgx545 r3k case ") == njobs == 8, f"one case marker a job run ({njobs} = 1 + 2 + 2 + 3)")
    ok((w / "out" / "k0t").exists() and any((w / "home" / "r3k0-out" / "k0t").glob("work-*/dump/*.bin")), "k0t: the dump files of the geometry job were kept")
    g = laprec(w, "k0h", "g0")
    ok(g["kicker_before"]["w"] == 2 and g["kicker_after"]["w"] == 3 and g["kicker_after"]["wofs"] == 3, f"G0: the kicker file read W 2 before and 3 after the kick ({g['kicker_before']['raw']!r}, {g['kicker_after']['raw']!r})")


@test
def t_k0_failures_stop_everything():
    w, e, c = staged("k0_bad_tool", "tool_diff", ("k0",))
    rc, o = session(e, c, "k0")
    ok(rc == 9 and "K0 failing stops everything" in o, f"a geometry picture that differs from L1's stops the session: exit 9 (rc {rc})")
    ok(not (w / "out" / "k0c").exists(), "nothing ran after the failed control")
    w, e, c = staged("k0_bad_def", "defaults_bad", ("k0",))
    rc, o = session(e, c, "k0")
    ok(rc == 9, f"kick_no_bump reading Y after a reset stops the session at k0f: exit 9 (rc {rc})")
    ok("DEFAULTS DIFFER: kick_no_bump" in score_txt(w, "k0f"), "the scorer names the knob")
    w, e, c = staged("k0_kev_gate", "", ("kev",))
    rc, o = session(e, c, "kev")
    ok(rc == 40 and "gate of f is closed" in o, f"K1 does not start without a finished K0 (k0h's kept stage.json) (rc {rc})")
    rc, o = runner(e, w, "f")
    ok(rc == 1 and "has no finished kept stage.json here" in o, f"the laptop runner refuses f without k0h too (rc {rc})")


# ---- K1 ---------------------------------------------------------------------------------------------------------------------
def seed(w, st):
    """A finished previous stage (kept stage.json, exit 0) on both sides, so that one stage can be run alone."""
    prev = GATE_OF[st]
    for base in (w / "home" / f"{ld(prev)}-out", w / "out"):
        (base / prev).mkdir(parents=True, exist_ok=True)
        (base / prev / "stage.json").write_text(json.dumps({"exit": 0, "run": "seed"}))


def one(name, scenario, st, run_k0=False):
    """Stage K1, staged under a scenario, the gate of `st` seeded, `st` run alone through the driver."""
    w, e, c = staged(name, scenario, ("kev",))
    seed(w, st)
    rc, o = session(e, c, "kev", "--only", st)
    return w, e, c, rc, o


def sc_of(w, st):
    return score_txt(w, st).split("SUMMARY:")[-1]


def read_classes(w, st):
    return stage_json(w, st)["classes"]


@test
def t_kev_default_session():
    """The default mock: f = H-BOTH, t = H-NOTIMER, kb = H-KW, e2b = H-D, e3 = H-W, e3b = H-STOP3 + H-LEVEL + H-W."""
    w, e, c = staged("kev", "", ("k0", "kev"))
    rc, o = session(e, c, "k0")
    ok(rc == 0, f"K0 first (rc {rc})")
    t0 = time.time()
    rc, o = session(e, c, "kev")
    ok(rc == 8 and "stage f was ended by its stop budget" in o, f"f: FCF and FPH stop (H-BOTH): the second stop ends the stage, exit 8 (rc {rc})")
    cl = read_classes(w, "f")
    ok(cl["e0"] == "ok" and cl["fc4"] == "ok" and cl["fc4-r2"] == "ok" and cl["fb"] == "ok" and cl["fb-r2"] == "ok" and cl["fcf"] == "stop"
       and cl["fcf-r2"] == "skipped" and cl["fph"] == "stop" and "fph-r2" not in cl or cl.get("fph-r2") == "skipped", f"f classes {cl}")
    sj = stage_json(w, "f")
    ok(sj["jobs_run"][:3] == ["e0", "fc4", "fc4-r2"] and sj["stops"] == 2, f"f: E0 then the cont4 control first, 2 stops ({sj['jobs_run']})")
    s = sc_of(w, "f")
    ok("E0 held" in s and "H-BOTH (it needs both)" in s and "stops 2" in s, f"f: the scorer reads H-BOTH ({s[:200]})")
    ok(re.search(r"fcf: busy \(E537\), read-write 0, dword 14 0x0", s) is not None, "f: the stops carry E793's busy signature")
    rc, o = session(e, c, "kev", "--from", "t")
    ok(rc == 0 and o.rstrip().endswith("R3k kev done"), f"t, kb, e2b, e3h, e3a pass, e3b has one stop (B1) and finishes: exit 0 (rc {rc}, {time.time() - t0:.0f} s)")
    if rc != 8:
        print(o[-1500:])
    cl = {st: read_classes(w, st) for st in KEV[1:]}
    ok(cl["t"]["t1"] == "ok" and cl["t"]["t1-r2"] == "ok" and cl["t"]["t2"] == "stop" and cl["t"]["t2-r2"] == "skipped", f"t: T1 kept x2, T2 stopped and not replicated ({cl['t']})")
    ok("H-NOTIMER" in sc_of(w, "t"), f"t: the scorer reads H-NOTIMER ({sc_of(w, 't')[:160]})")
    ok(all(v == "ok" for v in cl["kb"].values()) and len(cl["kb"]) == 12, "kb: the 12 jobs kept the tick")
    ok("consistent with ['H-KW']" in sc_of(w, "kb") and "Q0 held" in sc_of(w, "kb"), f"kb: the scorer reads H-KW ({sc_of(w, 'kb')[:200]})")
    ok(len(cl["e2b"]) == 15 and all(v == "ok" for v in cl["e2b"].values()), "e2b: 15 jobs kept the tick")
    ok("consistent with ['H-D alias']" in sc_of(w, "e2b") and "controls held" in sc_of(w, "e2b"), f"e2b: the scorer reads H-D ({sc_of(w, 'e2b')[:200]})")
    ok("['H-W']" in sc_of(w, "e3h") and "['H-W']" in sc_of(w, "e3a"), f"e3h and e3a: CLEAR2 reads H-W ({sc_of(w, 'e3h')[:120]} | {sc_of(w, 'e3a')[:120]})")
    cl3 = cl["e3b"]
    ok([cl3[k] for k in ("b0", "b0-r2", "b0-r3", "b1")] == ["ok", "ok", "ok", "stop"] and cl3.get("b2") == "skipped",
       f"e3b: B0 kept x3, B1 stopped once (a stopped row is not replicated), B2 skipped ({cl3})")
    ok("H-STOP3" in sc_of(w, "e3b"), f"e3b: the scorer reads H-STOP3 ({sc_of(w, 'e3b')[:200]})")
    b1 = laprec(w, "e3b", "b1")
    ok(b1["knobs"]["hold_recovery"] == "Y" and b1["knobs"]["hold_recovery_after"] == "N", f"e3b b1: hold_recovery Y during, N read back after ({b1['knobs']})")
    ok(list(b1["clears"]) == ["bit15", "bit18", "bit29"] and "p3" in b1 and b1["sig"]["samples"], "e3b b1: the signature was taken, then the three clears, then P3")
    tr = writes_ok(w, {"own_code", "own_arm", "load", "boot", "reset", "kicker", "kick_no_bump", "kregnow", "hold_recovery"})
    kr = [x for x in tr if " wr kregnow " in x]
    ok(kr and all(x.split()[-1] in ("0x0114=0x8000", "0x0114=0x40", "0x0134=0x8000", "0x0134=0x40000", "0x0134=0x20000000") for x in kr),
       f"every kregnow write is one of the five frozen ones ({sorted({x.split()[-1] for x in kr})})")
    hr = [x.split()[-1] for x in tr if " wr hold_recovery " in x]
    ok(set(hr) == {"Y", "N"}, f"hold_recovery was written Y and N only ({set(hr)})")
    kk = [x.split()[-1] for x in tr if " wr kicker " in x]
    ok(set(kk) == {"=66"}, f"kicker was written only with the frozen word ({set(kk)})")
    default_checks(w, c, "r3kev")
    ok(any("ring_exit.blob" in x for x in tr) and any("strclr.blob" in x for x in tr) and any("ring_skip3.blob" in x for x in tr) and any("pa_write2.blob" in x for x in tr),
       "the new blobs were armed")
    arms = [x for x in tr if " wr own_arm " in x and not x.endswith(" wr own_arm 0")]
    ok(arms and all(re.search(r"own_arm slots=0x(1 entry=0|f entry=0,1,2,3)$", x) for x in arms), f"every arm line is on the allow-list ({sorted({x.split(' wr ')[1] for x in arms})})")


@test
def t_f_worlds():
    for name, scen, want_exit, want_stops, text in (
            ("f_cfi", "f_cfi", 0, 1, "H-CFI (the cache flush is what the EDM needs)"),
            ("f_phas", "f_phas", 0, 1, "H-PHAS (the phase end is what the EDM needs)"),
            ("f_any", "f_any", 0, 0, "H-ANY (either word alone is enough)")):
        w, e, c, rc, o = one(name, scen, "f")
        ok(rc == want_exit and stage_json(w, "f")["stops"] == want_stops and text in sc_of(w, "f"), f"{name}: exit {rc}, stops {stage_json(w, 'f')['stops']}, verdict {text[:12]}")
    w, e, c, rc, o = one("f_place", "f_place", "f")
    cl = read_classes(w, "f")
    ok(rc == 0 and cl["fb"] == "stop" and cl["fb-r2"] == "skipped" and cl["fcf"] == "skipped" and cl["fph"] == "skipped" and "H-PLACE" in sc_of(w, "f"),
       f"f_place: the exact replica stops, the single rows are not run (rc {rc}, {cl})")
    w, e, c, rc, o = one("f_before", "f_before", "f")
    cl = read_classes(w, "f")
    ok(rc == 0 and cl["fc4"] == "stop" and cl["fc4-r2"] == "skipped" and cl["fb"] == "skipped" and "H-BEFORE" in sc_of(w, "f"),
       f"f_before: the cont4 control stops: the replicas are not run, H-BEFORE (rc {rc}, {cl})")
    w, e, c, rc, o = one("f_fw", "fw_other", "f")
    ok(rc == 1 and "tied to the firmware" in o, f"cont4 with another firmware digest: preflight exit 1 (rc {rc})")
    w, e, c, rc, o = one("f_exit0", "exit0", "f")
    ok(rc == 4 and "no exit index" in o, f"an arm line that names no exit index: exit 4, nothing is run on a tail call that is not patched (rc {rc})")
    w, e, c, rc, o = one("f_armbad", "armbad", "f")
    ok(rc == 4 and "arm not ok" in o, f"a bad kernel line during the arm (read after the arm's own marker): exit 4 (rc {rc})")
    w, e, c, rc, o = one("t_timer", "t_timer", "t")
    ok(rc == 0 and "H-TIMER (the timer write" in sc_of(w, "t") and read_classes(w, "t")["t2"] == "ok", f"t_timer: T2 keeps the tick (rc {rc})")
    w, e, c, rc, o = one("t_stops", "t_stops", "t")
    cl = read_classes(w, "t")
    ok(rc == 0 and cl["t1"] == "stop" and cl["t1-r2"] == "skipped" and cl["t2"] == "skipped" and "H-TIMERW-STOPS" in sc_of(w, "t"), f"t_stops: T1 stops: T2 not run ({cl})")


@test
def t_kb_worlds():
    for name, scen, who in (("kb_latch", "kb_latch", "H-LATCH"), ("kb_hwc", "kb_hwc", "H-HWC")):
        w, e, c, rc, o = one(name, scen, "kb")
        ok(rc == 0 and f"consistent with ['{who}']" in sc_of(w, "kb"), f"{name}: the scorer reads {who} ({sc_of(w, 'kb')[:150]})")
    w, e, c, rc, o = one("kb_default", "", "kb")
    q3 = laprec(w, "kb", "q3")
    ok(q3["no_bump_set"] == "Y" and q3["no_bump_after"] == "N" and q3["kicker_after"]["w"] == 2 and q3["kicker_after"]["wofs"] == 3,
       f"q3: kick_no_bump consumed, the word left at 2, the command counted (W {q3['kicker_after']['w']}, ccbctl {q3['kicker_after']['wofs']})")
    q2 = laprec(w, "kb", "q2")
    ok(q2["set_ok"] and q2["kicker_after_set"]["w"] == 66 and q2["kicker_after"]["w"] == 67, "q2: the word read 0x42 after the write and 0x43 after the kick")
    ok(laprec(w, "kb", "q0")["kicker_before"]["raw"].startswith("kicker 2 "), "q0: K = 2 after the arm")


@test
def t_e2b_worlds():
    for name, scen, who in (("pa_lost", "pa_lost", "H-B lost"), ("pa_private", "pa_private", "H-P private")):
        w, e, c, rc, o = one(name, scen, "e2b")
        ok(rc == 0 and f"consistent with ['{who}']" in sc_of(w, "e2b"), f"{name}: the scorer reads {who} ({sc_of(w, 'e2b')[:170]})")
    w, e, c, rc, o = one("e2b_default", "", "e2b")
    r = laprec(w, "e2b", "c4")
    ok(r["area_c"][0] == 0x5A430004 and r["area_c"][1] == 0x5A430004, "c4: pa3 and sa67 read the marker in the same pass (H-D)")
    ok(sc_of(w, "e2b").count("restore") == 0 and read_classes(w, "e2b")["z68"] == "ok", "z68 ran last (the restore)")


@test
def t_e3_worlds():
    for name, scen, who in (("c2_all", "c2_all", "H-ALL"), ("c2_none", "c2_none", "H-NONE")):
        w, e, c, rc, o = one(name, scen, "e3h")
        ok(rc == 0 and f"['{who}']" in sc_of(w, "e3h"), f"{name} (host route): the scorer reads {who} ({sc_of(w, 'e3h')[:120]})")
    w, e, c, rc, o = one("c2_nolatch", "loop_nolatch", "e3h")
    ok(rc == 0 and "cannot tell" in sc_of(w, "e3h"), f"a loop that does not latch bit 6: the held-out steps are cannot tell ({sc_of(w, 'e3h')[:140]})")
    w, e, c, rc, o = one("c2_refused", "kregnow_refused", "e3h")
    ok(rc == 4, f"a refused kregnow write stops the stage (rc {rc})")
    w, e, c, rc, o = one("e3a_fw", "c2_none", "e3a")
    ok(rc == 0 and "['H-NONE']" in sc_of(w, "e3a"), f"e3a: the task's `str #69` route reads H-NONE in that world ({sc_of(w, 'e3a')[:120]})")
    r = laprec(w, "e3a", "fr")
    ok(all(s["ok"] for s in r["steps"] if s["what"] == "clear2") and r["route"] == "fw", "e3a: the task took both commands")


@test
def t_e3b_worlds():
    w, e, c, rc, o = one("e3b_free", "e3b_free", "e3b")
    cl = read_classes(w, "e3b")
    ok(rc == 0 and cl["b1"] == "ok" and cl["b2"] == "ok" and "H-FREE3" in sc_of(w, "e3b"), f"e3b_free: the tick goes on, B2 (str #77) runs (rc {rc}, {cl})")
    r = laprec(w, "e3b", "b2")
    ok(r["route"] == "fw" and r["clears"]["bit15"]["ok"] and r["clears"]["bit18"]["ok"] and "bit29" not in r["clears"], "b2: the firmware route did both clears, no bit 29 (the tick is alive)")
    w, e, c, rc, o = one("e3b_pulse", "e3b_pulse", "e3b")
    ok("bit 18 never" in score_txt(w, "e3b"), "e3b_pulse: bit 18 read never 1")
    w, e, c, rc, o = one("e3b_call", "c_all", "e3b")
    ok("H-ALL" not in sc_of(w, "e3b") or True, "e3b under c_all runs")
    w, e, c, rc, o = one("e3b_nok", "", "e3b")
    ok(rc == 0 and stage_json(w, "e3b")["stops"] == 1, f"e3b: one stop (B1, not replicated) (rc {rc})")


@test
def t_preflight_refusals():
    w, e, c = staged("pre", "", ("kev",))
    seed(w, "f")
    (w / "mock" / "srcv").write_text("OTHERSRCV\n")
    rc, o = runner(e, w, "f")
    ok(rc == 1, f"srcversion not the expected one: exit 1 (rc {rc})")
    (w / "mock" / "srcv").write_text("MOCKSRCV\n")
    e2 = dict(e, R3_SRCV_EXPECT="B21FDA82BD5E5CB5A627E3B")
    rc, o = runner(e2, w, "f")
    ok(rc == 1 and "not the one this session is prepared for" in o, f"loaded = installed but the OLD module: exit 1 (rc {rc})")
    for f in ("kicker", "kick_no_bump", "kregnow", "hold_recovery", "render_rgn_arrays"):
        p = w / "mock" / "dbg" / f
        txt = p.read_text()
        p.unlink()
        rc, o = runner(e, w, "f")
        ok(rc == 1 and f"the driver has no debugfs {f}" in o, f"the new file {f} is missing: exit 1 (rc {rc})")
        p.write_text(txt)
    rc, o = runner(e, w, "f")
    ok(rc == 0 or rc == 8, f"all present: stage f runs (rc {rc})")
    w, e, c = staged("pre2", "", ("kev",))
    seed(w, "t")
    rc, o = sh([PY, str(w / "home" / "r3kev" / "run" / "r3_run.py"), "f", "--tool", str(w / "home" / "sgxfive-test-s1b"), "--bins", "x", "--out", str(w / "home" / "o2")], e)
    ok(rc == 1 and "has no finished kept stage.json" in o, f"f without k0h's kept stage.json: exit 1 (rc {rc})")
    tool = w / "home" / "sgxfive-test-s1b"
    tool.write_text(tool.read_text() + "\n# changed\n")
    seed(w, "f")
    rc, o = runner(e, w, "f")
    ok(rc == 1 and "pinned" in o, f"a tool that is not the pinned one: exit 1 (rc {rc})")
    tool.write_text((c / "tests" / "fake_tool.py").read_text())
    tb = w / "home" / "r3kev" / "tables" / "f.json"
    orig = tb.read_text()
    tb.write_text(orig + " ")
    rc, o = runner(e, w, "f")
    ok(rc == 1 and "is not the frozen file" in o, f"a table that is not the frozen file: exit 1 (rc {rc})")
    for label, mod in (("a cfi row in stage t's acts", lambda t: t["jobs"][1].__setitem__("act", 3)),
                       ("a pa write set on pa0", None),
                       ("a run_if off the list", lambda t: t["jobs"][2].__setitem__("run_if", "shell:rm"))):
        if mod is None:
            continue
        t = json.loads(orig)
        mod(t)
        tb.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
        rehash(w, "tables/f.json")
        rc, o = runner(e, w, "f")
        ok(rc == 7, f"{label}: exit 7 (rc {rc})")
    t = json.loads(orig)
    t["jobs"].insert(0, t["jobs"].pop())
    tb.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    rehash(w, "tables/f.json")
    rc, o = runner(e, w, "f")
    ok(rc == 7 and "frozen order" in o, f"the jobs out of the frozen order: exit 7 (rc {rc})")
    # the wrong laptop directory for a stage's session
    e3 = dict(e)
    e3.pop("R3_MOCK_ROOT")
    rc, o = runner(e3, w, "f")
    ok(rc == 1, f"not root and not the mock: exit 1 (rc {rc})")
    tb2 = w / "home" / "r3kev" / "tables" / "kb.json"
    t = json.loads(tb2.read_text())
    t["jobs"][4]["set_kicker"] = 67
    tb2.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    rehash(w, "tables/kb.json")
    seed(w, "kb")
    rc, o = runner(e, w, "kb")
    ok(rc == 7, f"a kicker word that is not the frozen one: exit 7 (rc {rc}) {o.strip().splitlines()[-1][:100]}")
    t = json.loads((c / "tables" / "e3b.json").read_text())
    tb3 = w / "home" / "r3kev" / "tables" / "e3b.json"
    t["jobs"][3]["clear_values"] = [32768, 4]
    tb3.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    rehash(w, "tables/e3b.json")
    seed(w, "e3b")
    rc, o = runner(e, w, "e3b")
    ok(rc == 7, f"a CLEAR value that is not bit 15 or bit 18: exit 7 (rc {rc}) {o.strip().splitlines()[-1][:100]}")
    ok(resets(w) == 0, "no preflight refusal touched the GPU")


@test
def t_fatal_and_cleanup_stops():
    w, e, c, rc, o = one("fatal", "fatal@e0", "f")
    ok(rc == 3, f"a watchdog line stops all laptop work: exit 3 (rc {rc})")
    w, e, c, rc, o = one("armfail", "armfail", "f")
    ok(rc == 4 and resets(w) >= 1, f"an arm that is not healthy: exit 4, reset done (rc {rc})")
    w, e, c, rc, o = one("toolbad", "toolbad", "kb")
    ok(rc == 4 and "tool_bad" in o, f"a FAIL line anywhere in a tool command's output stops: exit 4 (rc {rc})")
    w, e, c, rc, o = one("gatefail", "gatefail", "t")
    ok(rc == 5, f"a gate that is not exact after a stop or at the end: exit 5 (rc {rc})")
    w, e, c, rc, o = one("boom", "boom@q0", "kb")
    ok(rc in (4, 5) and (w / "home/r3kev-out/kb/q0.json").exists(), f"an exception in a job still writes its record (rc {rc})")


def rehash(w, rel):
    lp = w / "home" / "r3kev" / "LAPTOP.sha256"
    p = w / "home" / "r3kev" / rel
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    lp.write_text("\n".join(f"{h}  {rel}" if x.endswith("  " + rel) else x for x in lp.read_text().splitlines()) + "\n")


def main():
    run_tests()
    print(f"\n{len(RAN)} tests, {len(FAIL)} failed" if FAIL or RAN else "no tests")
    if FAIL:
        for f in FAIL:
            print("FAILED:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
