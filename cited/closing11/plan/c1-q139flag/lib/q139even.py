# SPDX-License-Identifier: MIT
"""q139even.py: r9-lgeo's Q139 slot rules, standard library only.

R7-BLK (E907, E944's block order, gen/q139model.py "blkrow", a byte copy of r8-lgeo's) gives a
block row of the first macrotile 16 floor(fx / 4) slots. H-EVEN (the round 9 seeds plan, finding
4: closing9/seeds/q139/residue_fit.py, bcols "row8half", order "abs", fitted on E944's three
readable residue dumps) gives it 8 floor(fx / 2):

  slot = (mcol n + mrow) S + (ly >> 2) NB + (lx >> 2) 16 + (r & 3) 4 + (c & 3)
  NB   = 16 floor(fx / 4)   R7-BLK
       = 8 floor(fx / 2)    H-EVEN   (the same whenever fx is 0 or 1 mod 4)

with the tiles written in block order (4 x 4 tile blocks, block rows across the target), a later
header overwriting an earlier one at its slot, and a target tile drawn iff its own header
survives (H-PRESENT, E907). The rivals of round 8 (raster, blkdown, mtblk) are q139model's."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import q139_fit as F  # noqa: E402
import q139model as Q  # noqa: E402

MODELS = ("H-EVEN", "blkrow", "raster", "blkdown", "mtblk")
NB = {"H-EVEN": lambda fx: 8 * (fx >> 1), "blkrow": lambda fx: 16 * (fx >> 2)}


def geometry(w, h, args):
    """(n, bx, by, S, fx, fy) of a job's words."""
    m1, m2, s = F.words(w, h, args)
    n, bx, by = F.bounds(m1, m2)
    return n, bx, by, s, bx[1], by[1]


def predict(w, h, args, model):
    """{target tile (c, r): its surviving header's slot, or None (the tile is wrong)}."""
    if model != "H-EVEN":
        return Q.predict(w, h, args, model)
    key = Q.KEYS["blkrow"]
    tx, ty = F.cdiv(w, 32), F.cdiv(h, 16)
    n, bx, by, s, fx, fy = geometry(w, h, args)
    nb = NB[model](fx)
    ws = []
    for r in range(max(ty, by[-1] + fy)):
        for c in range(max(tx, bx[-1] + fx)):
            mcol, lx = F.place(c, bx)
            mrow, ly = F.place(r, by)
            sl = (mcol * n + mrow) * s + (ly >> 2) * nb + (lx >> 2) * 16 + (r & 3) * 4 + (c & 3)
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


def headers(w, h, args, model):
    """{slot: (c, r)} of every surviving header (the fake tool's dump), target tiles or not."""
    key = Q.KEYS["blkrow" if model == "H-EVEN" else model]
    n, bx, by, s, fx, fy = geometry(w, h, args)
    nb = NB.get(model, NB["blkrow"])(fx)
    ws = []
    for r in range(max(F.cdiv(h, 16), by[-1] + fy)):
        for c in range(max(F.cdiv(w, 32), bx[-1] + fx)):
            mcol, lx = F.place(c, bx)
            mrow, ly = F.place(r, by)
            sl = (mcol * n + mrow) * s + (ly >> 2) * nb + (lx >> 2) * 16 + (r & 3) * 4 + (c & 3)
            ws.append((key(r, c, mcol, mrow, n), sl, (c, r)))
    ws.sort(key=lambda t: t[0])
    own = {}
    for _, sl, t in ws:
        own[sl] = t
    return own


wrong = Q.wrong
tiles_text = Q.tiles_text
slots_text = Q.slots_text
slots_parse = Q.slots_parse
