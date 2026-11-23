# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer replayed on round 42's KEPT stages (G1's m, G3's lv; pinned)
as the tokens edit them (tests/attempt.py): every frozen outcome of the session's stages held
where it must hold and FAILED or cannot tell where it must not, the controls able to fail (E0
and the job controls read in their jobs' records, never on the row-end page), the planting
stage's W-SA1 deciding whether the attribute-1 outcomes read, and the RULE and PREDICTION
lines."""
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


def of(m):
    return [s for s in STAGES if STAGES[s] == m]


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


def control(out, stage, k):
    return next((ln.split(": ", 1)[1] for ln in out.splitlines()
                 if ln.startswith(f"CONTROL {make.row_name(stage)}:{k}:")), None)


def rule(out, stage):
    return next(ln for ln in out.splitlines() if ln.startswith(f"Q128-N3H-{stage.upper()} RULE: "))


def pred(out, name):
    return next(ln for ln in out.splitlines() if ln.startswith(f"PREDICTION {name}:"))


def test_the_stages_are_the_generator_s():
    assert {s: v[0] for s, v in score.STAGES.items()} == STAGES
    assert {s: v[1] for s, v in score.STAGES.items()} == \
        {s[0]: s[4] for s in make.STAGES[make.STEP]}
    assert score.PLANT == make.PLANT


# ---- W (N1 w, N2 w2): mark, job 1 alone ---------------------------------------------------------
@pytest.mark.parametrize("stage", of("W"))
def test_w_s_predicted_reading_on_m_s_job_1(tmp_path, stage):
    out = run(tmp_path, stage)
    for x in ("W-SA1", "W-SA13", "W-QUIET"):
        assert outcome(out, x) == "held" and pred(out, x).endswith(": held"), (x, out)
    assert outcome(out, "W-FAULT") == "FAILED" and pred(out, "W-FAULT").endswith(": held")
    assert rule(out, stage).endswith("RULE: W-QUIET, W-SA1, W-SA13")
    assert all(control(out, stage, k) == "PASS" for k in ("PG", "E0", "T0", "B", "J1")), out


@pytest.mark.parametrize("stage", of("W"))
@pytest.mark.parametrize("token", ["wfault", "resetfault"])
def test_w_fault_holds_and_says_stop(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert outcome(out, "W-FAULT") == "held" and pred(out, "W-FAULT").endswith(": FAILED")
    assert "W-FAULT: a pass ran that we did not expect: stop the session" in out
    if token == "wfault":
        assert outcome(out, "W-QUIET") == "FAILED" and control(out, stage, "B") == "FAILED"


@pytest.mark.parametrize("stage", of("W"))
def test_w_fault_without_the_disarm_record_cannot_tell(tmp_path, stage):
    out = run(tmp_path, stage, "noreset")
    assert outcome(out, "W-FAULT") == "cannot tell"


@pytest.mark.parametrize("stage", of("W"))
def test_w_sa1_fails_when_attribute_1_is_not_m1(tmp_path, stage):
    out = run(tmp_path, stage, "nosa1")
    assert outcome(out, "W-SA1") == "FAILED" and "the next stage's attribute-1 outcomes" in out


# ---- V (N1 v): landv, the tick pass --------------------------------------------------------------
@pytest.mark.parametrize("stage", of("V"))
def test_v_s_predicted_reading(tmp_path, stage):
    """LV's kept stop with M1 planted and job 2's K5 at M1's page: V-KEEP, V-V, V-EARLY1 held,
    every predicted failure FAILED, every prediction held; the stop's fault is named (no FAULT)."""
    out = run(tmp_path, stage, "keep")
    for x in ("V-KEEP", "V-V", "V-EARLY1"):
        assert outcome(out, x) == "held", (x, out)
    for x in ("V-EVT", "V-V1", "V-EARLY13", "V-EARLY0", "V-SERVE"):
        assert outcome(out, x) == "FAILED", (x, out)
    assert pred(out, "V-OTHER").endswith(": printed")
    assert all(ln.endswith((": held", ": printed")) for ln in out.splitlines()
               if ln.startswith("PREDICTION ")), out
    assert rule(out, stage).endswith("RULE: V-EARLY1, V-KEEP, V-V")
    assert control(out, stage, "E0") == "PASS" and control(out, stage, "J2") == "FAILED"


@pytest.mark.parametrize("stage", of("V"))
def test_lv_as_kept_reads_an_event_word_and_says_lv_again(tmp_path, stage):
    """LV's own words: sa1 0x04400000 (K 4, bit 22) is an event word: V-EVT held, V-KEEP
    FAILED; V-EARLY1 at that page with the LV-again note."""
    out = run(tmp_path, stage)
    assert outcome(out, "V-EVT") == "held" and outcome(out, "V-KEEP") == "FAILED"
    assert outcome(out, "V-EARLY1") == "held"
    assert "LV again, Q2 not advanced" in out
    assert pred(out, "V-EVT").endswith(": FAILED")


@pytest.mark.parametrize("stage", of("V"))
@pytest.mark.parametrize("tokens,held", [(("v1",), "V-V1"), (("other",), "V-OTHER"),
                                         (("keep", "early13"), "V-EARLY13"),
                                         (("keep", "early0"), "V-EARLY0"),
                                         (("keep", "serve"), "V-SERVE")])
def test_v_s_other_readings(tmp_path, stage, tokens, held):
    out = run(tmp_path, stage, *tokens)
    assert outcome(out, held) == "held", out
    if held.startswith("V-EARLY") or held == "V-SERVE":
        assert outcome(out, "V-EARLY1") == "FAILED"


@pytest.mark.parametrize("stage", of("V"))
@pytest.mark.parametrize("token", ["noplant", "wfail"])
def test_v_s_attribute_1_outcomes_need_the_plant(tmp_path, stage, token):
    out = run(tmp_path, stage, "keep", token)
    for x in ("V-KEEP", "V-EVT", "V-V1"):
        assert "cannot tell (W-SA1" in pred(out, x), pred(out, x)
    assert "V-KEEP" not in rule(out, stage) and "V-EARLY1" in rule(out, stage)


# ---- F (N2 f): the fill alone, the kick-only job, the stall --------------------------------------
@pytest.mark.parametrize("stage", of("F"))
def test_f_s_predicted_reading(tmp_path, stage):
    out = run(tmp_path, stage)
    for x in ("F-FILL4", "K-QUIET", "K-KICK", "K-REPLY", "K-STALL"):
        assert outcome(out, x) == "held", (x, out)
    for x in ("F-KEEP", "K-KICKOK", "K-SERVE"):
        assert outcome(out, x) != "held", (x, out)
    assert pred(out, "F-GATE").endswith(": not reached (K-STALL)")
    assert pred(out, "F-OTHER").endswith(": printed")
    assert all(ln.endswith((": held", ": printed", "not reached (K-STALL)"))
               for ln in out.splitlines() if ln.startswith("PREDICTION ")), out
    assert control(out, stage, "J2") == "PASS" and control(out, stage, "J3") == "FAILED"
    assert f"BIF {make.row_name(stage)} job 2 (printed, K5): pre BIF_INT_STAT 0x00080000 " \
           "BIF_FAULT 0x00000000; mid BIF_INT_STAT 0x000d0400 BIF_FAULT 0x005d300f" in out


@pytest.mark.parametrize("stage", of("F"))
def test_f_served_reaches_the_gate_s_fault(tmp_path, stage):
    """M's kept job 2 as job 3 (done, after = post) and M's gate (the fill's fault at M13)."""
    out = run(tmp_path, stage, "serve")
    assert outcome(out, "K-SERVE") == "held" and outcome(out, "K-STALL") == "FAILED"
    assert outcome(out, "F-GATE") == "held" and pred(out, "F-GATE").endswith(": held")
    assert control(out, stage, "J3") == "PASS"


@pytest.mark.parametrize("stage", of("F"))
@pytest.mark.parametrize("tokens,held,failed", [(("keep",), "F-KEEP", "F-FILL4"),
                                                (("evt22",), "F-OTHER", "F-FILL4"),
                                                (("kickok",), "K-KICKOK", "K-KICK"),
                                                (("replyerr",), None, "K-REPLY")])
def test_f_s_other_readings(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, *tokens)
    if held:
        assert outcome(out, held) == "held", out
    assert outcome(out, failed) == "FAILED", out


@pytest.mark.parametrize("stage", of("F"))
def test_f_s_q1_part_needs_the_plant(tmp_path, stage):
    out = run(tmp_path, stage, "wfail")
    for x in ("F-FILL4", "F-KEEP"):
        assert "cannot tell (W-SA1 FAILED" in pred(out, x), pred(out, x)
    assert pred(out, "K-KICK").endswith(": held")


# ---- every stage: the controls ----------------------------------------------------------------
@pytest.mark.parametrize("stage", list(STAGES))
@pytest.mark.parametrize("token,ctl", [("pgbad", "PG"), ("e0bad", "E0"), ("e0cmd", "E0"),
                                       ("t0stop", "T0"), ("j1bad", "J1")])
def test_each_control_can_fail_and_the_rule_cannot_tell(tmp_path, stage, token, ctl):
    out = run(tmp_path, stage, token)
    assert control(out, stage, ctl) == "FAILED", out
    assert "RULE: CANNOT TELL" in rule(out, stage)
    assert all("cannot tell" in ln or "not reached" in ln
               for ln in out.splitlines() if ln.startswith("PREDICTION ")), out
