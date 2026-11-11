#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""test_score_r4b.py: the scorer of stage fr on worlds built from E817's kept records (tests/worlds_r4b.py), written before the
scorer.  One world per outcome: H-REP (3 of 3 stops with E817's signature), H-NOREP (3 of 3 kept), mixed, a stop with another
signature (clock idle, P3 answered, read offset moved, dword 14 set), a failed control, a control with no data, a wrong exit index,
a void replicate.  Also: the scorer copies scorekit byte for byte and draws its verdicts from it."""
import hashlib
import pathlib
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
R4 = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(R4 / "score"))
import worlds_r4b as W  # noqa: E402

FAIL = []
TMP = pathlib.Path(tempfile.mkdtemp(prefix="r4b-score-"))


def ok(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAIL.append(what)


def run(name, **kw):
    import score_r4b as S
    d = W.make(TMP / name, **kw)
    return S.score(d)


def main():
    try:
        import score_r4b as S  # noqa: F401
    except Exception as e:
        ok(False, f"score/score_r4b.py imports ({e!r})")
        print(f"{len(FAIL)} FAILED")
        return 1
    src = (R4 / "score" / "score_r4b.py").read_text()
    ok("import scorekit" in src and "def bracket" not in src and "def headline" not in src,
       "the scorer imports scorekit and defines no verdict rule of its own")
    landed = subprocess.run(["git", "-C", str(pathlib.Path.home() / "src/resgx545"), "show", "6421c1c:tools/closing/scorekit.py"],
                            capture_output=True).stdout
    ok(hashlib.sha256(landed).hexdigest() == hashlib.sha256((R4 / "score" / "scorekit.py").read_bytes()).hexdigest(),
       "score/scorekit.py is resgx545 6421c1c's byte for byte")

    r = run("rep")
    ok(r["controls_gate"] is True, "H-REP world: every control passes")
    ok(r["reps"] == {"fcf1": "REPRO", "fcf2": "REPRO", "fcf3": "REPRO"}, f"H-REP world: three REPRO replicates ({r['reps']})")
    ok(r["h_rep"] == "held" and r["h_norep"] == "refuted", f"H-REP world: H-REP held, H-NOREP refuted ({r['h_rep']}, {r['h_norep']})")
    ok("3 of 3 rows decided" in r["headline_rep"] and "not supported" in r["headline_norep"], f"H-REP headline: {r['headline_rep']}")
    ok(r["summary"].startswith("SUMMARY: fr: ") and "H-REP held" in r["summary"], f"summary: {r['summary'][:160]}")

    r = run("norep", fcf=("kept", "kept", "kept"))
    ok(r["reps"] == {"fcf1": "KEPT", "fcf2": "KEPT", "fcf3": "KEPT"}, f"H-NOREP world: three KEPT ({r['reps']})")
    ok(r["h_rep"] == "refuted" and r["h_norep"] == "held", f"H-NOREP world: H-NOREP held ({r['h_rep']}, {r['h_norep']})")
    ok("3 of 3 rows decided" in r["headline_norep"] and "not supported" in r["headline_rep"], f"H-NOREP headline {r['headline_norep']}")

    r = run("mixed", fcf=("stop", "kept", "stop"))
    ok(r["h_rep"] == "mixed" and r["h_norep"] == "mixed", f"mixed world: mixed, never held ({r['h_rep']}, {r['h_norep']})")
    ok("mixed" in r["summary"], "mixed world: the summary says mixed")

    for name, kw, why in (("idle", {"sig": {"fcf2": {"0x8": 0x20}}}, "the clock idle"),
                          ("p3", {"p3": {"fcf2": True}}, "P3 answered"),
                          ("rmw", {"marks": {"fcf2": ([2, 3], 0)}}, "read offset = write + 1"),
                          ("hc14", {"marks": {"fcf2": ([2, 2], 0xAD002600)}}, "dword 14 the assert word"),
                          ("status", {"sig": {"fcf2": {"0x12c": 0}}}, "EVENT_STATUS 0")):
        r = run(name, **kw)
        ok(r["reps"]["fcf2"] == "STOP-OTHER", f"{why}: fcf2 is a stop with another signature ({r['reps']['fcf2']})")
        ok(r["h_rep"] == "mixed" and r["h_norep"] == "refuted", f"{why}: H-REP mixed, H-NOREP refuted ({r['h_rep']}, {r['h_norep']})")

    # the gates are per block: block N's e0, fc4 x2, fb x2 and its arm gate fcfN; fk(N-1) and its re-arm gate fcfN too
    r = run("ctlfail", classes={"b2fb-r2": "stop"})
    ok(r["controls"]["b2fb-r2"] == "FAILED", "a stopped control of block 2 (b2fb-r2) is FAILED")
    ok(r["gates"]["fcf2"] is False and r["gates"]["fcf1"] is True and r["gates"]["fcf3"] is True,
       f"it shuts block 2's gate only ({r['gates']})")
    ok(r["rows_rep"] == {"fcf1": True, "fcf2": None, "fcf3": True}, f"fcf2 cannot tell, fcf1 and fcf3 decided ({r['rows_rep']})")
    ok(r["h_rep"] == "cannot tell" and r["headline_rep"].startswith("controls FAILED"),
       f"a gated replicate: combine cannot tell, the headline names the failed control ({r['headline_rep'][:80]})")

    r = run("fk1fail", classes={"fk1": "stop"})
    ok(r["controls"]["fk1"] == "FAILED" and r["gates"]["fcf2"] is False and r["gates"]["fcf3"] is True,
       f"fk1 (the pass after block 1's recovery) gates block 2 only ({r['gates']})")

    r = run("fk3fail", classes={"fk3": "stop"})
    ok(r["controls"]["fk3"] == "FAILED" and all(r["gates"].values()) and r["h_rep"] == "held",
       "fk3 gates no replicate (no block follows it): H-REP still held")
    ok("fk3: FAILED" in r["summary"], "fk3's failure is reported in the SUMMARY")

    r = run("ctlnodata", drop=("b3fc4",))
    ok(r["controls"]["b3fc4"] == "NODATA" and r["gates"]["fcf3"] is False, "a control with no record is NODATA and shuts its block's gate")
    ok(r["headline_rep"].startswith("cannot tell"), f"NODATA control headline: {r['headline_rep'][:80]}")

    r = run("ctlskip", skip=("b1fb",))
    ok(r["controls"]["b1fb"] == "NODATA", "a skipped control is NODATA, never a pass")

    r = run("e817own")
    ok(all(r["controls"][f"b{b}{x}"] == "PASS" for b in (1, 2, 3) for x in W.BLOCK), "E817's own kept records pass as every block control")
    ok(r["controls"]["fk1"] == "PASS", "E817's fph passes as fkN")

    r = run("armexit", arm_exit={"b2e0.arm": 0})
    ok(r["controls"]["arm2"] == "FAILED" and r["gates"]["fcf2"] is False, "block 2's arm with exit 0 fails arm2 and gates fcf2")
    r = run("rearmexit", arm_exit={"rearm-fcf1": 0})
    ok(r["controls"]["rearm1"] == "FAILED" and r["gates"]["fcf2"] is False and r["gates"]["fcf1"] is True,
       "the re-arm after fcf1 with exit 0 gates block 2")

    r = run("void", fcf=("stop", "stop", "void"))
    ok(r["reps"]["fcf3"] is None, "a void replicate is cannot tell, never a pass")
    ok(r["h_rep"] == "cannot tell" and "2 of 3 rows decided" in r["headline_rep"], f"void: combine cannot tell, headline {r['headline_rep']}")

    r = run("allvoid", fcf=("void", "void", "void"))
    ok(r["headline_rep"].startswith("cannot tell: no row decided"), f"no FCF row decided: {r['headline_rep']}")

    # the CLI prints the lines and one SUMMARY line, exit 0
    d = W.make(TMP / "cli")
    p = subprocess.run([sys.executable, str(R4 / "score" / "score_r4b.py"), "fr", str(d)], capture_output=True, text=True)
    ok(p.returncode == 0 and sum(1 for ln in p.stdout.splitlines() if ln.startswith("SUMMARY: ")) == 1, "the CLI prints one SUMMARY")
    p = subprocess.run([sys.executable, str(R4 / "score" / "score_r4b.py"), "fr", str(TMP / "nothing-here")], capture_output=True,
                       text=True)
    ok("cannot tell" in p.stdout and "SUMMARY" in p.stdout, "an empty directory: cannot tell, still one SUMMARY")
    print(f"{len(FAIL)} FAILED" if FAIL else "all passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
