# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer of stage own (R1) on kept attempts (tests/attempt.py,
r37 A's register snapshots). N0-OK and N0-STOP each hold on their attempt (and are the RULE line)
while the other FAILED; each control can fail and then nothing is claimed (BIF_FAULT is its own
outcome); the pre-declared cannot-tell cases; r37 A's own kept attempt (E1149, emitsb: no done,
ticks 10) reads N0-STOP; the post scorer reads its controls."""
import gzip
import os
import shutil
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import attempt  # noqa: E402
import kitscore as K  # noqa: E402
import score  # noqa: E402

HOLDS = {"N0-OK": ("done",), "N0-STOP": ("stop",)}


def run(tmp_path, tokens):
    d = attempt.own(str(tmp_path), tokens)
    lines, ctl, hyp, rl = score.score_own(d)
    return lines + rl, ctl, hyp["n0"]


def rule(out):
    return next(ln for ln in out if ln.startswith("N3c-R1 RULE: "))


def test_every_frozen_outcome_has_an_attempt():
    names = {m for q in K.predictions(KP, "own").values() for mv in q.values() for m in mv}
    assert names - {"CTL"} == set(HOLDS)


def test_each_outcome_holds_on_its_attempt_and_the_other_fails(tmp_path_factory):
    for m, tokens in HOLDS.items():
        out, ctl, hyp = run(tmp_path_factory.mktemp("h"), tokens)
        assert all(s is True for s in ctl.values()), (m, ctl)
        assert hyp[m] is True and all(s is False for k, s in hyp.items() if k != m), (m, hyp)
        assert rule(out) == f"N3c-R1 RULE: {m}: {score.WHAT[m]}", rule(out)


def test_a_done_job_with_few_ticks_is_n0_stop(tmp_path):
    out, _, hyp = run(tmp_path, ("done", "ticks20"))
    assert hyp == {"N0-OK": False, "N0-STOP": True}
    assert rule(out).startswith("N3c-R1 RULE: N0-STOP")


def test_the_pre_declared_cannot_tell_cases(tmp_path_factory):
    for tokens in (("done", "gatebad"), ("done", "nox0")):
        out, _, hyp = run(tmp_path_factory.mktemp("n"), tokens)
        assert rule(out).startswith("N3c-R1 RULE: CANNOT TELL"), (tokens, rule(out))
        assert not any(s is True for s in hyp.values()), (tokens, hyp)


def test_each_control_can_fail_and_then_nothing_is_claimed(tmp_path_factory):
    for base in HOLDS.values():
        for tok, key in (("e0bad", "E0"), ("pgbad", "PG"), ("t0stop", "T0")):
            out, ctl, _ = run(tmp_path_factory.mktemp("c"), base + (tok,))
            assert ctl[f"n0:{key}"] is False, (tok, ctl)
            assert rule(out).startswith("N3c-R1 RULE: CANNOT TELL") and key in rule(out)
        out, ctl, _ = run(tmp_path_factory.mktemp("b"), base + ("bif",))
        assert ctl["n0:B"] is False and rule(out).startswith("N3c-R1 RULE: FAULT")


def test_the_page_falls_back_to_the_stop_dump(tmp_path):
    d = attempt.own(str(tmp_path), ("stop",))
    os.remove(os.path.join(d, "n0.own_res.json.gz"))
    lines, ctl, hyp, rl = score.score_own(d)
    assert "page stop0-own_res.json" in lines[0] and rl[0].startswith("N3c-R1 RULE: N0-STOP")


def test_r37_a_s_kept_attempt_reads_n0_stop(tmp_path):
    """E1149's kept files (emitsb, the emit's stop) renamed to n0: ticks 10, no done."""
    import pins
    d = tmp_path / "own"
    d.mkdir()
    for suf in ("snap0.regs", "snap9.regs", "stop0-regs.txt"):
        (d / f"n0.{suf}.gz").write_bytes(gzip.compress(pins.blob(attempt.E1149 + suf + ".gz"),
                                                       mtime=0))
    src = attempt.own(str(tmp_path / "x"), ("stop",))
    for f in ("n0.own_res.json.gz", "n0.stop0-own_res.json.gz", "n0.txt.gz", "cases.tsv",
              "void.tsv", "readings.tsv"):
        shutil.copy(os.path.join(src, f), d / f)
    lines, ctl, hyp, rl = score.score_own(str(d))
    assert hyp["n0"] == {"N0-OK": False, "N0-STOP": True} and all(ctl.values())
    assert rl[0] == "N3c-R1 RULE: N0-STOP: our path stops the tick without any emit"


def test_the_scorer_runs_as_the_driver_runs_it(tmp_path):
    d = attempt.own(str(tmp_path), ("done",))
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "own", d],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "N3c-R1 RULE: N0-OK" in r.stdout, r.stdout + r.stderr


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
