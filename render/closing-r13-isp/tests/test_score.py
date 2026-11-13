# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on,
and on the mock's worlds.

q201: E606's kept I1 case 1016 (coordinate set 0 iterating the clip x under 0x88, 128 x 128) reads
s = 1/2 at every drawn pixel and not 6/16; E1010's kept w0-te60-64x64-x and -y (source 0 under
byte 0 = 0x26) read 6/16 and 2/16, not 1/2; E1010's -x image in the 0x26 src0 control's place
FAILED (its coverage is the whole target, not this triangle). Worlds: model H-SAMPLE0 held on
every held-out row, the rivals FAILED; split H-SPLIT held, H-SAMPLE0 FAILED; centre: the 0x26
source-0 controls FAILED, no headline.
q261: E979's kept far-ctl and far-x24p as the two controls PASS; far-x23p in far-x24p's place
FAILED. Worlds: model (G 18, a 20, g 16) H-CLIP held, G's set contains 18, H-REL held and H-ABS
not; abs (h 82) H-ABS held, H-REL not; exact: far-x24p's control FAILED, no headline.
far: model H-CLIP held, H-CULL, H-SAT and H-WRAP FAILED."""
import gzip
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("gen", "score", "tests", "kit"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import kept  # noqa: E402
import score as SC  # noqa: E402
from fractions import Fraction as F  # noqa: E402

R9X = "render/closing-r9-x/out/20261113-081821/far/"
WIN0 = "render/closing-r10-x/out/20261113-101116/win0/"


def line(lines, start):
    return [ln for ln in lines if ln.startswith(start)][0]


def summ(lines, key):
    return kept.summary(lines, key)[0]


# ---- q201 ----------------------------------------------------------------------------------------
def test_offsets_on_e606_coordinate_set():
    text = kept.data("isp/arith-1138/main/I1/1016.txt.gz").decode()
    assert "tri 128x128 (2 coordinates)" in text
    px = SC.pixels(text, 128 * 128)
    offs = SC.offsets(px, 128, "cset", "x")
    assert len(offs) > 1000
    assert SC.held_at(offs, F(1, 2)) is True
    assert SC.held_at(offs, F(6, 16)) is False


def test_offsets_on_e1010_position_source():
    for comp, want in (("x", F(6, 16)), ("y", F(2, 16))):
        px = SC.pixels(kept.data(WIN0 + "w0-te60-64x64-%s.txt.gz" % comp).decode(), 4096)
        offs = SC.offsets(px, 64, "src0", comp)
        assert len(offs) == 4096
        assert SC.held_at(offs, want) is True
        assert SC.held_at(offs, F(1, 2)) is False


def test_q201_control_fails_on_another_image(tmp_path):
    t = kept.data(WIN0 + "w0-te60-64x64-x.txt.gz").decode()
    out = kept.score("q201", kept.from_text("q201", str(tmp_path / "c"), {"q201-26-src0-x": t}))
    assert line(out, "CONTROL q201-26-src0-x").endswith("FAILED")
    assert "controls FAILED" in summ(out, "H-SAMPLE0")


def test_q201_worlds(tmp_path):
    out = kept.score("q201", kept.from_world("q201", str(tmp_path / "m"), "model"))
    assert all(ln.endswith("PASS") for ln in out if ln.startswith("CONTROL"))
    assert "(18 of 18 rows decided)" in summ(out, "H-SAMPLE0")
    for m in ("H-CENTRE", "H-SWAP", "H-SPLIT"):
        assert "is not supported" in summ(out, m + ":")
    assert "(18 of 18 rows decided)" in summ(out, "E1018")
    out = kept.score("q201", kept.from_world("q201", str(tmp_path / "s"), "split"))
    assert "(18 of 18 rows decided)" in summ(out, "H-SPLIT")
    assert "is not supported" in summ(out, "H-SAMPLE0")
    out = kept.score("q201", kept.from_world("q201", str(tmp_path / "c"), "centre"))
    assert line(out, "CONTROL q201-26-src0-x").endswith("FAILED")
    assert "controls FAILED" in summ(out, "H-CENTRE")


# ---- q261 ----------------------------------------------------------------------------------------
def test_q261_controls_on_e979(tmp_path):
    d = kept.from_files("q261", str(tmp_path / "a"), {"q261-ctl-far21": {".txt": R9X + "far-ctl.txt.gz"},
                                                       "q261-ctl-x24p": {".txt": R9X + "far-x24p.txt.gz"}})
    out = kept.score("q261", d)
    assert line(out, "CONTROL q261-ctl-far21").endswith("PASS")
    ln = line(out, "CONTROL q261-ctl-x24p")
    assert ln.endswith("PASS") and "G=16, G=17, G=18, G=19, G=20, G=21, G=22" in ln
    d = kept.from_files("q261", str(tmp_path / "b"), {"q261-ctl-x24p": {".txt": R9X + "far-x23p.txt.gz"}})
    out = kept.score("q261", d)
    assert line(out, "CONTROL q261-ctl-x24p").endswith("FAILED")
    assert "controls FAILED" in summ(out, "H-CLIP:")


def test_q261_worlds(tmp_path):
    out = kept.score("q261", kept.from_world("q261", str(tmp_path / "m"), "model"))
    assert all(ln.endswith("PASS") for ln in out if ln.startswith("CONTROL"))
    assert "(14 of 14 rows decided)" in summ(out, "H-CLIP:")
    assert 18 in eval(line(out, "READING q261 family G:").split(": ")[1].split(" over")[0])
    assert 20 in eval(line(out, "READING q261 family a:").split(": ")[1].split(" over")[0])
    assert 16 in eval(line(out, "READING q261 family g:").split(": ")[1].split(" over")[0])
    assert "rows decided" in summ(out, "H-REL") and "is not supported" in summ(out, "H-ABS")
    assert "(1 of 1 rows decided)" in summ(out, "H-CLIP-ONE")
    out = kept.score("q261", kept.from_world("q261", str(tmp_path / "a"), "abs"))
    assert "rows decided" in summ(out, "H-ABS") and "is not supported" in summ(out, "H-REL")
    out = kept.score("q261", kept.from_world("q261", str(tmp_path / "e"), "exact"))
    assert line(out, "CONTROL q261-ctl-x24p").endswith("FAILED")
    assert "controls FAILED" in summ(out, "H-EXACT")


def test_far_worlds(tmp_path):
    out = kept.score("far", kept.from_world("far", str(tmp_path / "m"), "model"))
    assert line(out, "CONTROL far-ctl").endswith("PASS")
    assert "(7 of 7 rows decided)" in summ(out, "H-CLIP:")
    for m in ("H-CULL", "H-SAT", "H-WRAP"):
        assert "is not supported" in summ(out, m + ":")
    assert "KEPT" not in " ".join(kept.summary(out, ""))
    ln = line(out, "ROW far-x25n")
    assert "KEPT held" in ln
