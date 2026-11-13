#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/q139_fit.py: added at the fold (2026-11-12), not by the run.  The placement model of Q139's
fit rows, fitted on `score/score_dump.py q139-fitdata` (fold/q139_fitdata.out: the fit and replicate
rows' header slots, read after the run; no held-out row's file is read here) and written as the
model file `score_dump.py q139-heldout` takes (fold/q139-model.json), hashed before the held-out rows
are read.

  q139_fit.py check FITDATA      the model against every fit row, tile by tile (slot and absence)
  q139_fit.py model OUT.json     the model's predictions for the held-out rows of tables/q139.txt

Model R7-BLK (fitted post hoc on the 11 fit and replicate rows; standard library only):
  - the job's words (tables/q139.txt's kpokes over the library's rule, E877's rules.py reading) give
    n (4 when CR_TE_MTILE1 bit 31 is set, else 2) and the macrotile bounds per axis (0, B1, B2, B3
    at n = 4; 0, B2 at n = 2); a tile's macrotile is found by comparing the bounds in order of use
    (E877's place()), lx, ly its offset from the macrotile's first tile;
  - f = the first macrotile's width per axis (bounds[1]); the TA writes one header for every tile
    (c, r) with c < max(tx, last x bound + f_x) and r < max(ty, last y bound + f_y), past the
    target too, row by row;
  - slot = N * S + ((ly >> 2) * (f_x >> 2) + (lx >> 2)) * 16 + (r & 3) * 4 + (c & 3), N = mcol * n
    + mrow (numbered down then across, E652), S the stride word: 4 x 4 tile blocks of 16 slots,
    the block's own offset from the tile's absolute position;
  - a later header overwrites an earlier one at the same slot; a target tile is predicted drawn
    iff its header survives (H-PRESENT, which the fit rows show: every wrong tile has no header,
    every drawn one has one), wrong otherwise.  No limit on the slot (none was exercised).
"""
import json
import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
TW, TH = 32, 16


def cdiv(a, b):
    return -(-a // b)


def rule(w, h):
    """(tx, ty, n, mx, my, mtile1, mtile2, stride): the library's rule (E877's q139_model.rule)."""
    tx, ty = cdiv(w, TW), cdiv(h, TH)
    n = 4 if w * h >= 640 * 480 else 2
    mx = cdiv(cdiv(tx, n), 4) * 4
    my = cdiv(cdiv(ty, n), 4) * 4
    b = (1, 2, 3) if n == 4 else (1, 1, 1)
    m1 = ((1 if n == 4 else 0) << 31) | (mx * b[0] << 22) | (mx * b[1] << 12) | (mx * b[2])
    m2 = (my * b[0] << 22) | (my * b[1] << 12) | (my * b[2])
    return tx, ty, n, mx, my, m1, m2, mx * my


def words(w, h, args):
    _, _, _, _, _, m1, m2, s = rule(w, h)
    for idx, val in re.findall(r"ta:(\d+)=(0x[0-9a-fA-F]+)", args):
        v = int(val, 16)
        if idx == "143":
            m1 = v
        elif idx == "144":
            m2 = v
        elif idx == "146":
            s = v
        else:
            raise ValueError("unexpected poke ta:%s" % idx)
    return m1, m2, s


def bounds(m1, m2):
    n = 4 if (m1 >> 31) & 1 else 2
    x = ((m1 >> 22) & 0xff, (m1 >> 12) & 0xff, m1 & 0xff)
    y = ((m2 >> 22) & 0x1ff, (m2 >> 12) & 0x1ff, m2 & 0x1ff)
    if n == 4:
        return n, (0,) + x, (0,) + y
    return n, (0, x[1]), (0, y[1])


def place(v, bs):
    k = 0
    while k < len(bs) - 1 and v >= bs[k + 1]:
        k += 1
    return k, v - bs[k]


def predict(w, h, args):
    """{target tile: slot or None} under R7-BLK."""
    tx, ty = cdiv(w, TW), cdiv(h, TH)
    m1, m2, s = words(w, h, args)
    n, bx, by = bounds(m1, m2)
    fx, fy = bx[1], by[1]
    owner = {}
    for r in range(max(ty, by[-1] + fy)):
        for c in range(max(tx, bx[-1] + fx)):
            mcol, lx = place(c, bx)
            mrow, ly = place(r, by)
            sl = (mcol * n + mrow) * s + ((ly >> 2) * (fx >> 2) + (lx >> 2)) * 16 + (r & 3) * 4 + (c & 3)
            owner[sl] = (c, r)
    pred = {(c, r): None for r in range(ty) for c in range(tx)}
    for sl, t in owner.items():
        if t in pred:
            pred[t] = sl
    return pred


def table():
    out = {}
    with open(os.path.join(KP, "tables", "q139.txt")) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            c = line.rstrip("\n").split("|")
            out[c[0]] = (c[1], c[5])
    return out


def size(args):
    return int(re.search(r"--width (\d+)", args).group(1)), int(re.search(r"--height (\d+)", args).group(1))


def check(path):
    tab = table()
    rows, cur = {}, None
    with open(path) as f:
        for line in f:
            if line.startswith("== "):
                cur = line.split()[1]
                rows[cur] = {}
                continue
            p = line.split()
            if cur and len(p) == 4 and re.fullmatch(r"\d+\.\d+", p[0]):
                rows[cur][tuple(int(v) for v in p[0].split("."))] = (None if p[2] == "-" else int(p[2]), p[3])
    allok = True
    for name, obs in sorted(rows.items()):
        st, args = tab[name]
        w, h = size(args)
        pr = predict(w, h, args)
        slot_ok = sum(1 for t, (o, _) in obs.items() if pr[t] == o)
        pres = sum(1 for t, (o, wr) in obs.items() if (o is None) == (wr == "wrong"))
        wrong_ok = {t for t, (o, wr) in obs.items() if wr == "wrong"} == {t for t, v in pr.items() if v is None}
        ok = slot_ok == len(obs) and wrong_ok
        allok &= ok
        print("%s (%s): slots %d of %d tiles as R7-BLK; H-PRESENT %d of %d; wrong set %s" % (
            name, st, slot_ok, len(obs), pres, len(obs), "as predicted" if wrong_ok else "DIFFERS"))
    print("R7-BLK on the fit rows: %s" % ("every row exact" if allok else "NOT exact"))
    return 0 if allok else 1


def model(out):
    tab = table()
    cases = {}
    for name, (st, args) in sorted(tab.items()):
        if st != "heldout":
            continue
        w, h = size(args)
        pr = predict(w, h, args)
        cases[name] = {"wrong": ["%d.%d" % t for t, v in sorted(pr.items(), key=lambda kv: (kv[0][1], kv[0][0]))
                                 if v is None],
                       "slots": {"%d.%d" % t: v for t, v in sorted(pr.items(), key=lambda kv: (kv[0][1], kv[0][0]))}}
    with open(out, "w") as f:
        json.dump({"model": "R7-BLK (fold/q139_fit.py)", "cases": cases}, f, indent=1, sort_keys=True)
        f.write("\n")
    for name, c in sorted(cases.items()):
        print("%s: %d wrong predicted" % (name, len(c["wrong"])))
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "check":
        sys.exit(check(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == "model":
        sys.exit(model(sys.argv[2]))
    print(__doc__)
    sys.exit(2)
