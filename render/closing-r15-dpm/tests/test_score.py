# SPDX-License-Identifier: MIT
"""r15-dpm: the frozen scorer replayed on kept records (published jobs of the scene, laid out as the
kit keeps them) and on synthetic jobs for the branches no kept record has. Kept jobs are 16-register
timelines (period 7.5 us), so a control's `short` reads 0 on them, which is itself a branch to hold:

  as kept     the PR 0 controls FAIL on `short` (a long period: R-PULSE is not tested) and the gate
              shuts every verdict and the ranking
  made fast   the same jobs with the header's samples x16 (a 0.46 us period, the plan's premise):
              controls PASS; R-PULSE FAILS at every PR > 0 row (kept clears 0, 0, 1, 0 at 1, 4, 4,
              7 partial renders: fewer than the count) and R-RARE-TOTAL holds (1 in 1..8)
and must fail on: a PR 0 row with a clear after the start (control FAILED, gate shut), a row whose
rc proof is off (cannot tell), and hold the strict form on synthetic jobs with a pulse per partial
render, and the ranking rule on synthetic reads."""
import gzip
import pathlib
import re
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "kit"), str(KP / "gen")]
import score as SC  # noqa: E402
import kitscore as K  # noqa: E402
import plan as PL  # noqa: E402

DATA = pathlib.Path.home() / "src/resgx545-data/render"
R8 = DATA / "closing-r8-ldpm/out/20261113-021431"
R13 = DATA / "closing-r13-dpm/out/20261113-212348/pr2"
CAL = [R13 / "pr2-c0-1", R8 / "f9/f9-cal-c1208"]
BY_PR = {1: R8 / "m6/m6-c1208-0x294", 4: R13 / "pr2-c4-2", 7: R8 / "f9/f9-c1208-0x60"}


def kept_text(src):
    return gzip.open(str(src) + ".txt.gz").read().decode(errors="replace")


def fast(text, k=16):
    """The same job with the header's samples times k: a period k times shorter."""
    return re.sub(r"samples (\d+) seconds", lambda m: f"samples {int(m.group(1)) * k} seconds", text, count=1)


def synth(pulses, period=1682):
    """A synthetic job: `pulses` clear lines after the start, the sampler period in ns."""
    end, start = 1_500_000_000, 300_000_000
    rows = [(0, 0x1F)]
    for i in range(pulses):
        rows += [(start + 1_000_000 * (i + 1), 0x1B), (start + 1_000_000 * (i + 1) + 500, 0x1F)]
    return (f"probe p1139-green: tri 3072x2048 (1500 vertices), pixel replaced\n"
            f"timeline: regs 0x0748 samples {end // period} seconds 0 start {start} end {end} rc 0\n"
            + "".join(f"tl {t} {v:08x}\n" for t, v in rows))


def kept(tmp, texts):
    """A kit kept directory of pr4 holding the rows `texts` {row: job text}."""
    d = tmp / "pr4"
    d.mkdir(parents=True)
    rows = {r["name"]: r for r in K.table(str(KP), "pr4")}
    lines = []
    for n, text in texts.items():
        r = rows[n]
        with gzip.open(d / (n + ".txt.gz"), "wt") as f:
            f.write(text)
        code = 0 if PL.pr_of(r) == 0 else 3
        lines.append("\t".join((n, "pr4", r["set"], r["risk"], " ".join(r["knobs"]), r["tool"], r["args"],
                                str(code), "ok", "-", "-", "1")) + "\n")
    (d / "cases.tsv").write_text("\t".join(K.COLUMNS) + "\n" + "".join(lines))
    (d / "void.tsv").write_text("\t".join(K.COLUMNS) + "\n")
    (d / "readings.tsv").write_text("name\tkeys\treading\n")
    return d


def all_rows(f=lambda t: t, over=None):
    texts, ci = {}, 0
    for r in K.table(str(KP), "pr4"):
        c = PL.pr_of(r)
        if c == 0:
            texts[r["name"]] = f(kept_text(CAL[ci % 2]))
            ci += 1
        else:
            texts[r["name"]] = f(kept_text(BY_PR[c]))
    texts.update(over or {})
    return texts


def test_kept_16_register_jobs_fail_the_short_control_and_shut_the_gate(tmp_path):
    c, lines, t, ll, rank = SC.verdicts("pr4", kept(tmp_path, all_rows()))
    assert c == {"pr4-c0-1": False, "pr4-c0-2": False}, lines
    assert all(s is None for s in t["R-PULSE"]) and rank.startswith("cannot tell")
    assert any("short 0" in ln and "FAILED" in ln for ln in lines)


def test_made_fast_the_controls_pass_and_the_strict_form_fails(tmp_path):
    c, lines, t, ll, rank = SC.verdicts("pr4", kept(tmp_path, all_rows(fast)))
    assert c == {"pr4-c0-1": True, "pr4-c0-2": True}, lines
    assert t["R-PULSE"] == [False] * 8, lines
    assert t["R-RARE-TOTAL"] == [True]                      # 1 clear in 1..8
    assert ll is not None and rank in ("R-RARE RANKED FIRST", "NO RANKING")


def test_a_row_with_the_wrong_rc_has_no_reading_and_a_control_gates(tmp_path):
    texts = all_rows(fast)
    d = kept(tmp_path, texts)
    cases = (d / "cases.tsv").read_text().replace("\t0\tok", "\t3\tok", 1)    # the first PR 0 row ends rc 3
    (d / "cases.tsv").write_text(cases)
    assert SC.readings("pr4", d)["pr4-c0-1"] is None
    c, lines, t, ll, rank = SC.verdicts("pr4", d)
    assert c["pr4-c0-1"] is None and not SC.SK.gate(c).ok
    assert rank.startswith("cannot tell") and all(s is None for s in t["R-PULSE"])


def test_a_control_with_a_clear_after_the_start_fails(tmp_path):
    d = kept(tmp_path, all_rows(fast, {"pr4-c0-1": synth(1)}))
    c, lines, t, ll, rank = SC.verdicts("pr4", d)
    assert c["pr4-c0-1"] is False and not SC.SK.gate(c).ok, lines
    assert rank.startswith("cannot tell") and all(s is None for s in t["R-PULSE"])


def test_a_clear_before_the_start_is_not_a_job_event(tmp_path):
    t = synth(0).replace("tl 0 0000001f", "tl 0 0000001b\ntl 9 0000001f")
    c, lines, tl, ll, rank = SC.verdicts("pr4", kept(tmp_path, all_rows(fast, {"pr4-c0-1": t})))
    assert c["pr4-c0-1"] is True, lines


def test_the_strict_form_holds_on_a_pulse_per_partial_render(tmp_path, capsys):
    texts = {r["name"]: synth(PL.pr_of(r)) for r in K.table(str(KP), "pr4")}
    d = kept(tmp_path, texts)
    assert SC.main(["score.py", "pr4", str(d)]) == 0
    out = capsys.readouterr().out
    assert "DECISION: R-PULSE HOLDS" in out and "MODEL R-PULSE: 8 held" in out
    c, lines, t, ll, rank = SC.verdicts("pr4", d)
    assert t["R-RARE-TOTAL"] == [False]                      # 35 pulses are far above the Poisson interval
    assert ll["R-PULSE"] < ll["R-RARE"] and rank == "NO RANKING"


def test_one_pulse_short_of_the_count_fails_the_strict_form(tmp_path, capsys):
    texts = {r["name"]: synth(PL.pr_of(r)) for r in K.table(str(KP), "pr4")}
    texts["pr4-c7-2"] = synth(6)
    d = kept(tmp_path, texts)
    assert SC.main(["score.py", "pr4", str(d)]) == 0
    assert "DECISION: R-PULSE FAILS" in capsys.readouterr().out


def test_the_decision_line_prints_strict_form_and_ranking(tmp_path, capsys):
    d = kept(tmp_path, all_rows(fast))
    assert SC.main(["score.py", "pr4", str(d)]) == 0
    out = capsys.readouterr().out
    assert "DECISION: R-PULSE FAILS" in out and "ranking:" in out and "MODEL log-loss" in out
    assert "READING pr4-c4-1" in out


# ---- the ranking on synthetic readings ----------------------------------------------------------
def rk(clears):
    rows = K.table(str(KP), "pr4")
    rds = {r["name"]: dict(clr=clears(PL.pr_of(r), i), n=10) for i, r in enumerate(rows)}
    return rows, rds, K.predictions(str(KP), "pr4")


def test_no_clears_anywhere_ranks_r_rare_first():
    rows, rds, preds = rk(lambda c, i: 0)
    ll, rank = SC.ranking(rows, rds, preds)
    assert rank == "R-RARE RANKED FIRST" and ll["R-RARE"] < ll["R-CONST"] < ll["R-PULSE"]


def test_a_clear_per_count_row_does_not_rank_r_rare():
    rows, rds, preds = rk(lambda c, i: 1 if c else 0)                 # what R-PULSE says
    ll, rank = SC.ranking(rows, rds, preds)
    assert rank == "NO RANKING" and ll["R-PULSE"] < ll["R-RARE"]


def test_a_clear_in_every_job_is_not_ranked():
    rows, rds, preds = rk(lambda c, i: 1)
    assert SC.ranking(rows, rds, preds)[1] == "NO RANKING"


def test_ranking_needs_every_row():
    rows, rds, preds = rk(lambda c, i: 0)
    rds[rows[3]["name"]] = None
    assert SC.ranking(rows, rds, preds) == (None, "cannot tell")
