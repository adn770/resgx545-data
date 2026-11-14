#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/twostage.py: POST HOC (written after the run, on the kept images; no held-out claim of its
own). The frozen scorer compared H-WIDE's taps blended jointly ((sum + 2048) >> 12, texmodel's) to
each kept byte within 1. Here the same taps go through E720's landed two-stage filter (each 8-bit
channel (a (64 - f) + b f + 32) >> 6 in x on both rows, then in y; sgx-sim's tex.rs) and are
compared exactly, on every bilinear bit-14 row kept: E1049's two and E1058's six (gen/derive.py's
fit set) and E1067's eight (tw17). For each rival the exact pixels too, and at H-WIDE's left-wrap
pixels where H-WIDE-G's two-stage value differs from H-WIDE's, how many are exact under H-WIDE-G.

  python3 fold/twostage.py      (from the session directory; reads out/20261114-104432/tw17)"""
import gzip
import os
import re
import sys

sys.dont_write_bytecode = True
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import derive  # noqa: E402
import tw17 as T  # noqa: E402

ATT = os.path.join(KP, "out/20261114-104432/tw17")


def stage(a, b, f):
    return (a * (64 - f) + b * f + 32) >> 6


def two(t, kx, ky):
    out = 0
    for c in range(4):
        at = [x >> 8 * c & 255 for x in t]
        out |= stage(stage(at[0], at[1], kx), stage(at[2], at[3], kx), ky) << 8 * c
    return out


def kept(n):
    t = gzip.decompress(open(os.path.join(ATT, n + ".txt.gz"), "rb").read()).decode()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()]
            for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", t, re.M)}
    return [v for y in sorted(rows) for v in rows[y]]


def value(m, u, v, w, h):
    t, kx, ky = T.taps(m, u, v, w, h)
    return two([T.name_of(i) for i in t], kx, ky)


def main():
    rows = derive.bil_rows() + [("E1067:" + r[0], r[2], r[3], lambda x, y, n=r[0]: T.uv(n, x, y),
                                 kept(r[0])) for r in T.ROWS if r[4] == "bil"]
    forms = [m for m in T.BIL if m != "H-POINT"]
    tot = {m: 0 for m in forms}
    lw = [0, 0]
    for label, w, h, uvf, px in rows:
        hit = {m: 0 for m in forms}
        for i, (x, y) in enumerate(T.pixels()):
            u, v = uvf(x, y)
            vals = {m: value(m, u, v, w, h) for m in forms}
            for m in forms:
                hit[m] += vals[m] == px[i]
            if T.columns("H-WIDE", u, w)[3] < 0 and vals["H-WIDE-G"] != vals["H-WIDE"]:
                lw[0] += 1
                lw[1] += vals["H-WIDE-G"] == px[i]
        print(label, "; ".join(f"{m} {hit[m]}/2048" for m in forms))
        for m in forms:
            tot[m] += hit[m]
    n = 2048 * len(rows)
    print("TOTAL exact (two-stage):", "; ".join(f"{m} {a}/{n}" for m, a in tot.items()))
    print(f"LEFT WRAP (two-stage): {lw[0]} pixels where H-WIDE-G differs from H-WIDE; "
          f"H-WIDE-G exact on {lw[1]}")


if __name__ == "__main__":
    main()
