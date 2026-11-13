#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ol7_a_dumps.py (round 8, leftovers OL7 (a), Q210, record P3; offline, read-only, a dump check
written before it was run, which can fail). P3 [infer, source reading]: `--vtx-coords N` raises the
vertex size and the outputs the TA takes, but the default vertex program writes o0 to o3 only, so
the TA receives whatever o4 on held. Check: the object blocks of the published 2048x2048
calibration dumps of the tool's 1500-vertex triangle (R6-dpm out/a2/r-v and R7-dpm out/a1/s-v,
v-cal-c4 with --vtx-coords 4 and v-cal-c8 with 8, the same command run in two sessions):

  P3-DUMP  at N 8 the object blocks of the two runs differ (in size or in some dword), and at
           N 4 every object block is the same dwords in both runs.

Objects are read as g5_blocks.py read them (every region's stream chain, the global list's pages
put in object order, objects ranked by ISP address, a block from its address to the next object's
or its page's end). Refuted by: N 4 blocks that differ, or N 8 blocks that are the same.

  python3 -I -B ol7_a_dumps.py
"""
import collections
import gzip
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ol7lib as L  # noqa: E402
from f3_streams import chain, regions  # noqa: E402  (published round 6 library, hash-checked)
from pbdump import PB_BASE  # noqa: E402

W = H = 2048
RUNS = {"R6-dpm": ("closing-r6-dpm", "out/a2/r-v"), "R7-dpm": ("closing-r7-dpm", "out/a1/s-v")}


def blocks(pre):
    param = gzip.open(pre + "param.bin.gz").read()
    tad = gzip.open(pre + "tadata.bin.gz").read()
    seqs = []
    for r in regions(tad, W, H):
        if r.stream:
            seqs.append([a for addr, ents, used in chain(param, r.stream) for _, a, _, _ in ents])
    pages = sorted({a // 1024 for s in seqs for a in s})
    before = collections.defaultdict(set)
    for s in seqs:
        ps = []
        for a in s:
            if not ps or ps[-1] != a // 1024:
                ps.append(a // 1024)
        for x, y in zip(ps, ps[1:]):
            before[y].add(x)
    order, left = [], set(pages)
    while left:
        nxt = sorted(p for p in left if not (before[p] & left))
        if len(nxt) != 1:
            raise SystemExit(f"{pre}: global page order not total")
        order.append(nxt[0])
        left.discard(nxt[0])
    gpos = {p: i for i, p in enumerate(order)}
    lin = sorted({(gpos[a // 1024] * 1024 + a % 1024, a) for s in seqs for a in s})
    out = []
    for i, (la, a) in enumerate(lin):
        end = lin[i + 1][0] if i + 1 < len(lin) else la + 256
        n = min(end - la, 1024 - a % 1024)
        out.append(struct.unpack_from(f"<{n}I", param, 4 * a - PB_BASE))
    return out


def main():
    got = {}
    for run, (ds, sub) in RUNS.items():
        for n in (4, 8):
            pre = os.path.join(str(L.DATA), "render", ds, sub, f"v-cal-c{n}.p1139-green.")
            got[(run, n)] = blocks(pre)
            b = got[(run, n)]
            print(f"{run} N {n}: {len(b)} objects, block sizes (first 8) {[len(x) for x in b[:8]]}")
    res = {}
    for n in (4, 8):
        a, b = got[("R6-dpm", n)], got[("R7-dpm", n)]
        same_n = len(a) == len(b)
        same = sum(1 for x, y in zip(a, b) if x == y)
        diff_dw = sum(1 for x, y in zip(a, b) for u, v in zip(x, y) if u != v)
        size = sum(1 for x, y in zip(a, b) if len(x) != len(y))
        res[n] = same_n and same == len(a)
        print(f"N {n}: objects {len(a)} and {len(b)}; identical blocks {same}; blocks of another size "
              f"{size}; differing dwords in the common part {diff_dw}")
    ok = res[4] and not res[8]
    print("VERDICT P3-DUMP:", "HELD (N 4 blocks identical across the runs, N 8 blocks differ)" if ok
          else f"REFUTED (N 4 identical: {res[4]}, N 8 identical: {res[8]})")


if __name__ == "__main__":
    main()
