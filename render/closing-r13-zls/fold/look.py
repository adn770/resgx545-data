#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/look.py: r13-zls's post hoc reads (written after the run, not frozen) of the kept attempt
out/20261113-213117. Run from the session directory: python3 fold/look.py > fold/look.out

1. zbase: the offset d of each move (store dword k = depth dword k + d) and the base granule the
   seven moves allow.
2. zbits: per stencil row, which layout of the stencil store (E988's in-tile depth order or a
   linear image with rows of 64 bytes) and which order of the loaded stencil (the same two)
   explain every byte: the loaded byte is the stored one, inverted where the pixel was drawn (SOP3
   invert), and the bytes fill puts byte b at b mod 256.
3. zfmt: zf-flat-f6's changed dwords against F6C's prediction, group by group."""
import gzip
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import z13 as Z  # noqa: E402

D = os.path.join(KP, "out/20261113-213117")


def rd(stage, name):
    return gzip.open(os.path.join(D, stage, name + ".gz")).read()


def pix(t):
    rows = {}
    for ln in t.splitlines():
        if ln.startswith("row "):
            k, _, v = ln[4:].partition(": ")
            rows[int(k)] = v.split()
    return {(x, y) for y in rows for x, v in enumerate(rows[y]) if int(v, 16) == Z.TRI_COLOUR}


Z.TRI_COLOUR = 0xFF00FF00
print("== 1. zbase: the offset of each move")
ds = {}
for n, m in Z.ZB_MOVES.items():
    st = Z.dwords(rd("zbase", n + ".depth-store.1.bin"))
    d = {st[k] - k for k in range(Z.ZB_N)}
    ds[n] = d
    print(f"{n}: rd:12 move {'store base' if m is None else hex(m)}: d {sorted(d)[:3]}"
          f"{' (one offset)' if len(d) == 1 else ''}")
print("granules g (bytes, a power of two) with floor((0x1000 + m) / g) * g - 0x1000 = 4 d on every "
      "move:", [g for g in (4, 8, 16, 32, 64, 128, 256, 2048, 4096) if all(
          ((0x1000 + m) // g * g - 0x1000) == 4 * next(iter(ds[n]))
          for n, m in Z.ZB_MOVES.items() if m is not None)])

print("== 2. zbits: stencil store layout and load order (bytes explained of 2048)")
sl = lambda x, y: (2 * (y // 16) + x // 32) * 512  # noqa: E731
LAY = {"depth": lambda x, y: sl(x, y) + Z.in_tile_index(x, y), "linear64": lambda x, y: 64 * y + x}
ZBITS_CTL = lambda n: Z.ZBITS[n].split("--depth-ctl ")[1].split()[0]  # noqa: E731
for n in [x for x in Z.ZBITS if x.startswith("zbs-")]:
    s = rd("zbits", n + ".stencil-store.1.bin")
    p = pix(rd("zbits", n + ".txt").decode())
    fits = []
    for ls, fs in LAY.items():
        for ll, fl in LAY.items():
            ok = 0
            for y in range(32):
                for x in range(64):
                    v = s[fs(x, y)]
                    ok += ((v ^ 0xFF) if (x, y) in p else v) == fl(x, y) & 0xFF
            fits.append((ok, ls, ll))
    best = max(fits)
    zero = all(s[LAY["depth"](x, y)] == 0xFF for y in range(32) for x in range(64))
    print(f"{n}: control {ZBITS_CTL(n)}"
          f"; drawn {len(p)}; " + ", ".join(f"store {a} / load {b} {o}" for o, a, b in sorted(fits, reverse=True))
          + ("; every stored byte 0xff (the test read 0, stored inverted)" if zero else ""))

print("== 3. zfmt: zf-flat-f6 against F6C")
import score as SC  # noqa: E402
rule = SC.c7()
dw = Z.dwords(rd("zfmt", "zf-flat-f6.depth.1.bin"))
for blk, q, pred, raw in Z.f6_groups(Z.flat_rows(64, 32), 64, 32, rule)[:4]:
    got = dw[512 * blk + 12 * q:512 * blk + 12 * q + 12]
    print(f"block {blk} group {q}: got  " + " ".join(f"{v:08x}" for v in got))
    print(f"{'':19}F6C  " + " ".join(f"{v:08x}" for v in pred))
ch = [(i, v) for i, v in enumerate(dw) if v != Z.FILL_DEAD]
print("changed dwords:", len(ch), "at", sorted({i // 512 for i, _ in ch}), "blocks;",
      "offsets in the block", sorted({i % 512 for i, _ in ch}))
print("distinct values:", sorted({f"{v:08x}" for _, v in ch}))
