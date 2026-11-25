# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer replayed on KEPT stages (pinned, resgx545-data 72e07b2d6; round
45's N4 wi and lff, N5 zff, N6 q, round 41's H1 c) as the tokens edit them (tests/attempt.py), and
on round 45's kept LFF (E1217), LF2 (E1213) and Q (E1233) replayed whole (the design's fixtures,
§3.1: LFF scores LFF2-FILL2 held and LFF2-KEEP failed, LF2 LFF2-KEEP's sa1 rule held, Q Q2-SAME
held, Q doctored to fault at 0x005d200f Q2-SAME failed): every frozen outcome of the session's
stages held where it must hold and FAILED or cannot tell where it must not, the controls able to
fail (E0 and the job controls read in their jobs' records, never on the row-end page; DR read
from the kernel log's begin health mark and the kept draws; DK, K9's command count, from the
kernel log's `ccb_sent` lines; SV from the attempt's stage log), the plant stage right before a
read or land stage deciding whether its attribute-1 outcomes read, the page rows' -WRITE and the B
rows' start scoping their outcomes, and the RULE and PREDICTION lines."""
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


def replay(tmp_path, stage, kept, doctor=None):
    d = attempt.replay(str(tmp_path / f"replay-{kept}-{doctor}"), stage, kept, doctor)
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
    return next(ln for ln in out.splitlines() if ln.startswith(f"Q128-N3K-{stage.upper()} RULE: "))


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
    assert score.PLANT == make.PLANT and score.BUILD_CONTROL == make.BUILD_CONTROL == "wa"
    assert score.DRAWS == make.DRAWS
    assert (score.READS, score.LANDS, score.FILLS, score.PAGES, score.BROWS) == \
        (make.READS, make.LANDS, make.FILLS, make.PAGES, make.BROWS)
    assert score.SRCV == attempt.SRCV and len(score.SRCV) == 23


def test_the_draw_lists_each_stage_declares():
    assert score.DRAWS == {"b5": "fill,tri", "b6": "fill,tri", "zff2": "fill,fill",
                           "lff2": "fill,fill", "lff3": "fill,fill", "lf3f": "fill,fill,fill",
                           "q2": "none", "r": "none", "p": "none", "r2": "none", "p2": "none"}


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
    assert f"KC {make.row_name(stage)}: begin N0 " in out


@pytest.mark.parametrize("stage", of("W"))
@pytest.mark.parametrize("token", ["wfault", "resetfault"])
def test_w_fault_holds_and_says_stop(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert outcome(out, "W-FAULT") == "held" and pred(out, "W-FAULT").endswith(": FAILED")
    assert "W-FAULT: a pass ran that we did not expect: stop the session" in out
    assert ("WA (the build control on the r46-kernel module" in out) == (stage == "wa")
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
    assert ("WA (the build control on the r46-kernel module" in out) == (stage == "wa")


# ---- ZFF2: crumbz after fill,fill --------------------------------------------------------------
@pytest.mark.parametrize("stage", of("ZFF2"))
def test_zff2_s_predicted_reading(tmp_path, stage):
    out = run(tmp_path, stage)
    for x in ("ZFF2-KEEP", "ZFF2-QUIET"):
        assert outcome(out, x) == "held", (x, out)
    for x in ("ZFF2-FILL2", "ZFF2-OTHER", "ZFF2-FAULT"):
        assert outcome(out, x) == "FAILED", (x, out)
    assert all_as_predicted(out), out
    assert rule(out, stage).endswith("RULE: ZFF2-KEEP, ZFF2-QUIET"), rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in
               ("PG", "E0", "T0", "B", "J1", "DR", "DK", "SV", "PLANT")), out


@pytest.mark.parametrize("stage", of("ZFF2"))
@pytest.mark.parametrize("tokens,held,failed", [
    (("sa1=0x04000010", "sa0=0x00000000"), ("ZFF2-FILL2",), ("ZFF2-KEEP", "ZFF2-OTHER")),
    (("sa1=0x04000010",), ("ZFF2-OTHER",), ("ZFF2-KEEP", "ZFF2-FILL2")),
    (("sa0=0x00000000",), ("ZFF2-OTHER",), ("ZFF2-KEEP", "ZFF2-FILL2")),
    (("sa2=0x01061a70",), ("ZFF2-OTHER",), ("ZFF2-KEEP",)),
    (("sa1=0x02000010",), ("ZFF2-OTHER",), ("ZFF2-KEEP",))])
def test_zff2_s_other_readings(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, *tokens)
    for x in held:
        assert outcome(out, x) == "held", (x, out)
    for x in failed:
        assert outcome(out, x) == "FAILED", (x, out)
    assert pred(out, "ZFF2-OTHER").endswith(": printed")


@pytest.mark.parametrize("stage", of("ZFF2"))
def test_zff2_fault_says_stop(tmp_path, stage):
    out = run(tmp_path, stage, "rfault")
    assert outcome(out, "ZFF2-FAULT") == "held" and pred(out, "ZFF2-FAULT").endswith(": FAILED")
    assert "ZFF2-FAULT (a BIF fault in a quiet read): the row's read stands, stop the session" in out


# ---- the land stages after fills: LFF2, LFF3, LF3F ------------------------------------------------
FILL_STAGES = of(*make.FILLS)
FHELD = {"LFF2": ("LFF2-KEEP", "LFF2-PAGE0", "LFF2-SA0"), "LFF3": ("LFF3-KEEP", "LFF3-PAGE0",
                                                                    "LFF3-SA0"),
         "LF3F": ("LF3F-KEEP", "LF3F-PAGE0")}


@pytest.mark.parametrize("stage", FILL_STAGES)
def test_a_fill_land_stage_s_predicted_reading(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage)
    for x in FHELD[m]:
        assert outcome(out, x) == "held", (x, out)
    for x in names(stage):
        if x not in FHELD[m]:
            assert outcome(out, x) == "FAILED", (x, out)
    assert all_as_predicted(out), out
    assert rule(out, stage).endswith("RULE: " + ", ".join(sorted(FHELD[m]))), rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in
               ("PG", "E0", "T0", "J1", "DR", "DK", "SV", "PLANT")), out
    assert control(out, stage, "J2") == "FAILED" and control(out, stage, "B") == "FAILED"
    want = score.K.kc_expected(make.DRAWS[stage])
    assert want == (8 if m == "LF3F" else 6)
    assert f"delta {want}, expected 2 + 2 x " in out, out


@pytest.mark.parametrize("stage", FILL_STAGES)
@pytest.mark.parametrize("word,which", [(0x04000010, "FILL2"), (0x02000010, "FILL1"),
                                        (0x06000010, "LAST"), (0x12345678, "OTHER")])
def test_a_fill_land_stage_s_attribute_1_words(tmp_path, stage, word, which):
    m = STAGES[stage]
    out = run(tmp_path, stage, f"sa1=0x{word:08x}")
    name = {"LF3F": {"FILL2": "SECOND", "FILL1": "FIRST"}}.get(m, {}).get(which, which)
    if m != "LF3F" and which == "LAST":
        assert outcome(out, f"{m}-OTHER") == "held"
        return
    assert outcome(out, f"{m}-{name}") == "held", out
    assert outcome(out, f"{m}-KEEP") == "FAILED"
    if which == "OTHER":
        assert pred(out, f"{m}-OTHER").endswith(": printed")
    else:
        assert pred(out, f"{m}-{name}").endswith(": FAILED")


@pytest.mark.parametrize("stage", of("LFF2", "LFF3"))
def test_lffn_triple_is_the_3_4_entry_s(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "sa0=0x00000000", "sa1=0x04000010")
    assert outcome(out, f"{m}-TRIPLE") == "held" and outcome(out, f"{m}-SA0") == "FAILED"
    assert outcome(out, f"{m}-FILL2") == "held"


@pytest.mark.parametrize("stage", FILL_STAGES)
def test_a_fill_land_stage_s_other_page_and_serve(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "pg=0x005d100f")
    assert outcome(out, f"{m}-PAGE0") == "FAILED"
    out = run(tmp_path, stage, "serve")
    assert outcome(out, f"{m}-SERVE") == "held" and outcome(out, f"{m}-PAGE0") == "FAILED"
    assert "no fault and job 2 done" in out


@pytest.mark.parametrize("stage", of("ZFF2", *make.FILLS))
@pytest.mark.parametrize("token", ["noplant", "wfail"])
def test_the_attribute_1_outcomes_need_the_plant(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in score.NEEDS_PLANT[STAGES[stage]]:
        assert "cannot tell (W-SA1" in pred(out, x), pred(out, x)
    for x in names(stage):
        if x not in score.NEEDS_PLANT[STAGES[stage]]:
            assert "W-SA1" not in pred(out, x), pred(out, x)
    assert control(out, stage, "PLANT") == ("FAILED" if token == "wfail" else "cannot tell")
    assert "RULE: CANNOT TELL" not in rule(out, stage)


@pytest.mark.parametrize("stage", of("ZFF2", *make.FILLS))
@pytest.mark.parametrize("token", ["drmark", "drretry", "drbad", "drgone"])
def test_dr_fails_when_the_declared_draws_did_not_run_exact_at_try_1(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert control(out, stage, "DR") == "FAILED", out
    assert f"DR {make.row_name(stage)} (printed): " in out
    assert "control DR FAILED" in rule(out, stage) and "RULE: CANNOT TELL" in rule(out, stage)
    assert all("cannot tell" in ln for ln in out.splitlines()
               if ln.startswith("PREDICTION ") and not ln.endswith("printed")), out


@pytest.mark.parametrize("stage", of("ZFF2", *make.FILLS))
@pytest.mark.parametrize("token", ["dkbad", "dkgone"])
def test_dk_failing_or_unread_makes_the_k_outcomes_cannot_tell_only(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert control(out, stage, "DK") == ("FAILED" if token == "dkbad" else "cannot tell"), out
    assert f"DK {make.row_name(stage)} (printed): control DK " in out
    needs = score.NEEDS_DK[STAGES[stage]]
    for x in needs:
        assert "cannot tell (DK " in pred(out, x), pred(out, x)
    assert all("DK" not in pred(out, x) for x in names(stage) if x not in needs), out
    assert "RULE: CANNOT TELL" not in rule(out, stage), rule(out, stage)


@pytest.mark.parametrize("stage", of("ZFF2", *make.FILLS))
def test_dk_prints_the_counts_and_h_kc_s_words(tmp_path, stage):
    out = run(tmp_path, stage)
    n = make.row_name(stage)
    assert f"HKC {n} (printed, never scored): begin draws {make.DRAWS[stage]} (K from 1): " in out


def test_the_cannot_tell_sets_are_the_design_s():
    assert score.NEEDS_DK == {"ZFF2": ("ZFF2-FILL2",), "LFF2": ("LFF2-FILL2", "LFF2-FILL1"),
                              "LFF3": ("LFF3-FILL2", "LFF3-FILL1"),
                              "LF3F": ("LF3F-SECOND", "LF3F-LAST", "LF3F-FIRST")}
    assert score.NEEDS_PLANT["LF3F"] == ("LF3F-KEEP", "LF3F-SECOND", "LF3F-LAST", "LF3F-FIRST")
    assert score.NEEDS_WRITE["P"] == ("P-UNMAP", "P-MAPPED", "P-OTHER")


# ---- the design's fixtures (§3.1): round 45's kept LFF, LF2 and Q, replayed whole ----------------
@pytest.mark.parametrize("stage", of("LFF2", "LFF3"))
def test_lff_e1217_scores_fill2_held_and_keep_failed(tmp_path, stage):
    m = STAGES[stage]
    out = replay(tmp_path, stage, "lff")
    assert outcome(out, f"{m}-FILL2") == "held", out
    assert outcome(out, f"{m}-KEEP") == "FAILED", out
    assert outcome(out, f"{m}-TRIPLE") == "held" and outcome(out, f"{m}-PAGE0") == "held", out
    assert control(out, stage, "PLANT") == "PASS" and control(out, stage, "DK") == "PASS", out
    assert control(out, stage, "SV") == "FAILED"            # round 45's module, not r46's
    assert "RULE: CANNOT TELL (control SV FAILED)" in rule(out, stage)


@pytest.mark.parametrize("stage", of("LFF2", "LFF3"))
def test_lf2_e1213_scores_keep_s_sa1_rule_held(tmp_path, stage):
    m = STAGES[stage]
    out = replay(tmp_path, stage, "lf2")
    assert outcome(out, f"{m}-KEEP") == "held", out
    assert outcome(out, f"{m}-SA0") == "held" and outcome(out, f"{m}-PAGE0") == "held", out
    assert control(out, stage, "DR") == "FAILED"            # one fill, not the declared two
    assert control(out, stage, "DK") == "FAILED"


@pytest.mark.parametrize("stage", of("Q2"))
def test_q_e1233_scores_q2_same_held(tmp_path, stage):
    out = replay(tmp_path, stage, "q")
    assert outcome(out, "Q2-SAME") == "held" and outcome(out, "Q2-WRITE") == "held", out
    assert outcome(out, "Q2-SA0") == "FAILED" and outcome(out, "Q2-SERVE") == "FAILED"


@pytest.mark.parametrize("stage", of("Q2"))
def test_q_doctored_to_fault_at_q0_scores_q2_same_failed(tmp_path, stage):
    out = replay(tmp_path, stage, "q", "qdoc")
    assert outcome(out, "Q2-SAME") == "FAILED", out
    assert outcome(out, "Q2-SA0") == "held" and outcome(out, "Q2-WRITE") == "held", out


# ---- the page rows: Q2, R, P (R2, P2) -------------------------------------------------------------
PAGE_STAGES = of(*make.PAGES)
PHELD = {"Q2": ("Q2-SAME", "Q2-WRITE"), "R": ("R-LOW", "R-WRITE"), "R2": ("R2-LOW", "R2-WRITE"),
         "P": ("P-UNMAP", "P-WRITE"), "P2": ("P2-UNMAP", "P2-WRITE")}


@pytest.mark.parametrize("stage", PAGE_STAGES)
def test_a_page_row_s_predicted_reading(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage)
    for x in PHELD[m]:
        assert outcome(out, x) == "held", (x, out)
    for x in names(stage):
        if x not in PHELD[m]:
            assert outcome(out, x) == "FAILED", (x, out)
    assert all_as_predicted(out), out
    assert rule(out, stage).endswith("RULE: " + ", ".join(sorted(PHELD[m]))), rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in ("PG", "E0", "T0", "J1", "SV")), out
    assert control(out, stage, "DR") is None and control(out, stage, "DK") is None
    assert control(out, stage, "J2") == "FAILED"
    assert "printed only (the image writes sa0 and sa1 itself)" in out
    assert "delta 2, expected 2 + 2 x 0 + 6 x 0 = 2" in out


@pytest.mark.parametrize("stage", of("R", "R2"))
@pytest.mark.parametrize("page,held", [(0x0440000F, "SA0"), (0x0000000F, "OTHER"),
                                       (0x005D300F, "OTHER")])
def test_r_s_pages(tmp_path, stage, page, held):
    m = STAGES[stage]
    out = run(tmp_path, stage, f"pg=0x{page:08x}")
    assert outcome(out, f"{m}-{held}") == "held" and outcome(out, f"{m}-LOW") == "FAILED", out
    assert pred(out, f"{m}-{held}").endswith(": printed" if held == "OTHER" else ": FAILED")


@pytest.mark.parametrize("stage", of("P", "P2"))
@pytest.mark.parametrize("tokens,held", [(("serve",), ("MAPPED",)),
                                         (("pg=0x005d100f",), ("MAPPED", "OTHER")),
                                         (("pg=0x0000000f",), ("MAPPED", "OTHER"))])
def test_p_mapped_is_no_fault_at_q0(tmp_path, stage, tokens, held):
    m = STAGES[stage]
    out = run(tmp_path, stage, *tokens)
    for x in held:
        assert outcome(out, f"{m}-{x}") == "held", out
    assert outcome(out, f"{m}-UNMAP") == "FAILED"
    assert pred(out, f"{m}-MAPPED").endswith(": FAILED")


@pytest.mark.parametrize("stage", of("Q2"))
@pytest.mark.parametrize("tokens,held", [(("pg=0x005d200f",), "Q2-SA0"),
                                         (("pg=0x0000000f",), "Q2-OTHER"), (("serve",), "Q2-SERVE")])
def test_q2_s_other_pages(tmp_path, stage, tokens, held):
    out = run(tmp_path, stage, *tokens)
    assert outcome(out, held) == "held" and outcome(out, "Q2-SAME") == "FAILED", out


@pytest.mark.parametrize("stage", PAGE_STAGES)
@pytest.mark.parametrize("token", ["sa0=0x32004000", "sa1=0x005d3000", "sa0=0x00000002"])
def test_write_failing_makes_every_page_outcome_cannot_tell(tmp_path, stage, token):
    m = STAGES[stage]
    out = run(tmp_path, stage, token)
    if m in ("P", "P2") and token == "sa0=0x32004000":
        return                                  # V0 is P's own sa0
    assert outcome(out, f"{m}-WRITE") == "FAILED"
    for x in score.NEEDS_WRITE[m]:
        assert f"cannot tell ({m}-WRITE not held" in pred(out, x), pred(out, x)


@pytest.mark.parametrize("stage", PAGE_STAGES)
@pytest.mark.parametrize("token", ["noplant", "wfail", "drmark", "drbad", "dkbad", "dkgone"])
def test_a_page_row_prints_plant_dr_and_dk_and_does_not_score_them(tmp_path, stage, token):
    m = STAGES[stage]
    out = run(tmp_path, stage, token)
    assert "RULE: CANNOT TELL" not in rule(out, stage), rule(out, stage)
    assert outcome(out, PHELD[m][0]) == "held"
    assert pred(out, PHELD[m][0]).endswith(": held"), out
    if token.startswith(("dr", "dk")):
        assert "not scored here" in out, out


# ---- the B rows: crumb3 with sideband 0x043 or 0x803, the after-read on a kick, the gate ---------
B_STAGES = of(*make.BROWS)
BHELD = ("DONE", "RUN", "HID", "SAME", "GATE", "QUIET")


@pytest.mark.parametrize("stage", B_STAGES)
def test_a_b_row_s_predicted_reading(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage)
    held = tuple(f"{m}-{x}" for x in BHELD)
    for x in held:
        assert outcome(out, x) == "held", (x, out)
    for x in names(stage):
        if x not in held and x not in (f"{m}-LANDNONE",):
            assert outcome(out, x) == "FAILED", (x, out)
    assert all_as_predicted(out), out
    assert rule(out, stage).endswith("RULE: " + ", ".join(sorted(held))), rule(out, stage)
    assert all(control(out, stage, k) == "PASS" for k in
               ("PG", "E0", "T0", "B", "J1", "J2", "SV")), out
    assert f"AFTER {make.row_name(stage)} (printed): " in out
    assert "KC " in out


@pytest.mark.parametrize("stage", B_STAGES)
@pytest.mark.parametrize("token,held,failed", [
    ("rebase", ("REBASE",), ("SAME", "HID")), ("aother", ("AOTHER",), ("SAME", "REBASE")),
    ("nokick", ("NOKICK",), ("SAME",)), ("gatefail", ("FILL",), ("GATE",)),
    ("land4", ("LAND4",), ("LANDNONE",))])
def test_a_b_row_s_other_readings(tmp_path, stage, token, held, failed):
    m = STAGES[stage]
    out = run(tmp_path, stage, token)
    for x in held:
        assert outcome(out, f"{m}-{x}") == "held", (x, out)
    for x in failed:
        assert outcome(out, f"{m}-{x}") in ("FAILED", "cannot tell"), (x, out)
    assert "RULE: CANNOT TELL" not in rule(out, stage)


@pytest.mark.parametrize("stage", B_STAGES)
@pytest.mark.parametrize("token,start", [("never", "NEVER"), ("t3", "T3")])
def test_a_b_row_s_start_is_its_reading_and_scopes_the_rest(tmp_path, stage, token, start):
    m = STAGES[stage]
    out = run(tmp_path, stage, token)
    assert outcome(out, f"{m}-{start}") == "held" and outcome(out, f"{m}-DONE") == "FAILED", out
    assert pred(out, f"{m}-{start}").endswith(": FAILED")
    assert outcome(out, f"{m}-RUN") == ("FAILED" if start == "NEVER" else "held")
    assert control(out, stage, "J1") == "FAILED"
    assert "RULE: CANNOT TELL" not in rule(out, stage), rule(out, stage)
    for x in score.NEEDS_DONE[m]:
        assert f"not DONE: no after-read" in pred(out, x), pred(out, x)
    assert f"the start is {start}, not DONE" in out


@pytest.mark.parametrize("stage", B_STAGES)
def test_a_b_row_fault_says_stop(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "bfault")
    assert outcome(out, f"{m}-QUIET") == "FAILED" and control(out, stage, "B") == "FAILED"
    assert "stop the B rows for the user" in out


# ---- every stage: the controls and SV -----------------------------------------------------------
@pytest.mark.parametrize("stage", list(STAGES))
@pytest.mark.parametrize("token,ctl", [("pgbad", "PG"), ("e0bad", "E0"), ("e0cmd", "E0"),
                                       ("t0stop", "T0"), ("j1bad", "J1")])
def test_each_control_can_fail_and_the_rule_cannot_tell(tmp_path, stage, token, ctl):
    out = run(tmp_path, stage, token)
    assert control(out, stage, ctl) == "FAILED", out
    if STAGES[stage] in make.BROWS and ctl == "J1":
        assert "RULE: CANNOT TELL" not in rule(out, stage)       # the start is the reading
        return
    assert "RULE: CANNOT TELL" in rule(out, stage)
    assert all("cannot tell" in ln or ln.endswith("printed")
               for ln in out.splitlines() if ln.startswith("PREDICTION ")), out


@pytest.mark.parametrize("stage", list(STAGES))
@pytest.mark.parametrize("token,state", [("svbad", "FAILED"), ("svinst", "FAILED"),
                                         ("svgone", "cannot tell")])
def test_sv_reads_the_stage_log_and_the_rule_cannot_tell(tmp_path, stage, token, state):
    out = run(tmp_path, stage, token)
    assert control(out, stage, "SV") == state, out
    assert f"SV {make.row_name(stage)}: srcversion {score.SRCV} installed and loaded" in out
    assert f"control SV {state}" in rule(out, stage) and "RULE: CANNOT TELL" in rule(out, stage)
