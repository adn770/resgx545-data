#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/look.py: r14-zls's post hoc reads (written after the run, not frozen) of the kept attempt
out/20261114-054846. Run from the session directory: python3 fold/look.py > fold/look.out

1. zgran: the five granule rows' offsets and the granules of 4 to 128 bytes they allow with
   E1029's seven moves (H-BYTE, +4 and +0x40 included).
2. zbits2: the set-half rows read model-free (score.stencil_fit's read: the stored byte XOR 0xff
   where the pixel drew is the loaded byte of E988's bytes fill), the drawn count, and for the
   rows the loaded byte does not explain, the byte the test saw and the drawn columns.
3. zflat: each flat block against E1031's with row 0's record (bytes 7 to 10) set to v."""
import gzip
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402
import z14 as Z  # noqa: E402

D = os.path.join(KP, "out/20261114-054846")


def rd(stage, name):
    return gzip.open(os.path.join(D, stage, name + ".gz")).read()


print("== 1. zgran: granule offsets")
moves = {n: m for n, m in Z.GRAN_MOVES.items()}
ds = {}
for n, m in moves.items():
    st = Z.dwords(rd("zgran", n + ".depth-store.1.bin"))
    d = {st[k] - k for k in range(Z.ZB_N)}
    ds[m] = d.pop() if len(d) == 1 else None
    print(f"{n}: move {m:#x}: d {ds[m]}")
e1029 = {0x1000: 1024, 0x4000: 4096, 0x10000: 16384, 0x800: 512, 0x40: 16, 0x4: 0}
allm = {**e1029, **ds}
print("granules g with floor((0x1000 + m) / g) g - 0x1000 = 4 d on all", len(allm), "moves:",
      [g for g in (4, 8, 16, 32, 64, 128) if all((0x1000 + m) // g * g - 0x1000 == 4 * d
                                                for m, d in allm.items())])

print("== 2. zbits2: the set-half rows")
for n in [x for x in Z.STAGE_ROWS["zbits2"] if x.startswith(("zb2-b", "zb2-g", "zb2-c-"))]:
    t = rd("zbits2", n + ".txt").decode()
    st = rd("zbits2", n + ".stencil-store.1.bin")
    dr = SC.drawn_set(t)
    ok = sum(1 for y in range(32) for x in range(64)
             if st[Z.st_pos(x, y)] ^ (0xFF if (x, y) in dr else 0) == Z.s_loaded("S-UNMOVED", x, y, "bytes"))
    seen = {st[Z.st_pos(x, y)] ^ (0xFF if (x, y) in dr else 0) for y in range(32) for x in range(64)}
    print(f"{n}: drawn {len(dr)}; the loaded byte explains {ok}/2048"
          + ("" if ok == 2048 else f"; bytes seen (store, XOR 0xff where drawn) {sorted(seen)}"))
    if 0 < len(dr) < 2048 and ok < 2048:
        cols = "".join("D" if (x, 0) in dr else "." for x in range(64))
        same = all(((x, y) in dr) == ((x, 0) in dr) for y in range(32) for x in range(64))
        print(f"   row 0 drawn {cols}; every row alike {same}; period 16 in x "
              f"{all(((x, 0) in dr) == ((x % 16, 0) in dr) for x in range(64))}")

print("== 3. zflat: the flat blocks against E1031's with row 0's record at v (FL-REC0)")
ref = SC.kept("zl-c-flat")[:176]
for n in Z.FLAT_DEPTHS:
    b = rd("zflat", n + ".depth.1.bin")
    v = Z.flat_v(n)
    sub = bytearray(ref)
    sub[7:11] = struct.pack("<I", v)
    per = [sum(1 for i in range(176) if b[2048 * k + i] != ref[i]) for k in range(4)]
    print(f"{n}: v {v:#010x}; bytes differing from E1031's a block {per}; FL-REC0 "
          f"{sum(b[2048 * k:2048 * k + 176] == bytes(sub) for k in range(4))}/4 blocks")
