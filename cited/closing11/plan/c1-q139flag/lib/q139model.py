# SPDX-License-Identifier: MIT
"""q139model.py: r8-lgeo's Q139 write orders, standard library only. R7-BLK's slot rule (E907) is
gen/q139_fit.py, a byte copy of resgx545-data render/closing-r7-rp/fold/q139_fit.py (pinned in
FROZEN.commits); the orders are the round 8 planning's (closing8/leftovers/q139_o1_predict.py
and q139_o3_rivals.py, their key functions copied verbatim, P1 of exp-leftovers-r8.md):

  blkrow   4 x 4 tile blocks, block rows across the target (FROZEN: the prediction of L2)
  raster   row by row (R7-BLK as E907 froze it)
  blkdown  blocks column by column
  mtblk    macrotile by macrotile, then its blocks

The TA writes one header for every tile (c, r) with c < max(tx, last x bound + f_x) and r <
max(ty, last y bound + f_y), at slot (mcol n + mrow) S + ((ly >> 2)(f_x >> 2) + (lx >> 2)) 16 +
(r & 3) 4 + (c & 3), in the order's sequence; a later header overwrites an earlier one at its slot,
and a target tile is drawn iff its own header survives (H-PRESENT, E907)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import q139_fit as F  # noqa: E402

KEYS = {"blkrow": lambda r, c, mc, mr, n: (r >> 2, c >> 2, r, c),
        "raster": lambda r, c, mc, mr, n: (r, c),
        "blkdown": lambda r, c, mc, mr, n: (c >> 2, r >> 2, r, c),
        "mtblk": lambda r, c, mc, mr, n: (mc * n + mr, r >> 2, c >> 2, r, c)}
FROZEN = "blkrow"
RIVALS = ("raster", "blkdown", "mtblk")


def predict(w, h, args, order):
    """{target tile (c, r): its surviving header's slot, or None (the tile is wrong)}."""
    key = KEYS[order]
    tx, ty = F.cdiv(w, 32), F.cdiv(h, 16)
    m1, m2, s = F.words(w, h, args)
    n, bx, by = F.bounds(m1, m2)
    fx, fy = bx[1], by[1]
    ws = []
    for r in range(max(ty, by[-1] + fy)):
        for c in range(max(tx, bx[-1] + fx)):
            mcol, lx = F.place(c, bx)
            mrow, ly = F.place(r, by)
            sl = (mcol * n + mrow) * s + ((ly >> 2) * (fx >> 2) + (lx >> 2)) * 16 + (r & 3) * 4 + (c & 3)
            ws.append((key(r, c, mcol, mrow, n), sl, (c, r)))
    ws.sort(key=lambda t: t[0])
    own = {}
    for _, sl, t in ws:
        own[sl] = t
    pred = {(c, r): None for r in range(ty) for c in range(tx)}
    for sl, t in own.items():
        if t in pred:
            pred[t] = sl
    return pred


def wrong(pred):
    return {t for t, v in pred.items() if v is None}


def tiles_text(tiles):
    return ",".join("%d.%d" % t for t in sorted(tiles, key=lambda t: (t[1], t[0]))) or "none"


def slots_text(pred):
    """'c.r:slot' (or 'c.r:-') for every target tile, sorted by (r, c)."""
    return ",".join("%d.%d:%s" % (t[0], t[1], "-" if v is None else v)
                    for t, v in sorted(pred.items(), key=lambda kv: (kv[0][1], kv[0][0])))


def slots_parse(s):
    out = {}
    for p in s.split(","):
        t, v = p.split(":")
        out[tuple(int(x) for x in t.split("."))] = None if v == "-" else int(v)
    return out
