# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer replayed on round 41's KEPT stages (H1's c and x, H2's y, LC2's
lc; pinned) as the tokens edit them (tests/attempt.py): every frozen outcome of the session's
stages held where it must hold and FAILED or cannot tell where it must not, the controls able to
fail (E0 and J2 read in their jobs' records, never on the row-end page), and the RULE and
PREDICTION lines. X's and Y's own gate lines (the fill's BIF fault 0xd0400 at 0x4300f) are what
the FILL outcomes read; LC2's stop (job 2 posted and never served, BIF_FAULT 0x0000000f) is what
LV-EARLY0 reads."""
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


def rule(out, m):
    return next(ln for ln in out.splitlines() if ln.startswith(f"Q128-N3G-{m} RULE: "))


def pred(out, name):
    return next(ln for ln in out.splitlines() if ln.startswith(f"PREDICTION {name}:"))


def test_the_stages_are_the_generator_s():
    assert {s: v[0] for s, v in score.STAGES.items()} == STAGES
    assert {s: (v[1], v[2]) for s, v in score.STAGES.items()} == \
        {s[0]: (s[5], s[7]) for s in make.STAGES[make.STEP]}


# ---- C (G1 c) and S (G2 s): the control on H1's c ---------------------------------------------
@pytest.mark.parametrize("stage", of("C") + of("S"))
def test_the_control_holds_on_h1_s_c(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "c")
    assert outcome(out, "C-SAME") == "held" and outcome(out, "C-GATE") == "held", out
    assert outcome(out, "C-DIFF") == "FAILED" and outcome(out, "C-NOKICK") == "FAILED"
    assert "C-GATE, C-SAME" in rule(out, m)
    assert all(control(out, stage, k) == "PASS" for k in ("PG", "E0", "T0", "B", "J1", "J2")), out


@pytest.mark.parametrize("stage", of("C") + of("S"))
@pytest.mark.parametrize("tokens,held", [(("after2=diff",), "C-DIFF"), (("j2stop",), "C-NOKICK")])
def test_the_control_s_failures(tmp_path, stage, tokens, held):
    out = run(tmp_path, stage, "c", *tokens)
    assert outcome(out, held) == "held" and outcome(out, "C-SAME") != "held"
    assert pred(out, "C-SAME").endswith(": FAILED") or pred(out, "C-SAME").endswith("cannot tell")


@pytest.mark.parametrize("stage", of("C"))
def test_c_prints_r_boot_against_nine_kept_rows(tmp_path, stage):
    """H1's c: its post pa are the nine rows' odd words (pa1 0x00043000 ...), printed only."""
    out = run(tmp_path, stage, "c")
    assert f"RBOOT {make.row_name(stage)} (printed): 8 of 8 odd pa as in nine kept rows" in out
    assert "PREDICTION R-BOOT" not in out


@pytest.mark.parametrize("stage", of("S"))
@pytest.mark.parametrize("tokens,held", [(("pakeep",), "S-KEEP"), ((), "S-BACK"),
                                         (("paother",), "S-OTHER")])
def test_s_reads_pa1(tmp_path, stage, tokens, held):
    out = run(tmp_path, stage, "c", *tokens)
    assert [x for x in ("S-KEEP", "S-BACK", "S-OTHER") if outcome(out, x) == "held"] == [held]
    assert pred(out, "S-KEEP").endswith(": held" if held == "S-KEEP" else ": FAILED")
    assert pred(out, "S-OTHER").endswith(": printed")


# ---- M (G1 m): mark on X's kept stage -----------------------------------------------------------
@pytest.mark.parametrize("stage", of("M"))
def test_m_s_predicted_reading(tmp_path, stage):
    """X's stage with M's markers where H-BLOCK puts them and the fill's fault at M13's page:
    M-PA, M-SA13, M-SA1, M-REBASE and M-FILL held, every predicted failure FAILED; the snap9 fault
    (as X's, before the gate) is the rule's FAULT note."""
    out = run(tmp_path, stage, "marked")
    for x in ("M-PA", "M-SA13", "M-SA1", "M-REBASE", "M-FILL"):
        assert outcome(out, x) == "held", (x, out)
        assert pred(out, x).endswith(": held"), x
    for x in ("M-FILL43", "M-FILLM1", "M-FILLOK", "M-NOKICK"):
        assert outcome(out, x) == "FAILED", (x, out)
        assert pred(out, x).endswith(": held"), x
    assert rule(out, "M").startswith("Q128-N3G-M RULE: M-FILL, M-PA, M-REBASE, M-SA1, M-SA13")
    assert "M-MISS" not in rule(out, "M")
    assert "fault page 0x005d3000 is job 1's post sa13, pa1" in out


@pytest.mark.parametrize("stage", of("M"))
def test_m_s_h_copy_reading_fails_m_sa1(tmp_path, stage):
    """sa1 not M1 (H-COPY): M-SA1 FAILED, M-REBASE still held (after = post)."""
    out = run(tmp_path, stage, "marked", "after2=rebase")
    assert outcome(out, "M-SA1") == "held"
    d = attempt.build(str(tmp_path / "hcopy"), stage, ("marked",))
    import gzip
    import json
    p = os.path.join(d, f"{make.row_name(stage)}.own_res.json.gz")
    page = json.loads(gzip.decompress(open(p, "rb").read()))["page"]
    page[161] = 0x04000010
    open(p, "wb").write(gzip.compress(json.dumps({"page": page}).encode(), mtime=0))
    t = os.path.join(d, f"{make.row_name(stage)}.txt.gz")
    rec = json.loads(gzip.decompress(open(t, "rb").read()))
    rec["records"][1]["slots"]["40"][1] = 0x04000010
    open(t, "wb").write(gzip.compress(json.dumps(rec).encode(), mtime=0))
    r = subprocess.run([sys.executable, "-B", "score/score.py", stage, d], cwd=KP,
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    assert outcome(r.stdout, "M-SA1") == "FAILED" and outcome(r.stdout, "M-REBASE") == "held"
    assert outcome(r.stdout, "M-SA13") == "held"


@pytest.mark.parametrize("stage", of("M"))
@pytest.mark.parametrize("token,held", [("fill43", "M-FILL43"), ("fillm1", "M-FILLM1")])
def test_m_s_other_fault_pages(tmp_path, stage, token, held):
    out = run(tmp_path, stage, token)
    assert outcome(out, held) == "held" and outcome(out, "M-FILL") == "FAILED", out
    assert pred(out, held).endswith(": FAILED")


@pytest.mark.parametrize("stage", of("M"))
def test_m_miss_on_x_s_own_words(tmp_path, stage):
    """X's kept stage as it is: M13 in no word, so M-PA FAILED and the rule says M-MISS."""
    out = run(tmp_path, stage, "x")
    assert outcome(out, "M-PA") == "FAILED" and outcome(out, "M-SA13") == "FAILED"
    assert "M-MISS" in rule(out, "M")


@pytest.mark.parametrize("stage", of("M"))
def test_m_nokick_and_an_exact_gate(tmp_path, stage):
    out = run(tmp_path, stage, "marked", "j2stop")
    assert outcome(out, "M-NOKICK") == "held" and outcome(out, "M-PA") == "held"
    assert outcome(out, "M-SA13") == "cannot tell" and outcome(out, "M-REBASE") == "FAILED"
    assert control(out, stage, "E0") == "PASS" and control(out, stage, "J2") == "FAILED"
    out = run(tmp_path, stage, "marked", "gexact")
    assert outcome(out, "M-FILLOK") == "held" and outcome(out, "M-FILL") == "FAILED"


# ---- Q (G2 q): sb402 on Y's kept stage ----------------------------------------------------------
@pytest.mark.parametrize("stage", of("Q"))
def test_q_s_predicted_reading_on_y(tmp_path, stage):
    """Y's 0x403 stage reads as Q's prediction (rebase, V0/V2 every fourth sa, the fill's fault at
    post sa13's page): Q-REBASE, Q-REP, Q-FILL held, Q-NONE and Q-OTHER not."""
    out = run(tmp_path, stage, "y")
    for x in ("Q-REBASE", "Q-REP", "Q-FILL"):
        assert outcome(out, x) == "held", (x, out)
    assert outcome(out, "Q-NONE") == "FAILED" and outcome(out, "Q-OTHER") == "FAILED"
    assert pred(out, "Q-OTHER").endswith(": printed")
    assert rule(out, "Q").startswith("Q128-N3G-Q RULE: Q-FILL, Q-REBASE, Q-REP")


@pytest.mark.parametrize("stage", of("Q"))
@pytest.mark.parametrize("tokens,held,failed", [(("after2=none", "gexact"), "Q-NONE", "Q-REBASE"),
                                                (("after2=other",), "Q-OTHER", "Q-REBASE"),
                                                (("norep",), None, "Q-REP")])
def test_q_s_other_readings(tmp_path, stage, tokens, held, failed):
    out = run(tmp_path, stage, "y", *tokens)
    if held:
        assert outcome(out, held) == "held", out
    assert outcome(out, failed) == "FAILED", out


@pytest.mark.parametrize("stage", of("Q"))
def test_q_s_fault_at_14_s_page_is_printed_with_cannot_tell(tmp_path, stage):
    out = run(tmp_path, stage, "y", "j1bad", "bif")
    assert "RULE: CANNOT TELL" in rule(out, "Q") and "FAULT: BIF_FAULT 0x00090004" in rule(out, "Q")


# ---- LV (G3 lv): landv -------------------------------------------------------------------------
@pytest.mark.parametrize("stage", of("LV"))
def test_lv_early0_on_lc2_s_stop(tmp_path, stage):
    """LC2's kept stop (job 2 never served, BIF_FAULT 0x0000000f): LV-EARLY0 held, LV-EARLY not;
    LV-REBASE, LV-HEAL and LV-FILL not reached; E0 passes on job 1's record."""
    out = run(tmp_path, stage, "lc2")
    assert outcome(out, "LV-EARLY0") == "held" and outcome(out, "LV-EARLY") == "FAILED", out
    assert outcome(out, "LV-V") == "FAILED"                 # land wrote no V0/V2
    for x in ("LV-REBASE", "LV-HEAL", "LV-FILL"):
        assert pred(out, x).endswith(": not reached (LV-EARLY0)"), x
    assert control(out, stage, "E0") == "PASS"
    assert pred(out, "LV-EARLY0").endswith(": FAILED")
    assert "FAULT: BIF_FAULT is not 0" not in rule(out, "LV")
    out = run(tmp_path, stage, "lc2", "landv")
    assert outcome(out, "LV-V") == "held"


@pytest.mark.parametrize("stage", of("LV"))
def test_lv_early_by_another_fault(tmp_path, stage):
    out = run(tmp_path, stage, "lc2", "kickfault")
    assert outcome(out, "LV-EARLY") == "held" and outcome(out, "LV-EARLY0") == "FAILED", out
    assert pred(out, "LV-REBASE").endswith(": not reached (LV-EARLY)")


@pytest.mark.parametrize("stage", of("LV"))
def test_lv_s_predicted_reading(tmp_path, stage):
    """X's kept stage with LV's job 3 and no fault before the gate: LV-V, LV-REBASE and LV-FILL
    held, LV-EARLY0, LV-EARLY, LV-HEAL and LV-FILLOK FAILED, every prediction held."""
    out = run(tmp_path, stage, "x", "job3", "snap9ok")
    for x in ("LV-V", "LV-REBASE", "LV-FILL"):
        assert outcome(out, x) == "held", (x, out)
    for x in ("LV-EARLY0", "LV-EARLY", "LV-HEAL", "LV-FILLOK"):
        assert outcome(out, x) == "FAILED", (x, out)
    assert all(ln.endswith(": held") for ln in out.splitlines() if ln.startswith("PREDICTION "))
    out = run(tmp_path, stage, "x", "job3", "snap9ok", "heal", "gexact")
    assert outcome(out, "LV-HEAL") == "held" and outcome(out, "LV-FILLOK") == "held"


# ---- every stage: the controls, K5 ------------------------------------------------------------
@pytest.mark.parametrize("stage", list(STAGES))
@pytest.mark.parametrize("token,ctl", [("pgbad", "PG"), ("e0bad", "E0"), ("e0cmd", "E0"),
                                       ("t0stop", "T0"), ("j1bad", "J1")])
def test_each_control_can_fail_and_the_rule_cannot_tell(tmp_path, stage, token, ctl):
    m = STAGES[stage]
    out = run(tmp_path, stage, token)
    assert control(out, stage, ctl) == "FAILED", out
    assert "RULE: CANNOT TELL" in rule(out, m)
    assert all(ln.endswith(": cannot tell") or "not reached" in ln
               for ln in out.splitlines() if ln.startswith("PREDICTION "))


@pytest.mark.parametrize("stage", list(STAGES))
def test_j2_and_b_can_fail_without_the_rule_cannot_tell(tmp_path, stage):
    m = STAGES[stage]
    out = run(tmp_path, stage, "j2bad", "bif")
    assert control(out, stage, "J2") == "FAILED" and control(out, stage, "B") == "FAILED"
    assert "CANNOT TELL" not in rule(out, m)
    assert f"J2 {make.row_name(stage)} (printed): control J2 FAILED" in out


@pytest.mark.parametrize("stage", list(STAGES))
def test_e0_is_read_in_job_1_s_record_with_job_2_posted(tmp_path, stage):
    """Job 2 posted and never served leaves cmd word 6 on the page: E0 reads job 1's record."""
    out = run(tmp_path, stage, "lc2" if STAGES[stage] == "LV" else DEFAULT_BASE[STAGES[stage]],
              "j2stop")
    assert control(out, stage, "E0") == "PASS", out


DEFAULT_BASE = attempt.DEFAULT


@pytest.mark.parametrize("stage", list(STAGES))
def test_k5_s_words_are_printed_per_job_and_never_scored(tmp_path, stage):
    plain = run(tmp_path, stage)
    out = run(tmp_path, stage, "bifrec")
    n = make.row_name(stage)
    assert f"BIF {n} job 1 (printed, K5): pre BIF_INT_STAT 0x00000000 BIF_FAULT 0x00000000" in out
    assert f"BIF {n} job 2 (printed, K5): pre BIF_INT_STAT 0x000d0400 BIF_FAULT 0x0004300f" in out
    strip = [ln for ln in out.splitlines() if not ln.startswith("BIF ")]
    assert strip == [ln for ln in plain.splitlines() if not ln.startswith("BIF ")]
