# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer replayed on round 43's KEPT stages (N1's w and v, N2's f;
pinned, resgx545-data b3df8fc21) as the tokens edit them (tests/attempt.py): every frozen outcome of
the session's stages held where it must hold and FAILED or cannot tell where it must not, the
controls able to fail (E0 and the job controls read in their jobs' records, never on the row-end
page; DR read from the kernel log's begin health mark and the kept draws), the plant stage right
before a read stage (the pairing WA-FT, WB-FF, WC-T, WD-TF, WL-LM, WF-LF) deciding whether its
attribute-1 outcomes read, F2 reading TF's end health, LM's cannot-tell rule, and the RULE and
PREDICTION lines."""
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


def of(*ms):
    return [s for s in STAGES if STAGES[s] in ms]


def score_dir(d, stage, *roots):
    r = subprocess.run([sys.executable, "-B", "score/score.py", stage, d, *roots], cwd=KP,
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    assert r.returncode == 0 and "SUMMARY:" in r.stdout, r.stdout + r.stderr
    return r.stdout


def run(tmp_path, stage, *tokens):
    d = attempt.build(str(tmp_path / "-".join(tokens or ("plain",))), stage, tokens)
    return score_dir(d, stage)


def outcome(out, name):
    for ln in out.splitlines():
        if ln.startswith("OUTCOME ") and ln.split()[2] == name + ":":
            return ln.split(": ", 1)[1]
    return None


def control(out, stage, k):
    return next((ln.split(": ", 1)[1] for ln in out.splitlines()
                 if ln.startswith(f"CONTROL {make.row_name(stage)}:{k}:")), None)


def rule(out, stage):
    return next(ln for ln in out.splitlines() if ln.startswith(f"Q128-N3I-{stage.upper()} RULE: "))


def pred(out, name):
    return next(ln for ln in out.splitlines() if ln.startswith(f"PREDICTION {name}:"))


def all_as_predicted(out):
    return all(ln.endswith((": held", ": printed")) for ln in out.splitlines()
               if ln.startswith("PREDICTION ")), out


def test_the_stages_are_the_generator_s():
    assert {s: v[0] for s, v in score.STAGES.items()} == STAGES
    assert {s: v[1] for s, v in score.STAGES.items()} == \
        {s[0]: s[4] for s in make.STAGES[make.STEP]}
    assert score.PLANT == make.PLANT
    assert {k: v for k, v in score.DRAWS.items() if k in STAGES} == \
        {k: v for k, v in make.DRAWS.items() if k in STAGES}


# ---- W (every plant stage): mark, job 1 alone --------------------------------------------------
@pytest.mark.parametrize("stage", of("W"))
def test_w_s_predicted_reading_on_w_s_job_1(tmp_path, stage):
    out = run(tmp_path, stage)
    for x in ("W-SA1", "W-SA13", "W-QUIET"):
        assert outcome(out, x) == "held" and pred(out, x).endswith(": held"), (x, out)
    assert outcome(out, "W-FAULT") == "FAILED" and pred(out, "W-FAULT").endswith(": held")
    assert rule(out, stage).endswith("RULE: W-QUIET, W-SA1, W-SA13")
    assert all(control(out, stage, k) == "PASS" for k in ("PG", "E0", "T0", "B", "J1")), out
    assert control(out, stage, "DR") is None


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


# ---- the reads FT, FF, T, TF: crumb3 after a draw sequence --------------------------------------
READ_HELD = {"ft": "FT-SAME", "ff": "FF-N", "t": "T-N", "tf": "TF-N"}
READ_FAILED = {"ft": (), "ff": ("FF-LAST", "FF-K"), "t": ("T-LAST", "T-K"),
               "tf": ("TF-LAST", "TF-K", "TF-TRI")}
READ_STAGES = [s for s in READ_HELD if s in STAGES]


@pytest.mark.parametrize("stage", READ_STAGES)
def test_a_read_s_predicted_reading(tmp_path, stage):
    """The stage's frozen word (FT 0x04400000, FF 0x02000000, T 0x03400000, TF 0x04000000):
    the held outcome and X-QUIET held, every predicted failure FAILED (X-KEEP too), every
    prediction held, the controls pass (DR too), the rule names the held ones."""
    out = run(tmp_path, stage)
    for x in (READ_HELD[stage], "X-QUIET"):
        assert outcome(out, x) == "held", (x, out)
    for x in READ_FAILED[stage] + ("X-KEEP",):
        assert outcome(out, x) == "FAILED", (x, out)
    assert outcome(out, "X-OTHER") == "FAILED" and pred(out, "X-OTHER").endswith(": printed")
    assert all_as_predicted(out)
    assert rule(out, stage).endswith(f"RULE: {READ_HELD[stage]}, X-QUIET"), rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in
               ("PG", "E0", "T0", "B", "J1", "DR")), out


@pytest.mark.parametrize("stage,word,held", [
    ("ft", "0x04000010", "FT-SAME"),
    ("ff", "0x01000000", "FF-LAST"), ("ff", "0x04000010", "FF-K"),
    ("t", "0x03000010", "T-N"), ("t", "0x04400000", "T-LAST"), ("t", "0x04000010", "T-LAST"),
    ("t", "0x02400000", "T-K"), ("t", "0x02000010", "T-K"),
    ("tf", "0x01000000", "TF-LAST"), ("tf", "0x08000010", "TF-K"),
    ("tf", "0x04400000", "TF-TRI"), ("tf", "0x04000010", "TF-TRI"),
    ("ft", "0x005d1000", "X-KEEP"), ("ff", "0x005d1000", "X-KEEP"),
    ("ff", "0x12345678", "X-OTHER"), ("tf", "0x03400000", "X-OTHER"),
    ("ft", "0x01000000", "X-OTHER")])
def test_a_read_s_other_words(tmp_path, stage, word, held):
    if stage not in STAGES:
        pytest.skip("another session's stage")
    out = run(tmp_path, stage, f"sa1={word}")
    assert outcome(out, held) == "held", (held, out)
    named = [x for x in score.NEEDS_PLANT[STAGES[stage]] + ("X-OTHER",) if x != held]
    assert all(outcome(out, x) == "FAILED" for x in named), out
    if held == "X-OTHER":
        assert pred(out, "X-OTHER").endswith(": printed")
    else:
        assert f"PREDICTION {held}: predicted " in pred(out, held)


@pytest.mark.parametrize("stage", READ_STAGES)
@pytest.mark.parametrize("token", ["noplant", "wfail"])
def test_a_read_s_word_outcomes_need_the_plant(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in score.NEEDS_PLANT[STAGES[stage]]:
        assert "cannot tell (W-SA1" in pred(out, x), pred(out, x)
    assert outcome(out, "X-QUIET") == "held" and pred(out, "X-QUIET").endswith(": held")
    assert READ_HELD[stage] not in rule(out, stage)


def test_the_plant_is_the_stage_right_before_the_read(tmp_path):
    """FT reads WA, FF reads WB, T reads WC, TF reads WD, LM reads WL, LF reads WF: four plant
    stages in one attempt directory, one failing at a time; only its read stage cannot tell."""
    if make.STEP != "N1":
        pytest.skip("N1 has the four plants")
    pairs = [("wa", "ft"), ("wb", "ff"), ("wc", "t"), ("wd", "tf")]
    for bad, _ in pairs:
        root = str(tmp_path / f"bad-{bad}")
        for plant, read in pairs:
            attempt.build(root, read, ("wfail",) if plant == bad else ())
        for plant, read in pairs:
            out = score_dir(os.path.join(root, read), read)
            assert f"W-SA1 of stage {plant} " in out, (plant, read)
            word = pred(out, READ_HELD[read])
            assert ("cannot tell (W-SA1" in word) == (plant == bad), (bad, read, word)


# ---- DR: the declared begin draws ----------------------------------------------------------------
DR_STAGES = [s for s in ("ft", "ff", "t", "tf", "f2", "lm", "lf") if s in STAGES]


@pytest.mark.parametrize("stage", DR_STAGES)
@pytest.mark.parametrize("token", ["drmark", "drretry", "drbad", "drgone"])
def test_dr_fails_when_the_declared_draws_did_not_run_exact_at_try_1(tmp_path, stage, token):
    if token in ("drbad", "drgone") and stage == "lm":
        pytest.skip("lm's begin draws are the register health (none)")
    out = run(tmp_path, stage, token)
    assert control(out, stage, "DR") == "FAILED", out
    assert f"DR {make.row_name(stage)} (printed): " in out
    if stage != "lm":      # LM's DR is a control read, not a premise (design §3.4)
        assert "RULE: CANNOT TELL (control DR FAILED)" in rule(out, stage), rule(out, stage)
        assert all("cannot tell" in ln for ln in out.splitlines()
                   if ln.startswith("PREDICTION ") and not ln.endswith("printed")
                   and "X-QUIET" not in ln and "F2-QUIET" not in ln), out


def test_dr_names_the_list_the_stage_declares():
    assert {k: v for k, v in score.DRAWS.items() if k in score.STAGES} == \
        {k: v for k, v in make.DRAWS.items() if k in score.STAGES}
    assert score.DRAWS == {"ft": "fill,tri", "ff": "fill,fill", "t": "tri", "tf": "tri,fill",
                           "f2": "fill", "lm": "none", "lf": "fill"}


@pytest.mark.parametrize("stage", READ_STAGES + [s for s in ("f2",) if s in STAGES])
def test_a_fault_in_a_read_stage_says_stop(tmp_path, stage):
    out = run(tmp_path, stage, "rfault")
    assert control(out, stage, "B") == "FAILED"
    assert "B failing (a fault with no pass planned): stop the session" in out
    assert "FAULT: BIF_FAULT is not 0 after the row and no outcome names it" in rule(out, stage)


# ---- F2: no plant, after TF ---------------------------------------------------------------------
@pytest.mark.parametrize("stage", of("F2"))
def test_f2_s_predicted_reading(tmp_path, stage):
    out = run(tmp_path, stage)
    assert outcome(out, "F2-N") == "held" and outcome(out, "F2-QUIET") == "held"
    for x in ("F2-ACC", "F2-K", "F2-PRIOR"):
        assert outcome(out, x) == "FAILED", (x, out)
    assert all_as_predicted(out)
    assert "PLANT" not in out and rule(out, stage).endswith("RULE: F2-N, F2-QUIET")
    assert control(out, stage, "DR") == "PASS"


@pytest.mark.parametrize("stage", of("F2"))
@pytest.mark.parametrize("word,held", [("0x09000000", "F2-ACC"), ("0x02000010", "F2-K"),
                                       ("0x04400000", "F2-PRIOR"), ("0x04000010", "F2-PRIOR"),
                                       ("0x12345678", "F2-OTHER")])
def test_f2_s_other_words(tmp_path, stage, word, held):
    out = run(tmp_path, stage, f"sa1={word}")
    assert outcome(out, held) == "held", out
    assert outcome(out, "F2-N") == "FAILED"


@pytest.mark.parametrize("stage", of("F2"))
@pytest.mark.parametrize("token", ["notf", "tfretry", "tfbad"])
def test_f2_acc_and_prior_need_tf_s_end_health_ok_at_try_1(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in ("F2-ACC", "F2-PRIOR"):
        assert "cannot tell (TF's end health not ok" in pred(out, x), pred(out, x)
    assert pred(out, "F2-N").endswith(": held") and "F2-N" in rule(out, stage)


# ---- LM (N2 lm): land on W's bank, no draws ------------------------------------------------------
@pytest.mark.parametrize("stage", of("LM"))
def test_lm_s_predicted_reading(tmp_path, stage):
    """E1185's kept stop as LM's prediction: sa0 = V0, sa1 = M1, sa2 = V2, job 2's K5 at M1's
    page: LM-V0, LM-KEEP and LM-EARLY1 held, the rest FAILED, every prediction held."""
    out = run(tmp_path, stage)
    for x in ("LM-V0", "LM-KEEP", "LM-EARLY1"):
        assert outcome(out, x) == "held", (x, out)
    for x in ("LM-EARLY0", "LM-EARLY13", "LM-SERVE", "LM-OTHER"):
        assert outcome(out, x) == "FAILED", (x, out)
    assert pred(out, "LM-OTHER").endswith(": printed") and all_as_predicted(out)
    assert rule(out, stage).endswith("RULE: LM-EARLY1, LM-KEEP, LM-V0")
    assert control(out, stage, "E0") == "PASS" and control(out, stage, "J2") == "FAILED"
    assert control(out, stage, "DR") == "PASS"


@pytest.mark.parametrize("stage", of("LM"))
@pytest.mark.parametrize("tokens,held,failed", [
    (("early0",), "LM-EARLY0", "LM-EARLY1"), (("early13",), "LM-EARLY13", "LM-EARLY1"),
    (("other",), "LM-OTHER", "LM-EARLY1"), (("serve",), "LM-SERVE", "LM-EARLY1")])
def test_lm_s_other_readings(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, *tokens)
    assert outcome(out, held) == "held", out
    assert outcome(out, failed) == "FAILED"
    assert outcome(out, "LM-V0") == "held"


@pytest.mark.parametrize("stage", of("LM"))
@pytest.mark.parametrize("token", ["noplant", "wfail"])
def test_lm_s_attribute_1_and_early_outcomes_need_the_plant(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in ("LM-KEEP", "LM-EARLY1", "LM-EARLY0", "LM-EARLY13"):
        assert "cannot tell (W-SA1" in pred(out, x), pred(out, x)
    assert outcome(out, "LM-V0") == "held" and pred(out, "LM-V0").endswith(": held")
    assert "LM-KEEP" not in rule(out, stage)


@pytest.mark.parametrize("stage", of("LM"))
def test_lm_v0_failing_with_sa0_below_0x1000_cannot_split_the_readings(tmp_path, stage):
    """Page 0 is sa0's page under both readings: LM-EARLY0 and LM-EARLY1 cannot tell, with the
    LM-V0 note (the fold-time rule for LF)."""
    out = run(tmp_path, stage, "sa0=0x0", "early0")
    assert outcome(out, "LM-V0") == "FAILED"
    for x in ("LM-EARLY1", "LM-EARLY0"):
        assert "cannot tell (LM-V0 failed with post sa0 below 0x1000" in pred(out, x), pred(out, x)
    assert "NOTE lm: LM-V0 failed" in out and "LF's attribute 0 and 2 outcomes cannot tell" in out


@pytest.mark.parametrize("stage", of("LM"))
def test_lm_v0_failing_with_another_sa0_is_printed_and_the_page_still_reads(tmp_path, stage):
    out = run(tmp_path, stage, "sa0=0x32104000")
    assert outcome(out, "LM-V0") == "FAILED" and outcome(out, "LM-EARLY1") == "held"
    assert pred(out, "LM-EARLY1").endswith(": held") and "NOTE lm: LM-V0 failed" in out
    assert "post sa0" in out


# ---- LF (N3 lf): land after one fill ------------------------------------------------------------
@pytest.mark.parametrize("stage", of("LF"))
def test_lf_s_predicted_reading(tmp_path, stage):
    """LC's words after a fill: sa0 0, sa1 0x01000000, sa2 0x0104b95b, job 2's K5 at page 0."""
    out = run(tmp_path, stage)
    for x in ("LF-SA1", "LF-EVT", "LF-EARLY0"):
        assert outcome(out, x) == "held", (x, out)
    for x in ("LF-TICK", "LF-ONE", "LF-AOTHER", "LF-EARLY1", "LF-SERVE"):
        assert outcome(out, x) == "FAILED", (x, out)
    assert pred(out, "LF-AOTHER").endswith(": printed") and all_as_predicted(out)
    assert rule(out, stage).endswith("RULE: LF-EARLY0, LF-EVT, LF-SA1")
    assert control(out, stage, "DR") == "PASS" and control(out, stage, "J2") == "FAILED"


@pytest.mark.parametrize("stage", of("LF"))
@pytest.mark.parametrize("tokens,held,failed", [
    (("tick",), "LF-TICK", "LF-EVT"), (("one",), "LF-ONE", "LF-EVT"),
    (("sa2=0x12345678",), "LF-AOTHER", "LF-EVT"), (("sa2=0x01061a70",), "LF-AOTHER", "LF-EVT"),
    (("early1",), "LF-EARLY1", "LF-EARLY0"), (("serve",), "LF-SERVE", "LF-EARLY0")])
def test_lf_s_other_readings(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, *tokens)
    assert outcome(out, held) == "held", out
    assert outcome(out, failed) == "FAILED"


@pytest.mark.parametrize("stage", of("LF"))
@pytest.mark.parametrize("token", ["noplant", "wfail"])
def test_lf_outcomes_need_the_plant(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in ("LF-SA1", "LF-EVT", "LF-EARLY0"):
        assert "cannot tell (W-SA1" in pred(out, x), pred(out, x)
    assert pred(out, "LF-AOTHER").endswith(": printed")


# ---- every stage: the controls ----------------------------------------------------------------
@pytest.mark.parametrize("stage", list(STAGES))
@pytest.mark.parametrize("token,ctl", [("pgbad", "PG"), ("e0bad", "E0"), ("e0cmd", "E0"),
                                       ("t0stop", "T0"), ("j1bad", "J1")])
def test_each_control_can_fail_and_the_rule_cannot_tell(tmp_path, stage, token, ctl):
    out = run(tmp_path, stage, token)
    assert control(out, stage, ctl) == "FAILED", out
    assert "RULE: CANNOT TELL" in rule(out, stage)
    assert all("cannot tell" in ln or "not reached" in ln or ln.endswith("printed")
               for ln in out.splitlines() if ln.startswith("PREDICTION ")), out
