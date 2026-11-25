# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer replayed on round 44's KEPT stages (N1's wa and ff, N3's lf;
pinned, resgx545-data ebfeaa775) as the tokens edit them (tests/attempt.py): every frozen outcome of
the session's stages held where it must hold and FAILED or cannot tell where it must not, the
controls able to fail (E0 and the job controls read in their jobs' records, never on the row-end
page; DR read from the kernel log's begin health mark and the kept draws; DK, K9's command count,
from the kernel log's `ccb_sent` lines), the plant stage right before a read or land stage (the
pairing WA-FF2, WB-T2, WC-TF2, WD-TT, WE-F3, WG-LF2, WH-LT, WI-LFF) deciding whether its outcomes
read, F2b reading F3's end health and end command count, LT's cannot-tell rule, and the RULE and
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
    return next(ln for ln in out.splitlines() if ln.startswith(f"Q128-N3J-{stage.upper()} RULE: "))


def pred(out, name):
    return next(ln for ln in out.splitlines() if ln.startswith(f"PREDICTION {name}:"))


def all_as_predicted(out):
    return all(ln.endswith((": held", ": printed")) for ln in out.splitlines()
               if ln.startswith("PREDICTION ")), out


def names(stage):
    """The frozen outcomes of a stage's model."""
    return list(make.outcomes(STAGES[stage]))


def test_the_stages_are_the_generator_s():
    assert {s: v[0] for s, v in score.STAGES.items()} == STAGES
    assert {s: v[1] for s, v in score.STAGES.items()} == \
        {s[0]: s[4] for s in make.STAGES[make.STEP]}
    assert score.PLANT == make.PLANT
    assert {k: v for k, v in score.DRAWS.items() if k in STAGES} == \
        {k: v for k, v in make.DRAWS.items() if k in STAGES}


def test_the_draw_lists_each_stage_declares():
    assert score.DRAWS == {"ff2": "fill,fill", "t2": "tri", "tf2": "tri,fill", "tt": "tri,tri",
                           "f3": "fill", "f2b": "fill", "lf2": "fill", "lt": "tri",
                           "lff": "fill,fill"}


# ---- W (every plant stage): mark, job 1 alone --------------------------------------------------
@pytest.mark.parametrize("stage", of("W"))
def test_w_s_predicted_reading_on_w_s_job_1(tmp_path, stage):
    out = run(tmp_path, stage)
    for x in ("W-SA1", "W-SA13", "W-QUIET"):
        assert outcome(out, x) == "held" and pred(out, x).endswith(": held"), (x, out)
    assert outcome(out, "W-FAULT") == "FAILED" and pred(out, "W-FAULT").endswith(": held")
    assert rule(out, stage).endswith("RULE: W-QUIET, W-SA1, W-SA13")
    assert all(control(out, stage, k) == "PASS" for k in ("PG", "E0", "T0", "B", "J1")), out
    assert control(out, stage, "DR") is None and control(out, stage, "DK") is None
    assert f"KC {make.row_name(stage)}: begin N0 261, arm N1 271, delta 10" in out
    assert f"KC {make.row_name(stage)}: end N0 273, exit N1 275, delta 2" in out


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


# ---- the reads FF2, T2, TF2, TT, F3, F2b: crumb3 after a draw sequence ----------------------------
M1W = "0x005d1000"
READ_HELD = {"ff2": ("FF2-KEEP",), "t2": ("T2-SAME",), "tf2": ("TF2-SAME",), "tt": ("TT-LAST",),
             "f3": ("F3-KEEP",), "f2b": ("F2b-SAME",)}
QUIET = {"f2b": "F2b-QUIET"}
READ_STAGES = [s for s in READ_HELD if s in STAGES]
# (stage, the post sa1 word, the outcome that holds): the design's tables
WORDS = [
    ("ff2", M1W, "FF2-KEEP"), ("ff2", "0x04000010", "FF2-FILL"), ("ff2", "0x02000010", "FF2-FILL"),
    ("ff2", "0x01000000", "FF2-TICK"), ("ff2", "0x04000000", "FF2-TICK"),
    ("ff2", "0x00000000", "FF2-OTHER"), ("ff2", "0x04400000", "FF2-OTHER"),
    ("ff2", "0x05000001", "FF2-OTHER"), ("ff2", "0x12345678", "FF2-OTHER"),
    ("t2", "0x02400000", "T2-SAME"), ("t2", "0x02000010", "T2-34"), ("t2", M1W, "T2-KEEP"),
    ("t2", "0x04400000", "T2-OTHER"), ("t2", "0x03400000", "T2-OTHER"),
    ("tf2", "0x02400000", "TF2-SAME"), ("tf2", "0x08000010", "TF2-FILL"),
    ("tf2", M1W, "TF2-KEEP"), ("tf2", "0x04400000", "TF2-OTHER"),
    ("tt", "0x08400000", "TT-LAST"), ("tt", "0x08000010", "TT-LAST"),
    ("tt", "0x02400000", "TT-FIRST"), ("tt", "0x02000010", "TT-FIRST"), ("tt", M1W, "TT-KEEP"),
    ("tt", "0x04400000", "TT-OTHER"),
    ("f3", M1W, "F3-KEEP"), ("f3", "0x01000000", "F3-TICK"), ("f3", "0x02000010", "F3-FILL"),
    ("f3", "0x05400000", "F3-OTHER"),
    ("f2b", "0x05400000", "F2b-SAME"), ("f2b", "0x01000000", "F2b-TICK"),
    ("f2b", "0x02000010", "F2b-FILL"), ("f2b", M1W, "F2b-OTHER"),
]


@pytest.mark.parametrize("stage", READ_STAGES)
def test_a_read_s_predicted_reading(tmp_path, stage):
    """The stage's predicted word (design §3.2, §3.3): the held outcome and the quiet one held,
    every predicted failure FAILED, every prediction held, the controls pass (DR and DK too), the
    rule names the held ones."""
    out = run(tmp_path, stage)
    quiet = QUIET.get(stage, "X-QUIET")
    for x in READ_HELD[stage] + (quiet,):
        assert outcome(out, x) == "held", (x, out)
    for x in names(stage):
        if x not in READ_HELD[stage] + (quiet,):
            assert outcome(out, x) == "FAILED", (x, out)
    assert all_as_predicted(out)
    assert rule(out, stage).endswith(f"RULE: {', '.join(sorted(READ_HELD[stage] + (quiet,)))}"), \
        rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in
               ("PG", "E0", "T0", "B", "J1", "DR", "DK")), out


@pytest.mark.parametrize("stage,word,held", WORDS)
def test_a_read_s_other_words(tmp_path, stage, word, held):
    if stage not in STAGES:
        pytest.skip("another session's stage")
    out = run(tmp_path, stage, f"sa1={word}")
    assert outcome(out, held) == "held", (held, out)
    named = [x for x in names(stage) if x != held and "QUIET" not in x]
    assert all(outcome(out, x) == "FAILED" for x in named), out
    if held.endswith("OTHER"):
        assert pred(out, held).endswith(": printed")
    else:
        assert f"PREDICTION {held}: predicted " in pred(out, held)


@pytest.mark.parametrize("stage", [s for s in READ_STAGES if s != "f2b"])
@pytest.mark.parametrize("token", ["noplant", "wfail"])
def test_a_read_s_word_outcomes_need_the_plant(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in score.NEEDS_PLANT[STAGES[stage]]:
        assert "cannot tell (W-SA1" in pred(out, x), pred(out, x)
    assert outcome(out, "X-QUIET") == "held" and pred(out, "X-QUIET").endswith(": held")
    assert not set(READ_HELD[stage]) & set(rule(out, stage).split("RULE: ")[1].split(", "))


def test_the_plant_is_the_stage_right_before_the_read(tmp_path):
    """FF2 reads WA, T2 WB, TF2 WC, TT WD, F3 WE (the lands WG, WH, WI): the plant stages in one
    attempt directory, one failing at a time; only its own stage cannot tell."""
    pairs = [(w, r) for r, w in make.PLANT.items() if r in STAGES]
    if not pairs:
        pytest.skip("no read stage in this session")
    for bad, _ in pairs:
        root = str(tmp_path / f"bad-{bad}")
        for plant, read in pairs:
            attempt.build(root, read, ("wfail",) if plant == bad else ())
        for plant, read in pairs:
            out = score_dir(os.path.join(root, read), read)
            assert f"W-SA1 of stage {plant} " in out, (plant, read)
            word = pred(out, score.NEEDS_PLANT[STAGES[read]][0])
            assert ("cannot tell (W-SA1" in word) == (plant == bad), (bad, read, word)


# ---- DR: the declared begin draws ----------------------------------------------------------------
DR_STAGES = [s for s in STAGES if STAGES[s] != "W"]


@pytest.mark.parametrize("stage", DR_STAGES)
@pytest.mark.parametrize("token", ["drmark", "drretry", "drbad", "drgone"])
def test_dr_fails_when_the_declared_draws_did_not_run_exact_at_try_1(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert control(out, stage, "DR") == "FAILED", out
    assert f"DR {make.row_name(stage)} (printed): " in out
    assert "RULE: CANNOT TELL (control DR FAILED)" in rule(out, stage), rule(out, stage)
    assert all("cannot tell" in ln for ln in out.splitlines()
               if ln.startswith("PREDICTION ") and not ln.endswith("printed")
               and "QUIET" not in ln), out


@pytest.mark.parametrize("stage", [s for s in READ_STAGES])
def test_a_fault_in_a_read_stage_says_stop(tmp_path, stage):
    out = run(tmp_path, stage, "rfault")
    assert control(out, stage, "B") == "FAILED"
    assert "B failing (a fault with no pass planned): stop the session" in out
    assert "FAULT: BIF_FAULT is not 0 after the row and no outcome names it" in rule(out, stage)


# ---- DK: K9's command count -----------------------------------------------------------------------
@pytest.mark.parametrize("stage", DR_STAGES)
def test_dk_prints_the_counts_and_h_kc_s_words(tmp_path, stage):
    out = run(tmp_path, stage)
    n = make.row_name(stage)
    want = score.K.kc_expected(make.DRAWS[stage])
    assert f"KC {n}: begin N0 " in out and f"delta {want}, expected 2 + 2 x " in out, out
    assert f"HKC {n} (printed, never scored): begin draws {make.DRAWS[stage]} (K from 1): " in out


@pytest.mark.parametrize("stage", DR_STAGES)
@pytest.mark.parametrize("token", ["dkbad", "dkgone"])
def test_dk_failing_or_unread_makes_the_k_outcomes_cannot_tell_only(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert control(out, stage, "DK") == ("FAILED" if token == "dkbad" else "cannot tell"), out
    assert f"DK {make.row_name(stage)} (printed): control DK " in out
    needs = score.NEEDS_DK[STAGES[stage]]
    for x in needs:
        assert "cannot tell (DK " in pred(out, x), pred(out, x)
    rest = [x for x in names(stage) if x not in needs and not x.endswith("OTHER")
            and "QUIET" not in x]
    # an outcome that names no K still reads: the -KEEP, -SAME, the page and the SERVE ones
    assert all("DK" not in pred(out, x) for x in rest), out
    assert "RULE: CANNOT TELL" not in rule(out, stage), rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in ("PG", "E0", "T0", "J1", "DR"))


def test_dk_names_the_outcomes_the_design_lists():
    d = score.NEEDS_DK
    assert d["FF2"] == ("FF2-FILL",) and d["T2"] == ("T2-34",) and d["TF2"] == ("TF2-FILL",)
    assert d["TT"] == ("TT-LAST", "TT-FIRST", "TT-KEEP") and d["F3"] == ("F3-TICK", "F3-FILL")
    assert set(d["F2B"]) == {"F2b-SAME", "F2b-TICK", "F2b-FILL"}
    assert d["LF2"] == ("LF2-SA1", "LF2-SA0", "LF2-SA2")


# ---- F2b: no plant, after F3 --------------------------------------------------------------------
@pytest.mark.parametrize("stage", of("F2B"))
def test_f2b_has_no_plant_line(tmp_path, stage):
    out = run(tmp_path, stage)
    assert "PLANT" not in out and "F2b-SAME" in rule(out, stage)


@pytest.mark.parametrize("stage", of("F2B"))
@pytest.mark.parametrize("token", ["nof3", "f3retry", "f3bad", "f3kc"])
def test_f2b_needs_f3_s_end_health_and_end_count_10(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in ("F2b-SAME", "F2b-TICK", "F2b-FILL"):
        assert "cannot tell (F3's end health or end command count 10 not ok" in pred(out, x), \
            (token, pred(out, x))
    assert pred(out, "F2b-QUIET").endswith(": held")


# ---- the land stages LF2, LT, LFF -----------------------------------------------------------------
LAND_HELD = {"lf2": ("LF2-SA1", "LF2-SA0", "LF2-SA2", "LF2-PAGE", "LF2-EARLY0"),
             "lt": ("LT-SA1", "LT-TRIPLE", "LT-PAGE"),
             "lff": ("LFF-SA1", "LFF-SA0", "LFF-PAGE")}
LAND_STAGES = [s for s in LAND_HELD if s in STAGES]


@pytest.mark.parametrize("stage", LAND_STAGES)
def test_a_land_stage_s_predicted_reading(tmp_path, stage):
    """lf2 is E1200's kept stop (sa0 2, sa1 M1, sa2 0x01049b60, page 0); lt is LC's triple after
    a triangle (0, 0x02400000, 0x0104b95b, page 0); lff is lf2's words (infer)."""
    out = run(tmp_path, stage)
    for x in LAND_HELD[stage]:
        assert outcome(out, x) == "held", (x, out)
    for x in names(stage):
        if x not in LAND_HELD[stage]:
            assert outcome(out, x) == "FAILED", (x, out)
    assert all_as_predicted(out)
    assert rule(out, stage).endswith("RULE: " + ", ".join(sorted(LAND_HELD[stage])))
    assert control(out, stage, "DR") == "PASS" and control(out, stage, "DK") == "PASS"
    assert control(out, stage, "E0") == "PASS" and control(out, stage, "J2") == "FAILED"


@pytest.mark.parametrize("stage", of("LF2"))
@pytest.mark.parametrize("tokens,held,failed", [
    (("sa1=0x01000000",), "LF2-TICK", "LF2-SA1"), (("sa0=0x32004000",), "LF2-AOTHER", "LF2-SA0"),
    (("one",), "LF2-AOTHER", "LF2-SA2"), (("sa2=0x12345678",), "LF2-AOTHER", "LF2-SA2"),
    (("sa2=0x01061a70",), "LF2-AOTHER", "LF2-SA2"), (("sa0=0x00000000",), "LF2-AOTHER", "LF2-SA0"),
    (("early1",), "LF2-EARLY1", "LF2-EARLY0"), (("serve",), "LF2-SERVE", "LF2-EARLY0")])
def test_lf2_s_other_readings(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, *tokens)
    assert outcome(out, held) == "held", out
    assert outcome(out, failed) == "FAILED"


@pytest.mark.parametrize("stage", of("LF2"))
def test_lf2_page_cannot_tell_for_an_sa0_the_h_sa0_rule_does_not_cover(tmp_path, stage):
    out = run(tmp_path, stage, "sa0=0x00012345", "early0")
    assert outcome(out, "LF2-PAGE") == "cannot tell" and outcome(out, "LF2-EARLY0") == "held"


@pytest.mark.parametrize("stage", of("LT"))
@pytest.mark.parametrize("tokens,held,failed", [
    (("one",), "LT-ONE", "LT-TRIPLE"), (("sa0=0x00000001",), "LT-AOTHER", "LT-TRIPLE"),
    (("sa2=0x12345678",), "LT-AOTHER", "LT-TRIPLE"), (("sa1=0x005d1000",), "LT-PAGE", "LT-SA1")])
def test_lt_s_other_readings(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, *tokens)
    assert outcome(out, held) == "held", out
    assert outcome(out, failed) == "FAILED"


@pytest.mark.parametrize("stage", of("LT"))
def test_lt_one_splits_h_sa0_from_h_hist(tmp_path, stage):
    """The triangle writes attribute 1 alone (sa0 V0, sa2 V2): the stop at post sa1's page is
    LT-PAGE (H-SA0), at page 0 LT-HIST (H-HIST)."""
    out = run(tmp_path, stage, "one")
    assert outcome(out, "LT-PAGE") == "held" and outcome(out, "LT-HIST") == "FAILED"
    out = run(tmp_path, stage, "one", "early0")
    assert outcome(out, "LT-HIST") == "held" and outcome(out, "LT-PAGE") == "FAILED"
    assert pred(out, "LT-HIST").endswith(": FAILED")


@pytest.mark.parametrize("stage", of("LT"))
def test_lt_one_with_job_2_served_cannot_split_the_pages(tmp_path, stage):
    out = run(tmp_path, stage, "one", "serve")
    for x in ("LT-PAGE", "LT-HIST"):
        assert "cannot tell (LT-ONE and job 2 served" in pred(out, x), pred(out, x)
    assert outcome(out, "LT-SERVE") == "held"


@pytest.mark.parametrize("stage", of("LFF"))
@pytest.mark.parametrize("tokens,held,failed", [
    (("one",), "LFF-V0", "LFF-SA0"), (("sa0=0x00000000",), "LFF-PAGE", "LFF-SA0"),
    (("one", "early0"), "LFF-HIST", "LFF-PAGE")])
def test_lff_s_other_readings(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, *tokens)
    assert outcome(out, held) == "held", out
    assert outcome(out, failed) == "FAILED"


@pytest.mark.parametrize("stage", LAND_STAGES)
@pytest.mark.parametrize("token", ["noplant", "wfail"])
def test_a_land_stage_s_outcomes_need_the_plant(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in score.NEEDS_PLANT[STAGES[stage]]:
        assert "cannot tell (W-SA1" in pred(out, x), pred(out, x)
    for x in [x for x in names(stage) if x.endswith("OTHER")]:
        assert pred(out, x).endswith(": printed")


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
