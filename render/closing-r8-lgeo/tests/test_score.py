# SPDX-License-Identifier: MIT
"""tests/test_score.py: the frozen scorer replayed on kept records it must hold on and must fail on.

Published kept files (resgx545-data at the pinned commit) under this session's control names:
  tx  r7-geo's E725/E910/E911 images pass each tx control; another row's image in a control's
      place fails it.
  zs2 r7-geo's E681, E683 and -0.5 x sweep outputs pass the five controls; a swapped one fails.
  q139 r7-rp's 256 x 256 and 640 x 480 baselines pass (one header a tile, R7-BLK's slots) and its
      stride 4 passes its control; r7-rp's stride 24 output in the place of held-out stride 20 is
      a FAILED row for every order (its wrong set is another), never held or cannot tell.
The fake laptop's worlds (mock/world.py) through the same scorer: model holds every frozen
hypothesis; rival fails them; bandy holds H-BAND and H-YAXIS and fails H-GEOM; bandout fails
H-BAND; a soft-failed bridge makes the linear rows cannot tell."""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kept as KD  # noqa: E402

R7G = "render/closing-r7-geo/out/20261112-211113"
R7R = "render/closing-r7-rp/out/20261112-205431/q139"


def score(stage, d):
    r = subprocess.run([sys.executable, os.path.join(KP, "score/score.py"), stage, d], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def ctl(lines, name):
    return next(ln for ln in lines if ln.startswith("CONTROL %s:" % name))


TX_CTL = {"tx3": {"tx3-ctl-ty3-32x16": "tx-ctl-ty3-32x16", "tx3-ctl-ty3-4x16": "tx-ty3-4x16", "tx3-ctl-ty1-4x16": "tx-ty1-4x16"},
          "tx4": {"tx4-ctl-ty4-64x32": "tx-ty4-64x32", "tx4-ctl-ty4-4x16": "tx-ty4-4x16"},
          "tx5": {"tx5-ctl-8x8": "tx-ty5-8x8", "tx5-ctl-16x16": "tx-ty5-16x16", "tx5-ctl-16x16-zero": "tx-ty5-16x16-zero"}}


@pytest.mark.parametrize("stage", sorted(TX_CTL))
def test_tx_controls_hold_on_kept_images(tmp_path, stage):
    files = {n: {".txt": "%s/tx/%s.txt.gz" % (R7G, k)} for n, k in TX_CTL[stage].items()}
    out = score(stage, KD.from_files(stage, str(tmp_path), files))
    for n in TX_CTL[stage]:
        assert ctl(out, n).endswith(": PASS"), ctl(out, n)


@pytest.mark.parametrize("stage", sorted(TX_CTL))
def test_tx_controls_fail_on_another_image(tmp_path, stage):
    names = sorted(TX_CTL[stage])
    other = {"tx3": "tx-ty3-64x8", "tx4": "tx-ty4-128x8", "tx5": "tx-ty5-16x16-ones"}[stage]
    files = {names[0]: {".txt": "%s/tx/%s.txt.gz" % (R7G, other)}}
    out = score(stage, KD.from_files(stage, str(tmp_path), files))
    assert ctl(out, names[0]).endswith(": FAILED"), ctl(out, names[0])
    assert all("cannot tell" in s or "is not supported" in s or "controls" in s for s in KD.summary(out, ""))


ZS_CTL = {"zs2-ctl-e681": "zs-ctl-e681-1400606", "zs2-ctl-e683": "zs-ctl-e683-1401234", "zs2-ctl-m0.5-x-dm1": "zs-m0.5-x--1",
          "zs2-ctl-m0.5-x-d0": "zs-m0.5-x-+0", "zs2-ctl-m0.5-x-dp1": "zs-m0.5-x-+1"}


def test_zs2_controls_hold_on_kept_outputs(tmp_path):
    files = {n: {".txt": "%s/zs/%s.txt.gz" % (R7G, k)} for n, k in ZS_CTL.items()}
    out = score("zs2", KD.from_files("zs2", str(tmp_path), files))
    for n in ZS_CTL:
        assert ctl(out, n).endswith(": PASS"), ctl(out, n)


def test_zs2_control_fails_on_a_swapped_output(tmp_path):
    files = {"zs2-ctl-m0.5-x-dp1": {".txt": "%s/zs/zs-m0.5-x--1.txt.gz" % R7G}}
    out = score("zs2", KD.from_files("zs2", str(tmp_path), files))
    assert ctl(out, "zs2-ctl-m0.5-x-dp1").endswith(": FAILED")


def q139_files(name, src):
    return {name: {".txt": "%s/%s.txt.gz" % (R7R, src), ".tri.param.bin": "%s/%s.tri.param.bin.gz" % (R7R, src),
                   ".tri.tadata.bin": "%s/%s.tri.tadata.bin.gz" % (R7R, src)}}


def test_q139_controls_hold_and_a_wrong_row_fails(tmp_path):
    files = {}
    files.update(q139_files("q139-ctl-256x256", "q139-c-256x256-ctl"))
    files.update(q139_files("q139-ctl-640x480", "q139-c-640x480-ctl"))
    files.update(q139_files("q139-ctl-256x256-stride-4", "q139-h-256x256-stride-4"))
    files.update(q139_files("q139-h-256x256-stride-20", "q139-h-256x256-stride-24"))
    out = score("q139", KD.from_files("q139", str(tmp_path), files, rc=1))
    for n in ("q139-ctl-256x256", "q139-ctl-640x480", "q139-ctl-256x256-stride-4"):
        assert ctl(out, n).endswith(": PASS"), ctl(out, n)
    row = next(ln for ln in out if ln.startswith("ROW q139-h-256x256-stride-20 "))
    assert "blkrow no (wrong differs" in row and "raster no" in row, row
    head = KD.summary(out, "write order")[0]
    assert "0 held, 1 FAILED" in head, head


# ---- the fake laptop's worlds through the scorer ---------------------------------------------
def world_lines(tmp_path, stage, world):
    return score(stage, KD.from_world(stage, str(tmp_path / stage), world))


@pytest.mark.parametrize("stage,frozen", [
    ("tx3", ["H-MIN8 (rows max(8, w) dwords apart) held (5 of 5", "RASTERW held (2 of 2"]),
    ("tx4", ["H-BLKROW (32 x 32 blocks row by row) held (18 of 18", "RASTERW held (2 of 2"]),
    ("tx5", ["H-DW8 (bit 0 of dword floor(t / 8)) held (13 of 13", "H-DW8 = H-DW4B1 held (8 of 8"]),
    ("zs2", ["held (8 of 8", "the step table held (24 of 24", "(70 of 70", "(90 of 90"]),
    ("q139", ["every header slot (11 of 11"])])
def test_model_world_holds_the_frozen_hypotheses(tmp_path, stage, frozen):
    out = world_lines(tmp_path, stage, "model")
    assert not [ln for ln in out if ln.startswith("CONTROL") and not ln.endswith(": PASS")]
    s = "\n".join(KD.summary(out, ""))
    for f in frozen:
        assert f in s, (f, s)


@pytest.mark.parametrize("stage,key,failed", [
    ("tx3", "type 3 below 8 wide", "controls FAILED: tx3-ctl-ty3-32x16: FAILED"),
    ("tx4", "H-BLKROW", "9 held, 9 FAILED"), ("tx5", "H-DW8 (bit 0", "0 held, 13 FAILED"),
    ("zs2", "other grid points: ", "controls FAILED: zs2-ctl-e683: FAILED"),
    ("q139", "held-out strides", "controls FAILED: q139-ctl-256x256-stride-4: FAILED")])
def test_rival_world_fails_the_frozen_hypothesis_or_its_controls(tmp_path, stage, key, failed):
    """The rival world's images: the kept-image controls fail where the rival changes them (the
    controls can fail), else the frozen hypothesis is FAILED row by row."""
    out = world_lines(tmp_path, stage, "rival")
    head = KD.summary(out, key)[0]
    assert failed in head, head
    assert " held (" not in head, head


def test_band_worlds(tmp_path):
    out = world_lines(tmp_path, "zs2", "bandy")
    s = "\n".join(KD.summary(out, ""))
    assert "H-BAND: the image differs from HA's only within 6.4e-4 pixel" in s and "(90 of 90" in s, s
    assert "H-YAXIS (on target y sweeps only) held (" in s, s
    assert KD.summary(out, "H-GEOM")[0].count("FAILED"), s
    out = world_lines(tmp_path / "o", "zs2", "bandout")
    band = KD.summary(out, "H-BAND")[0]
    assert "is not supported" in band, band


def test_soft_bridge_voids_the_linear_rows(tmp_path):
    out = world_lines(tmp_path, "tx4", "soft2")
    assert any(ln.startswith("BRIDGE") and ln.endswith(": cannot tell") for ln in out)
    for ln in KD.summary(out, "24 and 40 wide"):
        assert "cannot tell" in ln, ln
