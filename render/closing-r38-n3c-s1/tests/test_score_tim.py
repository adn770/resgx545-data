# SPDX-License-Identifier: MIT
"""tests/test_score_tim.py: the frozen scorer of stage tim (R2). E1133's kept t1d timelines (a
running count, pinned) with snap9 running read V0-NOT with both controls passing; a fabricated
constant after the change with snap9 0x00abcde0 reads V0-HOLDS; each control can fail; the
pre-declared cannot-tell cases (scratch not 0x00abcde0, another constant, a change that moves on,
snap9 against the timeline, no timeline)."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import attempt  # noqa: E402
import kitscore as K  # noqa: E402
import pins  # noqa: E402
import score  # noqa: E402

E1133 = "data:render/closing-r33-tim2/out/20261116-213803/t1d/t1d-"
TIM = 0x00ABCDE0


def run(tmp_path, tokens=(), rows=None, text=None):
    d = attempt.tim(str(tmp_path), tokens, rows)
    if text is not None:
        import gzip
        with open(os.path.join(d, "th.txt.gz"), "wb") as f:
            f.write(gzip.compress(text.encode(), mtime=0))
    lines, ctl, hyp, rl = score.score_tim(d)
    return lines + rl, ctl, hyp["th"]


def rule(out):
    return next(ln for ln in out if ln.startswith("N3c-R2 RULE: "))


def e1133_text(row):
    """t30's probe lines (the recorded scratch) and E1133's kept timeline of row `row`."""
    t = pins.blob(E1133 + row + ".txt.gz").decode()
    tl = t[t.index("timeline: regs"):]
    return attempt.tim_text([], set()).split("timeline:")[0] + tl


def test_the_outcomes_are_the_design_s():
    names = {m for q in K.predictions(KP, "tim").values() for mv in q.values() for m in mv}
    assert names == {"V0-HOLDS", "V0-NOT", "CTL"}


def test_e1133_s_running_timelines_read_v0_not(tmp_path_factory):
    for row in ("c1", "01"):
        out, ctl, hyp = run(tmp_path_factory.mktemp("e"), ("snap9run",), text=e1133_text(row))
        assert ctl == {"th:ivl": True, "th:pre": True}, (row, ctl)
        assert hyp == {"V0-HOLDS": False, "V0-NOT": True}, (row, hyp)
        assert rule(out) == "N3c-R2 RULE: V0-NOT: a PDS tim is not the host's 0x0acc"


def test_a_constant_after_the_change_reads_v0_holds(tmp_path):
    out, ctl, hyp = run(tmp_path)
    assert ctl == {"th:ivl": True, "th:pre": True} and hyp == {"V0-HOLDS": True, "V0-NOT": False}
    assert rule(out) == "N3c-R2 RULE: V0-HOLDS: the host sees the PDS write (expected)"
    assert "change at 6000900 ns to 0x00abcde0 (0 stored after it)" in out[0]


def test_each_control_can_fail(tmp_path_factory):
    out, ctl, _ = run(tmp_path_factory.mktemp("i"), ("ivl6100",))
    assert ctl["th:ivl"] is False and rule(out).startswith("N3c-R2 RULE: CANNOT TELL")
    out, ctl, _ = run(tmp_path_factory.mktemp("i"), ("ivl2000",))
    assert ctl["th:ivl"] is False
    # the first stored sample already the constant: no running sample before the change
    out, ctl, _ = run(tmp_path_factory.mktemp("p"), rows=[(900, TIM)])
    assert ctl["th:pre"] is False and rule(out).startswith("N3c-R2 RULE: CANNOT TELL")
    out, ctl, _ = run(tmp_path_factory.mktemp("n"), rows=[])
    assert ctl["th:pre"] is None and rule(out).startswith("N3c-R2 RULE: CANNOT TELL")


def test_the_pre_declared_cannot_tell_cases(tmp_path_factory):
    run_rows = attempt.running_rows()
    t = run_rows[-1][0] + 3000
    cases = [
        (("scratchbad",), None),                              # the program did not run
        (("noscratch",), None),
        (("snap9other",), run_rows + [(t, 0x1234)]),          # another constant
        ((), run_rows + [(t, TIM), (t + 3000, 0x1234)]),      # a change that moves on
        ((), run_rows + [(t, TIM), (t + 3000, 0x0105B86C)]),  # running again after it
        (("snap9run",), None),                                # timeline stopped, snap9 running
        ((), run_rows),                                       # timeline running, snap9 stopped
    ]
    for tokens, rows in cases:
        out, _, hyp = run(tmp_path_factory.mktemp("c"), tokens, rows)
        assert rule(out).startswith("N3c-R2 RULE: CANNOT TELL"), (tokens, rule(out))
        assert not any(s is True for s in hyp.values()), (tokens, hyp)
    out, _, _ = run(tmp_path_factory.mktemp("s"), ("scratchbad",))
    assert any(ln.startswith("NOTE: scratch tim") for ln in out)
