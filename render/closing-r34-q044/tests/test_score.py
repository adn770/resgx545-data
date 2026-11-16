# SPDX-License-Identifier: MIT
"""tests/test_score.py: the scorer on kept records it must hold on and on synthetic kept
directories it must decide both ways and must refuse to decide. Kept: E385's mode 4 and mode 0
images and E268's mode 0 images as the controls (PASS), one dword changed (FAILED). Synthetic (the
mock's images, mock/world.py): the model world holds every frozen model and the retire rule reads
RETIRE; the alt world fails H-INV25 and H-GE and the rule reads NARROW; a mode 6 that bit 25 leaves
unchanged keeps RETIRE and names the mode; a reference that printed no image makes its rows cannot
tell; a p2 stage that did not run reads NARROW."""
import os
import shutil
import sys

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "gen"), os.path.join(KP, "mock")]
sys.dont_write_bytecode = True
import pins  # noqa: E402
import q044 as Q  # noqa: E402
import score as SC  # noqa: E402
import world as WD  # noqa: E402

COLS = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n"


def out_of(img, case="x"):
    return "".join("probe %s: row %d: %s\n" % (case, y, " ".join("%08x" % v for v in img[64 * y:64 * y + 64]))
                   for y in range(64))


def key(r):
    a = r["args"].split()
    form = "ramp" if "--vtx-coords" in a else "colour"
    return form, int(a[a.index("--sideband") + 1], 16) & 0x3F, \
        int(a[a.index("--cmd") + 1].split("=")[1], 16)


def kept_dir(tmp, stage, image_of, skip=()):
    d = os.path.join(tmp, stage)
    os.makedirs(d, exist_ok=True)
    cases, reads = [COLS], ["name\tstage\treading\n"]
    for r in SC.K.table(KP, stage):
        n = r["name"]
        cases.append("\t".join([n, stage, r["set"], r["risk"], " ".join(r["knobs"]), r["tool"],
                                r["args"], "0", "ok", "", "", "999999"]) + "\n")
        img = None if n in skip else image_of(r)
        with open(os.path.join(d, n + ".txt"), "w") as f:
            f.write("job: ok\n" + ("" if img is None else out_of(img)))
        if r["set"] == "control":
            reads.append(f"{n}\t{stage}\tpixels={0 if img is None else 64}\n")
    for f, t in (("cases.tsv", cases), ("readings.tsv", reads), ("void.tsv", [COLS])):
        with open(os.path.join(d, f), "w") as fh:
            fh.write("".join(t))
    return d


def world_images(world, override=None):
    def f(r):
        k = key(r)
        if override and k in override:
            return override[k]
        return WD.image(*k, world)
    return f


@pytest.fixture
def att(tmp_path):
    return str(tmp_path)


def test_controls_on_kept_records(att):
    k = {("ramp", 4, 0x80): Q.kept(pins.blob, Q.E385 % "mode4", "pbe-reg-0400-alpha-mode4__0"),
         ("ramp", 0, 0x80): Q.kept(pins.blob, Q.E385 % "mode0", "pbe-reg-0400-alpha-mode0__0"),
         ("colour", 0, 0x80): Q.kept(pins.blob, Q.E268, "pbe-reg-0400-modes-0__0")}
    d = kept_dir(att, "s0", world_images("model", k))
    c, _, lines = SC.verdicts("s0", d)
    assert all(v is True for v in c.values()), lines
    bad = dict(k)
    bad[("ramp", 4, 0x80)] = list(k[("ramp", 4, 0x80)])
    bad[("ramp", 4, 0x80)][100] ^= 1
    d = kept_dir(os.path.join(att, "b"), "s0", world_images("model", bad))
    c, _, _ = SC.verdicts("s0", d)
    assert c["s0-m04r-w080"] is False and SC.gate_of("p1", [os.path.join(att, "b")])[0] is False


def run_all(att, world, override=None, stages=SC.STAGES, skip=()):
    for s in stages:
        kept_dir(att, s, world_images(world, override), skip)


def test_model_world_holds_and_retires(att):
    run_all(att, "model")
    for s in SC.STAGES:
        c, per, lines = SC.verdicts(s, os.path.join(att, s))
        assert all(v is True for v in c.values()), (s, lines)
        for m, states in per.items():
            if m.startswith(("H-INV25", "H-GE", "H-THR1", "H-NULL", "H-E031", "H-REPEAT")):
                assert all(x is True for x in states), (s, m, lines)
            if m.startswith(("H-GT", "H-THRN", "H-ACT")):
                assert all(x is False for x in states), (s, m)
    SC._load_gen()
    v, why, notes = SC.retire(att)
    assert v == "RETIRE", why
    assert any(n.startswith("mode 22: xor 0xff000000") and n.endswith("-> Q012") for n in notes)
    assert "mode 14: not run (E031: faults in both runs, nothing stored)" in notes


def test_alt_world_narrows(att):
    run_all(att, "alt")
    _, per, lines = SC.verdicts("p1", os.path.join(att, "p1"))
    assert any(x is False for x in per["H-INV25 (heldout)"])
    assert all(x is True for x in per["H-SUBSET (heldout)"])
    _, per, _ = SC.verdicts("p2", os.path.join(att, "p2"))
    assert all(x is True for x in per["H-GT (heldout)"])
    assert all(x is False for x in per["H-GE (heldout)"])
    SC._load_gen()
    v, why, _ = SC.retire(att)
    assert v == "NARROW" and any("p2-m05-w" in w for w in why)


def test_bit25_none_in_a_mode_still_retires(att):
    ref = WD.image("colour", 6, 0x80, "model")
    run_all(att, "model", {("colour", 6, Q.B25): ref})
    SC._load_gen()
    v, why, notes = SC.retire(att)
    assert v == "RETIRE", why
    assert any("non-zero H-INV25 mask in [6]" in n for n in notes)


def test_a_reference_without_image_cannot_tell(att):
    run_all(att, "model", skip=("p1-m40-ref",))
    _, _, lines = SC.verdicts("p1", os.path.join(att, "p1"))
    ln = [x for x in lines if x.startswith("ROW p1-m40-b25")][0]
    assert ln.endswith("cannot tell"), ln
    SC._load_gen()
    v, why, _ = SC.retire(att)
    assert v == "NARROW" and "p1-m40-b25: cannot tell" in why


def test_a_stage_not_run_narrows(att):
    run_all(att, "model", stages=("s0", "p1", "pw"))
    SC._load_gen()
    v, why, _ = SC.retire(att)
    assert v == "NARROW" and "p2 did not run" in why


def test_q012_rows_are_not_tallied(att):
    run_all(att, "model")
    _, per, lines = SC.verdicts("p1", os.path.join(att, "p1"))
    assert not [m for m in per if "q012" in m]
    assert [x for x in lines if x.startswith("ROW p1-m34-b25 (q012)")][0].endswith("read (no model)")
    shutil.rmtree(att)
