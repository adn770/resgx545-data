# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer replayed on round 44's KEPT stages (N1's wa and ff, N2's lm;
pinned, resgx545-data ebfeaa775) as the tokens edit them (tests/attempt.py): every frozen outcome of
the session's stages held where it must hold and FAILED or cannot tell where it must not, the
controls able to fail (E0 and the job controls read in their jobs' records, never on the row-end
page; DR read from the kernel log's begin health mark and the kept draws; DK, K9's command count,
from the kernel log's `ccb_sent` lines; SV from the attempt's stage log; ZN from the stage zn of
the attempt), the plant stage right before a Z stage (the pairing WJ-ZN, WK-ZT, WL-ZFT, WM-ZF,
WN-ZFF, WO-ZTF, WP-ZTT) deciding whether its outcomes read, ZN scoping the sa0 and sa2 outcomes,
Q's cannot-tell rules, and the RULE and PREDICTION lines."""
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
               if ln.startswith("PREDICTION "))


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
    assert score.SRCV == "EC553F41FD8324BB6BF1764" == attempt.SRCV


def test_the_draw_lists_each_stage_declares():
    assert score.DRAWS == {"zn": "none", "zt": "tri", "zft": "fill,tri", "zf": "fill",
                           "zff": "fill,fill", "ztf": "tri,fill", "ztt": "tri,tri", "q": "none"}


# ---- W (every plant stage): mark, job 1 alone --------------------------------------------------
@pytest.mark.parametrize("stage", of("W"))
def test_w_s_predicted_reading_on_w_s_job_1(tmp_path, stage):
    out = run(tmp_path, stage)
    for x in ("W-SA1", "W-SA13", "W-QUIET"):
        assert outcome(out, x) == "held" and pred(out, x).endswith(": held"), (x, out)
    assert outcome(out, "W-FAULT") == "FAILED" and pred(out, "W-FAULT").endswith(": held")
    assert rule(out, stage).endswith("RULE: W-QUIET, W-SA1, W-SA13")
    assert all(control(out, stage, k) == "PASS" for k in ("PG", "E0", "T0", "B", "J1", "SV")), out
    assert control(out, stage, "DR") is None and control(out, stage, "DK") is None
    assert f"KC {make.row_name(stage)}: begin N0 261, arm N1 271, delta 10" in out
    assert f"KC {make.row_name(stage)}: end N0 273, exit N1 275, delta 2" in out


@pytest.mark.parametrize("stage", of("W"))
@pytest.mark.parametrize("token", ["wfault", "resetfault"])
def test_w_fault_holds_and_says_stop(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert outcome(out, "W-FAULT") == "held" and pred(out, "W-FAULT").endswith(": FAILED")
    assert "W-FAULT: a pass ran that we did not expect: stop the session" in out
    if stage == "wj":
        assert "WJ (the build control) failed an outcome: stop N5 for the user" in out
    if token == "wfault":
        assert outcome(out, "W-QUIET") == "FAILED" and control(out, stage, "B") == "FAILED"


@pytest.mark.parametrize("stage", of("W"))
def test_w_fault_without_the_disarm_record_cannot_tell(tmp_path, stage):
    out = run(tmp_path, stage, "noreset")
    assert outcome(out, "W-FAULT") == "cannot tell"


@pytest.mark.parametrize("stage", of("W"))
def test_w_sa1_fails_when_attribute_1_is_not_m1(tmp_path, stage):
    out = run(tmp_path, stage, "nosa1")
    assert outcome(out, "W-SA1") == "FAILED" and "the next stage's outcomes" in out
    if stage == "wj":
        assert "WJ (the build control) failed an outcome: stop N5 for the user" in out


# ---- the Z stages: crumbz after a draw sequence ---------------------------------------------------
ZHELD = {"zn": ("ZN-SAME",), "zt": ("ZT-SA1", "ZT-TRIPLE"), "zft": ("ZFT-SA1", "ZFT-TRIPLE"),
         "zf": ("ZF-SA1", "ZF-DRAW"), "zff": ("ZFF-SA1", "ZFF-DRAW"),
         "ztf": ("ZTF-SA1", "ZTF-DRAW"), "ztt": ("ZTT-LAST", "ZTT-TRIPLE")}
Z_STAGES = [s for s in ZHELD if s in STAGES]
# (stage, tokens, the outcomes that hold, the outcomes that fail): the design's tables (§9.4)
ZCASES = [
    ("zn", ("sa0=0x00000000",), ("ZN-OTHER",), ("ZN-SAME",)),
    ("zn", ("sa1=0x04400000",), ("ZN-OTHER",), ("ZN-SAME",)),
    ("zn", ("sa2=0x00000000",), ("ZN-OTHER",), ("ZN-SAME",)),
    ("zt", ("one",), ("ZT-ONE",), ("ZT-TRIPLE", "ZT-AOTHER")),
    ("zt", ("sa0=0x00000002",), ("ZT-AOTHER",), ("ZT-TRIPLE", "ZT-ONE")),
    ("zt", ("sa2=0x12345678",), ("ZT-AOTHER",), ("ZT-TRIPLE", "ZT-ONE")),
    ("zt", ("sa2=0x01061a70",), ("ZT-AOTHER",), ("ZT-TRIPLE",)),
    ("zt", ("sa1=0x04400000",), ("ZT-TRIPLE",), ("ZT-SA1",)),
    ("zt", ("sa1=0x02000010",), ("ZT-TRIPLE",), ("ZT-SA1",)),
    ("zft", ("sa1=0x04000010",), ("ZFT-SA1", "ZFT-TRIPLE"), ()),
    ("zft", ("sa1=0x02400000",), ("ZFT-TRIPLE",), ("ZFT-SA1",)),
    ("zft", ("one",), ("ZFT-ONE",), ("ZFT-TRIPLE", "ZFT-AOTHER")),
    ("zft", ("sa0=0x00000002",), ("ZFT-AOTHER",), ("ZFT-TRIPLE",)),
    ("zf", ("sa1=0x01000000",), ("ZF-TICK1", "ZF-DRAW"), ("ZF-SA1",)),
    ("zf", ("one",), ("ZF-PLANT", "ZF-SA1"), ("ZF-DRAW", "ZF-AOTHER")),
    ("zf", ("sa0=0x00000000",), ("ZF-AOTHER",), ("ZF-DRAW", "ZF-PLANT")),
    ("zf", ("sa1=0x02000010",), ("ZF-DRAW",), ("ZF-SA1", "ZF-TICK1")),
    ("zff", ("one",), ("ZFF-PLANT",), ("ZFF-DRAW", "ZFF-AOTHER")),
    ("zff", ("sa0=0x00000000",), ("ZFF-AOTHER",), ("ZFF-DRAW", "ZFF-PLANT")),
    ("zff", ("sa1=0x04000010",), ("ZFF-DRAW",), ("ZFF-SA1",)),
    ("ztf", ("sa0=0x00000000",), ("ZTF-TRIPLE",), ("ZTF-DRAW", "ZTF-AOTHER")),
    ("ztf", ("one",), ("ZTF-AOTHER",), ("ZTF-DRAW", "ZTF-TRIPLE")),
    ("ztf", ("sa1=0x08000010",), ("ZTF-DRAW",), ("ZTF-SA1",)),
    ("ztt", ("sa1=0x02400000",), ("ZTT-FIRST", "ZTT-TRIPLE"), ("ZTT-LAST",)),
    ("ztt", ("sa1=0x02000010",), ("ZTT-FIRST",), ("ZTT-LAST",)),
    ("ztt", ("sa1=0x08000010",), ("ZTT-LAST",), ("ZTT-FIRST",)),
    ("ztt", ("sa1=0x04400000",), ("ZTT-TRIPLE",), ("ZTT-LAST", "ZTT-FIRST")),
    ("ztt", ("one",), ("ZTT-ONE",), ("ZTT-TRIPLE", "ZTT-AOTHER")),
]


@pytest.mark.parametrize("stage", Z_STAGES)
def test_a_z_stage_s_predicted_reading(tmp_path, stage):
    """The stage's predicted words (design §9.4): the held outcomes and Z-QUIET held, every
    predicted failure FAILED, every prediction held, the controls pass (DR, DK, SV and ZN too),
    the rule names the held ones."""
    out = run(tmp_path, stage)
    held = ZHELD[stage] + ("Z-QUIET",)
    for x in held:
        assert outcome(out, x) == "held", (x, out)
    for x in names(stage):
        if x not in held:
            assert outcome(out, x) == "FAILED", (x, out)
    assert all_as_predicted(out), out
    assert rule(out, stage).endswith(f"RULE: {', '.join(sorted(held))}"), rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in
               ("PG", "E0", "T0", "B", "J1", "DR", "DK", "SV")), out
    assert control(out, stage, "ZN") == ("PASS" if stage != "zn" else None), out


@pytest.mark.parametrize("stage,tokens,held,failed", ZCASES)
def test_a_z_stage_s_other_readings(tmp_path, stage, tokens, held, failed):
    if stage not in STAGES:
        pytest.skip("another session's stage")
    out = run(tmp_path, stage, *tokens)
    for x in held:
        assert outcome(out, x) == "held", (x, out)
    for x in failed:
        assert outcome(out, x) == "FAILED", (x, out)
    for x in held:
        if x.endswith("AOTHER"):
            assert pred(out, x).endswith(": printed")


@pytest.mark.parametrize("stage", Z_STAGES)
@pytest.mark.parametrize("token", ["noplant", "wfail"])
def test_a_z_stage_s_outcomes_need_the_plant(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in score.NEEDS_PLANT[STAGES[stage]]:
        assert "cannot tell (W-SA1" in pred(out, x), pred(out, x)
    assert outcome(out, "Z-QUIET") == "held" and pred(out, "Z-QUIET").endswith(": held")


def test_the_plant_is_the_stage_right_before_the_z_stage(tmp_path):
    """ZN reads WJ, ZT WK, ZFT WL, ZF WM, ZFF WN, ZTF WO, ZTT WP: the plant stages in one attempt
    directory, one failing at a time; only its own stage cannot tell."""
    pairs = [(w, r) for r, w in make.PLANT.items() if r in STAGES]
    if not pairs:
        pytest.skip("no Z stage in this session")
    for bad, _ in pairs:
        root = str(tmp_path / f"bad-{bad}")
        for plant, read in pairs:
            attempt.build(root, read, ("wfail",) if plant == bad else ())
        for plant, read in pairs:
            out = score_dir(os.path.join(root, read), read)
            assert f"W-SA1 of stage {plant} " in out, (plant, read)
            word = pred(out, score.NEEDS_PLANT[STAGES[read]][0])
            assert ("cannot tell (W-SA1" in word) == (plant == bad), (bad, read, word)


# ---- ZN: the session-scoped control ---------------------------------------------------------------
ZN_AFTER = [s for s in Z_STAGES if s != "zn"]


@pytest.mark.parametrize("stage", ZN_AFTER)
@pytest.mark.parametrize("token,state", [("znbad", "FAILED"), ("nozn", "cannot tell")])
def test_zn_failing_or_unread_makes_the_sa0_and_sa2_outcomes_cannot_tell_only(
        tmp_path, stage, token, state):
    out = run(tmp_path, stage, token)
    assert control(out, stage, "ZN") == state, out
    assert f"ZNCTL {make.row_name(stage)}: ZN-SAME of stage zn " in out
    needs = score.NEEDS_ZN[STAGES[stage]]
    for x in needs:
        assert "cannot tell (control ZN" in pred(out, x), pred(out, x)
    # an outcome that names no sa0 or sa2 still reads, and the RULE is not CANNOT TELL
    for x in names(stage):
        if x not in needs and not x.endswith("AOTHER") and "QUIET" not in x and "FAULT" not in x:
            assert "control ZN" not in pred(out, x), (x, pred(out, x))
    assert "RULE: CANNOT TELL" not in rule(out, stage), rule(out, stage)


def test_zn_names_the_outcomes_the_design_lists():
    n = score.NEEDS_ZN
    assert set(n) == {"ZT", "ZFT", "ZF", "ZFF", "ZTF", "ZTT"}
    assert n["ZF"] == ("ZF-DRAW", "ZF-PLANT") and n["ZTF"] == ("ZTF-DRAW", "ZTF-TRIPLE")
    assert n["ZTT"] == ("ZTT-TRIPLE", "ZTT-ONE")


@pytest.mark.parametrize("stage", of("ZN"))
def test_zn_stage_says_what_a_failed_zn_costs(tmp_path, stage):
    out = run(tmp_path, stage, "sa0=0x00000000")
    assert outcome(out, "ZN-OTHER") == "held" and pred(out, "ZN-OTHER").endswith(": FAILED")
    assert "control ZN failed: every later Z row's sa0 and sa2 outcomes read cannot tell" in out


# ---- DR: the declared begin draws -----------------------------------------------------------------
DR_STAGES = [s for s in Z_STAGES]


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


@pytest.mark.parametrize("stage", Z_STAGES)
def test_a_fault_in_a_z_stage_says_stop(tmp_path, stage):
    out = run(tmp_path, stage, "rfault")
    assert control(out, stage, "B") == "FAILED"
    assert "Z-FAULT (a BIF fault after job 1): the row's read stands, stop the session" in out
    assert outcome(out, "Z-FAULT") == "held" and pred(out, "Z-FAULT").endswith(": FAILED")


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
    needs = score.NEEDS_DK.get(STAGES[stage], ())
    for x in needs:
        assert "cannot tell (DK " in pred(out, x), pred(out, x)
    rest = [x for x in names(stage) if x not in needs and not x.endswith("AOTHER")
            and "QUIET" not in x and "FAULT" not in x]
    # an outcome that names no K still reads: the sa0 and sa2 ones, ZF-SA1, ZFF-SA1 and ZN's
    assert all("DK" not in pred(out, x) for x in rest), out
    assert "RULE: CANNOT TELL" not in rule(out, stage), rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in ("PG", "E0", "T0", "J1", "DR", "SV"))


def test_dk_names_the_outcomes_the_design_lists():
    d = score.NEEDS_DK
    assert d == {"ZT": ("ZT-SA1",), "ZFT": ("ZFT-SA1",), "ZF": ("ZF-TICK1",), "ZTF": ("ZTF-SA1",),
                 "ZTT": ("ZTT-LAST", "ZTT-FIRST")}


# ---- SV: the srcversion ---------------------------------------------------------------------------
@pytest.mark.parametrize("stage", list(STAGES))
@pytest.mark.parametrize("token,state", [("svbad", "FAILED"), ("svinst", "FAILED"),
                                         ("svgone", "cannot tell")])
def test_sv_reads_the_stage_log_and_the_rule_cannot_tell(tmp_path, stage, token, state):
    out = run(tmp_path, stage, token)
    assert control(out, stage, "SV") == state, out
    assert f"SV {make.row_name(stage)}: srcversion EC553F41FD8324BB6BF1764 installed and loaded" in out
    assert f"control SV {state}" in rule(out, stage) and "RULE: CANNOT TELL" in rule(out, stage)


# ---- the land stage Q -------------------------------------------------------------------------------
LAND_STAGES = [s for s in STAGES if STAGES[s] == "Q"]


@pytest.mark.parametrize("stage", LAND_STAGES)
def test_q_s_predicted_reading(tmp_path, stage):
    """landq: sa0 Q0, sa1 M1, sa2 V2 (the bank's), job 2 not done, the K5 fault at Q0's page
    (H-SA0)."""
    out = run(tmp_path, stage)
    for x in ("Q-WRITE", "Q-SA0"):
        assert outcome(out, x) == "held", (x, out)
    for x in ("Q-LOW", "Q-OTHER", "Q-SERVE"):
        assert outcome(out, x) == "FAILED", (x, out)
    assert all_as_predicted(out), out
    assert rule(out, stage).endswith("RULE: Q-SA0, Q-WRITE"), rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in ("PG", "E0", "T0", "J1", "SV")), out
    assert control(out, stage, "DR") is None and control(out, stage, "DK") is None
    assert control(out, stage, "J2") == "FAILED"
    n = make.row_name(stage)
    assert f"KC {n}: begin N0 " in out and "delta 2, expected 2 + 2 x 0 + 6 x 0 = 2" in out


@pytest.mark.parametrize("stage", LAND_STAGES)
@pytest.mark.parametrize("tokens,held,failed", [
    (("early0",), "Q-OTHER", "Q-SA0"), (("early13",), "Q-OTHER", "Q-SA0"),
    (("other",), "Q-OTHER", "Q-SA0"), (("serve",), "Q-SERVE", "Q-SA0")])
def test_q_s_other_pages(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, *tokens)
    assert outcome(out, held) == "held", out
    assert outcome(out, failed) == "FAILED"
    if held == "Q-OTHER":
        assert pred(out, "Q-OTHER").endswith(": printed")
    else:
        assert pred(out, held).endswith(": FAILED")


@pytest.mark.parametrize("stage", LAND_STAGES)
def test_q_low_holds_and_reads_cannot_tell(tmp_path, stage):
    """The fault at 0x005d1000: Q-LOW, 'lowest page' or 'sa0 mapped' (design §9.5)."""
    out = run(tmp_path, stage, "low")
    assert outcome(out, "Q-LOW") == "held" and outcome(out, "Q-SA0") == "FAILED"
    assert "cannot tell ('lowest page'" not in pred(out, "Q-LOW")
    assert "cannot tell (a fault at 0x005d1000 with Q-WRITE held" in pred(out, "Q-LOW")
    assert "Q-LOW" not in rule(out, stage)


@pytest.mark.parametrize("stage", LAND_STAGES)
@pytest.mark.parametrize("tokens", [("sa0=0x32004000",), ("sa1=0x005d3000",), ("sa0=0x005d1000",)])
def test_q_write_failing_makes_every_page_outcome_cannot_tell(tmp_path, stage, tokens):
    out = run(tmp_path, stage, *tokens)
    assert outcome(out, "Q-WRITE") == "FAILED"
    for x in ("Q-SA0", "Q-LOW", "Q-OTHER", "Q-SERVE"):
        assert "cannot tell (Q-WRITE not held" in pred(out, x), pred(out, x)


@pytest.mark.parametrize("stage", LAND_STAGES)
@pytest.mark.parametrize("token", ["drmark", "drretry", "drbad", "drgone", "dkbad", "dkgone"])
def test_q_prints_dr_and_dk_and_does_not_score_them(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert "not scored here" in out, out
    assert "RULE: CANNOT TELL" not in rule(out, stage), rule(out, stage)
    assert outcome(out, "Q-SA0") == "held"


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
