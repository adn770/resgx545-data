# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer replayed on round 40's KEPT attempts (B11's two, B0's, L's; pinned)
with job 2 (and LC's job 3) fabricated as the tokens say (tests/attempt.py): every frozen outcome of
the session's stages held where it must hold and FAILED or cannot tell where it must not, the
controls able to fail, and the RULE and PREDICTION lines. B11's own gate lines (its fill's BIF
fault 0xd0400 at 0x4300f, both attempts) are what X-FILL and Y-FILL hold on."""
import os
import subprocess
import sys

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import attempt  # noqa: E402
import make  # noqa: E402
import score  # noqa: E402

STAGES = {s[0]: s[1] for s in make.STAGES[make.STEP]}


def run(tmp_path, stage, *tokens):
    d = attempt.build(str(tmp_path / "-".join(tokens or ("plain",))), stage, tokens)
    r = subprocess.run([sys.executable, "-B", "score/score.py", stage, d], cwd=KP,
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    assert r.returncode == 0 and "SUMMARY:" in r.stdout, r.stdout + r.stderr
    return r.stdout


def outcome(out, name):
    for ln in out.splitlines():
        if ln.startswith("OUTCOME ") and ln.split()[2] == name + ":":
            return ln.split(": ", 1)[1]
    return None


def rule(out, m):
    return next(ln for ln in out.splitlines() if ln.startswith(f"Q128-N3F-{m} RULE: "))


def pred(out, name):
    return next(ln for ln in out.splitlines() if ln.startswith(f"PREDICTION {name}:"))


def test_the_stages_are_the_generator_s():
    assert {s: v[0] for s, v in score.STAGES.items()} == STAGES
    assert {s: (v[1], v[2]) for s, v in score.STAGES.items()} == \
        {s[0]: (s[5], s[7]) for s in make.STAGES[make.STEP]}


@pytest.mark.skipif("c" not in STAGES, reason="H1 only")
def test_c_same_and_its_gate_hold_on_b0_s_attempt(tmp_path):
    out = run(tmp_path, "c", "b0", "after2=same", "gexact")
    assert outcome(out, "C-SAME") == "held" and outcome(out, "C-GATE") == "held"
    assert outcome(out, "C-DIFF") == "FAILED" and outcome(out, "C-NOKICK") == "FAILED"
    assert rule(out, "C").endswith("RULE: C-GATE, C-SAME")
    assert pred(out, "C-SAME").endswith(": held") and pred(out, "C-DIFF").endswith(": held")
    assert "every control passed" in out


@pytest.mark.skipif("c" not in STAGES, reason="H1 only")
@pytest.mark.parametrize("tokens,held", [(("after2=diff",), "C-DIFF"), (("j2stop",), "C-NOKICK")])
def test_c_s_failures(tmp_path, tokens, held):
    out = run(tmp_path, "c", "b0", "gexact", *tokens)
    assert outcome(out, held) == "held" and outcome(out, "C-SAME") == "FAILED"
    assert pred(out, "C-SAME").endswith(": FAILED")


@pytest.mark.skipif("c" not in STAGES, reason="H1 only")
def test_c_s_gate_failing_fails_c_gate(tmp_path):
    out = run(tmp_path, "c", "b0", "after2=same", "gfill")
    assert outcome(out, "C-GATE") == "FAILED" and pred(out, "C-GATE").endswith(": FAILED")


XY = [s for s in STAGES if STAGES[s] in ("X", "Y")]


@pytest.mark.parametrize("stage", XY)
@pytest.mark.parametrize("base", ["b11a", "b11b"])
def test_rebase_and_fill_hold_on_b11_s_kept_attempts(tmp_path, stage, base):
    """B11's page (pre, post, its survey) and its gate's fault line, verbatim, with job 2's
    after-read fabricated as job 1's post: M-REBASE and M-FILL held, nothing else."""
    m = STAGES[stage]
    out = run(tmp_path, stage, base, "after2=rebase", "gfill")
    assert outcome(out, f"{m}-REBASE") == "held" and outcome(out, f"{m}-FILL") == "held", out
    for x in ("HIGH", "NONE", "OTHER", "KICKFAULT", "NOKICK"):
        assert outcome(out, f"{m}-{x}") == "FAILED", (x, out)
    assert rule(out, m).endswith(f"RULE: {m}-FILL, {m}-REBASE")
    assert "GATE " in out and "fault page 0x00043000 is job 1's post sa13" in out


@pytest.mark.parametrize("stage", XY)
@pytest.mark.parametrize("after,held", [("high", "HIGH"), ("none", "NONE"), ("other", "OTHER")])
def test_the_other_after_reads_on_b11(tmp_path, stage, after, held):
    m = STAGES[stage]
    out = run(tmp_path, stage, "b11a", f"after2={after}", "gfill")
    assert outcome(out, f"{m}-{held}") == "held" and outcome(out, f"{m}-REBASE") == "FAILED"
    assert pred(out, f"{m}-REBASE").endswith(": FAILED")
    assert pred(out, f"{m}-{held}").endswith(": FAILED")     # predicted failed, read held


@pytest.mark.parametrize("stage", XY)
@pytest.mark.parametrize("tokens,held,not_held", [
    (("j2stop", "kickfault"), "KICKFAULT", "NOKICK"),
    (("j2stop",), "NOKICK", "KICKFAULT"),
])
def test_a_job_2_that_is_not_done(tmp_path, stage, tokens, held, not_held):
    m = STAGES[stage]
    out = run(tmp_path, stage, "b11a", *tokens)
    assert outcome(out, f"{m}-{held}") == "held" and outcome(out, f"{m}-{not_held}") == "FAILED"
    assert outcome(out, f"{m}-REBASE") == "FAILED"


@pytest.mark.parametrize("stage", XY)
def test_a_kick_fault_on_another_list_is_neither(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "b11a", "j2stop", "kickother")
    assert outcome(out, f"{m}-KICKFAULT") == "FAILED" and outcome(out, f"{m}-NOKICK") == "FAILED"
    assert "FAULT" in rule(out, m)


@pytest.mark.parametrize("stage", XY)
@pytest.mark.parametrize("tokens,state", [(("nodevcd",), "cannot tell"),
                                           (("devcdother",), "FAILED"),
                                           (("nogatemarks",), "cannot tell")])
def test_the_fill_needs_the_kernel_line_and_the_devcoredump(tmp_path, stage, tokens, state):
    m = STAGES[stage]
    out = run(tmp_path, stage, "b11a", "after2=rebase", "gfill", *tokens)
    assert outcome(out, f"{m}-FILL") == state, out


@pytest.mark.parametrize("stage", XY)
def test_an_exact_gate_fails_the_fill(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "b11a", "after2=rebase", "gexact")
    assert outcome(out, f"{m}-FILL") == "FAILED"


@pytest.mark.parametrize("stage", XY)
def test_pre_equal_post_cannot_tell_rebase_from_none(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "b11a", "prepost", "after2=rebase", "gfill")
    assert outcome(out, f"{m}-REBASE") == "cannot tell" == outcome(out, f"{m}-NONE")


@pytest.mark.parametrize("stage", list(STAGES))
@pytest.mark.parametrize("token,ctl", [("pgbad", "PG"), ("e0bad", "E0"), ("t0stop", "T0"),
                                       ("j1bad", "J1")])
def test_each_control_can_fail_and_the_rule_cannot_tell(tmp_path, stage, token, ctl):
    m = STAGES[stage]
    base = "b0" if m == "C" else "land" if m == "LC" else "b11a"
    out = run(tmp_path, stage, base, token)
    assert f"CONTROL {make.row_name(stage)}:{ctl}: FAILED" in out, out
    assert "RULE: CANNOT TELL" in rule(out, m)
    assert all(ln.endswith(": cannot tell") for ln in out.splitlines()
               if ln.startswith("PREDICTION "))


@pytest.mark.parametrize("stage", list(STAGES))
def test_a_bif_fault_after_the_row_fails_b(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "b0" if m == "C" else "b11a", "bif")
    assert f"CONTROL {make.row_name(stage)}:B: FAILED" in out


LCS = [s for s in STAGES if STAGES[s] == "LC"]


@pytest.mark.parametrize("stage", LCS)
def test_lc_rebase_and_fill_when_not_early(tmp_path, stage):
    """The kept B11 page (its post sa13 = 0x43000, B11's fill fault page) with jobs 2 and 3
    done: LC-REBASE and LC-FILL held, LC-EARLY and LC-HEAL failed."""
    out = run(tmp_path, stage, "b11a", "after2=rebase", "noheal", "gfill")
    assert outcome(out, "LC-REBASE") == "held" and outcome(out, "LC-FILL") == "held", out
    assert outcome(out, "LC-EARLY") == "FAILED" and outcome(out, "LC-HEAL") == "FAILED"
    assert outcome(out, "LC-FILLOK") == "FAILED"
    assert pred(out, "LC-REBASE").endswith(": held") and pred(out, "LC-EARLY").endswith(": FAILED")


@pytest.mark.parametrize("stage", LCS)
@pytest.mark.parametrize("tokens", [("j2stop",), ("kickfault",)])
def test_lc_early_by_a_stop_or_a_list_15_fault(tmp_path, stage, tokens):
    out = run(tmp_path, stage, "land", "after2=rebase", *tokens)
    assert outcome(out, "LC-EARLY") == "held", out
    assert pred(out, "LC-EARLY").endswith(": held")
    assert pred(out, "LC-REBASE").endswith(": not reached (LC-EARLY)")


@pytest.mark.parametrize("stage", LCS)
def test_lc_heal_and_fillok(tmp_path, stage):
    out = run(tmp_path, stage, "land", "after2=rebase", "heal", "gexact")
    assert outcome(out, "LC-HEAL") == "held" and outcome(out, "LC-FILLOK") == "held"
    assert outcome(out, "LC-FILL") == "FAILED"


TS = [s for s in STAGES if STAGES[s] == "T"]


@pytest.mark.parametrize("stage", TS)
@pytest.mark.parametrize("token,held", [("thead", "T-HEAD"), ("tother", "T-OTHER"),
                                        ("thang", "T-HANG"), ("gexact", "T-OK")])
def test_t_s_four_outcomes(tmp_path, stage, token, held):
    out = run(tmp_path, stage, "b11a", token)
    assert outcome(out, held) == "held", out
    assert [x for x in ("T-HEAD", "T-OTHER", "T-HANG", "T-OK")
            if outcome(out, x) == "held"] == [held]
    assert pred(out, "T-HEAD").endswith(": held" if held == "T-HEAD" else ": FAILED")
