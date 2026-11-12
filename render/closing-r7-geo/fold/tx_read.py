#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/tx_read.py (added at the fold, 2026-11-12, not by the run; POST HOC): stage tx row by row.  For each type 1, 3 and 4 row
(the 64 x 32 fill, dword i of the texture = 0xD0000000 | i, pixel (x, y) sampling texel (x mod w, y mod h)) the pixels that hold a
texel tag, then every raster stride s (1 to 256 dwords) with offset (y mod h) s + (x mod w) that reproduces all 2048 pixels, and
whether 32 x 32 tiles do (T32: offset ((y mod h) div 32 * ceil(w / 32) + (x mod w) div 32) 1024 + (y mod 32) 32 + (x mod 32), a
reading of these rows, not a frozen rival).  For each type 5 row the values, the distinct rows and the x and y periods of the image.
Reads only the kept files and the frozen tables.
  fold/tx_read.py ATT_DIR"""
import os
import sys
sys.dont_write_bytecode = True
K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(K, "score"))
import score_g as S  # noqa: E402


def img(d, n):
    r = S.parse_out(S._open(os.path.join(d, n + ".txt")).decode(errors="replace"))["rows"]
    return [r[y] for y in range(32)]


def size(n):
    w, h = n.split("-")[2].split("x")[:2]
    return int(w), int(h)


def t32(w, h, x, y):
    x, y = x % w, y % h
    return ((y // 32) * -(-w // 32) + x // 32) * 1024 + (y % 32) * 32 + x % 32


def period(seq):
    for p in range(1, len(seq) + 1):
        if all(seq[i] == seq[i % p] for i in range(len(seq))):
            return p


def main(att):
    d = os.path.join(att, "tx")
    for t in S.table("tx", K):
        n = t["name"]
        im = img(d, n)
        ty = int(n.split("-")[1][2:]) if n.startswith("tx-ty") else int(n.split("-")[2][2:])
        name = n
        if ty in (1, 3, 4):
            w, h = size(n if n.startswith("tx-ty") else n.replace("tx-ctl-", "tx-"))
            tags = sum(1 for row in im for v in row if v >> 28 == 0xD)
            off = [[v & 0xFFFFFFF for v in row] for row in im]
            ss = [s for s in range(1, 257) if all(off[y][x] == (y % h) * s + x % w for y in range(32) for x in range(64))]
            tl = all(off[y][x] == t32(w, h, x, y) for y in range(32) for x in range(64))
            print("%-20s type %d %3d x %-3d tags %4d  raster stride %-8s T32 %s" % (
                name, ty, w, h, tags, ",".join(map(str, ss)) or "none", "yes" if tl else "no"))
        else:
            vals = sorted({v for row in im for v in row})
            rows = len({tuple(row) for row in im})
            px = period(im[0])
            py = period([row[0] for row in im])
            print("%-20s type 5 values %s, %d distinct rows, x period %d, y period %d, row 0 starts %s" % (
                name, ",".join("0x%08x" % v for v in vals), rows, px, py, " ".join("%x" % v for v in im[0][:16])))


if __name__ == "__main__":
    main(sys.argv[1])
