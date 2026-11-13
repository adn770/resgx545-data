# SPDX-License-Identifier: MIT
"""r10-dpm: the frozen scorer replayed on kept records (the published render-closing-r9-ldpm run
out/20261113-082650, laid out as the kit keeps them), and on synthetic S_6 reads for the branches
no kept record has. It must hold on:

  controls   r9-ldpm's a0-cal-2048 and a0-cal-2048f (E935 again: both PASS)
  rows       the kept calibration of each target (w-cal-c1604, c1606, c1404, c0802 and m6b-cal-c0809)
             as the target's three replicates: every one is R + 1 or R + 2, so each target is BIAS
             (H-BIAS holds, H-NOISE does not), the decision is BIAS decided

and must fail on: a0-cal-2048f read from another target's calibration (FAILED, the decision cannot
tell), a replicate whose knob proof is off (cannot tell), and the classes and decision rule on
synthetic reads (NOISE, BIAS, NEITHER, MIXED, the span bound and the 4 of 5 bound)."""
import gzip
import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "kit"), str(KP / "gen")]
import score as SC  # noqa: E402
import kitscore as K  # noqa: E402
import plan as PL  # noqa: E402

R9 = pathlib.Path.home() / "src/resgx545-data/render/closing-r9-ldpm/out/20261113-082650"
A0 = {"a0-cal-2048": R9 / "a0/a0-cal-2048", "a0-cal-2048f": R9 / "a0/a0-cal-2048f"}
CAL = {(4096, 1024): R9 / "w/w-cal-c1604", (4096, 1536): R9 / "w/w-cal-c1606", (3584, 1024): R9 / "w/w-cal-c1404",
       (2048, 512): R9 / "w/w-cal-c0802", (2048, 2304): R9 / "m6b/m6b-cal-c0809"}


def kept(tmp, jobs, text_edit=None):
    """A kit kept directory of s6rep holding the rows `jobs` {row: published job prefix}."""
    d = tmp / "s6rep"
    d.mkdir(parents=True)
    rows = {r["name"]: r for r in K.table(str(KP), "s6rep")}
    lines = []
    for n, src in jobs.items():
        r = rows[n]
        text = gzip.open(str(src) + ".txt.gz").read().decode(errors="replace")
        if text_edit and n in text_edit:
            text = text.replace(*text_edit[n])
        with gzip.open(d / (n + ".txt.gz"), "wt") as f:
            f.write(text)
        code = 3 if "scene overflowed" in text else 0
        lines.append("\t".join((n, "s6rep", r["set"], r["risk"], " ".join(r["knobs"]), r["tool"], r["args"],
                                str(code), "ok", "-", "-", "1")) + "\n")
    (d / "cases.tsv").write_text("\t".join(K.COLUMNS) + "\n" + "".join(lines))
    (d / "void.tsv").write_text("\t".join(K.COLUMNS) + "\n")
    (d / "readings.tsv").write_text("name\tkeys\treading\n")
    return d


def replicas(per_target=None):
    jobs = {}
    for k in (1, 2, 3):
        for t, src in CAL.items():
            jobs[f"s6r-{PL.tag(*t)}-{k}"] = (per_target or {}).get(t, src)
    return jobs


def test_a0_pair_holds_on_r9s_jobs(tmp_path):
    c, lines, t, cl = SC.verdicts("s6rep", kept(tmp_path, A0))
    assert c == {"a0-cal-2048": True, "a0-cal-2048f": True}, lines


def test_every_target_is_bias_on_the_kept_calibrations(tmp_path):
    c, lines, t, cl = SC.verdicts("s6rep", kept(tmp_path, dict(A0, **replicas())))
    assert cl == ["BIAS"] * 5, lines
    assert SC.decision(cl) == "BIAS decided"
    assert t["H-BIAS"] == [True] * 5 and t["H-NOISE"] == [False] * 5
    assert all(s is True for s in t["H-BIAS-SAME"]) and all(s is False for s in t["H-REPLAY6"])
    assert all(s is True for s in t["H-REPLAY"]), lines            # need = U, nparts 0


def test_a0_control_fails_on_another_targets_calibration(tmp_path):
    jobs = dict(A0, **{"a0-cal-2048f": CAL[(4096, 1024)]})
    # the 4096x1024 job on the 2048x2048 row: the knob proof holds (0x400), the need does not
    c, lines, t, cl = SC.verdicts("s6rep", kept(tmp_path, dict(jobs, **replicas())))
    assert c["a0-cal-2048f"] is False and not SC.SK.gate(c).ok, lines
    assert all(s is None for s in t["H-BIAS"] + t["H-NOISE"])      # gated: no verdict
    out = [ln for ln in lines if ln.startswith("TARGET")]
    assert len(out) == 5


def test_knob_proof_off_is_cannot_tell(tmp_path):
    job = f"s6r-{PL.tag(4096, 1024)}-2"
    d = kept(tmp_path, dict(A0, **replicas()), text_edit=None)
    rds = SC.readings("s6rep", d)
    assert rds[job] is not None
    d2 = kept(tmp_path / "b", dict(A0, **replicas(per_target={(4096, 1024): R9 / "w/w-c1604-0x9d"})))
    assert SC.readings("s6rep", d2)[job] is None                  # another threshold: the proof is off
    c, lines, t, cl = SC.verdicts("s6rep", d2)
    assert cl[0] == "cannot tell" and SC.decision(cl) == "cannot tell"


# ---- the classes and the decision on synthetic reads -------------------------------------------
def test_classes():
    R = 0x17C
    assert SC.classify([R + 1, R + 2, R + 2], R)[0] == "BIAS"
    assert SC.classify([R, R + 1, R + 2], R)[0] == "NOISE"
    assert SC.classify([R, R, R], R)[0] == "NOISE"                # exact replay: the degenerate noise
    assert SC.classify([R - 1, R, R + 1], R)[0] == "NOISE"
    assert SC.classify([R - 1, R, R + 2], R)[0] == "NEITHER"      # span 3
    assert SC.classify([R + 1, R + 2, R + 3], R)[0] == "NEITHER"  # one above R + 2, none at R
    assert SC.classify([R + 1, R + 1, R + 1], R) == ("BIAS", False, True)
    assert SC.classify([R, R + 2, None], R) == ("cannot tell", None, None)


def test_decision_rule():
    N, B, X = "NOISE", "BIAS", "NEITHER"
    assert SC.decision([N] * 5) == "NOISE decided" and SC.decision([N] * 4 + [B]) == "NOISE decided"
    assert SC.decision([N] * 4 + [X]) == "NOISE decided"
    assert SC.decision([B] * 5) == "BIAS decided" and SC.decision([B] * 4 + [N]) == "BIAS decided"
    assert SC.decision([N, N, N, B, B]) == "MIXED" and SC.decision([N, N, B, B, X]) == "MIXED"
    assert SC.decision([N] * 3 + [X] * 2) == "MIXED"
    assert SC.decision([N] * 4 + ["cannot tell"]) == "cannot tell"
