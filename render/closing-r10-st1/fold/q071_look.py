#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/q071_look.py (post hoc, not frozen): what the inert control bits changed in q071-b0 and
q071-l1 against st1-b0 and st1-lane1: drawn counts, the image difference by H-DEPTHORD byte lane
and in-tile index, the stencil store and depth dumps, and the tool's summary lines.
Usage: python3 -I -B fold/q071_look.py [KEPT_DIR] > fold/q071_look.out"""
import gzip
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
import st1 as S  # noqa: E402

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KP, "out/20261113-103934/st1")


def rd(n, suf):
    p = os.path.join(D, n + suf)
    return gzip.open(p + ".gz").read() if os.path.exists(p + ".gz") else open(p, "rb").read()


for q, base in (("q071-b0", "st1-b0"), ("q071-l1", "st1-lane1")):
    tq, tb = rd(q, ".txt").decode(), rd(base, ".txt").decode()
    iq, ib = S.pixels_drawn(tq, 64, 32), S.pixels_drawn(tb, 64, 32)
    print(f"## {q} vs {base}")
    for t, n in ((tq, q), (tb, base)):
        print(n, [ln for ln in t.splitlines() if ln.startswith(("depth", "stencil", "tri 64", "job", "tri: isp2"))])
    print("drawn", len(iq), len(ib), "only in q071", len(iq - ib), "only in base", len(ib - iq))
    lanes = {}
    for (x, y) in iq ^ ib:
        j = S.in_tile_index(x, y)
        lanes[j & 3] = lanes.get(j & 3, 0) + 1
    print("differing pixels by lane", sorted(lanes.items()))
    for suf in (".stencil-store.1.bin", ".depth.1.bin", ".stencil.1.bin"):
        a, b = rd(q, suf), rd(base, suf)
        nd = sum(1 for i in range(0, min(len(a), len(b)), 4) if a[i:i + 4] != b[i:i + 4])
        print(suf, "dwords differ", nd, "of", len(a) // 4,
              "first", [(i // 4, a[i:i + 4].hex(), b[i:i + 4].hex()) for i in range(0, len(a), 4)
                        if a[i:i + 4] != b[i:i + 4]][:4])
    rows = [y for y in range(32) if any((x, y) in iq for x in range(64))]
    print("q071 drawn rows", rows[:8], "...", len(rows))
print("## q071 stores as H-NOLOAD (the ISP's stencil 0, inverted: 0xff) over the 4 tiles' 512 dwords")
for q in ("q071-b0", "q071-l1"):
    a = rd(q, ".stencil-store.1.bin")
    print(q, "0xffffffff dwords in the first 512:", sum(a[i:i + 4] == b"\xff" * 4 for i in range(0, 2048, 4)),
          "rest at the fill:", all(a[i:i + 4] == bytes.fromhex("efbeadde") for i in range(2048, len(a), 4)))
