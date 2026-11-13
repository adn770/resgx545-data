# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py replayed on kept records it must hold on and must fail on,
and on the mock's worlds.

pivot: E979's kept far-ctl (PASS) and far-x23p, far-x24p, far-x25n as the three d = 0 rows: H-EXACT
FAILED on each (E979's band misses), H-EXACT-BAND held, D above t* (42.6, 51.4, 41.6); far-x23p in
the control's place FAILED. Worlds: D = 100 pins D to (90.6, 106.6) and the two others, H-PIVOT
held; D = 0 (exact) pins D below t*, H-EXACT held; D = 500 inside (458.6, 586.6).
q139c: r8-lgeo's kept 256 x 256 baseline (PASS) and m1-B2-10 residue (E950, E959: H-EVEN's slots,
one flag bit 7 header, H-LAST right on every tile; it must hold here, read through this scorer's
helpers); worlds: model held, rival (slots off H-EVEN's) FAILED, noflag (no bit 7) H-LAST FAILED.
bgw: r9-k1's kept c-tex (identity: H-INERT right), e-b12-one (1.0: right), e-b12-ff (0xffffffff:
H-INERT wrong); worlds: model H-INERT held, H-SCALE0 FAILED; scale the reverse."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("gen", "score", "tests", "kit"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import kept  # noqa: E402

R9X = "render/closing-r9-x/out/20261113-081821/far/"
R8L = "render/closing-r8-lgeo/out/20261113-024441/q139/"
R9K = "render/closing-r9-k1/out/20261113-083450/"


def line(lines, start):
    return [ln for ln in lines if ln.startswith(start)][0]


# ---- pivot ---------------------------------------------------------------------------------------
def test_pivot_on_e979(tmp_path):
    files = {"piv-ctl": {".txt": R9X + "far-ctl.txt.gz"}}
    for t in ("x23p", "x24p", "x25n"):
        files["piv-%s-d0" % t] = {".txt": R9X + "far-%s.txt.gz" % t}
    out = kept.score("pivot", kept.from_files("pivot", str(tmp_path / "a"), files))
    assert line(out, "CONTROL piv-ctl").endswith("PASS")
    for t, lo in (("x23p", "42.625"), ("x24p", "51.375"), ("x25n", "41.625")):
        ln = line(out, "ROW piv-%s-d0 " % t)
        assert "H-EXACT-BAND" in ln and "D in (%s, " % lo in ln, ln
        assert line(out, "READING far-%s:" % t).startswith("READING far-%s: 1 of 12 rows read" % t)
    assert "not supported: 0 held, 3 FAILED" in kept.summary(out, "H-EXACT:")[0]
    assert "H-EXACT-BAND holds (3 of 3" in kept.summary(out, "H-EXACT-BAND")[0]
    assert "cannot tell" in kept.summary(out, "H-PIVOT")[0]          # rows missing


def test_pivot_control_fails_on_another_image(tmp_path):
    d = kept.from_files("pivot", str(tmp_path / "c"), {"piv-ctl": {".txt": R9X + "far-x23p.txt.gz"}})
    out = kept.score("pivot", d)
    assert line(out, "CONTROL piv-ctl").endswith("FAILED")
    assert "controls FAILED" in kept.summary(out, "H-PIVOT")[0]


def test_pivot_worlds(tmp_path):
    out = kept.score("pivot", kept.from_world("pivot", str(tmp_path / "m"), "model"))
    assert line(out, "READING far-x23p").endswith("in (90.625, 106.625)")
    assert line(out, "READING far-x24p").endswith("in (99.375, 115.375)")
    assert "H-PIVOT holds (3 of 3" in kept.summary(out, "H-PIVOT")[0]
    assert "H-CONSTD holds (1 of 1" in kept.summary(out, "H-CONSTD")[0]
    ex = kept.score("pivot", kept.from_world("pivot", str(tmp_path / "e"), "exact"))
    assert "H-EXACT holds (36 of 36" in kept.summary(ex, "H-EXACT:")[0]
    assert line(ex, "READING far-x23p").endswith("42.625)")
    far = kept.score("pivot", kept.from_world("pivot", str(tmp_path / "f"), "d500"))
    assert line(far, "READING far-x25n").endswith("in (457.625, 585.625)")


# ---- q139c ---------------------------------------------------------------------------------------
def test_q139c_helpers_on_r8_lgeo():
    import lib_dump as L
    import q139c as QC
    import q139even as E
    import score as S
    ctl = {s: kept.data(R8L + "q139-ctl-256x256" + s) for s in (".txt.gz", ".tri.param.bin.gz", ".tri.tadata.bin.gz")}
    ok, txt, ly = L.baseline_layout(ctl[".tri.tadata.bin.gz"], ctl[".tri.param.bin.gz"], 256, 256)
    assert ok
    res = {s: kept.data(R8L + "q139-res-256x256-m1-B2-10" + s) for s in (".txt.gz", ".tri.tadata.bin.gz")}
    comp, bad = L.image_tiles(res[".txt.gz"].decode(), 256, 256)
    assert comp and len(bad) == 28
    last, right, n = S.last_flag(res[".tri.tadata.bin.gz"], ly["base"], 256, 256, bad)
    assert last == [103] and right == n == 128                    # E959's reading
    a = "--kpoke-render 1:ta:143=0x0100a004"
    pred = E.predict(256, 256, a, "H-EVEN")
    obs = L.observed_slots(res[".tri.tadata.bin.gz"], ly["base"], 256, 256)
    assert S.slot_agree(pred, obs) == 128                          # E950: H-EVEN's slots
    fs, lw = QC.flag_slot(256, 256, a)
    assert fs == 103 and lw == bad                                 # H-FLAGSLOT on E950's fit row
    last0, _, _ = S.last_flag(ctl[".tri.tadata.bin.gz"], ly["base"], 256, 256, set())
    assert last0 == [127] and QC.flag_slot(256, 256, "")[0] == 127


def test_q139c_worlds(tmp_path):
    out = kept.score("q139c", kept.from_world("q139c", str(tmp_path / "m"), "model"))
    assert all("holds (" in ln for ln in kept.summary(out, "Q139")), out
    riv = kept.score("q139c", kept.from_world("q139c", str(tmp_path / "r"), "rival"))
    assert "not supported" in kept.summary(riv, "held out (fy 11")[0]
    nf = kept.score("q139c", kept.from_world("q139c", str(tmp_path / "n"), "noflag"))
    assert "H-LAST holds is not supported: 0 held, 4 FAILED" in kept.summary(nf, "H-LAST")[0]


# ---- bgw -----------------------------------------------------------------------------------------
def test_bgw_on_r9_k1():
    import bgl_model as M
    import bgw as BGW
    mask = M.load_mask()
    ident = BGW.predict("H-INERT", None, None, mask)
    for name, want in (("s0t/c-tex", True), ("s3/e-b12-one", True), ("s3/e-b12-ff", False)):
        img = M.tri_rows(kept.data(R9K + name + ".txt.gz").decode())
        assert M.score_tex(ident, img, mask)[0] is want, name
    img = M.tri_rows(kept.data(R9K + "s3/e-b12-ff.txt.gz").decode())
    assert M.score_tex(BGW.predict("H-SCALE0", 12, 1.0, mask), img, mask)[0] is False


def test_bgw_worlds(tmp_path):
    out = kept.score("bgw", kept.from_world("bgw", str(tmp_path / "m"), "model"))
    assert line(out, "CONTROL bgw-ctl:").endswith("PASS") and line(out, "CONTROL bgw-ctl-end").endswith("PASS")
    assert "H-INERT holds (16 of 16" in kept.summary(out, "H-INERT")[0]
    assert "not supported: 0 held, 12 FAILED" in kept.summary(out, "H-SCALE0")[0]
    sc = kept.score("bgw", kept.from_world("bgw", str(tmp_path / "s"), "scale"))
    assert "H-SCALE0 holds (12 of 12" in kept.summary(sc, "H-SCALE0")[0]
    assert "not supported" in kept.summary(sc, "H-INERT")[0]
