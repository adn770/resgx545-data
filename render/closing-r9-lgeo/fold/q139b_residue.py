#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/q139b_residue.py (post hoc, the fold, not frozen): the 1280 x 720 m2-B3p1 residue of
r9-lgeo q139b read against its baseline's header base. Per wrong tile beyond H-EVEN's 40 (row 36,
the rows no header names): the header H-EVEN puts at its slot (word 0 tile, word 1 stream,
flags) beside the drawn tiles of the same macrotile, and every other header naming the tile.
Reads the kept files of out/20261113-080029 only; standard library.
    python3 fold/q139b_residue.py [ATTEMPT_DIR]"""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("kit", "gen", "score"):
    sys.path.insert(0, os.path.join(KP, d))
import kitscore as K  # noqa: E402
import lib_dump as L  # noqa: E402
import q139even as E  # noqa: E402
import pbdump_dump as P  # noqa: E402

A = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KP, "out/20261113-080029")
D = os.path.join(A, "q139b")
W, H = 1280, 720
ARGS = "--kpoke-render 1:ta:144=0x03018025"


def job(n):
    return (K.text(D, n + ".txt"), L.read_bytes(os.path.join(D, n + ".tri.param.bin")),
            L.read_bytes(os.path.join(D, n + ".tri.tadata.bin")))


_, bp, bt = job("q139b-ctl-1280x720")
ok, txt, ly = L.baseline_layout(bt, bp, W, H)
print("baseline:", txt)
text, par, tad = job("q139b-res-1280x720-m2-B3p1")
comp, bad = L.image_tiles(text, W, H)
pred = E.predict(W, H, ARGS, "H-EVEN")
n, bx, by, s, fx, fy = E.geometry(W, H, ARGS)
print("geometry: n %d bx %s by %s S %d fx %d fy %d" % (n, bx, by, s, fx, fy))
model_wrong = E.wrong(pred)
extra = sorted(bad - model_wrong, key=lambda t: (t[1], t[0]))
print("wrong %d, H-EVEN's %d, beyond it %d: %s" % (len(bad), len(model_wrong), len(extra), L.tiles_text(extra)))
hs = {i: (c, r, fl, st) for i, c, r, fl, st in L.headers(tad, ly["base"], stop_zero=1 << 30)}
print("\ntile   mtile  ly lx  slot  header(c,r)  flags  stream     state  stream words (first 6)")
for r in range(36, 45):
    for c in range(32, 40):
        sl = pred[(c, r)]
        h = hs.get(sl) if sl is not None else None
        mcol, lx = E.F.place(c, bx)
        mrow, lyy = E.F.place(r, by)
        st = "WRONG" if (c, r) in bad else "drawn"
        sw = P.stream(par, h[3]) if h and h[3] else []
        print("%2d.%2d  %d,%d   %2d %2d  %5s  %-11s  %5s  %s  %s  %d: %s" % (
            c, r, mcol, mrow, lyy, lx, "-" if sl is None else sl, "-" if h is None else "%d,%d" % h[:2],
            "-" if h is None else "0x%02x" % h[2], "-" if h is None else "0x%08x" % h[3], st, len(sw),
            " ".join("%08x" % w for w in sw[:6])))
others = {}
for i, (c, r, fl, st) in hs.items():
    others.setdefault(L.tile_of(c, r), []).append(i)
print("\nheaders naming each extra wrong tile:", {L.tiles_text([t]): others.get(t, []) for t in extra})
