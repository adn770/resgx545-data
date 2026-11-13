#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/zbits_layout.py: r10-x's post hoc read of zbits (not frozen). The rows with bits 12, 16
and 20 of the ZLS control cleared (zb-all-*, zb-clr-f0) store the same values as the control but
at other dwords; this reads which: for each kept dump, every dword of the target's tiles is
compared with the control's value of the pixel each candidate layout puts there.
  H-TWID: the control's in-tile index (E465/E490, r9-x gen/zls.py in_tile_index)
  H-LIN:  dword 512 (ty (G + 1) + tx) + 32 y + x, raster order inside the tile
  H-STRIDE: dword 32 (G + 1) y + x, one linear image of the tile area, rows of 32 (G + 1) dwords
The z242-c ramp depends on x only (z 1, 0, 1 at (0,0), (2W,0), (0,2H)), so a layout is read by
the x each dword's value names; y is not named by the values (a reading, post hoc).
Usage: python3 fold/zbits_layout.py OUT_DIR (the attempt directory)."""
import gzip
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "gen"))
sys.dont_write_bytecode = True
import z as Z  # noqa: E402


def in_tile_index(x, y):
    """E465's twiddle inside a 32 x 16 tile (r9-x gen/zls.py)."""
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def in_tile_pixel(k):
    x, y = (k >> 8 & 1) << 4, 0
    for b in range(4):
        y |= (k >> (2 * b) & 1) << b
        x |= (k >> (2 * b + 1) & 1) << b
    return x, y


def dump(d, n):
    b = gzip.open(os.path.join(d, n + ".depth.1.bin.gz")).read()
    return struct.unpack("<%dI" % (len(b) // 4), b)


def pixels(ctl, w, h, g):
    """{(x, y): value} of the control's dump (twiddled tiles)."""
    out = {}
    tx, ty = Z.tiles(w, h)
    for t_y in range(ty):
        for t_x in range(tx):
            for k in range(512):
                x, y = in_tile_pixel(k)
                out[(32 * t_x + x, 16 * t_y + y)] = ctl[512 * (t_y * (g + 1) + t_x) + k]
    return out


def layouts(px, w, h, g):
    tx, ty = Z.tiles(w, h)
    twid, lin, stride = {}, {}, {}
    for (x, y), v in px.items():
        base = 512 * ((y >> 4) * (g + 1) + (x >> 5))
        twid[base + in_tile_index(x, y)] = v
        lin[base + 32 * (y & 15) + (x & 31)] = v
        stride[32 * (g + 1) * y + x] = v
    return {"H-TWID": twid, "H-LIN": lin, "H-STRIDE": stride}


def main(out):
    d = os.path.join(out, "zbits")
    for ctl, rows in (("zb-ctl-f0", ("zb-all-f0", "zb-clr-f0", "zb-set-f0", "zb-b0-f0")),
                      ("zb-ctl-f1", ("zb-all-f1", "zb-b0-f1"))):
        px = pixels(dump(d, ctl), 80, 40, 2)
        lay = layouts(px, 80, 40, 2)
        for n in rows:
            got = dump(d, n)
            res = ", ".join(f"{m} {sum(got[i] == v for i, v in p.items())}/{len(p)}"
                            for m, p in lay.items())
            print(f"{n} (against {ctl}'s pixels): {res}")


if __name__ == "__main__":
    main(sys.argv[1])
