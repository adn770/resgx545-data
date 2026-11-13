# SPDX-License-Identifier: MIT
"""tests/test_gen.py: the generator is current, its byte copies are the pinned files, every input
it reads is pinned, and the premises each stage rests on hold on the pinned data:

  pivot  the in-span band pixels of each triangle flip at one displacement t* (42.6, 51.4, 41.6
         px), they are E979's band misses (the kept images, pinned), every pixel's frozen interval
         agrees with H-EXACT at s = 0, and the rows bracket D from t* to t* + 544
  q139c  each word drew a whole image and never faulted in every kept job that ran it (the risky
         dataset and r7-rp's q139, pinned): the safe class the lead asked for; the frozen kept
         wrong-tile sets are the dataset's; H-EVEN = R7-BLK (blkrow) on every row (fx 4 and 8)
  bgw    the control's object words 9 and 11-14 are 0 (r9-k1's kept c-tex dump): 0 is the
         control, and H-SCALE0's frozen texels are clamped and edge-free as gen/bgw.py says"""
import os
import re
import subprocess
import sys
import tomllib
from fractions import Fraction as F

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.dont_write_bytecode = True
import kept  # noqa: E402
import pins  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
COPIES = {"gen/far.py": "data:render/closing-r9-x/gen/far.py",
          "gen/q139even.py": "data:render/closing-r9-lgeo/gen/q139even.py",
          "gen/q139model.py": "data:render/closing-r9-lgeo/gen/q139model.py",
          "gen/q139_fit.py": "data:render/closing-r9-lgeo/gen/q139_fit.py",
          "score/lib_dump.py": "data:render/closing-r9-lgeo/score/lib_dump.py",
          "score/pbdump_dump.py": "data:render/closing-r9-lgeo/score/pbdump_dump.py",
          "score/region_tiles_dump.py": "data:render/closing-r9-lgeo/score/region_tiles_dump.py",
          "gen/bgl_model.py": "data:render/closing-r9-k1/gen/bgl_model.py",
          "gen/bgmask.txt": "data:render/closing-r9-k1/gen/bgmask.txt"}
R9X = "render/closing-r9-x/out/20261113-081821/far/"


def test_generator_current():
    r = subprocess.run([sys.executable, "-B", os.path.join(KP, "gen/make.py"), "--check"],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr


def test_byte_copies_are_the_pinned_files():
    for rel, pin in COPIES.items():
        assert pin in CFG["freeze"]["pins"], pin
        assert open(os.path.join(KP, rel), "rb").read() == pins.blob(pin), rel


def test_pins_read_are_pinned():
    import q139c as QC
    pins.blob(QC.DATASET)
    assert pins.READ <= set(CFG["freeze"]["pins"])


# ---- pivot ---------------------------------------------------------------------------------------
TSTAR = {"far-x23p": F(341, 8), "far-x24p": F(411, 8), "far-x25n": F(333, 8)}


def kept_drawn(name):
    t = kept.data(R9X + name + ".txt.gz").decode()
    px = [int(v, 16) for m in re.finditer(r"^row \d+: (.*)$", t, re.M) for v in m.group(1).split()]
    assert len(px) == 4096
    return [v == 0xFF00FF00 for v in px]


def test_pivot_thresholds_and_e979_misses():
    import pivot as PIV
    for tri in PIV.TRIS:
        vp = PIV.verts_px(tri)
        iv = PIV.pixel_intervals(vp)
        ex = PIV.predictions(vp)["H-EXACT"]
        near = {p for p, (lo, hi) in iv.items() if lo is not None and abs(lo) < 1000}
        assert near and {iv[p][0] for p in near} == {TSTAR[tri]}, tri
        assert all(iv[p][1] is None or iv[p][1] > 1000 for p in near)
        got = kept_drawn(tri)
        off = {(i % 64, i // 64) for i in range(4096) if got[i] != ex[i]}
        assert off == near, tri                     # E979's misses are exactly the pixels at t*
        assert len(off) == {"far-x23p": 2, "far-x24p": 10, "far-x25n": 14}[tri]
        for (x, y), (lo, hi) in iv.items():          # H-EXACT at s = 0 is the interval's verdict
            if lo != 0 and hi != 0:
                assert ex[y * 64 + x] == ((lo is None or lo < 0) and (hi is None or 0 < hi)), (tri, x, y)


def test_pivot_rows_bracket_d():
    import pivot as PIV
    assert PIV.DLIST[0] == 0 and list(PIV.DLIST) == sorted(PIV.DLIST, reverse=True)
    steps = [a - b for a, b in zip(PIV.DLIST, PIV.DLIST[1:])]
    assert max(steps) == 128 and -PIV.DLIST[-1] == 544
    for tri in PIV.TRIS:                            # a moved row's t* is t* - d: same pixels
        for d in PIV.DLIST[1:3]:
            iv = PIV.pixel_intervals(PIV.moved(PIV.verts_px(tri), d))
            assert {lo for lo, hi in iv.values() if lo is not None and abs(lo) < 1000} == {TSTAR[tri] - d}


# ---- q139c ---------------------------------------------------------------------------------------
def test_q139c_words_safe():
    """Every kept job that ran one of the four words: job ok (a whole image), no fault line."""
    import q139c as QC
    out = kept.data("ta/mtile-fields-risky/output.txt").decode()
    cases = kept.data("ta/mtile-fields-risky/cases.tsv").decode()
    rp = kept.data("render/closing-r7-rp/out/20261112-205431/q139/cases.tsv").decode()
    rplog = kept.data("render/closing-r7-rp/out/20261112-205431/q139.log").decode()
    seen = {}
    for name, sset, w, h, word, case in QC.ROWS:
        if word is None:
            continue
        assert SAFE(word) == (w, h)
        hx = "0x%08x" % word
        blocks = [b for b in out.split("\n== ")[1:] if b.split("\n")[0].endswith("=" + hx)]
        assert len(blocks) == 1 and blocks[0].startswith(case + " ")
        assert blocks[0].split("\n")[1].strip().startswith("rc 1 job: ok diff:")
        assert "fault" not in blocks[0] and "%d" % w in blocks[0].split("\n")[0]
        assert sum(hx in ln for ln in cases.splitlines()) == 1
        rows = [ln.split("\t") for ln in rp.splitlines() if hx in ln]
        for f in rows:
            assert f[7:11] == ["1", "ok", "-", "-"], f[0]     # rc 1, class ok (expectdiff), no fault
            i = rplog.index("1:ta:144=" + hx)
            res = rplog[i:].split("\n")[2]
            assert "job: ok" in res and "fault" not in res, res
        seen[word] = 1 + len(rows)
    assert seen == {0x0200a008: 2, 0x0200b008: 1, 0x0280a00a: 2, 0x05c10018: 1}


def SAFE(word):
    import q139c as QC
    return QC.SAFE_WORDS[word]


def test_q139c_models_on_the_rows():
    import q139c as QC
    import q139even as E
    out = kept.data(QC.DATASET[5:]).decode()
    for name, sset, w, h, word, case in QC.ROWS:
        a = QC.kpokes(QC.args_of(w, h, word))
        n, bx, by, s, fx, fy = E.geometry(w, h, a)
        assert fx in (4, 8)
        assert E.predict(w, h, a, "H-EVEN") == E.predict(w, h, a, "blkrow")
        if case:
            assert E.wrong(E.predict(w, h, a, "H-EVEN")) == QC.dataset_wrong(out, case)
            assert fy == {"m2-B2-10": 10, "part2-10_10_10": 10, "m2-B2-11": 11, "m2-B1-23": 23}[case.split("x", 1)[1].split("-", 1)[1]]


# ---- bgw -----------------------------------------------------------------------------------------
def test_bgw_control_words_are_zero():
    import struct
    import bgl_model as M
    b = kept.data("render/closing-r9-k1/out/20261113-083450/s0t/c-tex.tri.param.bin.gz")
    o = struct.unpack_from("<23I", b, M.OBJ_OFF)
    assert [o[w] for w in (9, 11, 12, 13, 14)] == [0] * 5
    assert {w: M.CTRL[w] for w in (9, 11, 12, 13, 14)} == dict.fromkeys((9, 11, 12, 13, 14), 0)


def test_bgw_scale_predictions():
    import bgl_model as M
    import bgw as BGW
    mask = M.load_mask()
    for w in (11, 12, 14):
        for v in BGW.VALUES[w]:
            p = BGW.predict("H-SCALE0", w, v, mask)
            assert len(p) == len(mask)               # no pixel on a texel edge
            k = 0 if BGW.COORD[w] == "u" else 1
            c = {t[k] for t in p.values()}
            if v < 0:
                assert c == {0}
            if v == 1.5:
                assert 63 in c and max(c) == 63
        assert BGW.predict("H-SCALE0", w, 0.0, mask) == BGW.predict("H-INERT", w, 0.0, mask)
    assert BGW.predict("H-SCALE0", 9, 2.0, mask) == BGW.predict("H-INERT", 9, 2.0, mask)
