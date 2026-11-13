# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer replayed on kept records it must hold on and must fail on.

Published kept files (resgx545-data at the pinned commit) under this session's control names:
  tx6   r7-geo's E910 type 4 64 x 32 and E725 type 3 32 x 16 images pass the two controls;
        another row's image (E910's 128 x 8) in the type 4 control's place fails it, and every
        headline is then cannot tell.
  q139b r8-lgeo's 1280 x 720 m2-B3p1 output (E944: 52 wrong tiles) in the place of the 1280 x
        720 baseline fails the control (an exact image is its premise).
The fake laptop's worlds (mock/world.py) through the same scorer: model holds every frozen
hypothesis; rival fails them (and the q139b slot claims, its controls passing); hi (format 5
with the high half first) fails the padding rules and says so in its READING lines; a
soft-failed bridge makes the linear rows cannot tell."""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kept as KD  # noqa: E402

R7G = "render/closing-r7-geo/out/20261112-211113/tx/"
R8Q = "render/closing-r8-lgeo/out/20261113-024441/q139/"


def score(stage, d):
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "score/score.py"), stage, d], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def ctl(lines, name):
    return next(ln for ln in lines if ln.startswith("CONTROL %s:" % name))


TX_CTL = {"tx6-ctl-ty4-64x32": "tx-ty4-64x32", "tx6-ctl-ty3-32x16": "tx-ctl-ty3-32x16"}


def test_tx6_controls_hold_on_kept_images(tmp_path):
    files = {n: {".txt": R7G + k + ".txt.gz"} for n, k in TX_CTL.items()}
    out = score("tx6", KD.from_files("tx6", str(tmp_path), files))
    for n in TX_CTL:
        assert ctl(out, n).endswith(": PASS"), ctl(out, n)


def test_tx6_control_fails_on_another_image(tmp_path):
    files = {"tx6-ctl-ty4-64x32": {".txt": R7G + "tx-ty4-128x8.txt.gz"},
             "tx6-ctl-ty3-32x16": {".txt": R7G + "tx-ctl-ty3-32x16.txt.gz"}}
    out = score("tx6", KD.from_files("tx6", str(tmp_path), files))
    assert ctl(out, "tx6-ctl-ty4-64x32").endswith(": FAILED")
    for s in KD.summary(out, ""):
        assert " held (" not in s and "controls FAILED" in s, s


def test_q139b_control_fails_on_a_residue_image(tmp_path):
    src = R8Q + "q139-res-1280x720-m2-B3p1"
    files = {"q139b-ctl-1280x720": {".txt": src + ".txt.gz", ".tri.param.bin": src + ".tri.param.bin.gz",
                                    ".tri.tadata.bin": src + ".tri.tadata.bin.gz"}}
    out = score("q139b", KD.from_files("q139b", str(tmp_path), files, rc=1))
    c = ctl(out, "q139b-ctl-1280x720")
    assert c.endswith(": FAILED") and "52 wrong tiles" in c, c
    for s in KD.summary(out, ""):
        assert " held (" not in s and "controls FAILED" in s, s


# ---- the fake laptop's worlds through the scorer ---------------------------------------------
def world_lines(tmp_path, stage, world):
    return score(stage, KD.from_world(stage, str(tmp_path / stage), world))


@pytest.mark.parametrize("stage,frozen", [
    ("tx6", ["H-CEIL (ceil(w / 32) blocks a block row) held (7 of 7", "H-DW8 (rows max(8 dwords, w texels) apart) held (2 of 2",
             "RASTERW held (2 of 2"]),
    ("q139b", ["gives every baseline header slot (2 of 2", "every header slot (1 of 1"])])
def test_model_world_holds_the_frozen_hypotheses(tmp_path, stage, frozen):
    out = world_lines(tmp_path, stage, "model")
    assert not [ln for ln in out if ln.startswith("CONTROL") and not ln.endswith(": PASS")]
    s = "\n".join(KD.summary(out, ""))
    for f in frozen:
        assert f in s, (f, s)


def test_rival_world_fails_the_frozen_hypotheses(tmp_path):
    out = world_lines(tmp_path, "tx6", "rival")
    assert "2 held, 5 FAILED" in KD.summary(out, "H-CEIL")[0]
    assert "0 held, 2 FAILED" in KD.summary(out, "H-DW8")[0]
    assert "0 held, 2 FAILED" in KD.summary(out, "24 and 40 wide (soft, bridge held): RASTERW held")[0]
    out = world_lines(tmp_path, "q139b", "rival")
    assert not [ln for ln in out if ln.startswith("CONTROL") and not ln.endswith(": PASS")]
    assert "0 held, 2 FAILED" in KD.summary(out, "baseline header slot")[0]
    assert "0 held, 1 FAILED" in KD.summary(out, "768 x 640 m2-B3p1")[0]


def test_high_half_first_is_a_reading_not_a_pass(tmp_path):
    out = world_lines(tmp_path, "tx6", "hi")
    assert "0 held, 2 FAILED" in KD.summary(out, "H-DW8")[0]
    rd = [ln for ln in out if ln.startswith("READING tx6-ty3-f5-")]
    assert len(rd) == 2 and all("the high half first matches H-DW8" in ln for ln in rd), rd


def test_soft_bridge_voids_the_linear_rows(tmp_path):
    out = world_lines(tmp_path, "tx6", "soft2")
    assert any(ln.startswith("BRIDGE") and ln.endswith(": cannot tell") for ln in out)
    for ln in KD.summary(out, "24 and 40 wide"):
        assert "cannot tell" in ln, ln
