# SPDX-License-Identifier: MIT
"""r13-dpm: the frozen scorer replayed on kept records (the published r8-ldpm run out/20261113-021431,
3072x2048 jobs, laid out as the kit keeps them) and on synthetic readings for the branches no kept
record has. It must hold on:

  controls   the kept PR 0 calibrations (f9-cal-c1208, m6-cal-c1208): nparts 0, no bit 2 clear: PASS
  rows       H-COUNT 6 of 6 (the kept jobs at thr0 0x294, 0x1a0, 0xc0 read 1, 2, 4), H0 8 of 8; the
             plan's strict form FAILS at three of the six (kept clear lines are 0, 0, 1 at 1, 2, 4
             partial renders): the strict clause is not what the kept jobs show [infer, see README]

and must fail on: a PR 0 row that reads a partial render or a bit 2 clear (control FAILED, the
gate shuts every verdict), a row whose knob proof is off (cannot tell), and the ranking rule on
synthetic reads (R-PR ranked first on clears that follow the count; no ranking on a flat pattern;
R-PR not first when a PR 0 row clears)."""
import gzip
import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "kit"), str(KP / "gen")]
import score as SC  # noqa: E402
import kitscore as K  # noqa: E402
import plan as PL  # noqa: E402

R8 = pathlib.Path.home() / "src/resgx545-data/render/closing-r8-ldpm/out/20261113-021431"
CAL = [R8 / "f9/f9-cal-c1208", R8 / "m6/m6-cal-c1208"]
BY_PR = {1: R8 / "m6/m6-c1208-0x294", 2: R8 / "f9/f9-c1208-0x1a0", 4: R8 / "f9/f9-c1208-0xc0"}


def kept(tmp, jobs):
    """A kit kept directory of pr2 holding the rows `jobs` {row: published job prefix}."""
    d = tmp / "pr2"
    d.mkdir(parents=True)
    rows = {r["name"]: r for r in K.table(str(KP), "pr2")}
    lines = []
    for n, src in jobs.items():
        r = rows[n]
        text = gzip.open(str(src) + ".txt.gz").read().decode(errors="replace")
        with gzip.open(d / (n + ".txt.gz"), "wt") as f:
            f.write(text)
        code = 3 if "scene overflowed" in text else 0
        lines.append("\t".join((n, "pr2", r["set"], r["risk"], " ".join(r["knobs"]), r["tool"], r["args"],
                                str(code), "ok", "-", "-", "1")) + "\n")
    (d / "cases.tsv").write_text("\t".join(K.COLUMNS) + "\n" + "".join(lines))
    (d / "void.tsv").write_text("\t".join(K.COLUMNS) + "\n")
    (d / "readings.tsv").write_text("name\tkeys\treading\n")
    return d


def all_rows(over=None):
    jobs, ci = {}, 0
    for r in K.table(str(KP), "pr2"):
        c = PL.pr_of(r)
        if c == 0:
            jobs[r["name"]] = CAL[ci % 2]
            ci += 1
        else:
            jobs[r["name"]] = BY_PR[c]
    jobs.update(over or {})
    return jobs


def test_controls_and_counts_hold_on_the_kept_jobs(tmp_path):
    c, lines, t, ll, rank = SC.verdicts("pr2", kept(tmp_path, all_rows()))
    assert c == {"pr2-c0-1": True, "pr2-c0-2": True}, lines
    assert t["H-COUNT"] == [True] * 8 and t["H0"] == [True] * 8, lines
    assert t["H-PR-STRICT"] == [False] * 2 + [False] * 2 + [False] * 2, lines   # 0, 0, 1 clears vs 1, 2, 4
    assert ll is not None and rank in ("R-PR RANKED FIRST", "NO RANKING")


def test_another_threshold_on_a_pr0_row_has_no_reading_and_gates(tmp_path):
    # the 0x1a0 job on the PR 0 row: the knob proof is off (cannot tell), not a pass
    d = kept(tmp_path / "b", all_rows({"pr2-c0-2": BY_PR[2]}))
    assert SC.readings("pr2", d)["pr2-c0-2"] is None
    c, lines, t, ll, rank = SC.verdicts("pr2", d)
    assert c["pr2-c0-2"] is None and not SC.SK.gate(c).ok
    assert rank.startswith("cannot tell") and all(s is None for s in t["H-COUNT"])


def test_knob_proof_off_is_cannot_tell(tmp_path):
    d = kept(tmp_path, all_rows({"pr2-c1-1": R8 / "m6/m6-c1208-0x292"}))     # the 0x292 job on a 0x294 row
    assert SC.readings("pr2", d)["pr2-c1-1"] is None
    c, lines, t, ll, rank = SC.verdicts("pr2", d)
    assert rank == "cannot tell" and "cannot tell" in " ".join(ln for ln in lines if "pr2-c1-1 [H-COUNT" in ln)


def test_the_decision_line_reports_the_strict_form_and_the_ranking(tmp_path, capsys):
    d = kept(tmp_path, all_rows())
    assert SC.main(["score.py", "pr2", str(d)]) == 0
    out = capsys.readouterr().out
    assert "DECISION: R-PR STRICT FAILS" in out and "ranking:" in out
    assert "MODEL H-COUNT: 8 held" in out


def test_a_control_with_a_clear_line_fails(tmp_path):
    d = kept(tmp_path, all_rows())
    t = gzip.open(d / "pr2-c0-1.txt.gz", "rt").read()
    lines = t.splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith("tl ") and k > 20)
    p = lines[i].split()
    regs = next(ln for ln in lines if ln.startswith("timeline: regs")).split()
    col = regs.index("0x0748") - 2                     # the column of 0x0748 in a `tl` line
    p[2 + col] = "0000000b"
    lines[i] = " ".join(p)
    with gzip.open(d / "pr2-c0-1.txt.gz", "wt") as f:
        f.write("\n".join(lines) + "\n")
    c, out, tl, ll, rank = SC.verdicts("pr2", d)
    assert c["pr2-c0-1"] is False and not SC.SK.gate(c).ok, out
    assert rank.startswith("cannot tell")


# ---- the ranking on synthetic readings ----------------------------------------------------------
def synth(clears, n=400):
    rows = K.table(str(KP), "pr2")
    rds = {r["name"]: dict(clr=clears(PL.pr_of(r), i), n=n) for i, r in enumerate(rows)}
    return rows, rds, K.predictions(str(KP), "pr2")


def test_ranking_follows_the_count():
    rows, rds, preds = synth(lambda c, i: 1 if c == 4 else 0)         # clears only at the largest count
    ll, rank = SC.ranking(rows, rds, preds)
    assert rank == "R-PR RANKED FIRST" and ll["H-R-PR"] < ll["H-CONST"] and ll["H-R-PR"] < ll["H-R-LEN"]


def test_no_ranking_on_a_flat_pattern():
    rows, rds, preds = synth(lambda c, i: 0)                          # no clear anywhere
    ll, rank = SC.ranking(rows, rds, preds)
    assert rank == "NO RANKING" or ll["H-R-PR"] == min(ll.values())
    rows, rds, preds = synth(lambda c, i: 1 if i % 2 == 0 else 0)     # alternating, count-independent
    assert SC.ranking(rows, rds, preds)[1] == "NO RANKING"


def test_a_clear_at_pr0_is_not_ranked_first():
    rows, rds, preds = synth(lambda c, i: 1)                          # a clear in every job, PR 0 too
    ll, rank = SC.ranking(rows, rds, preds)
    assert rank == "NO RANKING" and ll["H-R-PR"] > ll["H-CONST"]


def test_ranking_needs_every_row():
    rows, rds, preds = synth(lambda c, i: 0)
    rds[rows[3]["name"]] = None
    assert SC.ranking(rows, rds, preds) == (None, "cannot tell")
