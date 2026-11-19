# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generated files are current (gen/make.py --check, the inputs read at the
frozen commits), every path the generator and the test attempts read is a [freeze] pin, emitsn.s
at the frozen commit stores what the scorer and the hooks read where they read it (no emit, one
entry), and the staged bins/ are the recorded probe's at the frozen data commit."""
import hashlib
import os
import subprocess
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.dont_write_bytecode = True
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", "gen/make.py", "--check"], cwd=KP,
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pins_cover_what_the_generator_and_the_attempts_read(tmp_path):
    import attempt
    import make
    import pins
    make.build()
    make.source_facts()
    attempt.own(str(tmp_path), ("stop",))
    attempt.tim(str(tmp_path), ())
    import test_score_tim
    test_score_tim.e1133_text("c1")
    test_score_tim.e1133_text("01")
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])


def test_emitsn_stores_where_the_scorer_reads():
    import make
    import score
    f = make.source_facts()
    # res+0, slot 1 (M1, the run id, X0), slot 4 (M4, the run id), as byte offsets
    assert f["patches"] == [0, 4 * 0x44, 4 * score.SLOT4]
    assert f["marks"] == [make.M1, make.X0, make.M4]
    assert f["emit"] == 0 and f["pds"] == 0 and f["entries"] == ["@entry 0"]
    assert score.X0_AT == make.X0_AT == 70 and score.SLOT4 == make.SLOT4 == 80


def test_the_staged_bins_are_the_recorded_probe_s():
    import make
    b = make.bins()
    assert sorted(os.listdir(os.path.join(KP, "bins"))) == sorted(b)
    for n, data in b.items():
        assert open(os.path.join(KP, "bins", n), "rb").read() == data, n
    assert hashlib.sha256(b[make.PROG]).hexdigest().startswith("3968221c7f27")


def test_the_recorded_run_stored_tim_where_the_scorer_reads():
    """raw.txt (the recorded run of the same program): every one of the scorer's eight tim reads
    is 0x00abcde0 there, and the input A (+0x000) too."""
    import pins
    import score
    raw = pins.blob("data:pds/timer/pds-timer-tim-host/raw.txt").decode()
    sc = score.scratch(raw)
    assert [sc[o] for o in score.SCRATCH_TIM] == [0x00ABCDE0] * 8 and sc[0] == 0x00ABCDE0
    assert sorted(set(range(0, 0x40, 4)) - set(score.SCRATCH_TIM) - {0}) == [
        o for o in range(4, 0x40, 4) if sc[o] == 0]
