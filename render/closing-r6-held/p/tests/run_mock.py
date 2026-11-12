#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: r6-held part P (stage p1: B0, B1P x2, the peek of CR_DPM_TASK_STATE) end to end against a mock laptop.  Nothing touches
the laptop.  R5-events' run_mock.py adapted: the real scripts run on a COPY of this directory (its pinned tool hash is the fake tool's, its
freeze is redone there): run/stage_p.sh and run/p.sh with the ssh, scp, sudo, sha256sum, python3, modinfo and dmesg shims (tests/shims),
the laptop runner run/r6hp_run.py with the fake fwtask_run (tests/mockfw: a simulated EDM on the API of the landed file), the fake tool
(tests/fake_tool.sh in front of tests/fake_tool.py) and the scorer score/score_p.py.  The mock answers by what the runner WROTE (the
clock knob, the page's skip flag, the CLEAR values, the miscinfo, the tool's argv), never by a job's name; MOCK_SCENARIO picks the world.

Round 6 (BRIEF-BUILD.md "Round 6 additions"):
  * the laptop side runs with ONLY the laptop's environment: the ssh shim starts it under `env -i` (HOME, a PATH of the shims and
    /usr/bin:/bin, the mock's own MOCK_ / R3_ hooks), python3 is the system /usr/bin/python3 (never the Mac's venv), and the mock's
    firmware, layout and shims are COPIES in the mock home: no path into this source tree reaches the laptop side;
  * the staged tree is exactly what stage_p.sh lays out (t_laptop_tree), and tests/laptop_check.py, run on the mock laptop against it with
    the REAL landed fwtask_run.py, checks that every function the runner calls exists there;
  * every file the scorer reads is one the runner kept (t_scorer_reads_kept: the scorer's opens are recorded on the default world);
  * no start-up timing: the fake tool may start 3 s late (MOCK_TOOL_DELAY) and every outcome stays (t_slow_tool); the mock window
    holds at most 4 ticks before the fill's kick (tests/mockfw);
  * the argv-twin test against PLAN_ROWS, a hand transcription of the plan (rank-round6.md section 4 and session B, the parent's
    brief: B0, B1P x2 at timer_clock 0, the clears after the watch), NOT derived from r5layout.

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
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r6hpmock-"))
sys.path.insert(0, str(R5 / "gen"))
import r5layout as L  # noqa: E402

ATT = "mock1"
STAGES = L.STAGES
JOBS = {st: [L.rep_name(r, k) for r in L.ROW_ORDER[st] for k in range(L.ROW_SPEC[st][r]["reps"])] for st in STAGES}
ALL_JOBS = [j for st in STAGES for j in JOBS[st]]

# The plan's rows, transcribed by hand from rank-round6.md section 4 ("Q111 (E855's row), K1": one b1p stop read with the 0x0694 peek)
# and the parent's brief for part P (E855's h1 job cut to B0 + B1P x2 at timer_clock 0, hold N in B0, Y in B1P, E855's clears after the
# watch): (job, clock, skip, hold_recovery while the fill runs, clears, the peek phases read).
PLAN_ROWS = {
    "p1": [("b0", 0, 0, "N", "none", ("arm", "after_watch")),
           ("b1p", 0, 1, "Y", "late", ("arm", "stop", "after_clears", "after_recovery")),
           ("b1p-r2", 0, 1, "Y", "late", ("arm", "stop", "after_clears", "after_recovery"))],
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
    dst = BASE / name / "r6hp"
    shutil.copytree(R5, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "*.pyc", "debug"))
    (dst / "debug").mkdir()
    h = hashlib.sha256((dst / "tests" / "fake_tool.sh").read_bytes()).hexdigest()
    (dst / "TOOL.sha256").write_text(f"{h}  /home/jtorra/sgxfive-test-s1b\n")
    rc, o = sh([str(dst / "run" / "freeze_p.sh"), "freeze"], e=dict(os.environ, PY=PY, RESGX545=WT), cwd=str(dst))
    assert rc == 0, o
    return dst


STAGED = "scratch/r6h/p/stage"            # the laptop's staged tree, relative to HOME (r5layout.LAPTOP_DIR)
OUTD = "scratch/r6h/p/out"
PEEK0 = "reg 0x0694 0x00000000\n"


def env_for(name, scenario="", knobs=None, srcv="MOCKSRCV", copy=None, extra=None):
    """The mock laptop: its debugfs (mock/dbg), its home (the fake tools, COPIES of the mock firmware and the shims: nothing on the
    laptop side points into this source tree), the Mac side's env for the driver."""
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
    for t_, src in (("sgxfive-test", "fake_tool.py"), ("sgxfive-test-s1b", "fake_tool.sh")):
        q = home / t_
        q.write_text((c / "tests" / src).read_text())
        q.chmod(0o755)
    shutil.copytree(c / "tests" / "mockfw", home / ".mockfw", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(c / "tests" / "shims", home / ".mockbin")
    (home / ".check").mkdir()
    shutil.copy(c / "tests" / "laptop_check.py", home / ".check" / "laptop_check.py")
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo", "kregnow"):
        (mock / "dbg" / f).write_text("")
    (mock / "dbg" / "peek").write_text("reg 0x0694 skip\n" if "peek_badfmt" in scenario else PEEK0)
    kn = {"kick_no_bump": "N", "render_rgn_arrays": "0x00000000", "hold_recovery": "N", "render_pb_pages": "0x00000422",
          "timer_clock": "0x00000000", "render_tail_room": "0x00000000"}
    kn.update(knobs or {})
    for k, v in kn.items():
        (mock / "dbg" / k).write_text(v)
    (mock / "srcv").write_text(srcv + "\n")
    (mock / "kmsg").write_text("")
    e = dict(os.environ)
    e.update({"PATH": f"{c / 'tests' / 'shims'}:{os.environ['PATH']}", "MOCK_DIR": str(mock), "MOCK_HOME": str(home),
              "MOCK_SHIMS": str(home / ".mockbin"), "MOCK_GEN": str(home / STAGED / "gen"), "MOCK_BINS": str(home / STAGED / "bins"),
              "MOCK_PY": "/usr/bin/python3", "MOCK_SCENARIO": scenario, "R3_MOCK_ROOT": "1", "R3_FWTASK_DIR": str(home / ".mockfw"),
              "R3_KMSG": str(mock / "kmsg"), "R3_SRCV_PATH": str(mock / "srcv"), "R3_SRCV_EXPECT": "MOCKSRCV", "SGX_EXPECT_SRCV": "MOCKSRCV",
              "MOCK_SRCV": srcv, "R3_DEBUGFS": str(mock / "dbg"), "R3_OUT": str(out), "MOCK_TOOL_WAIT": "1.5",
              "PY": PY, "PYTHON": PY, "SGX_LOCAL_ENV": "/nonexistent", "SGX_TARGET_HOST": "mock@laptop", "RESGX545": WT,
              "PYTHONDONTWRITEBYTECODE": "1"})
    e.update(extra or {})
    return w, e, c


def staged(name, scenario="", **kw):
    w, e, c = env_for(name, scenario, **kw)
    rc, o = sh(["bash", str(c / "run" / "stage_p.sh")], e)
    assert rc == 0, f"staging: {o[-800:]}"
    return w, e, c


def session(e, c, att=ATT, *args):
    return sh(["bash", str(c / "run" / "p.sh"), att] + list(args), e)


def laptop(e, c, cmd):
    """One command on the mock laptop, through the ssh shim (the laptop's environment only)."""
    return sh(["bash", str(c / "tests" / "shims" / "ssh"), "mock@laptop", cmd], e)


def runner(e, w, st, att=ATT, c=None):
    c = c or (w / "r6hp")
    return laptop(e, c, f"sudo -n python3 ~/{STAGED}/run/r6hp_run.py {st} --tool ~/sgxfive-test-s1b --bins ~/{STAGED}/bins "
                        f"--out ~/{OUTD}/{att} --work ~/scratch/tmp")


def lapdir(w, st, att=ATT):
    return w / "home" / OUTD / att / st


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
    import score_p
    S, summ = score_p.score(st, w / "out" / att / st, R5)
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
    rc, o = sh([str(R5 / "run" / "freeze_p.sh"), "verify"], dict(os.environ, PY=PY, RESGX545=WT))
    ok(rc == 0 and "files verified" in o, f"the frozen files of this directory verify ({o.strip().splitlines()[-1] if o.strip() else ''})")
    rc, o = sh([str(R5 / "run" / "guard_p.sh")], dict(os.environ, PYTHON=PY, RESGX545=WT))
    ok(rc == 0 and "guard: clean" in o, f"guard_p.sh is clean ({o.strip()[-200:]})")
    fc, fp = R5 / "FROZEN.commits", R5 / "FROZEN.pin"
    pin = fp.read_text().strip() if fp.exists() else "?"
    pins = [ln for ln in fc.read_text().splitlines() if ln and not ln.startswith("#")] if fc.exists() else []
    ok(bool(pins) and all(ln.split()[1] in (pin, "untracked") for ln in pins) and pin.startswith("d9b2969"),
       f"FROZEN.commits pins every file of the tree to FROZEN.pin, resgx545 main d9b2969 ({pin[:7]}, {len(pins)} pins)")


@test
def t_guard_catches():
    c = copy_tree("guard")
    e = dict(os.environ, PYTHON=PY, RESGX545=WT)

    def guard_with(path, old, new, label, binary=False):
        q = c / path
        orig = q.read_bytes()
        if binary:
            q.write_bytes(orig[:100] + bytes([orig[100] ^ 1]) + orig[101:])
        else:
            tx = orig.decode()
            assert not old or old in tx, f"{label}: {old!r} not in {path}"
            q.write_text(tx.replace(old, new, 1) if old else tx + new)
        rc, o = sh([str(c / "run" / "guard_p.sh")], e)
        q.write_bytes(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")

    def guard_json(path, fn, label):
        q = c / path
        orig = q.read_text()
        tj = json.loads(orig)
        fn(tj)
        q.write_text(json.dumps(tj, indent=1, sort_keys=True) + "\n")
        rc, o = sh([str(c / "run" / "guard_p.sh")], e)
        q.write_text(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")
    guard_with("run/p.sh", "", "\nwhile true; do sleep 1; done\n", "a wait loop in the driver")
    guard_with("run/p.sh", "", "\necho 0 > /sys/kernel/debug/dri/0/sgx/timer_clock\n", "an unprivileged debugfs write")
    guard_with("run/p.sh", "", "\nset -f\n", "set -f in a script")
    guard_with("run/p.sh", "", "\nreboot\n", "a reboot in a script")
    guard_with("run/p.sh", "sudo -n python3 ~/$LD/run/r6hp_run.py", "python3 ~/$LD/run/r6hp_run.py", "the runner without sudo")
    guard_with("run/p.sh", "--work ~/$WK", "--work /tmp", "a work directory in /tmp")
    guard_with("run/health_remote.sh", "timeout -k 5 60", "timeout 60", "a timeout without -k")
    guard_with("run/r6hp_run.py", "", "\nFR.wr(\"render_rgn_arrays\", \"1\")\n", "a debugfs write off the allow-list in the runner")
    guard_with("run/r6hp_run.py", "", "\nFR.wr(\"peek\", \"0x0690\")\n", "a write to the peek")
    guard_with("run/ops_h.py", "", "\n        fd = os.open(f\"{FR.D}/peek\", os.O_WRONLY)\n", "the peek opened for writing")
    guard_with("run/r6hp_run.py", '["timeout", "-k", str(k), str(s), "cat"', '["cat"', "a peek read without timeout -k")
    guard_with("run/r6hp_run.py", "", "\nimport tempfile\nW = tempfile.mkdtemp()\n", "a tempfile (the laptop's /tmp)")
    guard_with("run/r6hp_run.py", "if not self.work_re.fullmatch(p) or p not in self.workdirs:", "if False:", "rm_work without its path check")
    guard_with("run/ops_h.py", "", "\nshutil.rmtree(p)\n", "a delete outside rm_work")
    guard_with("run/r6hp_run.py", "", "\nlines = FR.dmesg_new(0)\n", "a kernel log sliced by a line count")
    guard_with("run/r6hp_run.py", "", "\nFR.wr(\"kregnow\", \"0x0c04=0x1\")\n", "a kregnow write outside ops_h.py")
    guard_with("run/r6hp_run.py", "os.open(KMSG, os.O_WRONLY | os.O_APPEND)", "open(KMSG, \"a\").fileno()", "kmsg opened in mode a")
    guard_with("run/r6hp_run.py", "signal.SIGTERM", "signal.SIGUSR1", "a runner without the trap")
    guard_with("run/r6hp_run.py", "int(val) not in L.CLOCKS", "int(val) < 0", "a timer_clock check that is not the allow-list")
    guard_with("run/ops_h.py", 'f"0x0134=0x{value:x}"', 'f"0x0114=0x{value:x}"', "a CLEAR2 write by the host")
    guard_with("run/ops_h.py", 'self.knob("hold_recovery", j["hold_recovery"])', 'self.knob("rtds_keep", "Y")', "a knob other than the two")
    guard_with("bins/ring_skip3p.blob", None, None, "a blob byte changed", binary=True)
    guard_with("asm/ring_skip3p.s", "@entry 0", "@entry 0\n        str #77, r10", "a firmware str added to the source")
    guard_with("gen/r5layout.py", "CLOCKS = (0,)", "CLOCKS = (0, 800000)", "a clock value off part P's (0,)")
    guard_json("tables/p1.json", lambda tj: [j.update(may_stop=True) for j in tj["jobs"] if j["row"] == "B0"], "a control row that may stop")
    guard_json("tables/p1.json", lambda tj: [j.update(timer_clock=800000) for j in tj["jobs"] if j["row"] == "B1P"], "a table clock off the allow-list")
    guard_json("tables/p1.json", lambda tj: [j.update(clear_values=[0x8000, 0x20000000]) for j in tj["jobs"] if j["row"] == "B1P"],
               "a CLEAR value off the allow-list (bit 29)")
    guard_json("tables/p1.json", lambda tj: tj.update(arm="slots=0xf entry=0,1,2,3 trc=1"), "an arm line off the allow-list")


@test
def t_landed_api():
    """Every landed fwtask_run name the runner and the op module use exists in the landed file, with the arguments they pass."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("landed_fwtask_run", f"{WT}/tools/fwtask/fwtask_run.py")
    landed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(landed)
    names = set()
    for f in ("r6hp_run.py", "ops_h.py"):
        names |= set(re.findall(r"\bFR\.([A-Za-z_]+)", (R5 / "run" / f).read_text()))
    missing = sorted(n for n in names if not hasattr(landed, n) and n != "D")
    ok(not missing, f"every FR.name the runner uses exists in the landed fwtask_run.py ({sorted(names)}; missing {missing})")
    for n, nargs in (("wr", 2), ("rd", 1), ("miscinfo", 0), ("regs", 0), ("alive", 0), ("tick_rate", 1), ("health", 0), ("dmesg_new", 1),
                     ("hang_dump", 2), ("sh", 2), ("is_bad_log", 1)):
        sig = inspect.signature(getattr(landed, n))
        ok(len([q for q in sig.parameters.values() if q.default is q.empty]) <= nargs, f"landed {n}{sig} accepts the runner's {nargs} arguments")
    for n in ("cmd_arm", "cmd_reset", "cmd_gate"):
        ok(len(inspect.signature(getattr(landed, n)).parameters) == 1, f"landed {n}(a) takes one argument dict")
    os.environ.setdefault("MOCK_DIR", str(BASE))
    (pathlib.Path(os.environ["MOCK_DIR"]) / "dbg").mkdir(parents=True, exist_ok=True)
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


P1_DEFAULT = {"H-HWR": "consistent", "H-NOMARK": "REFUTED", "H-TICKS": "consistent", "H-LEVEL": "consistent", "H-PULSE": "REFUTED",
              "H-W": "consistent", "H-ALL": "REFUTED", "H-NONE": "REFUTED", "H-R6": "consistent", "H-IDLE": "REFUTED", "H-RESET": "consistent"}


def check_default(w, rc, o, label):
    ok(rc == 0 and "R6hp mock1 done" in o, f"{label}: the session exits 0 (rc {rc}: {o.strip()[-300:]})")
    sj = stage_json(w, "p1")
    ok(sj.get("exit") == 0 and sj.get("jobs_run") == JOBS["p1"] and sj.get("stops") == 2,
       f"{label}: p1 exit 0, every job in the frozen order, 2 stops, each signed, explained and recovered ({sj})")
    cb = json.loads((lapdir(w, "p1") / "clock-back.json").read_text()) if (lapdir(w, "p1") / "clock-back.json").exists() else {}
    ok(cb.get("ok") and cb.get("knob") == "0x00000000" and cb.get("gap_median") == 25000, f"{label}: the clock came back ({cb.get('gap_median')})")
    s = summary(w, "p1")
    v = verdicts(s, tuple(P1_DEFAULT))
    ok(v == P1_DEFAULT and "B0 held" in s, f"{label}: p1 as frozen ({v}; {s[:240]})")


@test
def t_default_session():
    """The default world (H-HWR, H-TICKS, H-LEVEL, H-W, H-R6, H-RESET): the whole session through the driver: p1, 2 predicted stops."""
    d = default_world()
    w, rc, o = d["w"], d["rc"], d["o"]
    check_default(w, rc, o, "default")
    ok(len(ALL_JOBS) == 3, f"3 jobs in all ({len(ALL_JOBS)})")
    S, _ = score_now(w, "p1")
    none_rows = sorted({(c_, q) for (c_, q, m, k, okk, n) in S.t.rows if okk is None})
    ok(not none_rows, f"every frozen row has a measurement in the default world ({none_rows[:4]})")
    ok(len(S.t.rows) == len(S.preds), f"every frozen row was scored ({len(S.t.rows)} of {len(S.preds)})")
    calls = (w / "mock" / "ssh.log").read_text().splitlines()
    ih = next((i for i, x in enumerate(calls) if x.startswith(f"ssh bash ~/{STAGED}/run/health_remote.sh")), None)
    ir = next((i for i, x in enumerate(calls) if x.startswith(f"ssh sudo -n python3 ~/{STAGED}/run/r6hp_run.py")), None)
    ok(ih is not None and ir is not None and ih < ir, "the load step (a fill and a triangle) runs before the stage")
    ok(any("--work ~/scratch/tmp" in x for x in calls) and any(x.startswith("ssh df -Pk ~") for x in calls),
       "the driver names ~/scratch/tmp as the work directory and checks the free space on ~")
    names = {}
    for job, act in per_job(w):
        m = re.match(r"wr (\S+) ?(.*)$", act)
        if m:
            names.setdefault(m.group(1), set()).add(m.group(2).strip())
    ok(set(names) <= {"own_code", "own_arm", "load", "boot", "reset", "hold_recovery", "kregnow", "timer_clock"},
       f"the debugfs writes are on the allow-list, never the peek ({sorted(names)})")
    ok(names.get("kregnow") == {"0x0134=0x8000", "0x0134=0x40000"}, f"kregnow: only CLEAR (0x0134) bits 15 and 18 ({names.get('kregnow')})")
    ok(names.get("timer_clock") == {"0"}, f"timer_clock: only 0 ({names.get('timer_clock')})")
    ok((w / "mock" / "dbg" / "hold_recovery").read_text() == "N" and (w / "mock" / "dbg" / "timer_clock").read_text() == "0x00000000",
       "hold_recovery ends N and timer_clock ends 0")
    ok((w / "mock" / "dbg" / "peek").read_text() == PEEK0, "the peek file ends as the idle EDM's (the reset rebuilt it)")
    for j in JOBS["p1"]:
        dm = (lapdir(w, "p1") / f"{j}.dmesg").read_text()
        r = laprec(w, "p1", j)
        ok("(kernel log marker not found" not in dm and "marker not in dmesg" not in r["note"], f"p1/{j}: the log is the slice after its own case marker")
    ok("resgx545 r6hp " in (w / "mock" / "kmsg").read_text(), "the kernel-log markers are r6hp's")
    # round 6's files: the work directories, the tool's cwd, nothing left; nothing under the laptop's /tmp
    cw = [ln.split("] ", 1)[1] for ln in (w / "mock" / "cwd.log").read_text().splitlines() if ln.split("] ")[0][1:] in JOBS["p1"]]
    tmp = str(w / "home" / "scratch" / "tmp")
    rtmp = os.path.realpath(tmp)
    ok(len(cw) == 3 and len(set(cw)) == 3 and all(re.fullmatch(re.escape(rtmp) + r"/r6hp\.[A-Za-z0-9]{6}", x) for x in cw),
       f"each job's tool ran in its own ~/scratch/tmp/r6hp.XXXXXX ({cw})")
    ok(os.listdir(tmp) == [], f"every work directory was removed once kept ({os.listdir(tmp)})")
    ok(all(laprec(w, "p1", j).get("free_mb_before", 0) >= 300 for j in JOBS["p1"]), "the free space was read before each job")
    for j in ("b1p", "b1p-r2"):
        pk = laprec(w, "p1", j).get("peek", {})
        ok(sorted(pk) == sorted(["arm", "stop", "after_clears", "after_recovery"]) and pk["stop"]["value"] == 2 and pk["arm"]["value"] == 0,
           f"p1/{j}: the peek read at the arm, at the stop (2), after the clears and after the recovery ({ {k: v.get('value') for k, v in pk.items()} })")
    tr = per_job(w)
    for j in ("b1p", "b1p-r2"):
        a = [x for jj, x in tr if jj == j]
        ik = next((i for i, x in enumerate(a) if x.startswith("wr kregnow ")), None)
        ok(ik is not None, f"p1/{j}: the clears ran (the peek's stop read comes before them: its record order)")


@test
def t_argv_twin():
    """What each job APPLIED (the mock's trace, the tool's log, the record's peek phases) against PLAN_ROWS, the hand transcription."""
    d = default_world()
    w = d["w"]
    acts = per_job(w)
    tool = [ln for ln in (w / "mock" / "tool.log").read_text().splitlines()]
    order = [("p1", row[0]) for row in PLAN_ROWS["p1"]]
    seen = []
    for job, act in acts:
        if job and (not seen or seen[-1] != job) and job != "clock-back":
            seen.append(job)
    ok(seen == [j for _s, j in order], f"the jobs ran in the plan's order ({seen})")
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
    for (name, clock, skip, hold, clears, phases), (job, a) in zip(PLAN_ROWS["p1"], runs):
        tc = [x.split()[-1] for x in a if x.startswith("wr timer_clock ")]
        ires = next((i for i, x in enumerate(a) if x == "reset"), None)
        itc = next((i for i, x in enumerate(a) if x.startswith("wr timer_clock ")), None)
        ok(job == name and tc[:1] == [str(clock)] and itc is not None and ires is not None and itc < ires,
           f"p1/{name}: timer_clock {clock} written before the job's reset ({tc}, at {itc} before {ires})")
        sk = [x for x in a if x.startswith("page skip3 ")]
        ok(sk[-1:] == [f"page skip3 {skip}"] and all(x == "page skip3 0" for x in sk[:-1]), f"p1/{name}: the page's skip flag {skip}, written last ({sk})")
        hr = [x.split()[-1] for x in a if x.startswith("wr hold_recovery ")]
        ok(hr[:1] == [hold] and hr[-1:] == ["N"], f"p1/{name}: hold_recovery {hold} for the fill, N after ({hr})")
        kr = [i for i, x in enumerate(a) if x.startswith("wr kregnow ")]
        dumps = [i for i, x in enumerate(a) if x.startswith("dump stop-")]
        if clears == "none":
            ok(not kr, f"p1/{name}: no host write ({len(kr)})")
        else:
            ok(len(kr) == 2 and dumps and dumps[0] < kr[0], f"p1/{name}: the clears after the stop's signature ({kr}, dump {dumps[:1]})")
        r = laprec(w, "p1", name)
        ok(sorted(r.get("peek", {})) == sorted(phases), f"p1/{name}: the peek read at {phases} ({sorted(r.get('peek', {}))})")
        ok(r["timer_clock_read"] == L.knob_text(clock), f"p1/{name}: the record echoes the clock it ran at ({r['timer_clock_read']})")
    jt = [ln for ln in tool if ln.endswith(" (armed)")]
    ok(len(jt) == len(order) and all(ln.split("] ", 1)[1] == "sgxfive-test-s1b fill (armed)" for ln in jt)
       and [ln[1:].split("]")[0] for ln in jt] == [j for _s, j in order],
       f"every job ran the pinned tool with the plan's argv `fill` ({len(jt)}: {sorted(set(ln.split('] ', 1)[1] for ln in jt))})")


@test
def t_scorer_reads_kept():
    """Round 6: every file the scorer reads is one the runner kept (and the driver copied back): the scorer's opens on the default world
    are recorded; each must exist in the Mac's copy and in the laptop's kept directory, byte for byte."""
    d = default_world()
    w = d["w"]
    out = w / "out" / ATT / "p1"
    seen = []
    orig_rt, orig_open = pathlib.Path.read_text, open
    import builtins

    def rt(self, *a, **k):
        seen.append(str(self))
        return orig_rt(self, *a, **k)

    def op(f, *a, **k):
        seen.append(str(f))
        return orig_open(f, *a, **k)
    pathlib.Path.read_text, builtins.open = rt, op
    try:
        S, s = score_now(w, "p1")
    finally:
        pathlib.Path.read_text, builtins.open = orig_rt, orig_open
    mine = sorted({x for x in seen if x.startswith(str(out))})
    ok(len(mine) >= 7, f"the scorer read the kept files ({len(mine)}: {[pathlib.Path(x).name for x in mine]})")
    miss = [x for x in mine if not pathlib.Path(x).exists()]
    ok(not miss, f"every file the scorer opens exists in the copy ({miss})")
    lap = lapdir(w, "p1")
    diff = [x for x in mine if pathlib.Path(x).exists() and (lap / pathlib.Path(x).relative_to(out)).read_bytes() != pathlib.Path(x).read_bytes()]
    ok(not diff, f"each is the runner's kept file, byte for byte ({diff})")
    for need in ("b0.json", "b1p.json", "b1p-r2.json", "stop-b1p-status.txt", "stop-b1p-own_res.json", "stop-b1p-r2-status.txt"):
        ok(str(out / need) in mine, f"the scorer reads {need}")


@test
def t_laptop_tree():
    """Round 6: the staged tree is exactly gen/laptop_files.py + the landed fwtask_run.py + LAPTOP.sha256, and laptop_check.py, run on the
    mock laptop (system python3, the laptop's environment only) against it with the REAL landed fwtask_run, finds every function, layout
    name and command the runner calls."""
    d = default_world()
    w, e, c = d["w"], d["e"], d["c"]
    st = w / "home" / STAGED
    got = sorted(str(q.relative_to(st)) for q in st.rglob("*") if q.is_file() and "__pycache__" not in q.parts)
    want = sorted(subprocess.run([PY, str(c / "gen" / "laptop_files.py")], capture_output=True, text=True).stdout.split()
                  + ["run/fwtask_run.py", "LAPTOP.sha256"])
    ok(got == want, f"the staged tree is exactly the frozen file list ({sorted(set(got) ^ set(want))})")
    ok((st / "run" / "fwtask_run.py").read_bytes() == pathlib.Path(f"{WT}/tools/fwtask/fwtask_run.py").read_bytes(),
       "the staged fwtask_run.py is the landed one")
    rc, o = laptop(e, c, f"python3 ~/.check/laptop_check.py ~/{STAGED}")
    ok(rc == 0 and "LAPTOP CHECK OK" in o, f"laptop_check.py on the mock laptop: {o.strip()[-400:]}")
    rc, o = laptop(e, c, "env; command -v python3")
    ok(not re.search(r"^(PY|PYTHON|PYTHONPATH|VIRTUAL_ENV|RESGX545)=", o, re.M) and "VIRTUAL_ENV" not in o and "RESGX545" not in o and str(R5) not in o and ".mockbin/python3" in o,
       f"the laptop side sees only the laptop's environment (no PY, venv, RESGX545 or source-tree path) ({o.strip()[-200:]})")
    # a broken staged runner (a call of a method that is not there) is caught by the same check
    f = st / "run" / "ops_h.py"
    orig = f.read_text()
    f.write_text(orig.replace('self.peek_read(rec, "arm")', 'self.peek_reed(rec, "arm")', 1))
    rc, o = laptop(e, c, f"python3 ~/.check/laptop_check.py ~/{STAGED}")
    f.write_text(orig)
    ok(rc == 1 and "self.peek_reed() is not a method" in o, f"laptop_check.py catches a missing method ({o.strip()[-160:]})")


@test
def t_slow_tool():
    """Round 6: the fake tool starts 3 s late (MOCK_TOOL_DELAY=3): every outcome is the default world's (no start-up timing)."""
    w, e, c = staged("slow", extra={"MOCK_TOOL_DELAY": "3"})
    rc, o = session(e, c)
    check_default(w, rc, o, "a tool 3 s slow")
    ok(all(laprec(w, "p1", j)["slot3_wait_ms"] >= 2900 for j in JOBS["p1"]), "the tool really started late (slot 3 after 3 s)")


# ---- worlds ----------------------------------------------------------------------------------------------------------------------
def world(name, scenario, **kw):
    w, e, c = staged(name, scenario, **kw)
    rc, o = session(e, c, ATT)
    return w, rc, o


@test
def t_world_peek():
    w, rc, o = world("nowrite", "peek_nowrite")
    v = verdicts(summary(w, "p1"), ("H-R6", "H-IDLE", "H-HWR"))
    ok(rc == 0 and v == {"H-R6": "REFUTED", "H-IDLE": "consistent", "H-HWR": "consistent"},
       f"a lockup that leaves 0x0694 as at the arm: H-R6 REFUTED, H-IDLE consistent ({v}; rc {rc})")
    w, rc, o = world("idletwo", "peek_idle_two")
    S, s = score_now(w, "p1")
    rows = [(c_, q, n) for c_, q, m, k, okk, n in S.t.rows if q in ("peek_stop", "peek_stop_eq_arm")]
    ok(rc == 0 and rows and all("already 2" in n for c_, q, n in rows), f"an arm read of 2: H-R6 / H-IDLE cannot tell, with the reason ({rows[:1]})")
    w, rc, o = world("sticky2", "peek_sticky")
    v = verdicts(summary(w, "p1"), ("H-R6", "H-RESET"))
    S, s = score_now(w, "p1")
    rr = {(c_, q): okk for c_, q, m_, k, okk, n in S.t.rows if q in ("peek_recovered_eq_arm", "peek_stop")}
    ok(v["H-RESET"] in ("REFUTED", "mixed") and rr.get(("b1p", "peek_recovered_eq_arm")) is False and rr.get(("b1p", "peek_stop")) is True
       and rr.get(("b1p-r2", "peek_stop")) is None,
       f"a reset that leaves 0x0694 at 2: b1p's H-RESET row FAILS, b1p-r2 (arm read 2) cannot tell H-R6 ({v}; {rr})")
    for sc in ("peek_badfmt", "peek_enodev"):
        w, e, c = staged(sc, sc)
        rc, o = runner(e, w, "p1", c=c)
        tr = trace(w)
        ok(rc == 1 and "peek" in o and not any(re.search(r"\] (reset|arm|wr) ", x) for x in tr),
           f"{sc}: the preflight refuses (no `reg 0x0694` line), nothing touched (rc {rc}: {o.strip()[-160:]})")


@test
def t_world_nomark():
    w, rc, o = world("nomark", "nomark")
    sj = stage_json(w, "p1")
    ok(rc == 8 and sj.get("exit") == 8 and sj.get("jobs_run") == ["b0", "b1p"] and "unexplained" in sj.get("why", ""),
       f"a stop without the marks ends the stage and the session (rc {rc}, {sj.get('why', '')[:100]})")
    v = verdicts(summary(w, "p1"), ("H-HWR", "H-NOMARK"))
    ok(v == {"H-HWR": "REFUTED", "H-NOMARK": "consistent"}, f"H-NOMARK consistent ({v})")
    ok(os.listdir(w / "home" / "scratch" / "tmp") == [], "the work directories are gone after the stop")


@test
def t_world_phas_any():
    w, rc, o = world("phas", "phas_any")
    s = summary(w, "p1")
    v = verdicts(s, ("H-HWR", "H-NOMARK", "H-R6"))
    ok(rc == 0 and v["H-HWR"] == "REFUTED" and stage_json(w, "p1").get("stops") == 0, f"the skipped pass keeps the tick: H-HWR REFUTED ({v}; rc {rc})")
    ok(sorted(x.name for x in lapdir(w, "p1").glob("*recovery*")) == ["b1p-r2-recovery-reset.json", "b1p-recovery-reset.json"],
       "each held B1P that kept the tick ends with a reset, the gate and the health")
    ok(all(sorted(laprec(w, "p1", j)["peek"]) == sorted(("arm", "after_watch", "after_recovery")) for j in ("b1p", "b1p-r2")),
       "a B1P that kept the tick: the peek at the arm, after the watch and after the recovery")


@test
def t_world_sticky_and_controls():
    w, rc, o = world("sticky", "sticky_marks")
    S, s = score_now(w, "p1")
    ar = [(c_, okk) for c_, q, m, k, okk, n in S.t.rows if q == "arm_marks"]
    ok(dict(ar).get("b1p-r2") is False, f"a reset that leaves dword 3 set: the arm_marks control fails on the next job ({ar})")
    w, rc, o = world("b0stop", "b0_stop")
    sj = stage_json(w, "p1")
    ok(rc == 8 and sj.get("jobs_run") == ["b0"] and "a control stopped" in sj.get("why", ""), f"a B0 that stops ends the stage (rc {rc}, {sj.get('why', '')[:80]})")
    w, rc, o = world("b0fail", "fill_fail")
    S, s = score_now(w, "p1")
    ok(rc == 4 and ("B0 NOT held" in s or "B0 not read" in s), f"a B0 whose fill fails ends the stage and gates the B1P rows (rc {rc}: {s[:160]})")


# ---- refusals, traps, stops ----------------------------------------------------------------------------------------------------------
@test
def t_preflight_refusals():
    def refused(name, why, scenario="", **kw):
        if kw.get("srcv"):
            w, e, c = env_for(name, scenario, **kw)
            sh(["bash", str(c / "run" / "stage_p.sh")], e)
        else:
            w, e, c = staged(name, scenario, **kw)
        rc, o = runner(e, w, "p1", c=c)
        tr = trace(w)
        ok(rc in (1, 21) and not any(re.search(r"\] (reset|arm|wr) ", x) for x in tr), f"the preflight refuses {why}, nothing touched (rc {rc}: {o.strip()[-160:]})")
        return rc
    refused("nofw", "a firmware that is not running (no load step)", "nofw")
    refused("knob", "timer_clock not 0 (another session left it)", knobs={"timer_clock": "0x000c3500"})
    refused("knob2", "hold_recovery Y", knobs={"hold_recovery": "Y"})
    refused("knob3", "render_tail_room not 0 (r6-render4x's stage B left it)", knobs={"render_tail_room": "0x00004000"})
    refused("oldmod", "the rgn4 module 99CD90DA", srcv="99CD90DA26E3AFF9C450517")
    rc = refused("full", "less than 300 MiB free", extra={"R3_FREE_MB": "120"})
    ok(rc == 21, f"a full disk at the preflight is exit 21 ({rc})")
    w, e, c = staged("fulljob", extra={"R3_FREE_MB_JOB": "120"})
    rc, o = runner(e, w, "p1", c=c)
    ok(rc == 21 and not (lapdir(w, "p1") / "b0.json").exists() and stage_json(w, "p1").get("jobs_run") == [],
       f"too little space before a job: exit 21, the job never starts (rc {rc})")
    w, e, c = staged("again", "b0_stop")
    session(e, c, "a2")
    rc2, o2 = session(e, c, "a2")
    ok(rc2 == 22, f"the driver refuses an existing attempt (rc {rc2})")
    w, e, c = staged("loadfail", "tool_fail")
    rc, o = session(e, c, "lf")
    calls = (w / "mock" / "ssh.log").read_text().splitlines()
    ok(rc == 31 and not any(x.startswith(f"ssh sudo -n python3 ~/{STAGED}/run/r6hp_run.py") for x in calls), f"a failed load step stops before the stage (rc {rc})")
    w, e, c = staged("frozen")
    (c / "gen" / "r5layout.py").write_text((c / "gen" / "r5layout.py").read_text() + "\n# changed\n")
    rc, o = session(e, c)
    ok(rc == 20, f"a changed frozen file stops the driver (rc {rc})")
    w, e, c = staged("lapfile")
    f = w / "home" / STAGED / "tables" / "p1.json"
    f.write_text(f.read_text().replace('"stage": "p1"', '"stage":  "p1"'))
    rc, o = runner(e, w, "p1", c=c)
    ok(rc == 1 and "not the frozen file" in o, f"the runner refuses a laptop file that is not the frozen one (rc {rc})")


@test
def t_fatal_and_errors():
    w, e, c = staged("fatal", "fatal@b1p-r2")
    rc, o = session(e, c)
    ok(rc == 3 and stage_json(w, "p1").get("exit") == 3, f"a watchdog line in b1p-r2's log stops all laptop work: exit 3 (rc {rc})")
    w, e, c = staged("boom", "boom@b1p")
    rc, o = session(e, c)
    ok(rc == 4 and (w / "mock" / "dbg" / "hold_recovery").read_text() == "N" and (w / "mock" / "dbg" / "timer_clock").read_text() == "0x00000000"
       and os.listdir(w / "home" / "scratch" / "tmp") == [], f"an exception in b1p (hold_recovery Y): exit 4, knobs back, work directories gone (rc {rc})")
    w, e, c = staged("armbad", "armfail")
    rc, o = session(e, c)
    ok(rc == 4 and stage_json(w, "p1").get("jobs_run") == ["b0"], f"an arm that fails stops at the first job (rc {rc})")
    w, e, c = staged("gatefail", "gatefail")
    rc, o = session(e, c)
    ok(rc != 0, f"a gate that fails ends the session (rc {rc})")
    w, e, c = staged("latebad", "latebad")
    rc, o = session(e, c)
    ok(rc == 38, f"a BIF fault line in the stage's kernel log stops after the stage (rc {rc})")


@test
def t_trap_restores_knobs():
    """SIGTERM during b1p (hold_recovery Y): the finally blocks and the exit handler put the knobs back and remove the work directory."""
    w, e, c = staged("trap", "")
    e2 = dict(e, MOCK_TOOL_WAIT="6", MOCK_SCENARIO="phas_any")
    cmd = (f"sudo -n python3 ~/{STAGED}/run/r6hp_run.py p1 --tool ~/sgxfive-test-s1b --bins ~/{STAGED}/bins --out ~/{OUTD}/{ATT} "
           "--work ~/scratch/tmp")
    pr = subprocess.Popen(["bash", str(c / "tests" / "shims" / "ssh"), "mock@laptop", cmd], env=e2, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True)
    hr, tc = w / "mock" / "dbg" / "hold_recovery", w / "mock" / "dbg" / "timer_clock"
    seen = False
    for _ in range(600):
        time.sleep(0.05)
        if hr.exists() and hr.read_text().strip() == "Y":
            seen = True
            break
    ok(seen, "hold_recovery reads Y while B1P runs")
    ok(len(os.listdir(w / "home" / "scratch" / "tmp")) == 1, "its work directory exists while it runs")
    pr.send_signal(signal.SIGTERM)
    try:
        out, _ = pr.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        pr.kill()
        out, _ = pr.communicate()
    ok(hr.read_text().strip() == "N" and tc.read_text().strip() == "0x00000000", f"after SIGTERM hold_recovery N, timer_clock 0 ({hr.read_text()}, {tc.read_text()}; rc {pr.returncode})")
    ok(pr.returncode != 0 and (lapdir(w, "p1") / "stage.json").exists(), f"the runner exits non-zero and writes its stage record (rc {pr.returncode})")
    ok(os.listdir(w / "home" / "scratch" / "tmp") == [], f"the work directory is removed at the exit ({os.listdir(w / 'home' / 'scratch' / 'tmp')})")


@test
def t_dry_run_and_resume():
    w, e, c = staged("dry")
    rc, o = sh(["bash", str(c / "run" / "p.sh"), "d1"], dict(e, SGX_DRY_RUN="1"))
    ok(rc == 0 and "--work ~/scratch/tmp" in o and "df -Pk ~" in o and f"~/{STAGED}/run/r6hp_run.py p1" in o and "/tmp" not in o.replace("scratch/tmp", ""),
       f"the dry run prints the stage's commands, the work directory and the space check ({o.strip()[-200:]})")
    w, e, c = staged("resume", "b0_stop")
    rc, o = session(e, c, ATT)
    ok(rc == 8 and stage_json(w, "p1").get("exit") == 8, f"p1 ends at exit 8 (rc {rc})")
    rc, o = session(e, c, ATT, "--from", "p1")
    ok(rc == 1 and "exists" in o, f"--from p1 never reruns into the kept attempt: the runner refuses (rc {rc})")
    rc, o = session(e, c, "nothere", "--from", "p1")
    ok(rc == 22, f"--from needs an existing attempt (rc {rc})")


if __name__ == "__main__":
    run_tests()
    print(f"{len(RAN)} tests, {len(FAIL)} failed" if FAIL else f"{len(RAN)} tests, all passed")
    sys.exit(1 if FAIL else 0)
