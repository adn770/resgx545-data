#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: R5-events (stages h1, h2, h3) end to end against a mock laptop.  Nothing touches the laptop.  R4-events' run_mock.py
adapted: the real scripts run on a COPY of this directory (its pinned tool hash is the fake tool's, its freeze is redone there):
run/stage_r5e.sh and run/r5e.sh with the ssh, scp, sudo, sha256sum, python3, modinfo and dmesg shims (tests/shims), the laptop runner
run/r5e_run.py with the fake fwtask_run (tests/mockfw: a simulated EDM on the API of the landed file), the fake tool (tests/fake_tool.sh in
front of tests/fake_tool.py) and the scorer score/score_r5e.py.  The mock answers by what the runner WROTE (the clock knob, the page's skip
flag, the CLEAR values, the miscinfo, the tool's argv), never by a job's name; MOCK_SCENARIO picks the world (tests/mockfw/kmock.py).

The argv-twin test (round 5): every job's applied commands, read from the mock's trace and the tool's log, against PLAN_ROWS, a transcription
of the plan's table (exp-events-r5.md section 5 and DECISIONS-R5.md) written here by hand and NOT derived from r5layout.

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
R5 = pathlib.Path(__file__).resolve().parent.parent
PY = os.environ.get("PY", "/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python")
WT = os.environ.get("RESGX545", "/Users/jtorra/src/resgx545")
FAIL, RAN, TESTS = [], [], []
ONLY = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r5emock-"))
sys.path.insert(0, str(R5 / "gen"))
import r5layout as L  # noqa: E402

ATT = "mock1"
STAGES = L.STAGES
JOBS = {st: [L.rep_name(r, k) for r in L.ROW_ORDER[st] for k in range(L.ROW_SPEC[st][r]["reps"])] for st in STAGES}
ALL_JOBS = [j for st in STAGES for j in JOBS[st]]

# The plan's rows, transcribed by hand from closing5/events/exp-events-r5.md section 5 (table, h1/h2/h3 rows) and DECISIONS-R5.md R5-3,
# R5-4, R5-7 (a): (job, clock, skip, hold_recovery while the fill runs, clears: none | late (after the watch) | early (at the slot 3
# entry, then one miscinfo), the tool's argv).
PLAN_ROWS = {
    "h1": [("b0", 0, 0, "N", "none"), ("b1p", 0, 1, "Y", "late"), ("b1p-r2", 0, 1, "Y", "late"), ("b1p-r3", 0, 1, "Y", "late")],
    "h2": [("b0a", 800000, 0, "N", "none"), ("b1pa", 800000, 1, "Y", "none"), ("b1pa-r2", 800000, 1, "Y", "none"),
           ("b0b", 1600000, 0, "N", "none"), ("b1pb", 1600000, 1, "Y", "none"), ("b1pb-r2", 1600000, 1, "Y", "none")],
    "h3": [("b0", 1600000, 0, "N", "none"), ("b1e", 1600000, 1, "Y", "early"), ("b1e-r2", 1600000, 1, "Y", "early"),
           ("b1e-r3", 1600000, 1, "Y", "early")],
}
PLAN_TOOL_ARGV = "fill"


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
    dst = BASE / name / "r5"
    shutil.copytree(R5, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "*.pyc", "debug"))
    (dst / "debug").mkdir()
    h = hashlib.sha256((dst / "tests" / "fake_tool.sh").read_bytes()).hexdigest()
    (dst / "TOOL.sha256").write_text(f"{h}  /home/jtorra/sgxfive-test-s1b\n")
    rc, o = sh([str(dst / "run" / "freeze_r5e.sh"), "freeze"], e=dict(os.environ, PY=PY, RESGX545=WT), cwd=str(dst))
    assert rc == 0, o
    return dst


def env_for(name, scenario="", knobs=None, srcv="MOCKSRCV", copy=None):
    w = BASE / name
    c = copy or copy_tree(name)
    mock, home, out = w / "mock", w / "home", w / "out"
    for d in (mock / "dbg", home, out):
        d.mkdir(parents=True, exist_ok=True)
    dri = mock / "sysdebug" / "dri"
    (dri / "0").mkdir(parents=True, exist_ok=True)
    for n_, tgt in (("0/sgx", "../../../dbg"), ("128", "0"), ("0000:00:02.0", "0")):
        if not (dri / n_).exists():
            os.symlink(tgt, dri / n_)
    shutil.copy(c / "tests" / "fake_tool.py", home / "fake_tool.py")
    for t, src in (("sgxfive-test", "fake_tool.py"), ("sgxfive-test-s1b", "fake_tool.sh")):
        p = home / t
        p.write_text((c / "tests" / src).read_text())
        p.chmod(0o755)
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo", "kregnow"):
        (mock / "dbg" / f).write_text("")
    kn = {"kick_no_bump": "N", "render_rgn_arrays": "0x00000000", "hold_recovery": "N", "render_pb_pages": "0x00000422",
          "timer_clock": "0x00000000"}
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
              "PY": PY, "PYTHON": PY, "SGX_LOCAL_ENV": "/nonexistent", "SGX_TARGET_HOST": "mock@laptop", "RESGX545": WT,
              "PYTHONDONTWRITEBYTECODE": "1"})
    return w, e, c


def staged(name, scenario="", **kw):
    w, e, c = env_for(name, scenario, **kw)
    rc, o = sh(["bash", str(c / "run" / "stage_r5e.sh")], e)
    assert rc == 0, f"staging: {o[-800:]}"
    return w, e, c


def session(e, c, att=ATT, *args):
    return sh(["bash", str(c / "run" / "r5e.sh"), att] + list(args), e)


def runner(e, w, st, att=ATT):
    return sh([PY, str(w / "home" / "r5e-run" / "run" / "r5e_run.py"), st, "--tool", str(w / "home" / "sgxfive-test-s1b"),
               "--bins", str(w / "home" / "r5e-run" / "bins"), "--out", str(w / "home" / "r5e-out" / att)], e)


def lapdir(w, st, att=ATT):
    return w / "home" / "r5e-out" / att / st


def laprec(w, st, job, att=ATT):
    p = lapdir(w, st, att) / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def stage_json(w, st, att=ATT):
    p = lapdir(w, st, att) / "stage.json"
    return json.loads(p.read_text()) if p.exists() else {}


def trace(w):
    p = w / "mock" / "trace"
    return p.read_text().splitlines() if p.exists() else []


def summary(w, st, att=ATT):
    p = w / "out" / att / f"score-{st}.txt"
    t = p.read_text() if p.exists() else ""
    return next((ln for ln in t.splitlines() if ln.startswith("SUMMARY")), "")


def score_now(w, st, att=ATT):
    sys.path.insert(0, str(R5 / "score"))
    os.environ["R3_NO_FREEZE_CHECK"] = "1"
    import score_r5e
    S, summ = score_r5e.score(st, w / "out" / att / st, R5)
    return S, "SUMMARY: " + summ


def verdicts(s, names):
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


TRACE_RE = re.compile(r"^[0-9.]+ \[([^\]]*)\] (.*)$")


def per_job(w):
    """{job: [trace actions in order]} (the trace names the job of the kernel log's last case marker; a stage's jobs share names
    across stages only as b0, kept apart by order)."""
    out = []
    for ln in trace(w):
        m = TRACE_RE.match(ln)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


# ---- static ------------------------------------------------------------------------------------------------------------------------
@test
def t_freeze_and_guard():
    rc, o = sh([str(R5 / "run" / "freeze_r5e.sh"), "verify"], dict(os.environ, PY=PY, RESGX545=WT))
    ok(rc == 0 and "files verified" in o, f"the frozen files of this directory verify ({o.strip().splitlines()[-1] if o.strip() else ''})")
    rc, o = sh([str(R5 / "run" / "guard_r5e.sh")], dict(os.environ, PYTHON=PY, RESGX545=WT))
    ok(rc == 0 and "guard: clean" in o, f"guard_r5e.sh is clean ({o.strip()[-200:]})")
    fc, fp = R5 / "FROZEN.commits", R5 / "FROZEN.pin"
    pin = fp.read_text().strip() if fp.exists() else "?"
    pins = [ln for ln in fc.read_text().splitlines() if ln and not ln.startswith("#")] if fc.exists() else []
    ok(bool(pins) and all(ln.split()[1] in (pin, "untracked") for ln in pins), f"FROZEN.commits pins every file of the tree to FROZEN.pin ({pin[:7]}, {len(pins)} pins)")


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
        rc, o = sh([str(c / "run" / "guard_r5e.sh")], e)
        p.write_bytes(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")

    def guard_json(path, fn, label):
        p = c / path
        orig = p.read_text()
        t = json.loads(orig)
        fn(t)
        p.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
        rc, o = sh([str(c / "run" / "guard_r5e.sh")], e)
        p.write_text(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")
    guard_with("run/r5e.sh", "", "\nwhile true; do sleep 1; done\n", "a wait loop in the driver")
    guard_with("run/r5e.sh", "", "\necho 0 > /sys/kernel/debug/dri/0/sgx/timer_clock\n", "an unprivileged debugfs write")
    guard_with("run/r5e.sh", "", "\nset -f\n", "set -f in a script")
    guard_with("run/r5e.sh", "", "\nreboot\n", "a reboot in a script")
    guard_with("run/r5e.sh", "sudo -n python3 ~/$LD/run/r5e_run.py", "python3 ~/$LD/run/r5e_run.py", "the runner without sudo")
    guard_with("run/r5e_run.py", "", "\nFR.wr(\"render_rgn_arrays\", \"1\")\n", "a debugfs write off the allow-list in the runner")
    guard_with("run/r5e_run.py", "", "\nlines = FR.dmesg_new(0)\n", "a kernel log sliced by a line count")
    guard_with("run/r5e_run.py", "", "\nFR.wr(\"kregnow\", \"0x0c04=0x1\")\n", "a kregnow write outside ops_h.py")
    guard_with("run/r5e_run.py", "os.open(KMSG, os.O_WRONLY | os.O_APPEND)", "open(KMSG, \"a\").fileno()", "kmsg opened in mode a")
    guard_with("run/r5e_run.py", "signal.SIGTERM", "signal.SIGUSR1", "a runner without the trap")
    guard_with("run/r5e_run.py", "int(val) not in L.CLOCKS", "int(val) < 0", "a timer_clock check that is not the allow-list")
    guard_with("run/r5e_run.py", 'KNOB_BACK = {"hold_recovery": "N", "timer_clock": "0"}', 'KNOB_BACK = {"hold_recovery": "N", "timer_clock": "800000"}',
               "a timer_clock put back to something other than 0")
    guard_with("run/ops_h.py", 'f"0x0134=0x{value:x}"', 'f"0x0114=0x{value:x}"', "a CLEAR2 write by the host")
    guard_with("run/ops_h.py", "", "\nFR.wr(\"kregnow\", \"0x0c04=0x1\")\n", "a kregnow write of a BIF register")
    guard_with("run/ops_h.py", 'self.knob("hold_recovery", j["hold_recovery"])', 'self.knob("rtds_keep", "Y")', "a knob other than the two")
    guard_with("run/ops_h.py", "", "\nFR.wr(\"kicker\", \"=0x42\")\n", "a kicker write")
    guard_with("bins/ring_skip3p.blob", None, None, "a blob byte changed", binary=True)
    guard_with("asm/ring_skip3p.s", "@entry 0", "@entry 0\n        str #77, r10", "a firmware str added to the source")
    guard_with("gen/r5layout.py", "CLOCKS = (0, 800000, 1600000)", "CLOCKS = (0, 800000, 3200000)", "a clock value off the approved three")
    (c / "asm" / "ring_extra.s").write_text("; an unknown source\n")
    rc, o = sh([str(c / "run" / "guard_r5e.sh")], e)
    (c / "asm" / "ring_extra.s").unlink()
    ok(rc == 1 and "an unknown source" in o, f"the guard refuses an unknown source (rc {rc})")
    guard_json("tables/h1.json", lambda t: [j.update(may_stop=True) for j in t["jobs"] if j["row"] == "B0"], "a control row that may stop")
    guard_json("tables/h2.json", lambda t: [j.update(timer_clock=3200000) for j in t["jobs"] if j["row"] == "B1PB"], "a table clock off the allow-list")
    guard_json("tables/h2.json", lambda t: [j.update(timer_clock=0) for j in t["jobs"] if j["row"] == "B1PA"], "a table clock that is not the row's")
    guard_json("tables/h1.json", lambda t: [j.update(clear_values=[0x8000, 0x20000000]) for j in t["jobs"] if j["row"] == "B1P"],
               "a CLEAR value off the allow-list (bit 29)")
    guard_json("tables/h3.json", lambda t: t.update(arm="slots=0xf entry=0,1,2,3 trc=1"), "an arm line off the allow-list")


@test
def t_landed_api():
    """Every landed fwtask_run name the runner and the op module use exists in the landed file, with the arguments they pass."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("landed_fwtask_run", f"{WT}/tools/fwtask/fwtask_run.py")
    landed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(landed)
    names = set()
    for f in ("r5e_run.py", "ops_h.py"):
        names |= set(re.findall(r"\bFR\.([A-Za-z_]+)", (R5 / "run" / f).read_text()))
    missing = sorted(n for n in names if not hasattr(landed, n) and n != "D")
    ok(not missing, f"every FR.name the runner uses exists in the landed fwtask_run.py ({sorted(names)}; missing {missing})")
    for n, nargs in (("wr", 2), ("rd", 1), ("miscinfo", 0), ("regs", 0), ("alive", 0), ("tick_rate", 1), ("health", 0), ("dmesg_new", 1),
                     ("hang_dump", 2), ("sh", 2), ("is_bad_log", 1)):
        sig = inspect.signature(getattr(landed, n))
        ok(len([p for p in sig.parameters.values() if p.default is p.empty]) <= nargs, f"landed {n}{sig} accepts the runner's {nargs} arguments")
    for n in ("cmd_arm", "cmd_reset", "cmd_gate"):
        ok(len(inspect.signature(getattr(landed, n)).parameters) == 1, f"landed {n}(a) takes one argument dict")
    src = inspect.getsource(landed.cmd_arm)
    ok("900 <= out[\"rate_hz\"] <= 1100" in src, "the landed cmd_arm judges the rate at 900 to 1100 Hz (why the runner judges it again per clock)")
    os.environ.setdefault("MOCK_DIR", str(BASE))
    sys.path.insert(0, str(R5 / "tests" / "mockfw"))
    import fwtask_run as mock
    for n in names - {"D"}:
        ok(hasattr(mock, n), f"the mock has FR.{n} (the runner runs against it)")


# ---- the default session, end to end ---------------------------------------------------------------------------------------------
DEFAULT = {}


def default_world():
    if not DEFAULT:
        w, e, c = staged("default")
        rc, o = session(e, c)
        DEFAULT.update(w=w, e=e, c=c, rc=rc, o=o)
    return DEFAULT


@test
def t_default_session():
    """The default world (H-HWR, H-TICKS, H-LEVEL, H-W, H-STATE): the whole session through the driver: h1, h2, h3, 10 predicted stops."""
    d = default_world()
    w, rc, o = d["w"], d["rc"], d["o"]
    ok(rc == 0 and "R5e mock1 done" in o, f"the session exits 0 (rc {rc}: {o.strip()[-300:]})")
    for st, nstops in (("h1", 3), ("h2", 4), ("h3", 3)):
        sj = stage_json(w, st)
        ok(sj.get("exit") == 0 and sj.get("jobs_run") == JOBS[st], f"{st}: exit 0, every job in the frozen order ({sj.get('exit')}, {sj.get('jobs_run')})")
        ok(sj.get("stops") == nstops, f"{st}: {nstops} stops, each signed, explained and recovered, the stage going on ({sj.get('stops')})")
        cb = json.loads((lapdir(w, st) / "clock-back.json").read_text())
        ok(cb["ok"] and cb["knob"] == "0x00000000" and cb["gap_median"] == 25000, f"{st}: the clock came back (knob 0, gap {cb['gap_median']})")
    ok(len(ALL_JOBS) == 14, f"14 jobs in all ({len(ALL_JOBS)})")
    s = summary(w, "h1")
    v = verdicts(s, ("H-HWR", "H-NOMARK", "H-TICKS", "H-LEVEL", "H-PULSE", "H-W", "H-ALL", "H-NONE"))
    ok(v == {"H-HWR": "consistent", "H-NOMARK": "REFUTED", "H-TICKS": "consistent", "H-LEVEL": "consistent", "H-PULSE": "REFUTED",
             "H-W": "consistent", "H-ALL": "REFUTED", "H-NONE": "REFUTED"} and "B0 held" in s, f"h1 as frozen ({v}; {s[:200]})")
    s = summary(w, "h2")
    v = verdicts(s, ("H-HWR", "H-NOMARK", "H-TICKS", "H-TIME", "H-LEVEL"))
    ok(v == {"H-HWR": "consistent", "H-NOMARK": "REFUTED", "H-TICKS": "consistent", "H-TIME": "REFUTED", "H-LEVEL": "consistent"}
       and "B0 held" in s, f"h2 as frozen ({v}; {s[:200]})")
    s = summary(w, "h3")
    v = verdicts(s, ("H-STATE", "H-ACK18", "H-TICKS", "H-LEVEL", "H-W", "H-ALL", "H-NONE"))
    ok(v == {"H-STATE": "consistent", "H-ACK18": "REFUTED", "H-TICKS": "consistent", "H-LEVEL": "consistent", "H-W": "consistent",
             "H-ALL": "REFUTED", "H-NONE": "REFUTED"} and "B0 held" in s, f"h3 as frozen ({v}; {s[:200]})")
    for st in STAGES:
        S, _ = score_now(w, st)
        none_rows = sorted({(c_, q) for (c_, q, m, k, okk, n) in S.t.rows if okk is None and q != "dpm_task_state"})
        ok(not none_rows, f"{st}: every frozen row but 0x0694's has a measurement in the default world ({none_rows[:4]})")
        ok(len(S.t.rows) == len(S.preds), f"{st}: every frozen row was scored ({len(S.t.rows)} of {len(S.preds)})")
    calls = (w / "mock" / "ssh.log").read_text().splitlines()
    ih = next((i for i, x in enumerate(calls) if x.startswith("ssh bash ~/r5e-run/run/health_remote.sh")), None)
    ir = next((i for i, x in enumerate(calls) if x.startswith("ssh sudo -n python3 ~/r5e-run/run/r5e_run.py")), None)
    ok(ih is not None and ir is not None and ih < ir, "the load step (a fill and a triangle) runs before the first stage")
    names = {}
    for job, act in per_job(w):
        m = re.match(r"wr (\S+) ?(.*)$", act)
        if m:
            names.setdefault(m.group(1), set()).add(m.group(2).strip())
    ok(set(names) <= {"own_code", "own_arm", "load", "boot", "reset", "hold_recovery", "kregnow", "timer_clock"},
       f"the debugfs writes are on the allow-list ({sorted(names)})")
    ok(names.get("kregnow") == {"0x0134=0x8000", "0x0134=0x40000"}, f"kregnow: only CLEAR (0x0134) bits 15 and 18 ({names.get('kregnow')})")
    ok(names.get("timer_clock") == {"0", "800000", "1600000"}, f"timer_clock: only 0, 800000, 1600000 ({names.get('timer_clock')})")
    ok((w / "mock" / "dbg" / "hold_recovery").read_text() == "N" and (w / "mock" / "dbg" / "timer_clock").read_text() == "0x00000000",
       "hold_recovery ends N and timer_clock ends 0")
    ok(re.search(r"timer_clock at the end: timer_clock=0x00000000", o) is not None, f"the session's last lines print the knob ({o.strip().splitlines()[-2][:120]})")
    for st in STAGES:
        for j in JOBS[st]:
            dm = (lapdir(w, st) / f"{j}.dmesg").read_text()
            r = laprec(w, st, j)
            ok("(kernel log marker not found" not in dm and "marker not in dmesg" not in r["note"], f"{st}/{j}: the log is the slice after its own case marker")
    ok("resgx545 r5e " in (w / "mock" / "kmsg").read_text(), "the kernel-log markers are r5e's")


@test
def t_argv_twin():
    """Round 5: what each job APPLIED (the mock's trace and the tool's log) against PLAN_ROWS, the hand transcription of the plan.  A
    control run with the default clock (R4's o2 slip) or a clear written at the wrong moment fails here."""
    d = default_world()
    w = d["w"]
    acts = per_job(w)
    tool = [ln for ln in (w / "mock" / "tool.log").read_text().splitlines()]
    # split the trace by stage: each stage's run starts with its preflight; the job names repeat across stages (b0) so walk in order
    order = [(st, row[0]) for st in STAGES for row in PLAN_ROWS[st]]
    seen = []
    for job, act in acts:
        if job and (not seen or seen[-1] != job) and job != "clock-back":
            seen.append(job)
    ok(seen == [j for _s, j in order], f"the jobs ran in the plan's order ({seen})")
    # walk the trace job by job (consecutive runs of one job name)
    runs = []
    for job, act in acts:
        if not job or job == "clock-back":
            if runs and runs[-1][0] != "-":
                runs.append(("-", []))
            continue
        if not runs or runs[-1][0] != job:
            runs.append((job, []))
        runs[-1][1].append(act)
    runs = [r for r in runs if r[0] != "-"]
    ok(len(runs) == len(order), f"one trace run per planned job ({len(runs)} of {len(order)})")
    for (st, (name, clock, skip, hold, clears)), (job, a) in zip([(st, r) for st in STAGES for r in PLAN_ROWS[st]], runs):
        tc = [x.split()[-1] for x in a if x.startswith("wr timer_clock ")]
        ires = next((i for i, x in enumerate(a) if x == "reset"), None)
        itc = next((i for i, x in enumerate(a) if x.startswith("wr timer_clock ")), None)
        ok(job == name and tc[:1] == [str(clock)] and itc is not None and ires is not None and itc < ires,
           f"{st}/{name}: timer_clock {clock} written before the job's reset ({tc}, at {itc} before {ires})")
        sk = [x for x in a if x.startswith("page skip3 ")]
        ok(sk[-1:] == [f"page skip3 {skip}"] and all(x == "page skip3 0" for x in sk[:-1]),
           f"{st}/{name}: the page's skip flag {skip}, written last ({sk})")
        hr = [x.split()[-1] for x in a if x.startswith("wr hold_recovery ")]
        ok(hr[:1] == [hold] and hr[-1:] == ["N"], f"{st}/{name}: hold_recovery {hold} for the fill, N after ({hr})")
        kr = [i for i, x in enumerate(a) if x.startswith("wr kregnow ")]
        mi = [i for i, x in enumerate(a) if x == "misc"]
        dumps = [i for i, x in enumerate(a) if x.startswith("dump stop-")]
        fill = next((i for i, x in enumerate(a) if x == "page window 2"), None)
        if clears == "none":
            ok(not kr, f"{st}/{name}: no host write ({len(kr)})")
        elif clears == "late":
            ok(len(kr) == 2 and dumps and dumps[0] < kr[0], f"{st}/{name}: the clears after the stop's signature ({kr}, dump {dumps[:1]})")
        else:
            after = [i for i in mi if i > kr[-1]] if kr else []
            ok(len(kr) == 2 and after and (not dumps or kr[1] < dumps[0]) and fill is not None and fill < kr[0],
               f"{st}/{name}: the clears at the slot 3 entry, one miscinfo after them, before any stop ({kr}, misc {after[:1]}, dump {dumps[:1]})")
    jt = [ln for ln in tool if ln.endswith(" (armed)")]           # the jobs' calls (the health and load calls run unarmed)
    ok(len(jt) == len(order) and all(ln.split("] ", 1)[1] == f"sgxfive-test-s1b {PLAN_TOOL_ARGV} (armed)" for ln in jt)
       and [ln[1:].split("]")[0] for ln in jt] == [j for _s, j in order],
       f"every job ran the pinned tool with the plan's argv `{PLAN_TOOL_ARGV}` ({len(jt)}: {sorted(set(ln.split('] ', 1)[1] for ln in jt))})")
    for st in STAGES:
        for (name, clock, skip, hold, clears) in PLAN_ROWS[st]:
            r = laprec(w, st, name)
            ma = r.get("marks_arm") or {}
            ok(r["timer_clock_read"] == L.knob_text(clock) and (ma.get("hc") or {}).get(str(L.HC_CLOCK), (ma.get("hc") or {}).get(L.HC_CLOCK)) == L.eff_clock(clock),
               f"{st}/{name}: the record echoes the clock it ran at (knob {r['timer_clock_read']}, dword 6 in the arm dump)")


# ---- worlds ----------------------------------------------------------------------------------------------------------------------
def world(name, scenario):
    w, e, c = staged(name, scenario)
    rc, o = session(e, c, ATT)
    return w, rc, o


@test
def t_world_time():
    w, rc, o = world("time", "time_stop")
    s = summary(w, "h2")
    v = verdicts(s, ("H-TICKS", "H-TIME", "H-HWR"))
    ok(v["H-TIME"] == "consistent" and v["H-TICKS"] == "REFUTED" and v["H-HWR"] == "consistent", f"a mock that stops by time: H-TIME, H-TICKS refuted ({v}; rc {rc})")


@test
def t_world_ignore_clock():
    w, rc, o = world("noclock", "ignore_clock")
    sj = stage_json(w, "h2")
    ok(rc == 4 and sj.get("exit") == 4 and sj.get("jobs_run") == ["b0a"], f"a mock that ignores timer_clock: h2 stops at its first arm (rate out of the clock's band) (rc {rc}, {sj.get('jobs_run')})")
    S, s = score_now(w, "h2")
    ok(not any(okk for c_, q, m, k, okk, n in S.t.rows), f"no h2 row holds: the clock control voids it ({s[:160]})")
    ok((w / "mock" / "dbg" / "timer_clock").read_text() == "0x00000000", "timer_clock is put back to 0 after the stop")


@test
def t_world_nomark():
    w, rc, o = world("nomark", "nomark")
    sj = stage_json(w, "h1")
    ok(rc == 8 and sj.get("exit") == 8 and sj.get("jobs_run") == ["b0", "b1p"] and "unexplained" in sj.get("why", ""),
       f"a stop without the marks ends the stage and the session (R5-4: one unexplained stop) (rc {rc}, {sj.get('why', '')[:100]})")
    s = summary(w, "h1")
    v = verdicts(s, ("H-HWR", "H-NOMARK"))
    ok(v == {"H-HWR": "REFUTED", "H-NOMARK": "consistent"}, f"H-NOMARK consistent ({v})")
    ok(not (w / "out" / ATT / "h2").exists(), "h2 does not run after it")


@test
def t_world_ack18():
    w, rc, o = world("ack18", "ack18")
    s = summary(w, "h3")
    v = verdicts(s, ("H-STATE", "H-ACK18"))
    ok(rc == 0 and v == {"H-STATE": "REFUTED", "H-ACK18": "consistent"}, f"a mock where the clear of bit 18 disarms: H-ACK18 ({v}; rc {rc})")
    ok(stage_json(w, "h3").get("stops") == 0, "h3: no stop, each B1E recovered by its reset, gate and health")


@test
def t_world_phas_any():
    w, rc, o = world("phas", "phas_any")
    s = summary(w, "h1")
    v = verdicts(s, ("H-HWR", "H-NOMARK"))
    ok(rc == 0 and v["H-HWR"] == "REFUTED" and stage_json(w, "h1").get("stops") == 0, f"the skipped pass keeps the tick: H-HWR REFUTED ({v}; rc {rc})")
    ok(sorted(x.name for x in lapdir(w, "h1").glob("*recovery*")) == ["b1p-r2-recovery-reset.json", "b1p-r3-recovery-reset.json", "b1p-recovery-reset.json"],
       "each held B1P that kept the tick ends with a reset, the gate and the health")


@test
def t_world_sticky_and_controls():
    w, rc, o = world("sticky", "sticky_marks")
    S, s = score_now(w, "h1")
    ar = [(c_, okk) for c_, q, m, k, okk, n in S.t.rows if q == "arm_marks"]
    ok(dict(ar).get("b1p-r2") is False, f"a reset that leaves dword 3 set: the arm_marks control fails on the next job ({ar})")
    w, rc, o = world("b0stop", "b0_stop")
    sj = stage_json(w, "h1")
    ok(rc == 8 and sj.get("jobs_run") == ["b0"] and "a control stopped" in sj.get("why", ""), f"a B0 that stops ends the stage (rc {rc}, {sj.get('why', '')[:80]})")
    w, rc, o = world("b0fail", "fill_fail")
    S, s = score_now(w, "h1")
    ok(rc == 4 and "B0 NOT held" in s or "B0 not read" in s, f"a B0 whose fill fails ends the stage and gates the B1P rows (rc {rc}: {s[:160]})")


# ---- refusals, traps, stops ----------------------------------------------------------------------------------------------------------
@test
def t_preflight_refusals():
    def refused(name, why, scenario="", st="h1", **kw):
        if kw.get("srcv"):
            w, e, c = env_for(name, scenario, **kw)
            sh(["bash", str(c / "run" / "stage_r5e.sh")], e)
        else:
            w, e, c = staged(name, scenario, **kw)
        rc, o = runner(e, w, st)
        tr = trace(w)
        ok(rc == 1 and not any(re.search(r"\] (reset|arm|wr) ", x) for x in tr), f"the preflight refuses {why}, nothing touched (rc {rc}: {o.strip()[-160:]})")
    refused("nofw", "a firmware that is not running (no load step)", "nofw")
    refused("knob", "timer_clock not 0 (another session left it)", knobs={"timer_clock": "0x000c3500"})
    refused("knob2", "hold_recovery Y", knobs={"hold_recovery": "Y"})
    refused("oldmod", "E817's module 230E0EF5", srcv="230E0EF50FFFD606C53AE3C")
    w, e, c = staged("gate")
    rc, o = runner(e, w, "h2")
    ok(rc == 1 and "does not run" in o, f"h2 refuses to run without h1's kept stage.json (rc {rc}: {o.strip()[-120:]})")
    w, e, c = staged("again", "b0_stop")
    session(e, c, "a2")
    rc2, o2 = session(e, c, "a2")
    ok(rc2 == 22, f"the driver refuses an existing attempt (rc {rc2})")
    w, e, c = staged("loadfail", "tool_fail")
    rc, o = session(e, c, "lf")
    calls = (w / "mock" / "ssh.log").read_text().splitlines()
    ok(rc == 31 and not any(x.startswith("ssh sudo -n python3 ~/r5e-run/run/r5e_run.py") for x in calls), f"a failed load step stops before the first stage (rc {rc})")
    w, e, c = staged("frozen")
    (c / "gen" / "r5layout.py").write_text((c / "gen" / "r5layout.py").read_text() + "\n# changed\n")
    rc, o = session(e, c)
    ok(rc == 20, f"a changed frozen file stops the driver (rc {rc})")
    w, e, c = staged("lapfile")
    f = w / "home" / "r5e-run" / "tables" / "h1.json"
    f.write_text(f.read_text().replace('"stage": "h1"', '"stage":  "h1"'))
    rc, o = runner(e, w, "h1")
    ok(rc == 1 and "not the frozen file" in o, f"the runner refuses a laptop file that is not the frozen one (rc {rc})")


@test
def t_fatal_and_errors():
    w, e, c = staged("fatal", "fatal@b1p-r2")
    rc, o = session(e, c)
    ok(rc == 3 and stage_json(w, "h1").get("exit") == 3, f"a watchdog line in b1p-r2's log stops all laptop work: exit 3 (rc {rc})")
    w, e, c = staged("boom", "boom@b1pa")
    rc, o = session(e, c)
    ok(rc == 4 and (w / "mock" / "dbg" / "hold_recovery").read_text() == "N" and (w / "mock" / "dbg" / "timer_clock").read_text() == "0x00000000",
       f"an exception in b1pa (timer_clock 800000, hold_recovery Y): exit 4, both knobs back (rc {rc})")
    w, e, c = staged("armbad", "armfail")
    rc, o = session(e, c)
    ok(rc == 4 and stage_json(w, "h1").get("jobs_run") == ["b0"], f"an arm that fails stops at the first job (rc {rc})")
    w, e, c = staged("gatefail", "gatefail")
    rc, o = session(e, c)
    ok(rc != 0, f"a gate that fails ends the session (rc {rc})")
    w, e, c = staged("latebad", "latebad")
    rc, o = session(e, c)
    ok(rc == 38, f"a BIF fault line in a stage's kernel log stops after the stage (rc {rc})")


@test
def t_trap_restores_knobs():
    """SIGTERM during h2's b1pa (timer_clock 800000, hold_recovery Y): the finally blocks and the exit handler put both knobs back."""
    w, e, c = staged("trap", "")
    rc, o = runner(e, w, "h1")
    assert rc == 0, o[-300:]
    e2 = dict(e, MOCK_TOOL_WAIT="6", MOCK_SCENARIO="phas_any")
    p = subprocess.Popen([PY, str(w / "home" / "r5e-run" / "run" / "r5e_run.py"), "h2", "--tool", str(w / "home" / "sgxfive-test-s1b"),
                          "--bins", str(w / "home" / "r5e-run" / "bins"), "--out", str(w / "home" / "r5e-out" / ATT)], env=e2,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    hr, tc = w / "mock" / "dbg" / "hold_recovery", w / "mock" / "dbg" / "timer_clock"
    seen = False
    for _ in range(600):
        time.sleep(0.05)
        if hr.exists() and hr.read_text().strip() == "Y" and tc.read_text().strip() == "0x000c3500":
            seen = True
            break
    ok(seen, "hold_recovery reads Y and timer_clock 800000 while B1PA runs")
    p.send_signal(signal.SIGTERM)
    try:
        out, _ = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
    ok(hr.read_text().strip() == "N" and tc.read_text().strip() == "0x00000000", f"after SIGTERM hold_recovery N, timer_clock 0 ({hr.read_text()}, {tc.read_text()}; rc {p.returncode})")
    ok(p.returncode != 0 and (lapdir(w, "h2") / "stage.json").exists(), f"the runner exits non-zero and writes its stage record (rc {p.returncode})")


@test
def t_stage_resume():
    w, e, c = staged("resume", "b0_stop")
    rc, o = session(e, c, ATT)
    ok(rc == 8 and stage_json(w, "h1").get("exit") == 8, f"h1 ends at exit 8 (rc {rc})")
    rc, o = session(e, c, ATT, "--from", "h2")
    ok(rc != 22 and stage_json(w, "h2"), f"--from h2 resumes in the same attempt (gate: h1 finished with exit 8) (rc {rc})")
    rc, o = session(e, c, "nothere", "--from", "h2")
    ok(rc == 22, f"--from needs an existing attempt (rc {rc})")


if __name__ == "__main__":
    run_tests()
    print(f"{len(RAN)} tests, {len(FAIL)} failed" if FAIL else f"{len(RAN)} tests, all passed")
    sys.exit(1 if FAIL else 0)
