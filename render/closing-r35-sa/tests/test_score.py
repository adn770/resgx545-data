# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer on attempts built from mock/world.py (tests/attempt.py).
D2 (rank-round35.md section 1): every hypothesis name frozen in predictions/*.tsv has a world in
which the scorer prints it held on every held-out row and a world in which it prints it FAILED;
a name in no world fails the test. D1: a failed form control (c0/c1 position decode, c2 reader,
stage t's c reader) makes its rows cannot tell, never a verdict. And the row premises: a writer
whose readback, pixel rows or most frequent pixel is wrong is not read; a reader whose dword 0 is
not one of its values (E1139's form) cannot tell."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.dont_write_bytecode = True
import attempt  # noqa: E402
import kitscore as K  # noqa: E402
import score  # noqa: E402

# D2: the world each frozen name holds in, and one it fails in
HELD = {
    "H-FOUR": ("model",), "H-OTHERN": ("othern",), "H-FIXED4": ("fixed",),
    "H-SHIFT": ("model",), "H-VAR": ("var",), "H-UNION": ("model",), "H-ONEJOB": ("model",),
    "H-UNTILWRITE": ("untilwrite",), "H-LASTWRITER": ("model",), "H-LASTJOB": ("lastjob",),
    "H-SPLIT": ("split",), "H-TRI1536": ("tri1536",), "H-RESETCLR": ("resetclr",),
}
FAILS = {
    "H-FOUR": ("othern",), "H-OTHERN": ("model",), "H-FIXED4": ("model",), "H-SHIFT": ("var",),
    "H-VAR": ("model",), "H-UNION": ("fixed",), "H-ONEJOB": ("untilwrite",),
    "H-UNTILWRITE": ("model",), "H-LASTWRITER": ("lastjob",), "H-LASTJOB": ("model",),
    "H-SPLIT": ("model",), "H-TRI1536": ("model",), "H-RESETCLR": ("model",),
}
_CACHE = {}


def run(tmp_path_factory, tokens, edit=None, key=None):
    k = key or tokens
    if k not in _CACHE or edit:
        root = str(tmp_path_factory.mktemp("att"))
        attempt.build(root, tokens=tokens, edit=edit)
        a = score.score_a(os.path.join(root, "a"))
        t = score.score_t(os.path.join(root, "t"))
        out = (a, t, score.rule_q129(*a[1:]), score.rule_q193(*t[1:]))
        if edit:
            return out
        _CACHE[k] = out
    return _CACHE[k]


def frozen_names():
    names = set()
    for st in ("a", "t"):
        for case, q in K.predictions(KP, st).items():
            for mv in q.values():
                names |= set(mv)
    return names - {"H-REF"}


def summary(out, name):
    (la, *_), (lt, *_), _, _ = out
    return next(ln for ln in la + lt if ln.startswith(("SUMMARY: a: " + name + ": ",
                                                        "SUMMARY: t: " + name + ": ")))


def test_every_frozen_name_has_a_world_both_ways():
    names = frozen_names()
    assert names == set(HELD) == set(FAILS), names ^ set(HELD)


def test_d2_each_name_held_and_failed(tmp_path_factory):
    for name in sorted(frozen_names()):
        s = summary(run(tmp_path_factory, HELD[name]), name)
        assert re.search(r"\((\d+) of \1 rows decided\)$", s), (name, s)
        s = summary(run(tmp_path_factory, FAILS[name]), name)
        assert " is not supported: " in s and " FAILED" in s, (name, s)


def test_rules_decide_on_their_worlds(tmp_path_factory):
    _, _, q129, q193 = run(tmp_path_factory, ("model",))
    assert q129[0].endswith("DECIDED, H-SHIFT, H-UNION, H-FOUR"), q129[0]
    assert q129[1].endswith("DECIDED, H-ONEJOB")
    assert q129[2] == "Q129 RULE: RETIRE-CAPABLE (both clauses decided; R35-3a)"
    assert any(ln.startswith("Q129 WHY (R35-3a) [infer]") and "Q098" in ln for ln in q129)
    assert all(ln.endswith("DECIDED, H-LASTWRITER") for ln in q193[:4] if " t3:" not in ln)
    assert q193[2].endswith("DECIDED, kept")
    assert q193[-1].startswith("Q193 RULE: NARROW: clause (a) decided for t1, t2, t3, t4")
    _, _, q129, _ = run(tmp_path_factory, ("untilwrite",))
    assert q129[1].endswith("DECIDED, H-UNTILWRITE")
    for w, h in (("lastjob", "H-LASTJOB"), ("split", "H-SPLIT")):
        _, _, _, q193 = run(tmp_path_factory, (w,))
        assert q193[0].endswith(f"DECIDED, {h}") and q193[3].endswith(f"DECIDED, {h}"), q193
    _, _, _, q193 = run(tmp_path_factory, ("resetclr",))
    assert q193[2].endswith("DECIDED, cleared (H-RESETCLR)")


def test_positions_that_do_not_fit_narrow(tmp_path_factory):
    for w, why in (("var", "neither H-FIXED4 nor H-SHIFT"), ("othern", "H-FOUR does not hold"),
                   ("fixed", "H-FOUR does not hold")):
        _, _, q129, _ = run(tmp_path_factory, (w,))
        assert why in q129[0] and q129[2] == "Q129 RULE: NARROW: clause (b) decided, clause (a) open"


def test_d1_form_controls_gate_their_rows(tmp_path_factory):
    (la, per, _, _), _, q129, _ = run(tmp_path_factory, ("badcoords",))
    assert "FORM c1a-c: position decode on (y << 16) | x: 2016 of 2048 pixels differ: FAILED" in la
    assert all(v is None for m in ("H-FOUR", "H-SHIFT", "H-FIXED4", "H-UNION", "H-VAR")
               for v in per[m].values())
    assert "not decided (a form control did not pass)" in q129[0]
    # a reader form control that reads another value: every R_5 row cannot tell
    out = run(tmp_path_factory, ("model",), edit=lambda n, t: t.replace(
        "0x5a350305 (2048 of 2048)", "0x5a350305 (2048 of 2048)").replace(
        "5a350305", "5a350306") if n == "c2a-r" else t)
    (la, per, _, _), _, q129, _ = out
    assert any(ln.startswith("FORM c2a-r") and ln.endswith("FAILED") for ln in la)
    assert all(per[m][n] is None for m in score.B_HYP for n in per[m])
    assert q129[1].endswith("not decided")
    # stage t: a U control that reads a split
    out = run(tmp_path_factory, ("model",), edit=lambda n, t: t.replace(
        "7e000114", "7e000214", 1) if n == "ca-u" else t)
    _, (lt, per, _, _), _, q193 = out
    assert all(v is None for m in per for v in per[m].values())
    assert all("not decided" in ln for ln in q193[:4])


def test_row_premises(tmp_path_factory):
    (la, per, _, info), _, q129, _ = run(tmp_path_factory, ("wbad",))
    assert all(v is None for v in info["wr"].values()) and "a W row is not read" in q129[0]
    # pixel rows that disagree with the o0 line: the row is not read
    out = run(tmp_path_factory, ("model",), edit=lambda n, t: re.sub(
        r"(row 0: )c0de0a01", r"\g<1>c0de0a09", t) if n == "h3a-w" else t)
    (la, per, _, info), *_ = out
    assert info["wr"]["h3a-w"] is None and per["H-SHIFT"]["h3a-w"] is None
    # a reader whose dword 0 is not one of its values (E1139): cannot tell
    out = run(tmp_path_factory, ("model",), edit=lambda n, t: re.sub(
        r"scratch \+0x000 0x[0-9a-f]{8}", "scratch +0x000 0x693f0a01", t) if n == "pa-r" else t)
    (la, per, _, _), *_ = out
    assert per["H-ONEJOB"]["pa-r"] is None and per["H-UNTILWRITE"]["pa-r"] is None


def test_premise_and_gate_commands(tmp_path):
    root = attempt.build(str(tmp_path / "p"))
    for st in ("a", "t"):
        d = os.path.join(root, st)
        assert not K.premise(KP, st, d)
    d = os.path.join(root, "a")
    lines = open(os.path.join(d, "readings.tsv")).read().splitlines()
    open(os.path.join(d, "readings.tsv"), "w").write(
        "\n".join(ln for ln in lines if not ln.startswith("c1a-c")) + "\n")
    assert K.premise(KP, "a", d)
    assert score.main(["score.py", "gate", "a", root]) == 0
    assert score.main(["score.py", "q129", root]) == 0
    assert score.main(["score.py", "q193", root]) == 0


def test_a_kept_dir_without_rows(tmp_path):
    for st in ("a", "t"):
        os.makedirs(str(tmp_path / st))
    a = score.score_a(str(tmp_path / "a"))
    t = score.score_t(str(tmp_path / "t"))
    assert score.rule_q129(*a[1:])[2] == "Q129 RULE: NARROW: neither clause decided"
    assert all("not decided" in ln for ln in score.rule_q193(*t[1:])[:4])
