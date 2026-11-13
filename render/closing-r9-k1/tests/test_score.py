# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer on kept records it must hold on and must fail on.

Hardware records (pinned, resgx545-data at session.toml's commit):
- E590's layerless control (b66f1-control-1): as c-off it PASSes (hash 0x99385a04ee01c585, diff
  0); as c-tex's image it FAILs H-TEX (the library's 0xff203040 is no texel: 0 of 3034), which is
  the reading a layer that did not reach the render gives;
Mock-world records (mock/world.py, the hardware's 3034-pixel background):
- the model world holds every control and H-VM on every s1 held-out row, and the s2/s3 gate opens;
- the noread world (no poke of words 3-8 read) refutes H-VM on every s1 held-out row, H-NOREAD
  holds, and the s2/s3 gate stays shut;
- the none world: H-NONE holds at c-rawu and c-rawv, the s1n gate opens, the s1 gate stays shut;
- the mockgeom world (the library mock's 2998-pixel geometry): c-off and c-tex FAIL, every gate
  past s0t shuts;
- a poked row whose dump does not hold the poked word reads cannot tell, never right."""
import gzip
import os
import struct
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, HERE)
import bgl_model as M  # noqa: E402
import kept as KD  # noqa: E402
import kitscore as K  # noqa: E402
import make as G  # noqa: E402
import score as S  # noqa: E402

PY = sys.executable
SC = os.path.join(KP, "score/score.py")
E590 = "isp/bg-object-pokes/dumps/bg-words-f1/b66f1-control-1"


def gate(stage, root):
    return subprocess.run([PY, "-B", SC, "gate", stage, str(root)], capture_output=True,
                          text=True, timeout=600)


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    root = tmp_path_factory.mktemp("model")
    w = KD.world()
    for st in ("s0t", "s0p", "s1", "s4"):
        KD.from_world(st, str(root), ("model",), w)
    return root


def test_e590_control_holds_as_c_off_and_fails_as_c_tex(tmp_path):
    out = gzip.decompress(KD.git_show("data", E590 + ".txt.gz")).decode()
    param = gzip.decompress(KD.git_show("data", E590 + ".param.bin.gz"))
    words = b"rd:18=0x00046400\n"
    d = str(tmp_path / "s0t")
    rows = K.table(KP, "s0t")
    files = {"tri.param.bin": param, "words.1.txt": words}
    KD.write_row(d, "s0t", rows[0], out, 0, files)
    KD.write_row(d, "s0t", rows[1], out, 0, files)        # the layer that never reached it
    KD.write_row(d, "s0t", rows[2], out, 0, files)
    c, _, lines, _ = S.verdicts("s0t", d)
    assert c["c-off"] is True, lines
    assert c["c-tex:tex"] is False and c["c-tex:built"] is False, lines
    assert c["c-noop"] is False, lines
    assert gate("s0p", tmp_path).returncode == 1


def test_model_world_holds(model):
    c0 = S.verdicts("s0t", str(model / "s0t"))[0]
    c1 = S.verdicts("s0p", str(model / "s0p"))[0]
    assert all(v is True for v in {**c0, **c1}.values()), (c0, c1)
    _, rows, lines, ex = S.verdicts("s1", str(model / "s1"))
    assert rows == [True] * 30, lines
    for rv in S.S1_RIVALS:
        assert SK_failed(ex, rv) >= 3, rv
    for st in ("s0p", "s1", "s2", "s3", "s4"):
        assert gate(st, model).returncode == 0, st
    assert gate("s1n", model).returncode == 1


def SK_failed(ex, model):
    return sum(1 for s in ex["tallies"].get(("heldout", model), []) if s is False)


def test_noread_world_refutes_h_vm(tmp_path):
    w = KD.world()
    for st in ("s0t", "s0p", "s1"):
        KD.from_world(st, str(tmp_path), ("noread",), w)
    _, rows, lines, ex = S.verdicts("s1", str(tmp_path / "s1"))
    assert rows == [False] * 30, lines
    assert all(s is True for s in ex["tallies"][("heldout", "H-NOREAD")])
    assert gate("s2", tmp_path).returncode == 1
    assert gate("s3", tmp_path).returncode == 1


def test_none_world_opens_only_s1n(tmp_path):
    w = KD.world()
    for st in ("s0t", "s0p", "s1n"):
        KD.from_world(st, str(tmp_path), ("none",), w)
    c = S.verdicts("s0t", str(tmp_path / "s0t"))[0]
    assert c["c-tex:built"] is True and c["c-tex:tex"] is False
    ex = S.verdicts("s0p", str(tmp_path / "s0p"))[3]
    assert ex["c-rawu"]["H-NONE"] is True and ex["c-rawv"]["H-NONE"] is True
    assert ex["c-rawu"]["H-ITER"] is False
    assert gate("s1n", tmp_path).returncode == 0
    assert gate("s1", tmp_path).returncode == 1
    _, rows, lines, _ = S.verdicts("s1n", str(tmp_path / "s1n"))
    assert rows == [True] * 6, lines


def test_mockgeom_world_fails_the_controls(tmp_path):
    w = KD.world()
    KD.from_world("s0t", str(tmp_path), ("mockgeom",), w)
    c = S.verdicts("s0t", str(tmp_path / "s0t"))[0]
    assert c["c-off"] is False and c["c-tex:tex"] is not True, c
    for st in ("s0p", "s1n", "s1", "s4"):
        assert gate(st, tmp_path).returncode == 1, st


def test_a_poke_that_did_not_reach_the_object_is_cannot_tell(tmp_path):
    w = KD.world()
    d = str(tmp_path / "s1")
    for r in K.table(KP, "s1")[:3]:
        rc, out, files = KD.answer(w, r, ("model",), str(tmp_path / r["name"]))
        p = bytearray(files["tri.param.bin"])
        for wd in S.pokes_of(r):
            struct.pack_into("<I", p, M.OBJ_OFF + 4 * wd, M.CTRL[wd])     # the kernel's word
        files["tri.param.bin"] = bytes(p)
        KD.write_row(d, "s1", r, out, rc, files)
    _, _, lines, ex = S.verdicts("s1", d)
    assert all(s is None for s in ex["tallies"][("fit", "H-VM")]), lines
    names = [r["name"] for r in K.table(KP, "s1")[:3]]
    assert all("read back NO" in ln for ln in lines if ln.split(" ")[1:2] and ln.split(" ")[1] in names)
    assert sum(1 for ln in lines if "read back NO" in ln) == 3


def test_score_cli_prints_a_summary(model):
    r = subprocess.run([PY, "-B", SC, "s1", str(model / "s1"), str(model)], capture_output=True,
                       text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    assert "SUMMARY: s1: H-VM + H-AFF" in r.stdout and "(30 of 30 rows decided)" in r.stdout
