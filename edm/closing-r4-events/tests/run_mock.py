#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: R4-events (stages kb2, kp, e3p) end to end against a mock laptop.  Nothing touches the laptop.

The real scripts run on a COPY of this directory (its pinned tool hash is the fake tool's, its freeze is redone there): run/stage_r4e.sh and
run/r4e.sh with the ssh, scp, sudo, sha256sum, python3, modinfo and dmesg shims (tests/shims), the laptop runner run/r4e_run.py with the fake
fwtask_run (tests/mockfw: a simulated EDM on the API of the landed file at resgx545 5a13042), the fake tool (tests/fake_tool.py) and the
scorer score/score_r4e.py.  Worlds by MOCK_SCENARIO (tests/mockfw/kmock.py): every hypothesis of the plan, the stops, the refusals.

    .../pixel-faults/.venv/bin/python tests/run_mock.py [-k SUBSTRING]
"""
import hashlib
import inspect
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
PY = os.environ.get("PY", "/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python")
WT = os.environ.get("RESGX545", "/Users/jtorra/src/scratch/resgx545/closing4/lead/wt")
FAIL, RAN, TESTS = [], [], []
ONLY = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r4emock-"))
sys.path.insert(0, str(R4 / "gen"))
import r4layout as L  # noqa: E402

ATT = "mock1"
STAGES = L.STAGES
JOBS = {st: [L.rep_name(r, k) for r in L.ROW_ORDER[st] for k in range(L.ROW_SPEC[st][r]["reps"])] for st in STAGES}
ALL_JOBS = [j for st in STAGES for j in JOBS[st]]


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
    dst = BASE / name / "r4"
    shutil.copytree(R4, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "*.pyc", "debug"))
    (dst / "debug").mkdir()
    h = hashlib.sha256((dst / "tests" / "fake_tool.py").read_bytes()).hexdigest()
    (dst / "TOOL.sha256").write_text(f"{h}  /home/jtorra/sgxfive-test-s1b\n")
    rc, o = sh([str(dst / "run" / "freeze_r4e.sh"), "freeze"], e=dict(os.environ, PY=PY, RESGX545=WT), cwd=str(dst))
    assert rc == 0, o
    return dst


def env_for(name, scenario="", knobs=None, srcv="MOCKSRCV", copy=None):
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
    for t in ("sgxfive-test", "sgxfive-test-s1b"):        # the landed gate's tool, the pinned health tool
        p = home / t
        p.write_text((c / "tests" / "fake_tool.py").read_text())
        p.chmod(0o755)
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo", "kicker", "kregnow"):
        (mock / "dbg" / f).write_text("")
    kn = {"kick_no_bump": "N", "render_rgn_arrays": "0x00000000", "hold_recovery": "N", "render_pb_pages": "0x00000422"}
    kn.update(knobs or {})
    for k, v in kn.items():
        (mock / "dbg" / k).write_text(v)
    (mock / "srcv").write_text(srcv + "\n")
    (mock / "kmsg").write_text("")
    e = dict(os.environ)
    e.update({"PATH": f"{c / 'tests' / 'shims'}:{os.environ['PATH']}", "MOCK_DIR": str(mock), "MOCK_HOME": str(home),
              "MOCK_PY": PY, "MOCK_SCENARIO": scenario, "R3_MOCK_ROOT": "1", "R3_FWTASK_DIR": str(c / "tests" / "mockfw"),
              "R3_KMSG": str(mock / "kmsg"), "R3_SRCV_PATH": str(mock / "srcv"), "R3_SRCV_EXPECT": "MOCKSRCV", "SGX_EXPECT_SRCV": "MOCKSRCV",
              "MOCK_SRCV": srcv, "R3_DEBUGFS": str(mock / "dbg"), "R3_OUT": str(out), "MOCK_TOOL_WAIT": "1.5",
              "MOCK_FIXTURES": str(c / "tests" / "fixtures"), "PY": PY, "PYTHON": PY, "SGX_LOCAL_ENV": "/nonexistent",
              "SGX_TARGET_HOST": "mock@laptop", "RESGX545": WT, "PYTHONDONTWRITEBYTECODE": "1"})
    return w, e, c


def staged(name, scenario="", **kw):
    w, e, c = env_for(name, scenario, **kw)
    rc, o = sh(["bash", str(c / "run" / "stage_r4e.sh")], e)
    assert rc == 0, f"staging: {o[-800:]}"
    return w, e, c


def session(e, c, att=ATT, *args):
    return sh(["bash", str(c / "run" / "r4e.sh"), att] + list(args), e)


def runner(e, w, st, att=ATT):
    return sh([PY, str(w / "home" / "r4e-run" / "run" / "r4e_run.py"), st, "--tool", str(w / "home" / "sgxfive-test-s1b"),
               "--bins", str(w / "home" / "r4e-run" / "bins"), "--out", str(w / "home" / "r4e-out" / att)], e)


def lapdir(w, st, att=ATT):
    return w / "home" / "r4e-out" / att / st


def laprec(w, st, job, att=ATT):
    p = lapdir(w, st, att) / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def stage_json(w, st, att=ATT):
    p = lapdir(w, st, att) / "stage.json"
    return json.loads(p.read_text()) if p.exists() else {}


def trace(w):
    p = w / "mock" / "trace"
    return p.read_text().splitlines() if p.exists() else []


def score_txt(w, st, att=ATT):
    p = w / "out" / att / f"score-{st}.txt"
    return p.read_text() if p.exists() else ""


def summary(w, st, att=ATT):
    return next((ln for ln in score_txt(w, st, att).splitlines() if ln.startswith("SUMMARY")), "")


def score_now(w, st, att=ATT):
    """The SUMMARY of a stage the driver did not score (it stopped on the runner's exit): the scorer on the copied directory."""
    sys.path.insert(0, str(R4 / "score"))
    import score_r4e
    S, summ = score_r4e.score(st, w / "out" / att / st, R4)
    return "SUMMARY: " + summ


def verdicts(s, names):
    """{hypothesis: its word} from a SUMMARY line ('H-PEND consistent (4 row groups), H-NOEVENT REFUTED')."""
    out = {}
    for n in names:
        m = re.search(re.escape(n) + r" (consistent|REFUTED|mixed|cannot tell)", s)
        out[n] = m.group(1) if m else None
    return out


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


# ---- static ------------------------------------------------------------------------------------------------------------------------
@test
def t_freeze_and_guard():
    rc, o = sh([str(R4 / "run" / "freeze_r4e.sh"), "verify"], dict(os.environ, PY=PY, RESGX545=WT))
    ok(rc == 0 and "files verified" in o, f"the frozen files of this directory verify ({o.strip().splitlines()[-1] if o.strip() else ''})")
    rc, o = sh([str(R4 / "run" / "guard_r4e.sh")], dict(os.environ, PYTHON=PY, RESGX545=WT))
    ok(rc == 0 and "guard: clean" in o, f"guard_r4e.sh is clean ({o.strip()[-200:]})")
    fc = R4 / "FROZEN.commits"
    pins = [ln for ln in fc.read_text().splitlines() if ln and not ln.startswith("#")] if fc.exists() else []
    ok(bool(pins) and all(ln.split()[1].startswith("5a13042") or ln.split()[1] == "untracked" for ln in pins),
       f"FROZEN.commits pins every file of the tree to 5a13042 ({len(pins)} pins)")


@test
def t_guard_catches():
    c = copy_tree("guard")
    e = dict(os.environ, PYTHON=PY, RESGX545=WT)

    def guard_with(path, old, new, label, binary=False):
        p = c / path
        orig = p.read_bytes()
        if binary:
            p.write_bytes(orig[:100] + bytes([orig[100] ^ 1]) + orig[101:])
        else:
            t = orig.decode()
            assert not old or old in t, f"{label}: {old!r} not in {path}"
            p.write_text(t.replace(old, new, 1) if old else t + new)
        rc, o = sh([str(c / "run" / "guard_r4e.sh")], e)
        p.write_bytes(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")

    def guard_json(path, fn, label):
        p = c / path
        orig = p.read_text()
        t = json.loads(orig)
        fn(t)
        p.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
        rc, o = sh([str(c / "run" / "guard_r4e.sh")], e)
        p.write_text(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")
    guard_with("run/r4e.sh", "", "\nwhile true; do sleep 1; done\n", "a wait loop in the driver")
    guard_with("run/r4e.sh", "", "\necho N > /sys/kernel/debug/dri/0/sgx/hold_recovery\n", "an unprivileged debugfs write")
    guard_with("run/r4e.sh", "", "\nset -f\n", "set -f in a script")
    guard_with("run/r4e.sh", "", "\nreboot\n", "a reboot in a script")
    guard_with("run/r4e.sh", "sudo -n python3 ~/$LD/run/r4e_run.py", "python3 ~/$LD/run/r4e_run.py", "the runner without sudo")
    guard_with("run/r4e_run.py", "", "\nFR.wr(\"render_rgn_arrays\", \"1\")\n", "a debugfs write off the allow-list in the runner")
    guard_with("run/r4e_run.py", "", "\nlines = FR.dmesg_new(0)\n", "a kernel log sliced by a line count")
    guard_with("run/r4e_run.py", "", "\nFR.wr(\"kregnow\", \"0x0c04=0x1\")\n", "a kregnow write outside ops_e3p.py")
    guard_with("run/r4e_run.py", "os.open(KMSG, os.O_WRONLY | os.O_APPEND)", "open(KMSG, \"a\").fileno()", "kmsg opened in mode a")
    guard_with("run/r4e_run.py", "signal.SIGTERM", "signal.SIGUSR1", "a runner without the trap")
    guard_with("run/ops_e3p.py", 'f"0x0134=0x{value:x}"', 'f"0x0114=0x{value:x}"', "a CLEAR2 write by the host")
    guard_with("run/ops_e3p.py", "", "\nFR.wr(\"kregnow\", \"0x0c04=0x1\")\n", "a kregnow write of a BIF register")
    guard_with("run/ops_kicker2.py", 'FR.wr(L.KICK_NO_BUMP_FILE, "Y")', 'FR.wr(L.KICK_NO_BUMP_FILE, "N")', "a kick_no_bump write that is not Y")
    guard_with("run/ops_kicker2.py", "", "\nFR.wr(L.KICKER_FILE, \"=0x43\")\n", "a kicker write that is not the table's word")
    guard_with("run/ops_e3p.py", 'self.knob("hold_recovery", j["hold_recovery"])', 'self.knob("rtds_keep", "Y")', "a knob other than hold_recovery")
    guard_with("bins/ring_exit2.blob", None, None, "a blob byte changed", binary=True)
    guard_with("bins/ring_hold.blob", None, None, "ring_hold's bytes changed", binary=True)
    guard_with("asm/ring_skip3p.s", "@entry 0", "@entry 0\n        str #77, r10", "a firmware str added to a source")
    guard_with("asm/ring_exit2.s", "endp:\n        idf drc0, bif\n        wdf drc0\n        own_end", "endp:\n        idf drc0, bif\n        wdf drc0\n        nop.end",
               "an own end without the phase end (the lint and the block check)")
    (c / "asm" / "ring_extra.s").write_text("; an unknown source\n")
    rc, o = sh([str(c / "run" / "guard_r4e.sh")], e)
    (c / "asm" / "ring_extra.s").unlink()
    ok(rc == 1 and "an unknown source" in o, f"the guard refuses an unknown source (rc {rc})")
    guard_json("tables/kp.json", lambda t: [j.update(may_stop=True) for j in t["jobs"] if j["row"] == "E0"], "a control row that may stop")
    guard_json("tables/kp.json", lambda t: [j.update(trigger="kick") for j in t["jobs"] if j["row"] == "KP"], "a bare kick as a trigger")
    guard_json("tables/e3p.json", lambda t: [j.update(clear_values=[0x8000, 0x20000000]) for j in t["jobs"] if j["row"] == "B1P"],
               "a CLEAR value off the allow-list (bit 29)")
    guard_json("tables/kb2.json", lambda t: [j.update(set_kicker=0x43) for j in t["jobs"] if j["row"] == "Q2P"], "a kicker word that is not 0x42")
    guard_json("tables/e3p.json", lambda t: t.update(arm="slots=0xf entry=0,1,2,3 trc=1"), "an arm line off the allow-list")


@test
def t_landed_api():
    """Every landed fwtask_run name the runner and the op modules use exists in the landed file, with the arguments they pass."""
    sys.path.insert(0, f"{WT}/tools/fwtask")
    sys.path.insert(0, str(R4 / "tests" / "mockfw"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("landed_fwtask_run", f"{WT}/tools/fwtask/fwtask_run.py")
    landed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(landed)
    names = set()
    for f in ("r4e_run.py", "ops_kicker2.py", "ops_e3p.py"):
        names |= set(re.findall(r"\bFR\.([A-Za-z_]+)", (R4 / "run" / f).read_text()))
    missing = sorted(n for n in names if not hasattr(landed, n) and n != "D")
    ok(not missing, f"every FR.name the runner uses exists in the landed fwtask_run.py ({sorted(names)}; missing {missing})")
    for n, nargs in (("wr", 2), ("rd", 1), ("miscinfo", 0), ("regs", 0), ("alive", 0), ("tick_rate", 1), ("health", 0), ("dmesg_new", 1),
                     ("hang_dump", 2), ("sh", 2), ("is_bad_log", 1)):
        sig = inspect.signature(getattr(landed, n))
        ok(len([p for p in sig.parameters.values() if p.default is p.empty]) <= nargs, f"landed {n}{sig} accepts the runner's {nargs} arguments")
    for n in ("cmd_arm", "cmd_reset", "cmd_gate"):
        ok(len(inspect.signature(getattr(landed, n)).parameters) == 1, f"landed {n}(a) takes one argument dict")
    for m in ("r", "w", "page", "close"):
        ok(hasattr(landed.Res, m), f"landed Res has {m}")
    os.environ.setdefault("MOCK_DIR", str(BASE))
    import fwtask_run as mock
    for n in names - {"D"}:
        ok(hasattr(mock, n), f"the mock has FR.{n} (the runner runs against it)")


# ---- the default session, end to end ---------------------------------------------------------------------------------------------
DEBUGFS_WRITE = re.compile(r"^[0-9.]+ wr (\S+) ?(.*)$")


@test
def t_default_session():
    """The default world (H-CNT, H-PEND, H-PHAS-ANY, H-LEVEL, H-W): the whole session through the driver: kb2, kp, e3p."""
    w, e, c = staged("default")
    rc, o = session(e, c)
    ok(rc == 0 and "R4e mock1 done" in o, f"the session exits 0 (rc {rc}: {o.strip()[-300:]})")
    for st in STAGES:
        sj = stage_json(w, st)
        ok(sj.get("exit") == 0 and sj.get("jobs_run") == JOBS[st], f"{st}: exit 0, every job in the frozen order ({sj.get('exit')}, {len(sj.get('jobs_run', []))} jobs)")
        ok(sj.get("stops") == 0, f"{st}: no stop ({sj.get('stops')})")
    ok(len(ALL_JOBS) == 18, f"18 jobs in all ({len(ALL_JOBS)})")
    s = summary(w, "kb2")
    v = verdicts(s, ("H-LATCH", "H-CNT", "H-HWC", "H-PEND", "H-NOEVENT", "H-LATE"))
    ok(v["H-CNT"] == "consistent" and v["H-LATCH"] == "REFUTED" and v["H-HWC"] == "REFUTED", f"kb2: the count byte is H-CNT's ({v}; {s[:300]})")
    ok(v["H-PEND"] == "consistent" and v["H-NOEVENT"] == "REFUTED" and v["H-LATE"] == "REFUTED", f"kb2: an unbumped kick is pending ({v})")
    ok("G0P timing held" in s and "stops 0" in s, "kb2: the timing control held, no stop")
    s = summary(w, "kp")
    v = verdicts(s, ("H-PHAS-ANY", "H-KICK-MORE"))
    ok(v == {"H-PHAS-ANY": "consistent", "H-KICK-MORE": "REFUTED"} and "E0 and FK held" in s, f"kp: H-PHAS-ANY ({v}; {s[:260]})")
    s = summary(w, "e3p")
    v = verdicts(s, ("H-PHAS-ANY", "H-SLOT3-MORE", "H-LEVEL", "H-PULSE", "H-W", "H-ALL", "H-NONE"))
    ok(v["H-PHAS-ANY"] == "consistent" and v["H-SLOT3-MORE"] == "REFUTED" and v["H-LEVEL"] == "consistent" and v["H-PULSE"] == "REFUTED"
       and v["H-W"] == "consistent" and v["H-ALL"] == "REFUTED" and v["H-NONE"] == "REFUTED" and "B0 held" in s, f"e3p: H-PHAS-ANY, H-LEVEL, H-W ({v}; {s[:300]})")
    # every frozen row is measurable in the default world: nothing is cannot tell but the stop-only P3 rows (the rows read what the records hold)
    sys.path.insert(0, str(R4 / "score"))
    import score_r4e
    for st in STAGES:
        S, _ = score_r4e.score(st, w / "out" / ATT / st, R4)
        none_rows = sorted({(c, q) for (c, q, m, k, okk, n) in S.t.rows if okk is None and q != "p3_answered"})
        ok(not none_rows, f"{st}: every frozen row has a measurement in the default world ({none_rows[:4]})")
        ok(len(S.t.rows) == len(S.preds), f"{st}: every frozen row was scored ({len(S.t.rows)} of {len(S.preds)})")
    # the load step ran before the first runner: the ssh log has the health call first
    calls = (w / "mock" / "ssh.log").read_text().splitlines()
    ih = next((i for i, x in enumerate(calls) if x.startswith("ssh bash ~/r4e-run/run/health_remote.sh")), None)
    ir = next((i for i, x in enumerate(calls) if x.startswith("ssh sudo -n python3 ~/r4e-run/run/r4e_run.py")), None)
    ok(ih is not None and ir is not None and ih < ir, "the load step (a fill and a triangle) runs before the first stage")
    ok((w / "out" / ATT / "health-load.txt").exists(), "the load step's output is kept")
    # the debugfs writes of the whole session, by name: nothing but the allow-list
    tr = trace(w)
    names = {}
    for ln in tr:
        m = DEBUGFS_WRITE.match(ln)
        if m:
            names.setdefault(m.group(1), set()).add(m.group(2).strip())
    ok(set(names) <= {"own_code", "own_arm", "load", "boot", "reset", "kicker", "kick_no_bump", "hold_recovery", "kregnow"},
       f"the debugfs writes are on the allow-list ({sorted(names)})")
    ok(names.get("kicker") == {"=66"}, f"the kicker is only ever written =0x42 ({names.get('kicker')})")
    ok(names.get("kick_no_bump", set()) <= {"Y", "N"} and "Y" in names.get("kick_no_bump", set()), f"kick_no_bump Y ({names.get('kick_no_bump')})")
    ok(names.get("kregnow") == {"0x0134=0x8000", "0x0134=0x40000"}, f"kregnow: only CLEAR (0x0134) bits 15 and 18 ({names.get('kregnow')})")
    ok(names.get("hold_recovery", set()) <= {"Y", "N"} and (w / "mock" / "dbg" / "hold_recovery").read_text() == "N", "hold_recovery ends N")
    ok((w / "mock" / "dbg" / "kick_no_bump").read_text() == "N", "kick_no_bump ends N")
    # every job's kernel-log slice is its own marker's, and marked r4e
    for st in STAGES:
        for j in JOBS[st]:
            d = (lapdir(w, st) / f"{j}.dmesg").read_text()
            r = laprec(w, st, j)
            ok("(kernel log marker not found" not in d and "marker not in dmesg" not in r["note"] and r["log_bad"] == [],
               f"{st}/{j}: the log is the slice after its own case marker, no bad line")
    ok("resgx545 r4e " in (w / "mock" / "kmsg").read_text() and "resgx545 r4b" not in (w / "mock" / "kmsg").read_text(), "the kernel-log markers are r4e's")
    # resets: kb2 one before every job's arm and one at the end; kp one at KP's arm (its arm is the stage's, reset_arm) ...
    resets = sum(1 for x in tr if x.endswith(" reset"))
    ok(resets == 10 + 1 + 0 + 2 + 5 + 1 + 3 or resets > 20, f"resets counted ({resets})")


@test
def t_job_shapes():
    """What each job does, in the kept records of the default session."""
    w, e, c = staged("shapes")
    rc, o = session(e, c, ATT)
    ok(rc == 0, f"the session runs (rc {rc})")
    g = laprec(w, "kb2", "g0p")
    ok(g["job"]["pre_ms"] == 1 and g["kicker_after"]["raw"] == "kicker 3 ccbctl 3 3 kicks 3" and "sig_after_timeout" not in g,
       f"g0p: one ordinary kick, the file after reads 3 3 3 ({g['kicker_after']['raw']})")
    q2 = laprec(w, "kb2", "q2p")
    ok(q2["kicker_after_set"]["w"] == 66 and q2["kicker_after"]["raw"] == "kicker 67 ccbctl 3 3 kicks 3", f"q2p: W set before the window, 0x43 after the kick ({q2['kicker_after']['raw']})")
    ok(q2["stamp_before_kick"] - q2["window_stamp"] > 0, "q2p: the call's stamp is after the window's")
    q3 = laprec(w, "kb2", "q3p")
    ok(q3["no_bump_set"] == "Y" and q3["no_bump_after"] == "N" and q3["kick"]["answered"] is False and q3["class"] == "kick-timeout"
       and len(q3["sig_after_timeout"]) == 2, "q3p: kick_no_bump set before the window, read back N, the call not answered, the signature taken twice")
    ok(q3["kicker_after"]["raw"] == "kicker 2 ccbctl 3 2 kicks 3", f"q3p: the file after reads E819's (kicker 2 ccbctl 3 2 kicks 3): {q3['kicker_after']['raw']}")
    q4 = laprec(w, "kb2", "q4")
    ok(q4["q4_done"] and q4["q4"]["kicker_after"]["wofs"] == 4 and q4["q4"]["kicker_after"]["rofs"] == 4 and q4["q4"]["kick"]["answered"],
       f"q4: the second window ran, one ordinary kick after the unbumped one (ccbctl {q4['q4']['kicker_after']['wofs']} {q4['q4']['kicker_after']['rofs']})")
    ok(q4["page"] != q4["q4"]["page"], "q4: the second window has its own page")
    kp = laprec(w, "kp", "kp")
    ok(kp["job"]["trigger"] == "miscinfo" and kp["page"][L.ACTED] == 1 and kp["page"][L.ACT_SEEN] == 4 and kp["class"] == "kick-timeout"
       and "pre_reset" in kp, f"kp: a kick pass acted (ACTED 1, ACT_SEEN 4), the call not answered, reset + arm before it ({kp['class']})")
    ok("pre_reset" not in laprec(w, "kp", "e0") and "pre_reset" not in laprec(w, "kp", "fk"), "kp: E0 and FK run under the stage's one arm (no reset between them)")
    ok(sorted(x.name for x in lapdir(w, "kp").glob("*arm*.json")) == sorted(["arm.json", "kp.arm.json", "kp-r2.arm.json"]), "kp: the stage's arm, then a reset + arm before each KP job")
    b1 = laprec(w, "e3p", "b1p")
    ok(b1["knobs"] == {"hold_recovery": "Y", "hold_recovery_after": "N"} and b1["slot3_seen"] and b1["skipped"] == 1 and b1["tool_returned_in_watch"] is False,
       f"b1p: hold_recovery Y during the job and N after, the slot 3 entry seen before the watch ({b1['knobs']})")
    ok(sorted(b1["clears"]) == ["bit15", "bit18"] and [r["ms_after"] for r in b1["clears"]["bit15"]["reads"]] == [1, 3]
       and [r["ms_after"] for r in b1["clears"]["bit18"]["reads"]] == [1, 3, 20], "b1p: bit 15 read at 1 and 3 ms, bit 18 at 1, 3 and 20 ms")
    ok(all(r["t_ms"] >= r["ms_after"] for k in b1["clears"] for r in b1["clears"][k]["reads"]), "b1p: every read is taken at or after its time from the write")
    ok(sorted(x.name for x in lapdir(w, "e3p").glob("*recovery*")) == ["b1p-r2-recovery-reset.json", "b1p-r3-recovery-reset.json", "b1p-recovery-reset.json"],
       "e3p: each B1P ends with a reset, the gate and the health")
    b0 = laprec(w, "e3p", "b0")
    ok(b0["knobs"]["hold_recovery"] == "N" and b0["tool_rc"] == 0 and "clears" in b0 and b0["clears"] == {}, "b0: hold_recovery N, the fill completes, no clear is written")


# ---- worlds ----------------------------------------------------------------------------------------------------------------------
def world(name, scenario, stage, upto=None):
    """Stage the mock, run the session with the stage given (the earlier stages run too), return (w, rc, output)."""
    w, e, c = staged(name, scenario)
    rc, o = session(e, c, ATT)
    return w, rc, o


@test
def t_kb2_worlds():
    names = ("H-LATCH", "H-CNT", "H-HWC", "H-PEND", "H-NOEVENT", "H-LATE")
    for sc, want in (("kb_latch", {"H-LATCH": "consistent", "H-CNT": "REFUTED", "H-HWC": "REFUTED", "H-PEND": "consistent"}),
                     ("kb_hwc", {"H-LATCH": "REFUTED", "H-CNT": "REFUTED", "H-HWC": "consistent", "H-PEND": "consistent"}),
                     ("noevent", {"H-CNT": "consistent", "H-PEND": "REFUTED", "H-NOEVENT": "consistent", "H-LATE": "REFUTED"}),
                     ("late", {"H-CNT": "consistent", "H-PEND": "REFUTED", "H-NOEVENT": "REFUTED", "H-LATE": "consistent"})):
        w, rc, o = world("kb2-" + sc, sc, "kb2")
        s = summary(w, "kb2")
        v = verdicts(s, names)
        ok(all(v[k] == val for k, val in want.items()), f"world {sc}: {want} (got {v}; rc {rc})")
        ok(stage_json(w, "kb2").get("jobs_run") == JOBS["kb2"] and stage_json(w, "kb2").get("stops") == 0, f"world {sc}: every kb2 job ran, no stop")
        if sc == "noevent":
            q4 = laprec(w, "kb2", "q4")
            ok(q4["q4"]["kicker_after"]["wofs"] == 4 and q4["q4"]["kicker_after"]["rofs"] == 3, "world noevent: Q4 reads ccbctl 4 3")


@test
def t_kb2_timing_control_stops_the_stage():
    w, rc, o = world("kb2-nokick", "nokick_entry", "kb2")
    sj = stage_json(w, "kb2")
    ok(rc == 8 and sj.get("exit") == 8 and sj.get("jobs_run") == ["g0p"], f"a G0P without a kick entry in the ring stops the stage after the first job (rc {rc}, {sj.get('jobs_run')})")
    ok("timing control failed" in sj.get("why", ""), f"the reason is named ({sj.get('why', '')[:120]})")
    s = summary(w, "kb2")
    ok("G0P NOT held" in s, f"the scorer says the control did not hold ({s[:200]})")
    ok(not (w / "out" / ATT / "kp").exists(), "kp does not run after it (the session ends at exit 8)")


@test
def t_kp_worlds():
    w, rc, o = world("kp-more", "kp_more", "kp")
    sj = stage_json(w, "kp")
    s = summary(w, "kp")
    v = verdicts(s, ("H-PHAS-ANY", "H-KICK-MORE"))
    ok(sj.get("exit") == 0 and sj.get("stops") == 1 and sj["classes"]["kp"] == "stop" and sj["classes"].get("kp-r2") == "skipped",
       f"H-KICK-MORE: KP stops, signed, never replicated, the stage ends at exit 0 ({sj.get('exit')}, {sj.get('classes')})")
    ok(v == {"H-PHAS-ANY": "REFUTED", "H-KICK-MORE": "consistent"}, f"H-KICK-MORE consistent ({v}; {s[:300]})")
    rec = laprec(w, "kp", "kp")
    ok(rec["stopped"] and rec["p3"]["answered"] is False and rec["sig"]["samples"], "the KP stop carries the signature twice and P3 (not answered)")
    ok((lapdir(w, "kp") / "stop1-kp-reset.json").exists() and (lapdir(w, "kp") / "stop-kp-status.txt").exists(), "the stop was dumped, reset and gated")
    ok(rc == 8 or "e3p" in o or sj.get("exit") == 0, "the session goes on to e3p after kp's one budgeted stop")
    ok(stage_json(w, "e3p").get("exit") == 0, "e3p ran after kp's stop (the gate accepts exit 0)")
    w, rc, o = world("kp-fk", "fk_stop", "kp")
    sj = stage_json(w, "kp")
    ok(rc == 8 and sj.get("exit") == 8 and sj.get("jobs_run") == ["e0", "fk"], f"FK (a control) stopping ends the stage at once: exit 8 ({rc}, {sj.get('jobs_run')})")
    s = summary(w, "kp")
    ok("E0/FK NOT held" in s, f"the scorer reports the failed control ({s[:200]})")
    ok(not (w / "out" / ATT / "e3p").exists(), "e3p does not run after it")


@test
def t_e3p_worlds():
    w, rc, o = world("e3p-more", "e3p_more", "e3p")
    sj = stage_json(w, "e3p")
    s = summary(w, "e3p")
    v = verdicts(s, ("H-PHAS-ANY", "H-SLOT3-MORE", "H-LEVEL", "H-W"))
    ok(rc == 8 and sj.get("exit") == 8 and sj.get("jobs_run") == ["b0", "b1p"] and sj["classes"]["b1p"] == "stop",
       f"H-SLOT3-MORE: B1P stops, the stage ends at its first stop (rc {rc}, {sj.get('classes')})")
    ok(v["H-SLOT3-MORE"] == "consistent" and v["H-PHAS-ANY"] == "REFUTED" and v["H-LEVEL"] == "consistent" and v["H-W"] == "consistent",
       f"H-SLOT3-MORE consistent, and the clears still read on the stopped EDM ({v})")
    rec = laprec(w, "e3p", "b1p")
    ok(rec["stopped"] and rec["p3"]["answered"] is False and sorted(rec["clears"]) == ["bit15", "bit18"], "the stopped B1P was signed, written, then P3")
    for sc, want in (("e3p_pulse", {"H-LEVEL": "REFUTED", "H-PULSE": "consistent"}), ("c_all", {"H-ALL": "consistent", "H-W": "REFUTED"}),
                     ("c_none", {"H-NONE": "consistent", "H-W": "REFUTED"})):
        w, rc, o = world("e3p-" + sc, sc, "e3p")
        s = summary(w, "e3p")
        v = verdicts(s, ("H-LEVEL", "H-PULSE", "H-ALL", "H-W", "H-NONE"))
        sj = stage_json(w, "e3p")
        ok(all(v[k] == val for k, val in want.items()), f"world {sc}: {want} (got {v})")
        ok(sj.get("exit") == 0 and sj.get("jobs_run") == JOBS["e3p"], f"world {sc}: every e3p job ran")
    w, rc, o = world("e3p-noslot3", "no_slot3", "e3p")
    s = score_now(w, "e3p")
    sj = stage_json(w, "e3p")
    b = laprec(w, "e3p", "b0")
    ok(rc == 4 and sj.get("jobs_run") == ["b0"] and b["slot3_seen"] is False, f"no slot 3 entry: B0's wait times out and its fill fails: the stage ends at B0 (rc {rc}, {sj.get('jobs_run')})")
    ok("B0 not read" in s and "controls not all PASS" in s, f"the scorer reports the control as not read ({s[:200]})")
    w, rc, o = world("e3p-b0fail", "fill_fail", "e3p")
    s = score_now(w, "e3p")
    ok(rc == 4 and "B0 not read" in s and "controls not all PASS" in s, f"a B0 whose fill fails ends the stage and gates the B1P rows (rc {rc}: {s[:200]})")


# ---- refusals, traps, stops ----------------------------------------------------------------------------------------------------------
@test
def t_preflight_refusals():
    def refused(name, why, scenario="", st="kb2", **kw):
        if kw.get("srcv"):
            w, e, c = env_for(name, scenario, **kw)
            sh(["bash", str(c / "run" / "stage_r4e.sh")], e)        # the files are copied; only its last check (the module) refuses
        else:
            w, e, c = staged(name, scenario, **kw)
        rc, o = runner(e, w, st)
        tr = trace(w)
        ok(rc == 1 and not any(re.search(r" (reset|arm|wr) ", x) or x.endswith(" reset") for x in tr),
           f"the preflight refuses {why}, nothing touched (rc {rc}: {o.strip()[-160:]})")
        return w, e, c
    refused("nofw", "a firmware that is not running (no load step)", "nofw")
    refused("knob", "render_rgn_arrays not at its default 0", knobs={"render_rgn_arrays": "0x00000001"})
    refused("knob2", "hold_recovery Y", knobs={"hold_recovery": "Y"})
    refused("knob3", "kick_no_bump Y", knobs={"kick_no_bump": "Y"})
    refused("oldmod", "E817's module 230E0EF5", srcv="230E0EF50FFFD606C53AE3C")
    w, e, c = staged("gate")
    rc, o = runner(e, w, "kp")
    ok(rc == 1 and "does not run" in o, f"kp refuses to run without kb2's kept stage.json (rc {rc}: {o.strip()[-120:]})")
    rc, o = runner(e, w, "e3p")
    ok(rc == 1 and "does not run" in o, f"e3p refuses to run without kp's kept stage.json (rc {rc})")
    # an attempt is never overwritten: the driver refuses an existing attempt directory, the runner a kept stage.json
    w, e, c = staged("again")
    session(e, c)
    rc, o = session(e, c)
    ok(rc == 22, f"the driver refuses an existing attempt (rc {rc})")
    rc, o = runner(e, w, "kb2")
    ok(rc == 1 and "exists" in o, f"the runner refuses an output directory that holds a kept stage (rc {rc}: {o.strip()[-120:]})")
    # the load step fails: the runner is not started
    w, e, c = staged("loadfail", "tool_fail")
    rc, o = session(e, c, "lf")
    calls = (w / "mock" / "ssh.log").read_text().splitlines()
    ok(rc == 31 and not any(x.startswith("ssh sudo -n python3 ~/r4e-run/run/r4e_run.py") for x in calls), f"a failed load step stops before the first stage (rc {rc})")
    # a frozen file changed on the Mac: the driver stops
    w, e, c = staged("frozen")
    (c / "gen" / "r4layout.py").write_text((c / "gen" / "r4layout.py").read_text() + "\n# changed\n")
    rc, o = session(e, c)
    ok(rc == 20, f"a changed frozen file stops the driver (rc {rc})")
    # a file on the laptop that is not the frozen one
    w, e, c = staged("lapfile")
    f = w / "home" / "r4e-run" / "tables" / "kb2.json"
    f.write_text(f.read_text().replace('"stage": "kb2"', '"stage":  "kb2"'))
    rc, o = runner(e, w, "kb2")
    ok(rc == 1 and "not the frozen file" in o, f"the runner refuses a laptop file that is not the frozen one (rc {rc})")


@test
def t_fatal_and_errors():
    w, e, c = staged("fatal", "fatal@q2p")
    rc, o = session(e, c)
    ok(rc == 3, f"a watchdog line in q2p's log stops all laptop work: exit 3 (rc {rc})")
    ok(stage_json(w, "kb2").get("exit") == 3, "the stage record says exit 3")
    w, e, c = staged("boom", "boom@q3p")
    rc, o = session(e, c)
    ok(rc == 4 and (w / "mock" / "dbg" / "kick_no_bump").read_text() == "N", f"an exception in q3p: exit 4, the knobs are back to N (rc {rc})")
    w, e, c = staged("boom2", "boom@b1p")
    rc, o = session(e, c)
    ok(rc == 4 and (w / "mock" / "dbg" / "hold_recovery").read_text() == "N", f"an exception in b1p: exit 4, hold_recovery back to N (rc {rc})")
    w, e, c = staged("armbad", "armfail")
    rc, o = session(e, c)
    ok(rc == 4 and stage_json(w, "kb2").get("jobs_run") == ["g0p"], f"an arm that fails stops at the first job (rc {rc})")
    w, e, c = staged("gatefail", "gatefail")
    rc, o = session(e, c)
    ok(rc != 0, f"a gate that fails ends the session (rc {rc})")
    w, e, c = staged("latebad", "latebad")
    rc, o = session(e, c)
    ok(rc == 38, f"a hung line in a stage's kernel log (not e3p) stops after the stage (rc {rc})")


@test
def t_trap_restores_knobs():
    """SIGTERM during B1P (hold_recovery Y): the finally blocks and the exit handler put the knob back."""
    w, e, c = staged("trap", "")
    for st, att in (("kb2", ATT), ("kp", ATT)):
        rc, o = runner(e, w, st, att)
        assert rc == 0, o[-300:]
    e2 = dict(e, MOCK_TOOL_WAIT="6")
    p = subprocess.Popen([PY, str(w / "home" / "r4e-run" / "run" / "r4e_run.py"), "e3p", "--tool", str(w / "home" / "sgxfive-test-s1b"),
                          "--bins", str(w / "home" / "r4e-run" / "bins"), "--out", str(w / "home" / "r4e-out" / ATT)], env=e2,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    hr = w / "mock" / "dbg" / "hold_recovery"
    seen = False
    for _ in range(600):
        time.sleep(0.05)
        if hr.exists() and hr.read_text().strip() == "Y":
            seen = True
            break
    ok(seen, "hold_recovery reads Y while B1P runs")
    p.send_signal(signal.SIGTERM)
    try:
        out, _ = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
    ok(hr.read_text().strip() == "N", f"after SIGTERM hold_recovery reads N ({hr.read_text().strip()}; rc {p.returncode})")
    ok(p.returncode != 0 and (lapdir(w, "e3p") / "stage.json").exists(), f"the runner exits non-zero and writes its stage record (rc {p.returncode})")


@test
def t_knob_values_never_left():
    """Across the default session no knob was left set: the last write of each knob is N."""
    w, e, c = staged("knobs")
    rc, o = session(e, c)
    last = {}
    for ln in trace(w):
        m = DEBUGFS_WRITE.match(ln)
        if m and m.group(1) in ("hold_recovery", "kick_no_bump"):
            last[m.group(1)] = m.group(2).strip()
    ok(last.get("hold_recovery") == "N" and last.get("kick_no_bump") in (None, "N"), f"the last writes are N ({last})")


@test
def t_stage_resume():
    """The driver resumes at a stage with --from (its gate is the earlier stage's kept stage.json)."""
    w, e, c = staged("resume", "fk_stop")
    rc, o = session(e, c, ATT)
    ok(rc == 8 and stage_json(w, "kp").get("exit") == 8, f"kp ends at exit 8 (rc {rc})")
    rc, o = session(e, c, ATT, "--from", "e3p")
    ok(rc != 22 and stage_json(w, "e3p"), f"--from e3p resumes in the same attempt (gate: kp finished with exit 8) (rc {rc})")
    rc, o = session(e, c, "nothere", "--from", "kp")
    ok(rc == 22, f"--from needs an existing attempt (rc {rc})")


if __name__ == "__main__":
    run_tests()
    print(f"{len(RAN)} tests, {len(FAIL)} failed" if FAIL else f"{len(RAN)} tests, all passed")
    sys.exit(1 if FAIL else 0)
