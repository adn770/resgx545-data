#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""run_mock.py: R3x-events end to end against a mock laptop.  Nothing touches the laptop.

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
BASE = pathlib.Path(tempfile.mkdtemp(prefix="r3xmock-"))
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
    for f in ("own_code", "own_arm", "own_res", "load", "boot", "reset", "regs", "status", "miscinfo"):
        (mock / "dbg" / f).write_text("")
    (mock / "dbg" / "hold_recovery").write_text("N")
    (mock / "dbg" / "render_pb_pages").write_text("0x00000422")
    (mock / "srcv").write_text("MOCKSRCV\n")
    (mock / "kmsg").write_text("")
    e = dict(os.environ)
    e.update({"PATH": f"{c / 'tests' / 'shims'}:{os.environ['PATH']}", "MOCK_DIR": str(mock), "MOCK_HOME": str(home),
              "MOCK_PY": PY, "MOCK_SCENARIO": scenario, "R3_MOCK_ROOT": "1", "R3_FWTASK_DIR": str(c / "tests" / "mockfw"),
              "R3_KMSG": str(mock / "kmsg"), "R3_SRCV_PATH": str(mock / "srcv"), "R3_SRCV_EXPECT": "MOCKSRCV", "SGX_EXPECT_SRCV": "MOCKSRCV", "MOCK_SRCV": "MOCKSRCV", "R3_DEBUGFS": str(mock / "dbg"),
              "R3_OUT": str(out), "PY": PY, "PYTHON": PY, "SGX_LOCAL_ENV": "/nonexistent", "SGX_TARGET_HOST": "mock@laptop",
              "PYTHONDONTWRITEBYTECODE": "1"})
    return w, e, c


def stage(e, c):
    return sh(["bash", str(c / "run" / "stage_r3.sh")], e)


def session(e, c, *args):
    return sh(["bash", str(c / "run" / "r3.sh")] + list(args), e)


def runner(e, w, st, extra=()):
    return sh([PY, str(w / "home" / "r3xev" / "run" / "r3_run.py"), st, "--tool", str(w / "home" / "sgxfive-test-s1b"),
               "--bins", str(w / "home" / "r3xev" / "bins"), "--out", str(w / "home" / "r3xev-out")] + list(extra), e)


def laprec(w, st, job):
    p = w / "home" / "r3xev-out" / st / f"{job}.json"
    return json.loads(p.read_text()) if p.exists() else None


def stage_json(w, st):
    return json.loads((w / "home" / "r3xev-out" / st / "stage.json").read_text())


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
    guard_with("run/r3.sh", "", "\necho 1 > $D/kicker\n", "a write to a kicker file")
    guard_with("run/r3.sh", "", "\necho $R3_KMSG\n", "a test-only override in a laptop-driving script")
    guard_with("run/r3.sh", "", "\necho $R3_SRCV_EXPECT\n", "the srcversion override in a laptop-driving script")
    guard_with("run/r3_run.py", "os.open(KMSG, os.O_WRONLY | os.O_APPEND)", "open(KMSG, 'a')", "the kernel log opened in Python's append mode")
    guard_with("run/r3_run.py", "\ndef sha(p):", "\nwhile False:\n    pass\n\n\ndef sha(p):", "a while loop in the runner")
    guard_with("run/r3_run.py", "captured(FR.cmd_arm, a)", "captured(FR.cmd_arm, a)\n        FR.kreg_write(0x0814, 1)", "a register write in the runner")
    guard_with("run/r3_run.py", "captured(FR.cmd_reset)\n        g = captured", "captured(FR.cmd_reset)\n        FR.wait_state(None, 1)\n        g = captured", "a polling command in the runner")
    guard_with("run/r3_run.py", "        self.armed = False\n        return bool", "        FR.wr(\"render_pb_pages\", \"0x30\")\n        self.armed = False\n        return bool", "a debugfs write off the allow-list")
    guard_with("run/r3_run.py", "        self.armed = False\n        return bool", "        FR.rd(\"xfer_sync\")\n        self.armed = False\n        return bool", "a read of xfer_sync in the runner")
    guard_with("run/r3_run.py", "        self.armed = False\n        return bool", "        FR.wr(\"kicker\", \"=5\")\n        self.armed = False\n        return bool", "a write to the kicker file in the runner")
    guard_with("asm/alias2.s", "", "\n        mov sa100, r4\n", "an sa write in alias2.s (text screen aside, the blob no longer matches)")
    guard_with("asm/ring_end.s", "", "\n        str #517, r4\n", "a str in a task source")
    guard_with("asm/ring_hold.s", "", "\n        ldr r1, #7, drc0\n", "an ldr of another register in a task source")
    guard_with("tables/c.json", '"arm": "slots=0x1 entry=0"', '"arm": "slots=0x1 entry=0 trc=3"', "a trc in the arm line")
    guard_with("tables/e.json", '"trigger": "miscinfo"', '"trigger": "kick"', "a bare kick as a trigger")
    guard_with("tables/e.json", '"count": 20', '"count": 21', "a count outside the rows")
    guard_with("tables/d.json", '"cmd": 11', '"cmd": 12', "D4 with another command")


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
        run = type("A", (), {"stage": "h", "tool": "t", "bins": "b", "out": str(BASE / "o")})
        rn = r3.Runner(run)
        rn.mark("hello")
        r3.os.open = real
        ok(calls == [(str(kf), os.O_WRONLY | os.O_APPEND)], f"Runner.mark opens the kernel log with O_WRONLY | O_APPEND ({calls})")
        ok(kf.read_text().splitlines()[-1].startswith("resgx545 r3x hello ") and kf.read_text().startswith("older\n"),
           "Runner.mark appends one line and truncates nothing")
        t = r3.captured(lambda a: print('{"ok": true}\nfwtask: FAIL: x'))
        ok(t["tool_bad"] == ["fwtask: FAIL: x"], "captured: a failure named anywhere in the whole output (not the last line) is kept in tool_bad")
        ok(r3.captured(lambda a: print('{"ok": true, "health": {"ok": true}}'))["tool_bad"] == [], "captured: a clean output has no tool_bad")
        ok(r3.median_mode([3, 3, 4]) == 3 and r3.median_mode([]) is None, "median_mode helper")
    finally:
        os.environ.clear()
        os.environ.update(old)
        sys.modules.pop("r3_run", None)


# ---- the session ------------------------------------------------------------------------------------------------------
def default_checks(w, c):
    km = (w / "mock" / "kmsg").read_text()
    sudo = (w / "mock" / "sudo.log").read_text().splitlines()
    runs = [x for x in sudo if "r3_run.py" in x]
    ok(all(x.startswith("sudo python3 ") and "/r3xev/run/" in x for x in runs), f"every stage ran from ~/r3xev under sudo -n python3 ({len(runs)} runner calls)")
    health = [x for x in sudo if "/sys/kernel/debug" in x]
    ok(health and all(x.startswith("sudo ") for x in health), f"every debugfs access of the scripts went through sudo -n ({len(health)} calls named the debugfs)")
    tr = trace(w)
    wrs = sorted({x.split()[2] for x in tr if " wr " in x})
    ok(set(wrs) <= {"own_code", "own_arm", "load", "boot", "reset"}, f"the runner wrote only allow-listed debugfs files: {wrs}")
    ok((w / "mock" / "dbg" / "hold_recovery").read_text().strip() == "N" and int((w / "mock" / "dbg" / "render_pb_pages").read_text(), 0) == 0x422,
       "no knob was touched")
    return km, tr


@test
def t_full_session():
    """The default mock: H-NOTENDED, H-EXIT, H-CCB.  Stages h, c, e finish (exit 0); stage d takes its two stops (D2, D3) and ends by exit 8."""
    w, e, c = env_for("full")
    rc, o = stage(e, c)
    ok(rc == 0 and "staged: ~/r3xev" in o and "tool ok:" in o and "srcversion loaded MOCKSRCV installed MOCKSRCV" in o and "files ok" in o,
       f"staging into ~/r3xev (rc {rc}): srcversion and the debugfs files checked")
    ok("debugfs " in o and o.count("debugfs ") >= 3, "staging found the debugfs directories through dri/*/sgx (three names)")
    t0 = time.time()
    rc, o = session(e, c)
    el = time.time() - t0
    ok(rc == 8 and "stage d was ended by its tick-stop budget" in o, f"the session ends by stage d's second stop: exit 8 (rc {rc}, {el:.0f} s)")
    if rc != 8:
        print(o[-1800:])
    sc = {st: score_txt(w, st) for st in STAGES}
    for st in STAGES:
        ok("SUMMARY:" in sc[st], f"{st}: one SUMMARY line")
    ok("h: H0 held" in sc["h"] and "H1 reads H-NOTENDED (3 of 3 jobs look exactly like a running task)" in sc["h"] and "stops 0" in sc["h"], "h: H0 held, H1 reads H-NOTENDED, no stop")
    ok("c: C0 held" in sc["c"] and "C5 kept 2 of 2" in sc["c"] and "stops 0" in sc["c"], "c: C0 held, every row kept, no stop")
    ok("e: E0 held; H-EXIT" in sc["e"] and "stops 1 [b3: busy (E537), read-write -1, dword 14 0x0]" in sc["e"], "e: E0 held, the scorer reads H-EXIT, B3 stopped (read = write - 1)")
    ok("d: D0 held; H-CCB supported" in sc["d"] and "stops 2" in sc["d"] and "read-write 1, dword 14 0xad002600" in sc["d"], "d: D0 held, H-CCB supported, both stops carry the marks")
    ok(not re.search(r"[1-9]\d* FAILED", sc["h"].split("SUMMARY:")[1].split("Q152 rows:")[1].split("held out:")[0]), "h: no control row failed")
    km, tr = default_checks(w, c)
    sj = {st: stage_json(w, st) for st in STAGES}
    ok([sj[s]["exit"] for s in STAGES] == [0, 0, 0, 8] and [sj[s]["stops"] for s in STAGES] == [0, 0, 1, 2], f"stage.json exits {[sj[s]['exit'] for s in STAGES]}, stops {[sj[s]['stops'] for s in STAGES]}")
    ok(sj["h"]["jobs_run"] == ["h0", "h0-r2", "h0-r3", "h1", "h1-r2", "h1-r3"], "h: the six jobs in the frozen order")
    ok(len(sj["c"]["jobs_run"]) == 13 and all(v == "ok" for v in sj["c"]["classes"].values()), "c: the 13 jobs, all kept")
    ok(sj["e"]["classes"]["x1"] == "ok" and sj["e"]["classes"]["x20-r2"] == "ok" and sj["e"]["classes"]["b3"] == "stop" and sj["e"]["jobs_run"][-1] == "b3",
       f"e: X1 and X20 kept, B3 LAST and stopped ({sj['e']['classes']})")
    d = sj["d"]["classes"]
    ok(d["d0"] == "ok" and d["d1"] == "ok" and d["d1-r3"] == "ok" and d["d2"] == "stop" and d["d3"] == "stop" and "d4" not in d,
       f"d: D0, D1 x3 kept, D2 and D3 stop; D3's stop was the second and ended the stage before D4 ({d})")
    ok(sj["d"]["jobs_run"][-1] == "d3", "d: D3 is the last job run (D4 only runs if D3 kept the tick)")
    njobs = sum(len(v["jobs_run"]) for v in sj.values())
    ok(km.count("resgx545 r3x case ") == njobs == 32, f"one case marker a job run ({njobs} = 6 + 13 + 7 + 6)")
    ok(km.count("resgx545 r3x class ") == njobs, "one class marker a job run")
    r2 = laprec(w, "d", "d2")
    s0 = r2["sig"]["samples"][0]
    ok(s0["ccb"][1] - s0["ccb"][0] == 1 and s0["hc14"] == 0xAD002600,
       "d2: the signature sample holds read = write + 1 and dword 14 = 0xad002600, read BEFORE the reset")
    ok(r2["p3"]["answered"] is False and r2["p3"]["after"]["ccb"][0] == r2["p3"]["before"]["ccb"][0] + 1 and r2["p3"]["after"]["ccb"][1] == r2["p3"]["before"]["ccb"][1],
       "d2: P3 (one miscinfo into the stopped EDM) was sent and not answered; the write offset moved by one, the read offset did not")
    ok([i for i, x in enumerate(tr) if x.endswith(" dump")], "the stops' dumps were taken")
    b3 = laprec(w, "e", "b3")
    ok(b3["class"] == "stop" and "p3" not in b3 and b3["kick"]["answered"] is False and b3["sig"]["samples"][0]["ccb"][1] - b3["sig"]["samples"][0]["ccb"][0] == -1,
       "b3: stopped, no P3 (its own kick is the probe), the kick was not answered, read = write - 1")
    h1 = laprec(w, "h", "h1")
    ok(len(h1["inside"]) == 2 and all(i["state"] == [1, 1] for i in h1["inside"]) and h1["status_text"].startswith("loaded 1"),
       "h1: two signatures inside the hold (STATE busy around each), one status read")
    h0 = laprec(w, "h", "h0")
    ok(len(h0["d0"]) == 20, "h0: the 20 `status` reads of the row's D0 were taken")
    ok(resets(w) == 7 + 1 + 2 + 8, f"resets: h 6 + end, c end, e stop + end, d 6 pre-job + 2 stops = 18 ({resets(w)})")
    ek = w / "home/r3xev-out/e/stop1-b3-reset.json"
    ok(ek.exists() and json.loads(ek.read_text())["health"]["ok"], "e: the reset after B3's stop recorded its health")
    rc, o = stage(e, c)
    ok(rc == 0, "restaging after the session works")
    rc, o = session(e, c, "--only", "e")
    ok(rc == 0 and "stage e done" in o, f"after restaging, e still runs: its gate comes from the kept stage.json of c (rc {rc})")


L_RD63 = 11          # r3layout.RD_FIELDS.index("sa63")
L_WRX = 9            # r3layout.WR_X - WR


@test
def t_full_session_once():
    """H-ONCE world: nothing stops in stage d; D1 runs three times and D4 runs (E537's combination), sa63 restored."""
    w, e, c = staged("once", "d_once")
    rc, o = session(e, c)
    ok(rc == 0 and o.rstrip().endswith("R3 done"), f"the whole session passes when nothing stops in d (rc {rc})")
    sj = {st: stage_json(w, st) for st in STAGES}
    ok(sj["d"]["exit"] == 0 and sj["d"]["stops"] == 0 and len(sj["d"]["jobs_run"]) == 7 and sj["d"]["classes"]["d4"] == "ok",
       f"d_once: stage d finishes with 7 jobs, D4 ran and kept the tick ({sj['d']['classes']})")
    sc = score_txt(w, "d")
    ok("H-ONCE (E537's word alone does not stop it)" in sc and "stops 0" in sc, "d: the SUMMARY reads H-ONCE")
    r4 = laprec(w, "d", "d4")
    ok(r4["restore"]["reader_ran"] and r4["restore"]["rd"][L_RD63] == 0, "D4: sa63 was restored after E537's combination (cmd 7, then the reader)")
    ok(r4["writer"]["wr"][L_WRX] == 0xD7C5F5AE, "D4's record: E537's sa63 word was written and read back")
    ok(sj["e"]["exit"] == 0 and sj["e"]["classes"]["b3"] == "stop" and sj["e"]["stops"] == 1, "e: one stop (B3), exit 0")
    tables = {s: json.loads((c / "tables" / f"{s}.json").read_text()) for s in STAGES}
    km = (w / "mock" / "kmsg").read_text()
    ok(km.count("resgx545 r3x case ") == sum(len(t["jobs"]) for t in tables.values()), "one case marker for each of the 33 jobs (the maximum)")


@test
def t_h_stop_ends_stage():
    """No stop is expected in stage h: the first ends it (stop budget 0), reset and gate exact, and the lead decides."""
    w, e, c = staged("h_stop", "h_stop")
    rc, o = session(e, c, "--only", "h")
    ok(rc == 8, f"a tick stop in stage h ends the stage at once: exit 8 (rc {rc})")
    sj = stage_json(w, "h")
    ok(sj["exit"] == 8 and sj["stops"] == 1 and sj["classes"]["h1"] == "stop" and "h1-r2" not in sj["jobs_run"], f"h1 stopped, nothing ran after it ({sj['jobs_run'][-2:]})")
    ok("stage h was ended by its tick-stop budget" in o, "the driver says the stage was ended by a stop")
    ok("h1: class stop" in score_txt(w, "h") and "stops 1 ['h1']" in score_txt(w, "h"), "the ended stage is still scored")


@test
def t_h_rearm():
    w, e, c = staged("h_rearm", "h_rearm")
    rc, o = session(e, c, "--only", "h")
    ok(rc == 0, f"stage h with an idle signature inside the hold (rc {rc})")
    sc = score_txt(w, "h")
    ok("H1 reads H-REARM" in sc and "differ in" in sc, "the scorer reads H-REARM and names the differing elements")


@test
def t_c_one_stop():
    w, e, c = staged("c_stop", "c_stop_c3")
    session(e, c, "--only", "h")
    rc, o = session(e, c, "--only", "c")
    ok(rc == 0, f"one budgeted tick stop (C3): the stage goes on and finishes (rc {rc})")
    sj = stage_json(w, "c")
    ok(sj["classes"]["c3"] == "stop" and sj["classes"]["c3-r2"] == "skipped" and sj["classes"]["c4"] == "ok" and sj["stops"] == 1,
       f"c3 stopped, c3-r2 NOT replicated (skipped), c4 ran after the reset ({sj['classes']})")
    rec = laprec(w, "c", "c3")
    ok(rec.get("sig") and len(rec["sig"]["samples"]) == 2 and rec["sig"]["samples"][0]["regs"].get("0x8") == 0xccfa0 and rec["p3"]["answered"] is False,
       "the stop record holds two register samples (the signature) taken before the reset, and P3")
    ok((w / "home/r3xev-out/c/baseline-1.json").exists() and (w / "home/r3xev-out/c/stop1-c3-reset.json").exists(), "after the stop's reset and re-arm the baseline reader ran")
    sc = score_txt(w, "c")
    ok("stops 1 ['c3']" in sc and "P3 answered in 0 of 1 stops" in sc and "c3-r2: not run" in sc, "the scorer reports the stop, P3 and the skipped replicate")


@test
def t_c_second_stop():
    w, e, c = staged("c_two", "c_stop_c3,c_stop_c4,c_second_stop")
    session(e, c, "--only", "h")
    rc, o = session(e, c, "--only", "c")
    ok(rc == 8, f"a second stop (C4) ends the stage: exit 8 (rc {rc})")
    sj = stage_json(w, "c")
    ok(sj["exit"] == 8 and sj["stops"] == 2 and sj["classes"]["c4"] == "stop" and "c5" not in sj["jobs_run"], f"c4 stopped and nothing ran after it ({sj['jobs_run'][-2:]})")
    ok(resets(w) >= 3 and "gate" in trace(w)[-1], "reset and gate were done after the second stop")
    rc, o = session(e, c, "--from", "e")
    ok(rc in (0, 8), f"after the lead's --from e the next stage runs (its gate accepts exit 8) (rc {rc})")
    ok("GATE e OPEN" in o or "stage e" in o or "####  e" in o or "#### e" in o, "stage e was gated open by c's exit 8")


@test
def t_p3_answered():
    w, e, c = staged("p3", "c_stop_c2,p3_answers")
    session(e, c, "--only", "h")
    rc, o = session(e, c, "--only", "c")
    rec = laprec(w, "c", "c2")
    ok(rec["p3"]["answered"] is True, "P3 answered (the mock's H-REARM switch): recorded as answered")
    ok("P3 answered in 1 of 1 stops" in score_txt(w, "c"), "the scorer counts it")


@test
def t_e_body():
    w, e, c = staged("e_body", "e_body")
    for st in ("h", "c"):
        session(e, c, "--only", st)
    rc, o = session(e, c, "--only", "e")
    ok(rc == 8, f"X1 stops and B3 stops: the second stop ends stage e (rc {rc})")
    sj = stage_json(w, "e")
    ok(sj["classes"]["x1"] == "stop" and sj["classes"]["x1-r2"] == "skipped" and sj["classes"]["x20"] == "skipped" and sj["classes"]["b3"] == "stop",
       f"X1 stopped, its replicate and X20 skipped, B3 ran LAST ({sj['classes']})")
    sc = score_txt(w, "e")
    ok("H-BODY (a tick pass handed to a fast-path task stops it too)" in sc and "x1: busy (E537), read-write 0, dword 14 0x0" in sc, "the scorer reads H-BODY with read = write and dword 14 = 0")
    r = laprec(w, "e", "x1")
    ok(r["p3"]["answered"] is False and r["p3"]["ring_new_entries"] == 0, "X1's stop: P3 not answered, no new ring entry")


@test
def t_e_tickonly():
    w, e, c = staged("e_tick", "e_tickonly")
    for st in ("h", "c"):
        session(e, c, "--only", st)
    rc, o = session(e, c, "--only", "e")
    ok(rc == 0, f"B3 keeps the tick (H-TICKONLY): no stop, exit 0 (rc {rc})")
    sj = stage_json(w, "e")
    ok(sj["classes"]["b3"] == "kick-timeout" and sj["stops"] == 0, f"b3: kick-timeout (the kick is not answered, the tick is kept) ({sj['classes']['b3']})")
    sc = score_txt(w, "e")
    ok("H-TICKONLY (the skipped kick pass keeps the tick)" in sc, f"the scorer reads H-TICKONLY ({sc.split('SUMMARY:')[-1][:150]})")
    ok("(read - write -1)" in sc, "B3 kept: read = write - 1 from the marks after the job")


@test
def t_d_handler():
    w, e, c = staged("d_handler", "d_handler")
    for st in ("h", "c", "e"):
        session(e, c, "--only", st)
    rc, o = session(e, c, "--only", "d")
    ok(rc == 8, f"D1 and D3 stop (H-HANDLER): the second stop ends stage d (rc {rc})")
    sj = stage_json(w, "d")
    ok(sj["classes"]["d1"] == "stop" and sj["classes"]["d1-r2"] == "skipped" and sj["classes"]["d1-r3"] == "skipped" and sj["classes"]["d2"] == "ok" and sj["classes"]["d3"] == "stop",
       f"D1 stopped (replicates skipped), D2 kept, D3 stopped ({sj['classes']})")
    ok("H-HANDLER supported" in score_txt(w, "d"), "the scorer reads H-HANDLER")


@test
def t_gate_closed_without_h():
    w, e, c = staged("gate_c")
    rc, o = session(e, c, "--only", "c")
    ok(rc == 40 and "gate of c is closed" in o, f"stage c does not run without a finished stage h in the kept output (rc {rc})")
    rc, o = runner(e, w, "c")
    ok(rc == 1 and "has no finished kept stage.json here" in o, f"the laptop runner refuses c without h's kept stage.json too (rc {rc})")
    rc, o = runner(e, w, "d")
    ok(rc == 1, f"d refuses without e (rc {rc})")


@test
def t_fatal_and_cleanup_stops():
    w, e, c = staged("fatal", "fatal@h1")
    rc, o = session(e, c, "--only", "h")
    ok(rc == 3, f"a watchdog line stops all laptop work: exit 3 (rc {rc}, resets {resets(w)})")
    w, e, c = staged("armfail", "armfail")
    rc, o = session(e, c, "--only", "h")
    ok(rc == 4 and resets(w) >= 1, f"an arm that is not healthy: exit 4, reset done (rc {rc})")
    w, e, c = staged("toolbad", "toolbad")
    rc, o = session(e, c, "--only", "h")
    ok(rc == 4 and "tool_bad" in o, f"a FAIL line anywhere in a tool command's output (not the last line) stops: exit 4 (rc {rc})")
    w, e, c = staged("gatefail", "gatefail")
    rc, o = session(e, c, "--only", "h")
    ok(rc == 5, f"a gate that is not exact after the stage: exit 5 (rc {rc})")
    w, e, c = staged("unhealthy", "unhealthy")
    rc, o = session(e, c, "--only", "h")
    ok(rc in (4, 5), f"an unhealthy GPU after a job stops (rc {rc})")
    w, e, c = staged("boom", "boom@h1")
    rc, o = session(e, c, "--only", "h")
    ok(rc in (4, 5) and (w / "home/r3xev-out/h/h1.json").exists(), f"an exception in a job still writes its record (rc {rc})")


def rehash(w, rel):
    lp = w / "home" / "r3xev" / "LAPTOP.sha256"
    p = w / "home" / "r3xev" / rel
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    lp.write_text("\n".join(f"{h}  {rel}" if x.endswith(rel) else x for x in lp.read_text().splitlines()) + "\n")


@test
def t_preflight_refusals():
    w, e, c = staged("pre")
    (w / "mock" / "srcv").write_text("OTHERSRCV\n")
    rc, o = runner(e, w, "h")
    ok(rc == 1, f"srcversion changed under the mock (loaded and installed are the same file here, but not the expected one): exit 1 (rc {rc})")
    (w / "mock" / "srcv").write_text("MOCKSRCV\n")
    e2 = dict(e, R3_SRCV_EXPECT="B21FDA82BD5E5CB5A627E3B")
    rc, o = runner(e2, w, "h")
    ok(rc == 1 and "not the one this session is prepared for" in o, f"loaded = installed but not the expected B21FDA82...: exit 1 (rc {rc})")
    rc, o = runner(e, w, "h")
    ok(rc == 0, f"loaded = installed = expected: stage h runs (rc {rc})")
    w, e, c = staged("pre2")
    (w / "mock" / "dbg" / "miscinfo").unlink()
    rc, o = runner(e, w, "h")
    ok(rc == 1 and "the driver has no debugfs miscinfo" in o, f"a debugfs file the stages need is missing: exit 1 (rc {rc})")
    (w / "mock" / "dbg" / "miscinfo").write_text("")
    tool = w / "home" / "sgxfive-test-s1b"
    tool.write_text(tool.read_text() + "\n# changed\n")
    rc, o = runner(e, w, "h")
    ok(rc == 1 and "pinned" in o, f"a tool that is not the pinned one: exit 1 (rc {rc})")
    tool.write_text((c / "tests" / "fake_tool.py").read_text())
    os.makedirs(w / "home" / "r3xev-out" / "h", exist_ok=True)
    (w / "home" / "r3xev-out" / "h" / "stage.json").write_text(json.dumps({"exit": 0, "run": "x"}))
    tb = w / "home" / "r3xev" / "tables" / "c.json"
    orig = tb.read_text()
    tb.write_text(orig + " ")
    rc, o = runner(e, w, "c")
    ok(rc == 1 and "is not the frozen file" in o, f"a table that is not the frozen file: exit 1 (rc {rc})")
    t = json.loads(orig)
    t["jobs"][3]["sa"] = ["sa63", "sa100"]
    tb.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    rehash(w, "tables/c.json")
    rc, o = runner(e, w, "c")
    ok(rc == 7 and "is not row" in o, f"a job whose sa set is not its row's: exit 7 (rc {rc}) {o.strip().splitlines()[-1][:80]}")
    for label, mod in (("a row C6", lambda t: t["jobs"].append(dict(t["jobs"][0], name="c6", row="C6"))),
                       ("C3 with a tested bit", lambda t: [j.__setitem__("w65", {"k": 1, "or": 0x1C0CC}) for j in t["jobs"] if j["row"] == "C3"]),
                       ("a run_if off the list", lambda t: t["jobs"][2].__setitem__("run_if", "shell:rm"))):
        t = json.loads(orig)
        mod(t)
        tb.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
        rehash(w, "tables/c.json")
        rc, o = runner(e, w, "c")
        ok(rc == 7, f"{label}: exit 7 (rc {rc})")
    tb2 = w / "home" / "r3xev" / "tables" / "e.json"
    orig2 = tb2.read_text()
    t = json.loads(orig2)
    t["jobs"][-1]["trigger"] = "kick"
    tb2.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    rehash(w, "tables/e.json")
    (w / "home" / "r3xev-out" / "c").mkdir(parents=True, exist_ok=True)
    (w / "home" / "r3xev-out" / "c" / "stage.json").write_text(json.dumps({"exit": 0, "run": "x"}))
    rc, o = runner(e, w, "e")
    ok(rc == 7, f"B3 with a bare-kick trigger: exit 7 (rc {rc})")
    t = json.loads(orig2)
    t["jobs"].insert(0, t["jobs"].pop())
    tb2.write_text(json.dumps(t, indent=1, sort_keys=True) + "\n")
    rehash(w, "tables/e.json")
    rc, o = runner(e, w, "e")
    ok(rc == 7 and "frozen order" in o, f"B3 placed first: exit 7, the order is the frozen one (rc {rc})")
    ok(resets(w) <= 1, "no preflight refusal touched the GPU (only stage h's good run reset it)")


@test
def t_laptop_limits_in_trace():
    """Every debugfs write of a whole default session: no kreg, no clock register, no knob, only the allow-listed arm lines."""
    w, e, c = staged("limits")
    rc, o = session(e, c)
    tr = trace(w)
    bad = [x for x in tr if re.search(r" wr (kreg|kregnow|kpoke|kicker|kick_no_bump|alias_skip|trc_hazard|render_pb_pages|hold_recovery|xfer_sync)", x)]
    ok(rc == 8 and not bad, f"no kreg, kpoke, kicker, knob or trc write in the whole trace ({len(tr)} lines)")
    arms = [x for x in tr if " wr own_arm " in x and not x.endswith(" wr own_arm 0")]
    ok(arms and all(re.search(r"own_arm slots=0x(1 entry=0|f entry=0,1,2,3)$", x) for x in arms), f"every arm line is on the allow-list ({sorted({x.split(' wr ')[1] for x in arms})})")
    ok(any("alias2.blob" in x for x in tr) and any("ring_end.blob" in x for x in tr) and any("ring_hold.blob" in x for x in tr),
       "the three blobs were armed (alias2, ring_end, ring_hold)")


def main():
    run_tests()
    print(f"\n{len(RAN)} tests, {len(FAIL)} failed" if FAIL or RAN else "no tests")
    if FAIL:
        for f in FAIL:
            print("FAILED:", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
