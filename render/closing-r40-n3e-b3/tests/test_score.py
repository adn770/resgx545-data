# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer on kept attempts (tests/attempt.py, E1148's register
snapshots). Every outcome frozen in predictions/own.tsv for this STEP has an attempt where it holds
(and is the RULE) and every other outcome FAILED; each control can fail and then no outcome is
claimed (BIF_FAULT is its own outcome); the pre-declared cannot-tell cases print CANNOT TELL. B
rows: the H-DM and H-ALL lines read RUN or NEVER against the frozen predictions (held, FAILED,
cannot tell); D0's survey, P0 and P1 are printed, never scored. Row L: T runs in every outcome;
L-NEVER and L-E1 are CANNOT TELL for the landing; the five landings each hold on their attempt,
a marker pair with the marker already there before the emit or split between sa and pa names
none; L-TICK and LAND-L are printed. The arm's log line is printed; the post scorer reads its
controls."""
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.dont_write_bytecode = True
import attempt  # noqa: E402
import kitscore as K  # noqa: E402
import score  # noqa: E402

STEP = score.STEP
LAND = score.LAND
if LAND:
    HOLDS = {"L-NEVER": ("past", "trun"), "L-E1": ("e1", "trun"),
             "L-SA": ("done", "trun", "msa"), "L-SHIFT": ("done", "trun", "mshift"),
             "L-PA": ("done", "trun", "mpa"), "L-ONE": ("done", "trun", "mone"),
             "L-NONE": ("done", "trun")}
    LANDS = {f"L-{k}" for k in ("SA", "SHIFT", "PA", "ONE", "NONE")}
    NONE_FITS = [("past", "t3"), ("done", "t3", "msa"), ("e1", "t0"), ("past", "tunequal"),
                 ("done", "trun", "mboth"), ("done", "trun", "mpre"),
                 ("done", "trun", "msa", "mpa")]
    BASE = HOLDS["L-SA"]
else:
    HOLDS = {f"{STEP}-NEVER": ("past", "trun", "ticks10"), f"{STEP}-T1": ("past", "t0"),
             f"{STEP}-T2": ("past", "t200"), f"{STEP}-T3": ("past", "t3"),
             f"{STEP}-E1": ("e1", "t3"), f"{STEP}-DONE": ("done", "t3")}
    LANDS = set()
    NONE_FITS = [("past", "tother"), ("past", "tunequal"), ("done", "trun"), ("e1", "t0"),
                 ("e1", "t200")]
    BASE = HOLDS[f"{STEP}-T3"]


def run(tmp_path, tokens):
    d = attempt.build(str(tmp_path), tokens)
    lines, ctl, hyp, rl = score.score_own(d)
    return lines + rl, ctl, hyp["c1-a"]


def rule(out):
    return next(ln for ln in out if ln.startswith(f"Q128-{STEP} RULE: "))


def test_every_frozen_outcome_has_an_attempt():
    names = {m for q in K.predictions(KP, "own").values() for mv in q.values() for m in mv}
    assert names - {"CTL"} == set(HOLDS)


def test_each_outcome_holds_on_its_attempt_and_the_others_fail(tmp_path_factory):
    for m, tokens in HOLDS.items():
        out, ctl, hyp = run(tmp_path_factory.mktemp("h"), tokens)
        assert all(s is True for s in ctl.values()), (m, ctl)
        assert hyp[m] is True, (m, hyp)
        assert all(s is False for k, s in hyp.items() if k != m), (m, hyp)
        if LAND and m not in LANDS:
            assert rule(out) == (f"Q128-{STEP} RULE: CANNOT TELL (the landing needs DONE; start "
                                 f"outcome {m}: {score.WHAT[m]})"), (m, rule(out))
        else:
            assert rule(out) == f"Q128-{STEP} RULE: {m}: {score.WHAT[m]}", (m, rule(out))


def test_the_pre_declared_cannot_tell_cases(tmp_path_factory):
    for tokens in NONE_FITS:
        out, _, hyp = run(tmp_path_factory.mktemp("n"), tokens)
        assert rule(out).startswith(f"Q128-{STEP} RULE: CANNOT TELL"), (tokens, rule(out))
        assert not any(s is True for s in hyp.values()), (tokens, hyp)


def test_each_control_can_fail_and_then_nothing_is_claimed(tmp_path_factory):
    cases = (("e0bad", "E0"), ("pgbad", "PG"), ("t0stop", "T0"))
    if LAND:
        cases += (("p0bad", "P0"), ("p1bad", "P1"))
    for tok, key in cases:
        out, ctl, _ = run(tmp_path_factory.mktemp("c"), BASE + (tok,))
        assert ctl[f"c1-a:{key}"] is False, (tok, ctl)
        assert rule(out).startswith(f"Q128-{STEP} RULE: CANNOT TELL") and key in rule(out)
        if not LAND:
            assert any(ln.endswith(": cannot tell") and ln.startswith("H-DM: predicted")
                       for ln in out), out
    out, ctl, _ = run(tmp_path_factory.mktemp("b"), BASE + ("bif",))
    assert ctl["c1-a:B"] is False and rule(out).startswith(f"Q128-{STEP} RULE: FAULT")


def test_the_hypothesis_lines(tmp_path_factory):
    """B rows: RUN is any of T1..DONE, NEVER is NEVER; each frozen prediction held or FAILED."""
    if LAND:
        out, _, _ = run(tmp_path_factory.mktemp("l"), BASE)
        assert not any(ln.startswith(("H-DM", "H-ALL")) for ln in out)
        return
    hdm, hall = score.ROWS[STEP][2], score.ROWS[STEP][3]
    for m, read in (("NEVER", "NEVER"), ("T1", "RUN"), ("E1", "RUN"), ("DONE", "RUN")):
        out, _, _ = run(tmp_path_factory.mktemp("p"), HOLDS[f"{STEP}-{m}"])
        for h, want in (("H-DM", hdm), ("H-ALL", hall)):
            ln = next(x for x in out if x.startswith(f"{h}:"))
            if want == "-":
                assert ln.startswith(f"{h}: no prediction") and f"(read {read})" in ln, ln
            else:
                assert ln == (f"{h}: predicted {want}, read {read}: "
                              + ("held" if want == read else "FAILED")), ln


def test_the_survey_and_the_landing_lines(tmp_path_factory):
    out, _, _ = run(tmp_path_factory.mktemp("s"), HOLDS[f"{STEP}-DONE" if not LAND else "L-SA"])
    assert any(ln.startswith("SURVEY (printed, not scored): land ") for ln in out), out
    assert any(ln.startswith("SURVEY sa20-sa31 post: ") for ln in out), out
    assert any(ln.startswith("LANDING (one exploratory row") for ln in out), out
    if LAND:
        tick = next(ln for ln in out if ln.startswith("L-TICK (printed, not scored): "))
        assert "(running)" in tick and "after a DONE with no tim" in tick, tick
        land = next(ln for ln in out if ln.startswith("LAND-L (printed): "))
        assert "lland SA" in land and "post sa24 0x5a5a3a18 sa26 0x5a5a3a1a" in land, land
        assert any(ln.startswith("TICK: land has no tim") for ln in out)
    else:
        p = next(ln for ln in out if ln.startswith("SURVEY controls (printed, not scored): "))
        assert p.endswith("P0 PASS; P1 PASS"), p
        out2, _, _ = run(tmp_path_factory.mktemp("s"), HOLDS[f"{STEP}-DONE"] + ("p0bad",))
        assert rule(out2) == rule(out)          # P0 is printed, never scored, in the B rows
        assert "P0 FAILED" in next(ln for ln in out2 if ln.startswith("SURVEY controls"))
    out, _, _ = run(tmp_path_factory.mktemp("s"), BASE[:1] + ("t3",) if not LAND else
                    ("e1", "trun"))
    assert not any(x.startswith("LANDING") for x in out)


def test_the_page_falls_back_to_the_stop_dump(tmp_path):
    tokens = HOLDS["L-NEVER"] if LAND else BASE
    d = attempt.build(str(tmp_path), tokens)
    os.remove(os.path.join(d, "c1-a.own_res.json.gz"))
    lines, ctl, hyp, rl = score.score_own(d)
    assert "page stop0-own_res.json" in lines[0]
    m = "L-NEVER" if LAND else f"{STEP}-T3"
    assert hyp["c1-a"][m] is True and all(ctl.values()), (hyp, ctl)


def test_the_arm_line_and_the_x0_qualifier(tmp_path_factory):
    out, _, _ = run(tmp_path_factory.mktemp("x"), BASE)
    arm = next(ln for ln in out if ln.startswith("ARM (printed, not scored): "))
    words = [w for w in attempt.make.ARM.split()
             if w.startswith(("pds=", "pdsat=", "pds2=", "form="))]
    assert "emit image 0x" in arm and all(w in arm for w in words), arm
    assert any(ln.startswith("X0 qualifier: 0x5a5a3303 (the issuer went on") for ln in out)
    tick = next(ln for ln in out if ln.startswith("TICK: Δtick "))
    assert "from the command write" in tick and "no kick" in tick, tick


def test_the_scorer_runs_as_the_driver_runs_it(tmp_path):
    d = attempt.build(str(tmp_path), BASE)
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "own", d],
                       capture_output=True, text=True)
    assert r.returncode == 0 and f"Q128-{STEP} RULE: " in r.stdout, r.stdout + r.stderr


def test_post_controls(tmp_path):
    d = tmp_path / "post"
    d.mkdir()
    cols = "\t".join(K.COLUMNS)
    rows = [cols] + ["\t".join([n, "post", "control", "safe", "reads:diff", "t30", a, "0", "ok",
                                "-", "-", "1"]) for n, a in (("p1-tri", "tri"),
                                                            ("p2-fill", "fill"))]
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text(cols + "\n")
    import importlib.util
    spec = importlib.util.spec_from_file_location("world", os.path.join(KP, "mock/world.py"))
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    (d / "p1-tri.txt").write_text(w.TRI)
    (d / "p2-fill.txt").write_text(w.FILL)
    lines, c = score.score_post(str(d))
    assert c == {"p1-tri": True, "p2-fill": True} and "exactly" in lines[-1]
    (d / "p1-tri.txt").write_text(w.TRI.replace("diff: 0 of", "diff: 9 of"))
    lines, c = score.score_post(str(d))
    assert c["p1-tri"] is False and "FAILED" in lines[-1]
