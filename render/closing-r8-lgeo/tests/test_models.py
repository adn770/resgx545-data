# SPDX-License-Identifier: MIT
"""tests/test_models.py: the session's pure-Python models against published data.

- gen/zsmodel.py's coverage (no numpy) gives r7-geo's frozen covered_sha (made by model1140, numpy)
  for HU and HA on every one of r7-geo's 230 zs rows, and E681's and E683's kept hashes;
- gen/texmodel.py gives every image of r7-geo's stage tx (E910, E911) under the reading the records
  state: RASTERW for types 1 and 3 but type 3 at 4 x 16 (H-MIN8), the 32 x 32 blocks for type 4,
  H-DW8 (= H-DW4B1 there) for type 5, the memory rows with their 112 stored dwords."""
import gzip
import os
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, HERE)
import kept as KD  # noqa: E402
import texmodel as T  # noqa: E402
import zsmodel as Z  # noqa: E402

R7G = "render/closing-r7-geo"
TX = R7G + "/out/20261112-211113/tx/"
TX_ROWS = [(1, 4, 16), (1, 64, 8), (1, 128, 8), (3, 4, 16), (3, 64, 8), (3, 128, 8), (4, 4, 16), (4, 64, 8), (4, 128, 8),
           (4, 64, 32), (4, 128, 32)]
T5_ROWS = [("tx-ty5-16x16", 16, None), ("tx-ty5-8x8", 8, None), ("tx-ty5-32x32", 32, None), ("tx-ty5-64x64", 64, None),
           ("tx-ty5-16x16-zero", 16, 0), ("tx-ty5-16x16-ones", 16, 0xFFFFFFFF)]


def test_zsmodel_is_r7_geos_coverage():
    P = {}
    for ln in KD.blob(R7G + "/predictions/zs.tsv").decode().splitlines()[1:]:
        c, q, v, m, _s = ln.split("\t")
        P.setdefault((c, q), {})[m] = v
    n = 0
    for ln in KD.blob(R7G + "/tables/zs.txt").decode().splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        name, *_x, args = ln.split("|", 5)
        a = shlex.split(args)
        w, h = int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])
        v = [int(x) for x in a[a.index("--tri-v") + 1].split(",")]
        for var in ("HU", "HA"):
            assert Z.cov_sha(Z.cover4096(v, w, h, var), w) == P[(name, "covered_sha")]["H-" + var], (name, var)
            n += 1
        if name.startswith("zs-ctl-"):
            assert "0x%016x" % Z.fnv_image(Z.cover4096(v, w, h, "HA"), w) == P[(name, "hash")]["E681" if "e681" in name
                                                                                              else "E683"]
    assert n == 460


def kept(name):
    return T.probe_rows(gzip.decompress(KD.blob(TX + name + ".txt.gz")).decode())


def test_texmodel_gives_r7_geos_tx_images():
    assert kept("tx-ctl-ty3-32x16") == T.tex_image("RASTERW", 32, 16)
    for ty, w, h in TX_ROWS:
        hyp = "H-BLKROW" if ty == 4 else ("H-MIN8" if (ty, w) == (3, 4) else "RASTERW")
        assert kept("tx-ty%d-%dx%d" % (ty, w, h)) == T.tex_image(hyp, w, h), (ty, w, h)
    for name, w, fill in T5_ROWS:
        st = None if fill is None else {i: fill for i in range(112)}
        for hyp in ("H-DW8", "H-DW4B1"):
            assert kept(name) == T.type5_image(hyp, w, w, st), (name, hyp)
