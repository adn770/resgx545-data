# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current, its byte copies are the pinned files, every input
it reads is pinned, and the premises each stage rests on hold on the pinned data:

  q201  the coverage port is E1018's frozen rule (sample0_rule.image on the default triangle);
        every model's offset lies on the 1/16 grid and the models part each held-out value
  q261  c6's engine is the frozen one (q261_rule2.sha256, q261_rule3 imports it), clip4 is its
        clip_poly where the bounds agree, c6's held-out images (q261_heldout.out) are reproduced,
        E1012's fit holds on E979's kept rows (the controls' families at G 16..22 and a 8..32
        draw the kept images), and every held-out row depends on its own guard only
  far   the same independence; every held-out row's vertices reach 2^26 to 2^30 px"""
import gzip
import json
import os
import re
import subprocess
import sys
import tomllib
from fractions import Fraction as F

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import clip as C  # noqa: E402
import pins  # noqa: E402
import q201 as Q  # noqa: E402
import q261_rule2 as R2  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
C6 = "data:cited/closing11/plan/c6-q261/"


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_read_is_pinned():
    import make
    make.build()
    assert pins.READ <= set(CFG["freeze"]["pins"]), pins.READ - set(CFG["freeze"]["pins"])
    for rel, pin in list(make.COPIES.items()) + list(make.BINS.items()):
        assert pin in CFG["freeze"]["pins"]
        assert open(os.path.join(KP, rel), "rb").read() == pins.blob(pin), rel


def test_c6_engine_is_the_frozen_one():
    import hashlib
    for f in ("q261_rule2", "q261_rule3"):
        want = pins.blob(C6 + f + ".sha256").decode().split()[0]
        assert hashlib.sha256(pins.blob(C6 + f + ".py")).hexdigest() == want
    assert "import q261_rule2 as R2" in pins.blob(C6 + "q261_rule3.py").decode()
    import hashlib as h
    assert h.sha256(pins.blob("data:cited/closing12/plan/c6-q201/sample0_rule.py")).hexdigest() == \
        pins.blob("data:cited/closing12/plan/c6-q201/sample0_rule.sha256").decode().split()[0]


def test_clip4_is_clip_poly_with_one_box():
    props = json.loads(pins.blob(C.PROPOSALS).decode())
    for row in C.q261_rows(props):
        V = C.oriented([(C.g256(x), C.g256(y)) for x, y in row[6]])
        for lo, hi in ((-16, 80), (-8, 72), (-32, 96), (-20, 146)):
            assert C.clip4(V, (lo, hi, lo, hi)) == R2.clip_poly(V, lo, hi, "exact-halfup"), row[0]


def test_c6_heldout_images_reproduced():
    """q261_heldout.out's pixels off the exact image, per survivor, for the +x and -x vertices"""
    text = pins.blob(C6 + "q261_heldout.out").decode()
    props = json.loads(pins.blob(C.PROPOSALS).decode())
    rows = {r[0]: r for r in C.q261_rows(props)}
    blocks = re.split(r"\n  far vertex ", text)
    k = {"pos-x": 0, "neg-x": 0}
    for b in blocks[1:]:
        side = "pos-x" if k["pos-x"] < 4 else "neg-x" if k["neg-x"] < 3 else None
        if side is None:
            break
        k[side] += 1
        name = ("q261-px%d" if side == "pos-x" else "q261-nx%d") % k[side]
        r = rows[name]
        V3 = [(r[5][0], r[5][1]), (r[5][2], r[5][3]), (r[5][4], r[5][5])]
        exact, fam = C.predict(V3, 5, 64, side)
        fam = dict(fam)
        for m in re.finditer(r"(G|lo)=-?(\d+)\s+pixels off the exact image: (\d+) (\[.*\])", b):
            lab = ("G=%s" if m.group(1) == "G" else "a=%s") % m.group(2)
            off = sorted((i % 64, i // 64) for i, (a, c) in enumerate(zip(exact, fam[lab])) if a != c)
            assert off == sorted(eval(m.group(4))), (name, lab)
    assert k == {"pos-x": 4, "neg-x": 3}


def kept(name):
    return [v == 0xFF00FF00 for v in pins.pixels(gzip.decompress(pins.blob(C.KEPT % name)).decode(), 4096)]


def test_e1012_fit_on_the_kept_rows():
    """E1012 (post hoc): every survivor draws E979's kept far-ctl, far-x24p and far-x25n"""
    for name, side, unit, vp in (("far-x24p", "pos-x", 5, C.e979("far-x24p")),
                                 ("far-x25n", "neg-x", 5, C.e979("far-x25n"))):
        vt = C.to_units(vp, unit)
        exact, fam = C.predict([(vt[0], vt[1]), (vt[2], vt[3]), (vt[4], vt[5])], unit, 64, side)
        k = kept(name)
        assert exact != k                                   # E979's band: the exact image misses
        assert all(img == k for _, img in fam), name
    v = C.ctl_far21()
    exact, fam = C.predict([(v[0], v[1]), (v[2], v[3]), (v[4], v[5])], 8, 64, "pos-x")
    assert exact == kept("far-ctl") and all(img == exact for _, img in fam)


def test_every_heldout_row_depends_on_its_own_guard():
    props = json.loads(pins.blob(C.PROPOSALS).decode())
    for row in C.q261_rows(props) + C.far_rows():
        name, st, _, w, unit, vt, vp, side, abs_too = row
        if st == "control":
            continue
        for V in C.variants([(vt[0], vt[1]), (vt[2], vt[3]), (vt[4], vt[5])], unit, w):
            assert C.independent(V, w, side), name


def test_heldout_rows_part_their_family():
    """each held-out row's family has at least two images (it can tell values apart), and the
    far rows reach the plan's distances"""
    props = json.loads(pins.blob(C.PROPOSALS).decode())
    for row in C.q261_rows(props) + C.far_rows():
        name, st, _, w, unit, vt, vp, side, abs_too = row
        if st != "heldout":
            continue
        exact, fam = C.predict([(vt[0], vt[1]), (vt[2], vt[3]), (vt[4], vt[5])], unit, w, side, abs_too)
        assert len({tuple(img) for _, img in fam}) >= 2, name
    far = [r for r in C.far_rows() if r[1] == "heldout"]
    assert [max(abs(c) for p in r[6] for c in p) for r in far] == [2 ** 26] * 2 + [2 ** 28] * 2 + [2 ** 30] * 2


def test_q201_coverage_port_and_models():
    import sample0_rule as S0
    dflt = (8 * 256, 8 * 256, 56 * 256, 20 * 256, 20 * 256, 56 * 256)
    for b in (0x88, 0x26, 0x3C, 0x0F, 0xF0, 0x5A):
        mine = {(i % 64, i // 64) for i, v in enumerate(Q.coverage(b, dflt)) if v}
        assert mine == S0.image("SAMPLE0", b)
    for b in Q.VALUES:
        for p in ("src0", "cset"):
            for c in ("x", "y"):
                offs = [Q.offset(m, b, p, c) for m in Q.MODELS]
                assert all((o * 16).denominator == 1 for o in offs)
                assert Q.offset("H-SAMPLE0", b, p, c) != Q.offset("H-CENTRE", b, p, c)
                assert Q.offset("H-SAMPLE0", b, p, c) != Q.offset("H-SWAP", b, p, c)
            assert Q.offset("H-SAMPLE0", b, "cset", "x") != Q.offset("H-SPLIT", b, "cset", "x")
    assert sum(Q.coverage(0x88)) > 1000
