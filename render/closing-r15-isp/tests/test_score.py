# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on,
and on the mock's worlds.

zcut: E1045's kept wind-zhi and wind-zlo (their pixel rows and depth lines) in the places of the
two depth controls, the mock's E065 rows in the third: every control PASS; E1045's zlo in zhi's
place FAILED (no headline). Worlds (the truth the fake draws): model H-POLYCLIP held 6 of 6,
H-PIXCUT and H-POLYCLIP-NR FAILED, H-NONE 2 of 2, H-EQUIV FAILED; pixcut and nr each hold their own
form and H-POLYCLIP FAILED (the two are one image); equiv H-EQUIV held, H-NONE FAILED; old (the
library triangle ignores bit 15) the bit 15 control FAILED and no headline for H-EQUIV, H-NONE."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("gen", "score", "tests", "kit"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import kept  # noqa: E402

E1045 = "render/closing-r14-isp/out/20261114-060059/wind/"


def line(lines, start):
    return [ln for ln in lines if ln.startswith(start)][0]


def summ(lines, key):
    return kept.summary(lines, key)[0]


def held(s, n):
    return "(%d of %d rows decided)" % (n, n) in s and "not supported" not in s


def failed(s):
    return "not supported" in s and " 0 held" in s


def world_kept(tmp, world, z_from=("wind-zhi", "wind-zlo")):
    """E1045's kept rows as the two depth controls, every other row from the world"""
    f = lambda p: {".txt": p + ".txt.gz"}  # noqa: E731
    files = {"zcut-ctl-zhi": f(E1045 + z_from[0]), "zcut-ctl-zlo": f(E1045 + z_from[1])}
    d = kept.from_files("zcut", str(tmp), files)
    others = {"zcut-ctl-b15", "zcut-hi1", "zcut-hi2", "zcut-hi3", "zcut-lo1", "zcut-lo2", "zcut-lo3",
              "zcut-b16", "zcut-b17"}
    return kept.from_world("zcut", d, world, only=others, append=True)


def test_controls_pass_on_the_kept_rows_and_fail_on_a_swapped_one(tmp_path):
    out = kept.score("zcut", world_kept(tmp_path / "a", "model"))
    for c in ("zcut-ctl-zhi", "zcut-ctl-zlo", "zcut-ctl-b15"):
        assert line(out, "CONTROL " + c).endswith(": PASS"), out
    out = kept.score("zcut", world_kept(tmp_path / "b", "model", z_from=("wind-zlo", "wind-zlo")))
    assert line(out, "CONTROL zcut-ctl-zhi").endswith(": FAILED")
    assert "controls FAILED" in summ(out, "zcut: H-POLYCLIP:")


def test_model_world_holds_h_polyclip_and_h_none(tmp_path):
    out = kept.score("zcut", world_kept(tmp_path, "model"))
    assert held(summ(out, "zcut: H-POLYCLIP:"), 6), out
    assert failed(summ(out, "zcut: H-PIXCUT:")) and failed(summ(out, "zcut: H-POLYCLIP-NR:"))
    assert held(summ(out, "zcut: H-NONE:"), 2) and failed(summ(out, "zcut: H-EQUIV:"))
    for n in ("zcut-hi1", "zcut-lo2"):
        assert "READING parting pixels" in line(out, "ROW " + n)
    assert "is not the control's" in line(out, "READING zcut-b16")


def test_pixcut_and_nr_worlds(tmp_path):
    for world in ("pixcut", "nr"):
        out = kept.score("zcut", world_kept(tmp_path / world, world))
        assert held(summ(out, "zcut: H-PIXCUT:"), 6) and held(summ(out, "zcut: H-POLYCLIP-NR:"), 6), out
        assert failed(summ(out, "zcut: H-POLYCLIP:"))


def test_equiv_world(tmp_path):
    out = kept.score("zcut", world_kept(tmp_path, "equiv"))
    assert held(summ(out, "zcut: H-EQUIV:"), 2) and failed(summ(out, "zcut: H-NONE:"))
    assert "is the control's" in line(out, "READING zcut-b17")


def test_old_world_fails_the_bit_15_control(tmp_path):
    out = kept.score("zcut", world_kept(tmp_path, "old"))
    assert line(out, "CONTROL zcut-ctl-b15").endswith(": FAILED")
    assert "controls FAILED" in summ(out, "zcut: H-NONE:") and "controls FAILED" in summ(out, "zcut: H-EQUIV:")
    assert held(summ(out, "zcut: H-POLYCLIP:"), 6)          # the depth controls are another gate


def test_a_row_that_did_not_run_cannot_tell(tmp_path):
    d = world_kept(tmp_path, "model")
    os.remove(os.path.join(d, "zcut-hi1.txt"))
    out = kept.score("zcut", d)
    assert "cannot tell" in line(out, "ROW zcut-hi1")
