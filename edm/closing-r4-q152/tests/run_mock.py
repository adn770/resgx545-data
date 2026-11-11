#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: R4b end to end against a mock laptop (written before the runner's changes; a copy of R3k-events' run_mock.py
reduced to the one stage).  Nothing touches the laptop.

The real scripts run on a COPY of this directory (its pinned tool hash is the fake tool's, its freeze is redone there):
run/stage_r4b.sh and run/r4b.sh with the ssh, scp, sudo, sha256sum, python3, modinfo and dmesg shims (tests/shims), the laptop runner
run/r4b_run.py with the fake fwtask_run (tests/mockfw: R3k's simulated EDM on the API of the landed file at resgx545 6421c1c), the
fake tool (tests/fake_tool.py), the scorer score/score_r4b.py.  Worlds by MOCK_SCENARIO (tests/mockfw/kmock.py).

    /Users/jtorra/src/resgx545/.venv/bin/python tests/run_mock.py [-k SUBSTRING]
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
R4 = pathlib.Path(__file__).resolve().parent.parent
PY = os.environ.get("PY", "/Users/jtorra/src/resgx545/.venv/bin/python")
FAIL, RAN, TESTS = [], [], []
ONLY = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r4bmock-"))
BLOCK = ["e0", "fc4", "fc4-r2", "fb", "fb-r2"]
JOBS = [n for b in (1, 2, 3) for n in [f"b{b}{x}" for x in BLOCK] + [f"fcf{b}", f"fk{b}"]]
STARTS = ["b1e0", "b2e0", "b3e0"]
ATT = "mock1"


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
    dst = BASE / name / "r4b"
    shutil.copytree(R4, dst, ignore=shutil.ignore_patterns("out", "__pycache__", "*.pyc", "debug"))
    (dst / "debug").mkdir()
    h = hashlib.sha256((dst / "tests" / "fake_tool.py").read_bytes()).hexdigest()
    (dst / "TOOL.sha256").write_text(f"{h}  /home/jtorra/sgxfive-test-s1b\n")
    rc, o = sh([str(dst / "run" / "freeze_r4b.sh"), "freeze"], e=dict(os.environ, PY=PY), cwd=str(dst))
    assert rc == 0, o
    return dst


def env_for(name, scenario="", knobs=None, srcv="MOCKSRCV"):
    w = BASE / name
    c = copy_tree(name)
    mock, home, out = w / "mock", w / "home", w / "out"
    for d in (mock / "dbg", home, out):
        d.mkdir(parents=True, exist_ok=True)
    dri = mock / "sysdebug" / "dri"
    (dri / "0").mkdir(parents=True, exist_ok=True)
    for n_, tgt in (("0/sgx", "../../../dbg"), ("128", "0"), ("0000:00:02.0", "0")):
        if not (dri / n_).exists():
            os.symlink(tgt, dri / n_)
    for t in ("sgxfive-test", "sgxfive-test-s1b"):
        p = home / t
        p.write_text((c / "tests" / "fake_tool.py").read_text())
        p.chmod(0o755)
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo", "kicker", "kregnow", "kpoke"):
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
              "MOCK_SRCV": srcv, "R3_DEBUGFS": str(mock / "dbg"), "R4B_OUT": str(out), "MOCK_TOOL_WAIT": "1.5",
              "MOCK_FIXTURES": str(c / "tests" / "fixtures"), "PY": PY, "PYTHON": PY, "SGX_LOCAL_ENV": "/nonexistent",
              "SGX_TARGET_HOST": "mock@laptop", "RESGX545": str(pathlib.Path.home() / "src/resgx545"), "PYTHONDONTWRITEBYTECODE": "1"})
    return w, e, c


def staged(name, scenario="", **kw):
    w, e, c = env_for(name, scenario, **kw)
    rc, o = sh(["bash", str(c / "run" / "stage_r4b.sh")], e)
    assert rc == 0, f"staging: {o[-800:]}"
    return w, e, c


def session(e, c, att=ATT):
    return sh(["bash", str(c / "run" / "r4b.sh"), att], e)


def runner(e, w, att=ATT):
    return sh([PY, str(w / "home" / "r4b" / "run" / "r4b_run.py"), "fr", "--tool", str(w / "home" / "sgxfive-test-s1b"),
               "--bins", str(w / "home" / "r4b" / "bins"), "--out", str(w / "home" / "r4b-out" / att)], e)


def lapdir(w, att=ATT):
    return w / "home" / "r4b-out" / att / "fr"


def laprec(w, job, att=ATT):
    p = lapdir(w, att) / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def stage_json(w, att=ATT):
    p = lapdir(w, att) / "stage.json"
    return json.loads(p.read_text()) if p.exists() else {}


def trace(w):
    p = w / "mock" / "trace"
    return p.read_text().splitlines() if p.exists() else []


def kmsg(w):
    return (w / "mock" / "kmsg").read_text().splitlines()


def score_txt(w, att=ATT):
    p = w / "out" / att / "score-fr.txt"
    return p.read_text() if p.exists() else ""


def summary(w, att=ATT):
    return next((ln for ln in score_txt(w, att).splitlines() if ln.startswith("SUMMARY")), "")


# ---- static ----------------------------------------------------------------------------------------------------------------
@test
def t_freeze_and_guard():
    rc, o = sh([str(R4 / "run" / "freeze_r4b.sh"), "verify"])
    ok(rc == 0 and "files verified" in o, f"the frozen files of this directory verify ({o.strip().splitlines()[-1] if o.strip() else ''})")
    rc, o = sh([str(R4 / "run" / "guard_r4b.sh")], dict(os.environ, PYTHON=PY))
    ok(rc == 0 and "guard: clean" in o, f"guard_r4b.sh is clean ({o.strip()[-200:]})")


@test
def t_guard_catches():
    c = copy_tree("guard")
    e = dict(os.environ, PYTHON=PY)

    def guard_with(path, old, new, label, binary=False):
        p = c / path
        orig = p.read_bytes()
        if binary:
            p.write_bytes(orig[:100] + bytes([orig[100] ^ 1]) + orig[101:])
        else:
            t = orig.decode()
            assert not old or old in t, f"{label}: {old!r} not in {path}"
            p.write_text(t.replace(old, new, 1) if old else t + new)
        rc, o = sh([str(c / "run" / "guard_r4b.sh")], e)
        p.write_bytes(orig)
        ok(rc == 1 and "GUARD" in o, f"the guard refuses {label} (rc {rc})")
    guard_with("run/r4b.sh", "", "\nwhile true; do sleep 1; done\n", "a wait loop in the driver")
    guard_with("run/r4b.sh", "", "\necho N > /sys/kernel/debug/dri/0/sgx/hold_recovery\n", "an unprivileged debugfs write")
    guard_with("run/r4b_run.py", "", "\nFR.wr(\"render_rgn_arrays\", \"1\")\n", "a debugfs write by the runner")
    guard_with("run/r4b_run.py", "", "\nlines = FR.dmesg_new(0)\n", "a kernel log sliced by a line count")
    guard_with("run/r4b_run.py", "", "\nFR.wr(\"kregnow\", \"0x0c04=0x1\")\n", "a kregnow write")
    guard_with("run/r4b_run.py", "os.open(KMSG, os.O_WRONLY | os.O_APPEND)", "open(KMSG, \"a\").fileno()", "kmsg opened in mode a")
    guard_with("run/r4b.sh", "sudo -n python3 ~/$LD/run/r4b_run.py", "python3 ~/$LD/run/r4b_run.py", "the runner without sudo")
    guard_with("bins/ring_exit.blob", None, None, "a blob byte changed", binary=True)
    guard_with("tables/fr.json", '"may_stop": false', '"may_stop": true', "a control row that may stop")


# ---- sessions --------------------------------------------------------------------------------------------------------------
@test
def t_default_session():
    """H-REP's world (E817's): every FCF stops with E817's signature; the controls keep the tick."""
    w, e, c = staged("default")
    rc, o = session(e, c)
    ok(rc == 0, f"the session exits 0 with three FCF stops (rc {rc}: {o.strip()[-300:]})")
    sj = stage_json(w)
    ok(sj.get("exit") == 0 and sj.get("stops") == 3, f"stage.json: exit 0, 3 stops ({sj.get('exit')}, {sj.get('stops')})")
    ok(sj.get("jobs_run") == JOBS, f"every job ran in the frozen order ({sj.get('jobs_run')})")
    ok([sj["classes"][j] for j in ("fcf1", "fcf2", "fcf3")] == ["stop"] * 3, "fcf1, fcf2, fcf3 stopped (a replicate after a stop ran)")
    ok(all(sj["classes"][j] == "ok" for j in JOBS if not j.startswith("fcf")), "every control kept the tick")
    s = summary(w)
    ok("H-REP held" in s and "every control PASS" in s and "3 of 3 rows decided" in s, f"the SUMMARY: H-REP held ({s[:200]})")
    # the load step ran before the runner: the ssh log has the health call before the runner's
    calls = (w / "mock" / "ssh.log").read_text().splitlines()
    ih = next((i for i, x in enumerate(calls) if x.startswith("ssh bash ~/r4b/run/health_remote.sh")), None)
    ir = next((i for i, x in enumerate(calls) if x.startswith("ssh sudo -n python3 ~/r4b/run/r4b_run.py")), None)
    ok(ih is not None and ir is not None and ih < ir, "the load step (a fill and a triangle) runs before the stage")
    ok((w / "out" / ATT / "health-load.txt").exists(), "the load step's output is kept")
    # resets: one before each block's arm (in the block's first job), one after each FCF stop (then the re-arm), one at the end;
    # never one between the jobs of a block (E817's sequence from its arm to fcf)
    tr = trace(w)
    km = kmsg(w)
    ok(sum(1 for x in tr if x.endswith(" reset")) == 3 + 3 + 1, f"7 resets: 3 block starts, 3 stops, the end ({sum(1 for x in tr if x.endswith(' reset'))})")
    for j in JOBS:
        d = (lapdir(w) / f"{j}.dmesg").read_text()
        n = d.count("SGX reset: BIF_FAULT")
        ok(n == (1 if j in STARTS else 0), f"{j}: {'one reset (the block start)' if j in STARTS else 'no reset'} in its slice ({n})")
    arms = sorted(x.name for x in lapdir(w).glob("*arm*.json"))
    ok(arms == ["b1e0.arm.json", "b2e0.arm.json", "b3e0.arm.json", "rearm-fcf1.json", "rearm-fcf2.json", "rearm-fcf3.json"],
       f"an arm at each block start and a re-arm after each stop ({arms})")
    # the kernel log of every job is its own marker's slice, by the landed dmesg_new(marker): never the whole buffer
    for j in JOBS:
        d = (lapdir(w) / f"{j}.dmesg").read_text()
        r = laprec(w, j)
        ok("(kernel log marker not found" not in d and "resgx545 r4b case " not in d and f"case {j} " not in d
           and "marker not in dmesg" not in r["note"], f"{j}: the kernel log is the slice after its own case marker")
        ok(r["log_bad"] == [] and ("after the fault clear" in d) == (j in STARTS), f"{j}: no bad line; the reset's info line where a reset is")
    ok("dmesg whole buffer" not in "\n".join(tr), "no landed dmesg_new call fell back to the whole buffer")
    env = json.loads((lapdir(w) / "env.json").read_text())
    ok({k: env.get("knobs", {}).get(k) for k in ("render_rgn_arrays", "hold_recovery")} == {"render_rgn_arrays": "0x00000000",
                                                                                             "hold_recovery": "N"},
       f"the preflight records the knobs at their defaults ({env.get('knobs')})")
    ok(not any(x.startswith("wr render_rgn_arrays") or x.startswith("wr hold_recovery") or x.startswith("wr kregnow") for x in tr),
       "no knob was written")


@test
def t_worlds():
    for name, sc, want, stops in (("norep", "fcf_keep", "H-NOREP held", 0),
                                  ("mixed", "fcf_keep2", "H-REP mixed", 2),
                                  ("ctx5", "ctx5", "H-NOREP held", 0),
                                  ("ctxfirst", "ctx_first", "H-REP mixed", 1),
                                  ("othersig", "sig_pending", "STOP-OTHER", 3),
                                  ("p3", "p3_answers", "STOP-OTHER", 3)):
        w, e, c = staged(name, sc)
        rc, o = session(e, c)
        s = summary(w)
        sj = stage_json(w)
        ok(rc == 0 and want in s and sj.get("stops") == stops and sj.get("jobs_run") == JOBS,
           f"world {sc}: exit 0, {stops} stops, every job, '{want}' (rc {rc}, stops {sj.get('stops')}; {s[:200]})")
        if stops == 0:
            ok("3 of 3 rows decided" in s and not list(lapdir(w).glob("rearm-*.json")), f"world {sc}: 3 rows decided, no re-arm")


@test
def t_control_stop_ends_the_stage():
    w, e, c = staged("fbr2stop", "fb_stop2")
    rc, o = session(e, c)
    sj = stage_json(w)
    ok(rc == 8 and sj.get("exit") == 8 and sj.get("jobs_run") == JOBS[:5],
       f"block 1's fb-r2 (a control) stopping ends the stage at once: exit 8, nothing after ({rc}, {sj.get('jobs_run')})")
    s = summary(w)
    ok("b1fb-r2: FAILED" in s and "controls FAILED" in s and "H-REP cannot tell" in s, f"the SUMMARY names it, FCF cannot tell ({s[:200]})")
    ok((lapdir(w) / "stop1-b1fb-r2-reset.json").exists(), "the stopped control was signed, reset and gated")
    w, e, c = staged("fk1stop", "fph_stop")
    rc, o = session(e, c)
    sj = stage_json(w)
    ok(rc == 8 and sj.get("jobs_run") == JOBS[:7], f"fk1 (after block 1's recovery) stopping ends the stage before block 2 ({rc})")
    w, e, c = staged("b2fbstop", "fb_stop3")
    rc, o = session(e, c)
    sj = stage_json(w)
    s = summary(w)
    ok(rc == 8 and sj.get("jobs_run") == JOBS[:11], f"block 2's fb stopping ends the stage there ({rc}, {len(sj.get('jobs_run', []))} jobs)")
    ok("'fcf1': 'REPRO'" in s and "H-REP cannot tell" in s, f"fcf1 stays decided (its gate is block 1's), the rest cannot tell ({s[:200]})")


@test
def t_preflight_refusals():
    def refused(name, why, scenario="", **kw):
        w, e, c = staged(name, scenario, **kw) if not kw.get("srcv") else env_for(name, scenario, **kw)
        if kw.get("srcv"):
            rc, o = sh(["bash", str(c / "run" / "stage_r4b.sh")], dict(e, SGX_EXPECT_SRCV="MOCKSRCV"))
        rc, o = runner(e, w)
        tr = trace(w)
        ok(rc == 1 and not any(x.split()[1:2] in (["reset"], ["arm"]) or x.startswith("wr ") for x in tr if len(x.split()) > 1),
           f"the preflight refuses {why}, nothing touched (rc {rc}: {o.strip()[-160:]})")
        return w, e, c
    refused("nofw", "a firmware that is not running (no load step)", "nofw")
    refused("knob", "render_rgn_arrays not at its default 0", knobs={"render_rgn_arrays": "0x00000001"})
    refused("knob2", "hold_recovery Y", knobs={"hold_recovery": "Y"})
    refused("oldmod", "E817's module 230E0EF5", srcv="230E0EF50FFFD606C53AE3C")
    # an attempt is never overwritten: the driver refuses an existing attempt directory, the runner a kept stage.json
    w, e, c = staged("again")
    session(e, c)
    rc, o = session(e, c)
    ok(rc == 22, f"the driver refuses an existing attempt (rc {rc})")
    rc, o = runner(e, w)
    ok(rc == 1 and "exists" in o, f"the runner refuses an output directory that holds a kept stage (rc {rc}: {o.strip()[-120:]})")
    # the load step fails: the runner is not started
    w, e, c = staged("loadfail", "tool_fail")
    rc, o = session(e, c, "lf")
    calls = (w / "mock" / "ssh.log").read_text().splitlines()
    ok(rc == 31 and not any(x.startswith("ssh sudo -n python3 ~/r4b/run/r4b_run.py") for x in calls),
       f"a failed load step stops before the stage (rc {rc})")


@test
def t_fatal_and_budget():
    w, e, c = staged("fatal", "fatal@fcf2")
    rc, o = session(e, c)
    ok(rc == 3, f"a watchdog line in fcf2's log stops all laptop work: exit 3 (rc {rc})")
    w, e, c = staged("arm0", "exit0")
    rc, o = session(e, c)
    ok(rc == 4 and stage_json(w).get("jobs_run") == ["b1e0"], f"an arm that resolves exit 0 stops at the first job (rc {rc})")


def main():
    for fn in TESTS:
        if ONLY and ONLY not in fn.__name__:
            continue
        RAN.append(fn.__name__)
        t = time.time()
        print(f"--- {fn.__name__}")
        try:
            fn()
        except Exception as ex:
            import traceback
            traceback.print_exc()
            ok(False, f"{fn.__name__} raised {ex!r}")
        print(f"    ({time.time() - t:.1f} s)")
    print(f"{len(RAN)} tests, {len(FAIL)} failed" if FAIL else f"{len(RAN)} tests, all passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
