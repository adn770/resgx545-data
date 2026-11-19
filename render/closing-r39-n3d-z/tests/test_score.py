# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer on kept attempts (tests/attempt.py, E1148's register
snapshots). Every outcome frozen in predictions/own.tsv for this STEP has an attempt where it holds
(and is the RULE) and every other outcome FAILED; each control can fail (K0 both ways: a tick took
the command, a tick emitted) and then no outcome is claimed (BIF_FAULT is its own outcome); the
pre-declared cannot-tell cases (Δtick from the kick outside 8-11, T any other value) print CANNOT
TELL; S1 with T 0 or 0x200 is printed as its own reading; the arm's log line and the miscinfo
reply are printed; the post scorer reads its controls."""
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
# an attempt where each frozen outcome holds (ticksN: the record's ticks_from_kick)
HOLDS = {f"{STEP}-NEVER": ("past", "trun", "ticks10"), f"{STEP}-T1": ("past", "t0"),
         f"{STEP}-T2": ("past", "t200"), f"{STEP}-T3": ("past", "t3"),
         f"{STEP}-E1": ("e1", "t3"), f"{STEP}-DONE": ("done", "t3")}
# attempts no frozen outcome fits: CANNOT TELL
NONE_FITS = [("past", "tother"), ("past", "tunequal"), ("done", "trun"), ("e1", "t0"),
             ("e1", "t200")]
BASE = HOLDS[f"{STEP}-T3"]


def run(tmp_path, tokens):
    d = attempt.build(str(tmp_path), tokens)
    lines, ctl, hyp, rl = score.score_own(d)
    return lines + rl, ctl, hyp["c1-a"]


def rule(out):
    return next(ln for ln in out if ln.startswith(f"N3d-{STEP} RULE: "))


def test_every_frozen_outcome_has_an_attempt():
    names = {m for q in K.predictions(KP, "own").values() for mv in q.values() for m in mv}
    assert names - {"CTL"} == set(HOLDS)


def test_each_outcome_holds_on_its_attempt_and_the_others_fail(tmp_path_factory):
    for m, tokens in HOLDS.items():
        out, ctl, hyp = run(tmp_path_factory.mktemp("h"), tokens)
        assert all(s is True for s in ctl.values()), (m, ctl)
        assert hyp[m] is True, (m, hyp)
        assert all(s is False for k, s in hyp.items() if k != m), (m, hyp)
        assert rule(out) == f"N3d-{STEP} RULE: {m}: {score.WHAT[m]}", (m, rule(out))


def test_the_pre_declared_cannot_tell_cases(tmp_path_factory):
    for tokens in NONE_FITS:
        out, _, hyp = run(tmp_path_factory.mktemp("n"), tokens)
        assert rule(out).startswith(f"N3d-{STEP} RULE: CANNOT TELL"), (tokens, rule(out))
        assert not any(s is True for s in hyp.values()), (tokens, hyp)


def test_each_control_can_fail_and_then_nothing_is_claimed(tmp_path_factory):
    for tok, key in (("e0bad", "K1"), ("pgbad", "PG"), ("t0stop", "T0"), ("k0cmd", "K0"),
                     ("k0slot", "K0")):
        out, ctl, _ = run(tmp_path_factory.mktemp("c"), BASE + (tok,))
        assert ctl[f"c1-a:{key}"] is False, (tok, ctl)
        assert rule(out).startswith(f"N3d-{STEP} RULE: CANNOT TELL") and key in rule(out)
    out, ctl, _ = run(tmp_path_factory.mktemp("b"), BASE + ("bif",))
    assert ctl["c1-a:B"] is False and rule(out).startswith(f"N3d-{STEP} RULE: FAULT")


def test_the_page_falls_back_to_the_stop_dump(tmp_path):
    d = attempt.build(str(tmp_path), BASE)
    os.remove(os.path.join(d, "c1-a.own_res.json.gz"))
    lines, ctl, hyp, rl = score.score_own(d)
    assert "page stop0-own_res.json" in lines[0]
    assert not rule(rl).startswith(f"N3d-{STEP} RULE: CANNOT TELL"), rule(rl)


def test_never_reads_no_tick_band(tmp_path_factory):
    # refrozen 2026-11-19 after r39-n3d-k (20261119-152848) stopped the tick 7 from the kick,
    # outside the 8-11 band carried over from R4: NEVER is read from T and S1 alone, as R4's
    for n in (3, 7, 8, 11, 12, 30):
        out, _, hyp = run(tmp_path_factory.mktemp("b"), ("past", "trun", f"ticks{n}"))
        assert hyp[f"{STEP}-NEVER"] is True, (n, hyp)


def test_the_x0_qualifier_the_arm_the_kick_and_the_tick_notes(tmp_path_factory):
    out, _, _ = run(tmp_path_factory.mktemp("x"), BASE)
    assert any(ln.startswith("X0 qualifier: 0x5a5a3303 (the issuer went on") for ln in out)
    tick = next(ln for ln in out if ln.startswith("TICK: Δtick "))
    assert tick.startswith("TICK: Δtick 1 from the kick (K0)") and "; 4 from the command write" \
        in tick and "3 between the command write and K0" in tick, tick
    kick = next(ln for ln in out if ln.startswith("KICK (printed, not scored): "))
    assert "GETMISCINFO answered" in kick, kick
    out2, _, _ = run(tmp_path_factory.mktemp("k"), BASE + ("noreply",))
    assert "Connection timed out" in next(ln for ln in out2 if ln.startswith("KICK"))
    assert not rule(out2).startswith(f"N3d-{STEP} RULE: CANNOT TELL")     # printed, not scored
    arm = next(ln for ln in out if ln.startswith("ARM (printed, not scored): "))
    words = [w for w in attempt.make.ARM.split()
             if w.startswith(("pds=", "pdsat=", "pds2=", "form="))]
    assert "emit image 0x" in arm and all(w in arm for w in words), arm
    assert ("pdsat=fw14" in arm) == ("pdsat=fw14" in attempt.make.ARM), arm
    sig = next(ln for ln in out if ln.startswith("SIGNATURE"))
    # E1148's snap9: USE0_SERV_EVENT 0x000109a8 (bit 16 set), HostCtl dword 12 0x9a3
    assert "snap9: bit 16 1, count - tick 5" in sig, sig
    out, _, _ = run(tmp_path_factory.mktemp("i"), ("issuer",) + BASE[1:])
    assert any("X0 qualifier: 0xdeadc0de (the fill" in ln for ln in out), out
    assert any(ln.startswith("TICK: T1 stops the tick by design") for ln in out)


def test_the_alive_reading_is_printed(tmp_path_factory):
    out, _, _ = run(tmp_path_factory.mktemp("a"), ("past", "alive", "ticks230"))
    assert "; K0 cmd 1 slot 1 0xdeadc0de; ticks from the kick 230; ticks 233 " in out[0], out[0]
    assert "; alive true" in out[0], out[0]
    out, _, _ = run(tmp_path_factory.mktemp("a"), ("past", "ticks10"))
    assert "; alive false" in out[0], out[0]


def test_the_landing_is_printed_after_an_ok_end_only(tmp_path_factory):
    done = HOLDS[f"{STEP}-DONE"]
    out, _, _ = run(tmp_path_factory.mktemp("l"), done + ("pa",))
    ln = next(x for x in out if x.startswith("LANDING"))
    assert "pa0 = V0 yes, pa2 = V2 yes" in ln and "not N3's rule" in ln
    out, _, _ = run(tmp_path_factory.mktemp("l"), done)
    assert "pa0 = V0 no, pa2 = V2 no" in next(x for x in out if x.startswith("LANDING"))
    out, _, _ = run(tmp_path_factory.mktemp("l"), BASE)
    assert not any(x.startswith("LANDING") for x in out)


def test_s1_early_is_its_own_reading(tmp_path_factory):
    for t in ("t0", "t200"):
        out, _, _ = run(tmp_path_factory.mktemp("s"), ("e1", t))
        assert any(ln.startswith("S1-EARLY: ") for ln in out), (t, out)


def test_any_run_outcome_names_the_step_s_run(tmp_path_factory):
    for m in ("T1", "T2", "T3", "E1", "DONE"):
        out, _, _ = run(tmp_path_factory.mktemp("r"), HOLDS[f"{STEP}-{m}"])
        assert f"({STEP}-RUN: " in rule(out), rule(out)
    out, _, _ = run(tmp_path_factory.mktemp("r"), HOLDS[f"{STEP}-NEVER"])
    assert "-RUN" not in rule(out), rule(out)


def test_the_scorer_runs_as_the_driver_runs_it(tmp_path):
    d = attempt.build(str(tmp_path), BASE)
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "own", d],
                       capture_output=True, text=True)
    assert r.returncode == 0 and f"N3d-{STEP} RULE: " in r.stdout, r.stdout + r.stderr


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
