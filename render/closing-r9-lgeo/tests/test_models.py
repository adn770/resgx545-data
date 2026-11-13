# SPDX-License-Identifier: MIT
"""tests/test_models.py: the session's pure-Python models against published data.

- gen/tx6model.py's H-CEIL is E941's rule: through the window offsets it gives every one of
  r8-lgeo's 18 kept held-out type 4 images (64 x 64 to 256 x 32 at 64 scratch pages) and E910's
  64 x 32 control; at those sizes H-P2 equals it and H-PACK (no partial block) too, so the three
  differ only where this session parts them;
- the linear axis: texmodel's RASTERW gives r8-lgeo's kept type 3 rows at 24 and 40 wide and the
  32 x 16 bridge (E940), the rule tx6's type 1 rows and type 4 windows use;
- format 5's widening and word_of are inverse over every 16-bit word;
- gen/q139even.py's H-EVEN gives E944's three readable residue dumps exactly (the wrong-tile set
  and every header slot, from r8-lgeo's kept baselines: the fit E950 states), where R7-BLK does
  not; and it equals R7-BLK on every other row of r8-lgeo's q139 table (fx 0 or 1 mod 4 there)."""
import gzip
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, HERE)
import kept as KD  # noqa: E402
import lib_dump as L  # noqa: E402
import q139even as E  # noqa: E402
import texmodel as T  # noqa: E402
import tx6model as X  # noqa: E402

R8 = "render/closing-r8-lgeo/out/20261113-024441/"
R7G = "render/closing-r7-geo/out/20261112-211113/tx/"
TX4 = [(64, 64, 0, y) for y in (0, 32)] + [(128, 64, x, y) for y in (0, 32) for x in (0, 64)] + \
    [(128, 128, x, y) for y in (0, 32, 64, 96) for x in (0, 64)] + [(256, 32, x, 0) for x in (0, 64, 128, 192)]


def rows(path):
    return T.probe_rows(gzip.decompress(KD.blob(path)).decode())


def test_h_ceil_is_e941s_rule():
    assert len(TX4) == 18
    for w, h, xo, yo in TX4:
        k = rows(R8 + "tx4/tx4-ty4-%dx%d-x%dy%d.txt.gz" % (w, h, xo, yo))
        for hy in X.TYPE4:
            assert k == X.type4_image(hy, w, h, xo, yo, dwords=65536), (w, h, xo, yo, hy)
    assert rows(R7G + "tx-ty4-64x32.txt.gz") == X.type4_image("H-CEIL", 64, 32)


def test_linear_axis_is_e940s():
    for w, h in ((24, 8), (40, 8), (32, 16)):
        assert rows(R8 + "tx4/tx4-lin-ty3-%dx%d.txt.gz" % (w, h)) == T.tex_image("RASTERW", w, h, linear=True), (w, h)
        if w != 32:
            assert T.tex_image("RASTERW", w, h, linear=True) != T.tex_image("RASTERP2", w, h, linear=True)


def test_rivals_part_where_the_table_says():
    import kitscore as K
    P = K.predictions(KP, "tx6")
    for n, q in P.items():
        if "parts" in q:
            assert q["parts"]["all"] != "none" or n in ("tx6-ty4-96x32-x64y0", "tx6-ty4-80x64-x0y0"), n
    assert "H-CEIL/H-P2" in P["tx6-ty4-80x64-x0y32"]["parts"]["all"]
    assert "H-CEIL/H-PACK" in P["tx6-ty4-48x64-x0y0"]["parts"]["all"]
    assert P["tx6-ty3-f5-4x8"]["parts"]["all"] == "H-DW8/H-TX8 H-DW8/RASTERW H-TX8/RASTERW"


def test_format5_widening_inverts():
    for v in range(1 << 16):
        p = X.widen565(v)
        assert X.word_of(p) == v and p >> 24 == 0xFF


def q139_kept(name):
    d = R8 + "q139/" + name
    return (gzip.decompress(KD.blob(d + ".txt.gz")).decode(), gzip.decompress(KD.blob(d + ".tri.param.bin.gz")),
            gzip.decompress(KD.blob(d + ".tri.tadata.bin.gz")))


def r8_args():
    out = {}
    for ln in KD.blob("render/closing-r8-lgeo/tables/q139.txt").decode().splitlines():
        if ln and not ln.startswith("#"):
            p = ln.split("|", 5)
            a = p[5].split()
            out[p[0]] = (int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1]),
                         " ".join("--kpoke-render " + a[i + 1] for i, x in enumerate(a) if x == "--kpoke-render"))
    return out


def test_h_even_fits_e944s_residue_dumps():
    args = r8_args()
    base = {}
    for n in ("q139-ctl-256x256", "q139-ctl-640x480"):
        text, par, tad = q139_kept(n)
        w, h, _ = args[n]
        ok, _, ly = L.baseline_layout(tad, par, w, h)
        assert ok
        base[(w, h)] = ly["base"]
    held = {"H-EVEN": 0, "blkrow": 0}
    for n in ("q139-res-256x256-m1-B2-10", "q139-res-256x256-m1-B2-11", "q139-res-640x480-m1-B1-23"):
        text, par, tad = q139_kept(n)
        w, h, a = args[n]
        comp, bad = L.image_tiles(text, w, h)
        obs = L.observed_slots(tad, base[(w, h)], w, h)
        for m in held:
            pr = E.predict(w, h, a, m)
            ok = E.wrong(pr) == bad and all((v is None and not obs.get(t)) or (v is not None and v in obs.get(t, []))
                                            for t, v in pr.items())
            held[m] += ok
    assert held == {"H-EVEN": 3, "blkrow": 0}


def test_h_even_is_r7_blk_on_r8s_other_rows():
    args = r8_args()
    n = 0
    for name, (w, h, a) in args.items():
        if name.startswith("q139-res-") and name != "q139-res-1280x720-m2-B3p1":
            continue
        fx = E.geometry(w, h, a)[4]
        assert fx % 4 in (0, 1), name
        assert E.predict(w, h, a, "H-EVEN") == E.predict(w, h, a, "blkrow"), name
        n += 1
    assert n == 17
