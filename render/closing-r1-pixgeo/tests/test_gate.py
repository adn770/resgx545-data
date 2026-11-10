#!/usr/bin/env python3
"""score/gate072c.py on synthetic trial jobs: one clean job and one job for each criterion G1-G6 failing alone.  (The
laptop-side shell version of the same rule is exercised end to end by tests/run_mock.sh, `gate ...` lines.)"""
import sys
sys.dont_write_bytecode = True

import pathlib  # noqa: E402

R1 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R1 / "score"), str(R1 / "tests")]
import gate072c as GT  # noqa: E402
from synth import dpm_job_text  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


good = dpm_job_text(0x400, [19], count=1)
c, why = GT.gate_check(good, "", "ok", 19, True)
check("clean: class ok, empty slice, 0x072c plausible, 0x0724 peak = U, triangle fine", c and not why, str(why))
c, why = GT.gate_check(good, "[1234] resgx545 case x 1\n[1235] resgx545 r1 class x ok", "ok", 19, True)
check("a slice holding only our own markers is clean", c, str(why))
for label, args, want in (
        ("G1 hang", (good, "", "hang", 19, True), "G1"),
        ("G1 fault", (good, "", "fault", 19, True), "G1"),
        ("G2 a kernel log line", (good, "gma500 0000:00:02.0: [drm] SGX: odd", "ok", 19, True), "G2"),
        ("G3 no 0x072c column", (dpm_job_text(0x400, [19], with_072c=False), "", "ok", 19, True), "G3"),
        ("G3 five rows only", ("\n".join(good.splitlines()[:6]) + "\n", "", "ok", 19, True), "G3"),
        ("G4 0xffffffff", (dpm_job_text(0x400, [19], bad_072c=0xffffffff), "", "ok", 19, True), "G4"),
        ("G4 0xdeadbeef", (dpm_job_text(0x400, [19], bad_072c=0xdeadbeef), "", "ok", 19, True), "G4"),
        ("G4 high half 0x41", (dpm_job_text(0x400, [19], count=0x41), "", "ok", 19, True), "G4"),
        ("G4 never non-zero", (dpm_job_text(0x400, [19], bad_072c=0), "", "ok", 19, True), "G4"),
        ("G5 peak 20 for U 19", (dpm_job_text(0x400, [20]), "", "ok", 19, True), "G5"),
        ("G6 the triangle needed a reset", (good, "", "ok", 19, False), "G6")):
    c, why = GT.gate_check(*args)
    check(f"{label}: not clean, names {want}", (not c) and any(w.startswith(want) for w in why), str(why))
# an rc-3 overflow job of the normal class is clean when its timeline is
over = dpm_job_text(0x400, [19, 7], partials=1, count=2)
c, why = GT.gate_check("probe x: failed: scene overflowed the parameter buffer\n" + over, "", "ok", 19, True)
check("a job with a partial render (rc 3, scene overflowed) is clean when peak and values are", c, str(why))
sys.exit(0 if ok else 1)
