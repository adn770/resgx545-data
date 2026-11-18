# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer on kept attempts built from mock/world.py
(tests/attempt.py). Every hypothesis frozen in predictions/own.tsv has an attempt where it is
held on every row it is scored on and one where it FAILED; each control can fail and then no
claim is printed; the rule prints each of its outcomes on its own attempt and never RETIRE; V0-V3
come from each row's own snap0, never the hooks' fallback; the post scorer reads its controls."""
import os
import re
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.dont_write_bytecode = True
import attempt  # noqa: E402
import kitscore as K  # noqa: E402
import score  # noqa: E402

HELD = {"H-PA": ("model",), "H-SA": ("sa",), "H-NONE": ("none",)}
FAILS = {"H-PA": ("sa",), "H-SA": ("model",), "H-NONE": ("model",)}


def run(tmp_path, tokens):
    d = attempt.build(str(tmp_path), tokens)
    lines, per, ctl, sets = score.score_own(d)
    return lines + score.headlines(per, ctl, sets) + score.rule_n3(per, ctl, sets), per, ctl


def summary(out, h):
    return next(ln for ln in out if ln.startswith(f"SUMMARY: own: {h}: "))


def rule(out):
    return next(ln for ln in out if ln.startswith("N3 RULE: "))


def test_every_frozen_name_has_an_attempt_both_ways():
    names = set()
    for q in K.predictions(KP, "own").values():
        for mv in q.values():
            names |= set(mv)
    assert names - {"CTL"} == set(HELD) == set(FAILS)


def test_each_name_held_and_failed(tmp_path_factory):
    for h in HELD:
        out, _, _ = run(tmp_path_factory.mktemp("h"), HELD[h])
        s = summary(out, h)
        assert re.search(r"\((\d+) of \1 rows decided\)$", s), (h, s)
        out, _, _ = run(tmp_path_factory.mktemp("f"), FAILS[h])
        s = summary(out, h)
        assert " is not supported: " in s and " FAILED" in s, (h, s)


def test_h_pa_and_h_sa_are_scored_on_the_eight_held_out_rows(tmp_path):
    out, _, _ = run(tmp_path, ("model",))
    assert summary(out, "H-PA").endswith("(8 of 8 rows decided)")


def test_rule_outcomes(tmp_path_factory):
    want = {("model",): "N3 RULE: DECIDED-PA", ("sa",): "N3 RULE: NOT-PA",
            ("none",): "N3 RULE: NONE", ("split",): "N3 RULE: OPEN",
            ("sabad",): "N3 RULE: OPEN", ("sa1bad",): "N3 RULE: OPEN",
            ("pa1bad",): "N3 RULE: OPEN", ("nosnapv",): "N3 RULE: OPEN",
            ("nomark4",): "N3 RULE: OPEN", ("short",): "N3 RULE: OPEN",
            ("movedv",): "N3 RULE: DECIDED-PA"}
    for tokens, head in want.items():
        out, _, _ = run(tmp_path_factory.mktemp("r"), tokens)
        assert rule(out).startswith(head), (tokens, rule(out))
        q = next(ln for ln in out if ln.startswith("Q128 RULE: "))
        assert q.startswith("Q128 RULE: NARROW") and "RETIRE" in q and "never RETIRE" in q


def test_each_control_can_fail(tmp_path_factory):
    for tokens, key in ((("sabad",), "SA"), (("sa1bad",), "SA"), (("pa1bad",), "PA13"),
                        (("nomark4",), "E1")):
        _, _, ctl = run(tmp_path_factory.mktemp("c"), tokens)
        assert ctl[f"h1-a:{key}"] is False, (tokens, ctl)
        out, _, _ = run(tmp_path_factory.mktemp("c"), tokens)
        for h in ("H-PA", "H-SA"):
            assert "FAILED" in summary(out, h) and "rows decided" not in summary(out, h)


def test_a_split_landing_fails_both(tmp_path):
    _, per, _ = run(tmp_path, ("split",))
    assert all(s is False for s in per["H-PA"].values())
    assert all(s is False for s in per["H-SA"].values())


def test_values_come_from_each_rows_snap0_not_the_fallback(tmp_path_factory):
    _, per, ctl = run(tmp_path_factory.mktemp("m"), ("movedv",))
    assert all(per["H-PA"].values()) and all(ctl.values())
    _, per, ctl = run(tmp_path_factory.mktemp("n"), ("nosnapv",))
    assert all(s is None for s in per["H-PA"].values())
    assert all(ctl[k] is None for k in ctl if k.endswith(":SA"))


def test_h_none_reads_the_first_row_only_and_needs_entry_0(tmp_path):
    out, per, ctl = run(tmp_path, ("none",))
    assert list(per["H-NONE"]) == ["e1-a"] and per["H-NONE"]["e1-a"] is True
    assert ctl["e1-a:E0"] is True and ctl["e1-a:E1"] is False


def test_the_scorer_runs_as_the_driver_runs_it(tmp_path):
    d = attempt.build(str(tmp_path), ("model",))
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), "own", d],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "SUMMARY: own: H-PA: " in r.stdout, r.stdout + r.stderr
    assert "N3 RULE: DECIDED-PA" in r.stdout


def test_post_controls(tmp_path):
    d = tmp_path / "post"
    d.mkdir()
    cols = "\t".join(K.COLUMNS)
    rows = [cols] + ["\t".join([n, "post", "control", "safe", "reads:diff", "t30", a, "0", "ok",
                                "-", "-", "1"]) for n, a in (("p1-tri", "tri"),
                                                            ("p2-fill", "fill"))]
    (d / "cases.tsv").write_text("\n".join(rows) + "\n")
    (d / "void.tsv").write_text(cols + "\n")
    import importlib.util
    spec = importlib.util.spec_from_file_location("world", os.path.join(KP, "mock/world.py"))
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    (d / "p1-tri.txt").write_text(w.TRI)
    (d / "p2-fill.txt").write_text(w.FILL)
    lines, c = score.score_post(str(d))
    assert c == {"p1-tri": True, "p2-fill": True} and "exactly" in lines[-1]
    (d / "p1-tri.txt").write_text(w.TRI.replace("diff: 0 of", "diff: 9 of"))
    lines, c = score.score_post(str(d))
    assert c["p1-tri"] is False and "FAILED" in lines[-1]
