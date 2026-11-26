# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer replayed on KEPT stages (pinned, resgx545-data 72e07b2d6; round
45's N4 wi and lff, N5 zff, N6 q) as the tokens edit them (tests/attempt.py), and on kept stages
replayed whole (the design's fixtures, §11.5): round 46's n1 lff2 scores LFK-M1's page rule held
and -PAGE0 failed, and PAD fails on it (KC begin 138) and passes on a copy doctored to 900; round
45's LF2 (E1213) -PAGE0 held and -E12 failed; LT (E1215) LTK-PAGE0 and LTK-SA held; round 46's n4
q2 (fault at M1) P-OTHER's `@faultnotin` with the SUM page held and R-OTHER's failed (M1 is R-LOW's
page). Every frozen outcome held where it must hold and FAILED or cannot tell where it must not,
the controls able to fail (E0 and the job controls read in their jobs' records; DR from the kernel
log's begin health mark and the kept draws; DK, K9's command count; PAD, K11; SV from the
attempt's stage log), the plant deciding whether -SA reads, the page rows' -WRITE scoping their
outcomes, E12 and PAD as NOTEs, and the RULE and PREDICTION lines."""
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
    assert score.PLANT == make.PLANT and score.BUILD_CONTROL is make.BUILD_CONTROL is None
    assert score.DRAWS == make.DRAWS and score.PADS == make.PADS == {"lfkp": 830}
    assert (score.READS, score.LANDS, score.FILLS, score.PAGES, score.BROWS) == \
        (make.READS, make.LANDS, make.FILLS, make.PAGES, make.BROWS)
    assert score.SRCV == attempt.SRCV and len(score.SRCV) == 23


def test_the_draw_lists_each_stage_declares():
    assert score.DRAWS == {"lfk": "fill", "ltk": "tri", "lfk2": "fill", "lfkp": "fill",
                           "r": "none", "p": "none", "r2": "none", "p2": "none"}


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
    assert control(out, stage, "PAD") is None
    assert f"KC {make.row_name(stage)}: begin N0 " in out
    assert "build control" not in out


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


# ---- the land stages after draws: LFK, LFK2, LFKP (one fill), LTK (one triangle) ---------------
FILL_STAGES = of(*make.FILLS)
FHELD = {"LFK": ("LFK-E12", "LFK-M1", "LFK-SA"), "LFK2": ("LFK2-E12", "LFK2-M1", "LFK2-SA"),
         "LFKP": ("LFKP-E12", "LFKP-M1", "LFKP-SA"), "LTK": ("LTK-E12", "LTK-SA", "LTK-SA1")}


@pytest.mark.parametrize("stage", FILL_STAGES)
def test_a_draw_land_stage_s_predicted_reading(tmp_path, stage):
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
    assert want == (8 if m == "LTK" else 4)
    assert f"delta {want}, expected 2 + 2 x " in out, out
    assert "NOTE" not in out, out
    assert (control(out, stage, "PAD") == "PASS") == (m == "LFKP")
    assert ("PAD " + make.row_name(stage) + ": begin N0 900, at least 830 (ok)" in out) == \
        (m == "LFKP")


@pytest.mark.parametrize("stage", of("LFK", "LFK2", "LFKP"))
@pytest.mark.parametrize("page,held", [(0x0000000F, "PAGE0"), (0x005D300F, "OTHER"),
                                       (0x0240000F, "OTHER")])
def test_lfk_s_pages(tmp_path, stage, page, held):
    m = STAGES[stage]
    out = run(tmp_path, stage, f"pg=0x{page:08x}")
    assert outcome(out, f"{m}-{held}") == "held" and outcome(out, f"{m}-M1") == "FAILED", out
    assert pred(out, f"{m}-{held}").endswith(": printed" if held == "OTHER" else ": FAILED")


@pytest.mark.parametrize("stage", of("LTK"))
@pytest.mark.parametrize("tokens,held,failed", [
    (("pg=0x0000000f",), ("LTK-PAGE0",), ("LTK-SA1", "LTK-PAST")),
    (("pg=0x005d100f",), ("LTK-PAST",), ("LTK-SA1", "LTK-PAGE0")),
    (("serve",), ("LTK-PAST", "LTK-SERVE"), ("LTK-SA1", "LTK-PAGE0"))])
def test_ltk_s_pages(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, *tokens)
    for x in held:
        assert outcome(out, x) == "held", (x, out)
    for x in failed:
        assert outcome(out, x) == "FAILED", (x, out)


@pytest.mark.parametrize("stage", FILL_STAGES)
@pytest.mark.parametrize("token", ["sa0=0x00000003", "sa1=0x04000010", "sa2=0x01061a70"])
def test_sa_fails_on_another_word(tmp_path, stage, token):
    m = STAGES[stage]
    if m == "LTK" and token == "sa1=0x04000010":
        token = "sa1=0x005d1000"
    out = run(tmp_path, stage, token)
    assert outcome(out, f"{m}-SA") == "FAILED" and pred(out, f"{m}-SA").endswith(": FAILED")


@pytest.mark.parametrize("stage", of(*make.LANDS))
def test_e12_failing_is_a_note_and_the_outcomes_still_score(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "sa12=0x4b1f374b")
    assert outcome(out, f"{m}-E12") == "FAILED" and pred(out, f"{m}-E12").endswith(": FAILED")
    assert f"NOTE {stage}: {m}-E12 failed: post sa12 is not V0, so the row's C-E0 column " \
           "cannot tell" in out
    assert "RULE: CANNOT TELL" not in rule(out, stage)
    held = (FHELD.get(m) or PHELD[m])
    assert all(outcome(out, x) == "held" for x in held if not x.endswith("-E12")), out


@pytest.mark.parametrize("stage", of("LFKP"))
@pytest.mark.parametrize("tokens,state", [(("padlow",), "FAILED"), (("pad=829",), "FAILED"),
                                          (("pad=830",), "PASS"), (("dkgone",), "cannot tell")])
def test_pad_reads_the_begin_n0_and_is_a_note(tmp_path, stage, tokens, state):
    out = run(tmp_path, stage, *tokens)
    assert control(out, stage, "PAD") == state, out
    assert "control PAD" not in rule(out, stage), rule(out, stage)
    assert ("NOTE lfkp: PAD " in out) == (state != "PASS")
    if state != "PASS":
        assert "LFKP's C-K column cannot tell" in out
    if tokens != ("dkgone",):
        assert "RULE: CANNOT TELL" not in rule(out, stage)
        assert outcome(out, "LFKP-M1") == "held"


@pytest.mark.parametrize("stage", FILL_STAGES)
def test_serve(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "serve")
    assert outcome(out, f"{m}-SERVE") == "held" and outcome(out, f"{m}-PAGE0") == "FAILED"
    assert "no fault and job 2 done" in out


@pytest.mark.parametrize("stage", FILL_STAGES)
@pytest.mark.parametrize("token", ["noplant", "wfail"])
def test_sa_needs_the_plant(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    for x in score.NEEDS_PLANT[STAGES[stage]]:
        assert "cannot tell (W-SA1" in pred(out, x), pred(out, x)
    for x in names(stage):
        if x not in score.NEEDS_PLANT[STAGES[stage]]:
            assert "W-SA1" not in pred(out, x), pred(out, x)
    assert control(out, stage, "PLANT") == ("FAILED" if token == "wfail" else "cannot tell")
    assert "RULE: CANNOT TELL" not in rule(out, stage)


@pytest.mark.parametrize("stage", FILL_STAGES)
@pytest.mark.parametrize("token", ["drmark", "drretry", "drbad", "drgone"])
def test_dr_fails_when_the_declared_draws_did_not_run_exact_at_try_1(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert control(out, stage, "DR") == "FAILED", out
    assert f"DR {make.row_name(stage)} (printed): " in out
    assert "control DR FAILED" in rule(out, stage) and "RULE: CANNOT TELL" in rule(out, stage)
    assert all("cannot tell" in ln for ln in out.splitlines()
               if ln.startswith("PREDICTION ") and not ln.endswith("printed")), out


@pytest.mark.parametrize("stage", FILL_STAGES)
@pytest.mark.parametrize("token", ["dkbad", "dkgone"])
def test_dk_failing_or_unread_makes_the_list_outcomes_cannot_tell_only(tmp_path, stage, token):
    out = run(tmp_path, stage, token)
    assert control(out, stage, "DK") == ("FAILED" if token == "dkbad" else "cannot tell"), out
    assert f"DK {make.row_name(stage)} (printed): control DK " in out
    needs = score.NEEDS_DK[STAGES[stage]]
    for x in needs:
        assert "cannot tell (DK " in pred(out, x), pred(out, x)
    assert all("DK" not in pred(out, x) for x in names(stage) if x not in needs), out
    assert "RULE: CANNOT TELL" not in rule(out, stage), rule(out, stage)


@pytest.mark.parametrize("stage", FILL_STAGES)
def test_dk_prints_the_counts_and_h_kc_s_words(tmp_path, stage):
    out = run(tmp_path, stage)
    n = make.row_name(stage)
    assert f"HKC {n} (printed, never scored): begin draws {make.DRAWS[stage]} (K from 1): " in out


def test_the_cannot_tell_sets_are_the_design_s():
    assert score.NEEDS_PLANT == {"LFK": ("LFK-SA",), "LTK": ("LTK-SA",), "LFK2": ("LFK2-SA",),
                                 "LFKP": ("LFKP-SA",)}
    assert score.NEEDS_DK["LFK"] == ("LFK-SA", "LFK-PAGE0", "LFK-M1")
    assert score.NEEDS_DK["LTK"] == ("LTK-SA", "LTK-PAGE0", "LTK-SA1", "LTK-PAST")
    assert score.NEEDS_WRITE["R"] == ("R-LOW", "R-SA0", "R-OTHER", "R-SERVE", "R-SUM")
    assert score.NEEDS_WRITE["P"] == ("P-UNMAP", "P-MAPPED", "P-OTHER", "P-SUM")


# ---- the design's fixtures (§11.5): kept stages replayed whole -----------------------------------
def test_the_round_46_fixtures_are_the_kept_bytes():
    """Each fixture file under tests/fixtures/ (round 46's n1 lff2 and wb, n4 q2 and we) is the
    kept file: its unpacked bytes' sha256 and size are its kept raw.sha256 line (kernel.log, which
    the runner writes after that list, and the stage logs are byte copies without a line)."""
    import gzip
    import hashlib
    n = 0
    for rel in attempt.FIXTURES:
        if rel.endswith("raw.sha256") or rel.count("/") == 1:     # the stage logs: no raw line
            continue
        d, f = os.path.split(rel)
        raw = open(os.path.join(KP, "tests/fixtures", d, "raw.sha256")).read().split("\n")
        want = {ln.split()[0]: (int(ln.split()[1]), ln.split()[2]) for ln in raw if ln.strip()}
        b = open(os.path.join(KP, "tests/fixtures", rel), "rb").read()
        b = gzip.decompress(b) if f.endswith(".gz") else b
        name = f[:-3] if f.endswith(".gz") else f
        if name == "kernel.log":                # written after the raw list (not in it)
            continue
        assert want[name] == (len(b), hashlib.sha256(b).hexdigest()), rel
        n += 1
    assert n == 25


@pytest.mark.parametrize("stage", of("LFK", "LFK2", "LFKP"))
def test_n1_lff2_scores_lfk_m1_held_and_page0_failed(tmp_path, stage):
    m = STAGES[stage]
    out = replay(tmp_path, stage, "n1lff2")
    assert outcome(out, f"{m}-M1") == "held" and outcome(out, f"{m}-PAGE0") == "FAILED", out
    assert outcome(out, f"{m}-SA") == "held" and outcome(out, f"{m}-E12") == "held", out
    assert control(out, stage, "SV") == "PASS" and control(out, stage, "PLANT") == "PASS", out
    assert control(out, stage, "DR") == "FAILED"            # fill,fill, not the declared fill
    if m == "LFKP":
        assert control(out, stage, "PAD") == "FAILED"       # KC begin 138
        assert "PAD lfkp1-a: begin N0 138, at least 830 (failed)" in out


@pytest.mark.parametrize("stage", of("LFKP"))
def test_n1_lff2_doctored_to_900_passes_pad(tmp_path, stage):
    out = replay(tmp_path, stage, "n1lff2", "pad900")
    assert control(out, stage, "PAD") == "PASS", out
    assert "PAD lfkp1-a: begin N0 900, at least 830 (ok)" in out


@pytest.mark.parametrize("stage", of("LFK", "LFK2", "LFKP"))
def test_lf2_e1213_scores_page0_held_and_e12_failed(tmp_path, stage):
    m = STAGES[stage]
    out = replay(tmp_path, stage, "lf2")
    assert outcome(out, f"{m}-PAGE0") == "held" and outcome(out, f"{m}-M1") == "FAILED", out
    assert outcome(out, f"{m}-E12") == "FAILED" and outcome(out, f"{m}-SA") == "held", out
    assert control(out, stage, "DR") == "PASS" and control(out, stage, "DK") == "PASS", out
    assert control(out, stage, "SV") == "FAILED"            # round 45's module, not r46's
    assert "RULE: CANNOT TELL (control SV FAILED)" in rule(out, stage)


@pytest.mark.parametrize("stage", of("LTK"))
def test_lt_e1215_scores_ltk_page0_and_sa_held(tmp_path, stage):
    out = replay(tmp_path, stage, "lt")
    assert outcome(out, "LTK-PAGE0") == "held" and outcome(out, "LTK-SA") == "held", out
    assert outcome(out, "LTK-SA1") == "FAILED" and outcome(out, "LTK-PAST") == "FAILED", out
    assert control(out, stage, "DR") == "PASS" and control(out, stage, "DK") == "PASS", out


@pytest.mark.parametrize("stage", of("R", "R2", "P", "P2"))
def test_n4_q2_faultnotin_with_the_sum_pages(tmp_path, stage):
    """n4's q2 faulted at M1 (0x005d100f): P-OTHER's list (Q0, the SUM page) holds it; R-OTHER's
    (M1, 0x04400000, the SUM page) does not; neither SUM holds."""
    m = STAGES[stage]
    out = replay(tmp_path, stage, "n4q2")
    assert outcome(out, f"{m}-OTHER") == ("held" if m in ("P", "P2") else "FAILED"), out
    assert outcome(out, f"{m}-SUM") == "FAILED", out
    assert outcome(out, f"{m}-E12") == "held", out
    assert control(out, stage, "SV") == "PASS"


@pytest.mark.parametrize("stage", of("R", "R2"))
def test_q_e1233_scores_r_low_s_page_rule(tmp_path, stage):
    m = STAGES[stage]
    out = replay(tmp_path, stage, "q")
    assert outcome(out, f"{m}-LOW") == "held" and outcome(out, f"{m}-SUM") == "FAILED", out
    assert outcome(out, f"{m}-WRITE") == "FAILED"           # landq's Q0 in sa0, not 0x04400000


# ---- the page rows: R, P, R2, P2 ------------------------------------------------------------------
PAGE_STAGES = of(*make.PAGES)
PHELD = {"R": ("R-E12", "R-LOW", "R-WRITE"), "R2": ("R2-E12", "R2-LOW", "R2-WRITE"),
         "P": ("P-E12", "P-UNMAP", "P-WRITE"), "P2": ("P2-E12", "P2-UNMAP", "P2-WRITE")}


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
@pytest.mark.parametrize("page,held", [(0x0440000F, "SA0"), (0x3640400F, "SUM"),
                                       (0x0000000F, "OTHER"), (0x005D300F, "OTHER")])
def test_r_s_pages(tmp_path, stage, page, held):
    m = STAGES[stage]
    out = run(tmp_path, stage, f"pg=0x{page:08x}")
    assert outcome(out, f"{m}-{held}") == "held" and outcome(out, f"{m}-LOW") == "FAILED", out
    assert pred(out, f"{m}-{held}").endswith(": printed" if held == "OTHER" else ": FAILED")
    if held == "SUM":
        assert outcome(out, f"{m}-OTHER") == "FAILED"


@pytest.mark.parametrize("stage", of("P", "P2"))
@pytest.mark.parametrize("tokens,held,failed", [
    (("serve",), ("MAPPED",), ("OTHER", "SUM")),
    (("pg=0x005d100f",), ("MAPPED", "OTHER"), ("SUM",)),
    (("pg=0x0000000f",), ("MAPPED", "OTHER"), ("SUM",)),
    (("pg=0x6400800f",), ("MAPPED", "SUM"), ("OTHER",))])
def test_p_s_pages(tmp_path, stage, tokens, held, failed):
    m = STAGES[stage]
    out = run(tmp_path, stage, *tokens)
    for x in held:
        assert outcome(out, f"{m}-{x}") == "held", (x, out)
    for x in failed:
        assert outcome(out, f"{m}-{x}") == "FAILED", (x, out)
    assert outcome(out, f"{m}-UNMAP") == "FAILED"
    assert pred(out, f"{m}-MAPPED").endswith(": FAILED")


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
    assert f"{m}-WRITE not held" not in pred(out, f"{m}-E12")


@pytest.mark.parametrize("stage", PAGE_STAGES)
@pytest.mark.parametrize("token", ["noplant", "wfail", "drmark", "drbad", "dkbad", "dkgone"])
def test_a_page_row_prints_plant_dr_and_dk_and_does_not_score_them(tmp_path, stage, token):
    m = STAGES[stage]
    out = run(tmp_path, stage, token)
    assert "RULE: CANNOT TELL" not in rule(out, stage), rule(out, stage)
    assert outcome(out, PHELD[m][1]) == "held"
    assert pred(out, PHELD[m][1]).endswith(": held"), out
    if token.startswith(("dr", "dk")):
        assert "not scored here" in out, out


# ---- every stage: the controls and SV -----------------------------------------------------------
@pytest.mark.parametrize("stage", list(STAGES))
@pytest.mark.parametrize("token,ctl", [("pgbad", "PG"), ("e0bad", "E0"), ("e0cmd", "E0"),
                                       ("t0stop", "T0"), ("j1bad", "J1")])
def test_each_control_can_fail_and_the_rule_cannot_tell(tmp_path, stage, token, ctl):
    out = run(tmp_path, stage, token)
    assert control(out, stage, ctl) == "FAILED", out
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
