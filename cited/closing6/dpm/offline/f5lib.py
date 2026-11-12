#!/usr/bin/env python3
"""F5's block-level replay of the TA for the tool's triangle with 1500 vertices (round 6 dpm
offline stage, H-STEPMODEL [infer]).  The scene (userspace/libsgxfive src/tri_probe.c
put_copies): triangle j (vertices 3j..3j+2, j = 0..499) is the default triangle moved j/16 pixel
right and down; object b holds triangles 5b..5b+4 (15 vertices, F2's 67-dword blocks).  Its
constants are read from the dumps (F2, F3), none fitted to a step:
- L = 67 dwords an object block, 18 the first block's ISP offset: global page k is requested by
  object b_k = floor(1024 (k - 1) / 67);
- a region's stream entry for an object is 2 dwords when the object meets both 16 x 16 tiles
  with all five primitives in each (0x90) or one tile with at most two (0x80, 0x98), else 3 (a
  mask dword: 0x88, 0x8a, 0x8c), plus 1 at object b_k (the base dword, F3); a 128-byte block
  holds 31 dwords of entries and the link; a region opens a block at its first entry and when
  the next entry does not fit;
- a macrotile takes a page when a block opens and its current page holds 32 blocks already.
The tile test is HU1's (closing5/r5-dpm/gen/hu1.py, E773), unchanged."""
import math, os, sys
DATA = os.environ.get('RESGX545_DATA', '/Users/jtorra/src/resgx545-data')
sys.path.insert(0, os.path.join(DATA, 'render', 'closing-r5-dpm', 'gen'))
import hu1 as H

L, CAP, BPP, OBJS, PER = 67, 31, 32, 100, 5


def tri(w, h, j):
    return H.default_tri(w, h, j / 16.0, j / 16.0)


def bk(k):
    return (1024 * (k - 1)) // L


def entries(w, h):
    """{object: [(region col, row, dwords without the base)]} in row order of the target."""
    tx, ty, n, mx, my = H.tiling(w, h)
    out = {}
    for b in range(OBJS):
        ts = [tri(w, h, PER * b + i) for i in range(PER)]
        x0 = min(p[0] for t in ts for p in t); x1 = max(p[0] for t in ts for p in t)
        y0 = min(p[1] for t in ts for p in t); y1 = max(p[1] for t in ts for p in t)
        ents = []
        for r in range(max(0, int(y0 // 16)), min(ty, int(y1 // 16) + 1)):
            for c in range(max(0, int(x0 // 32)), min(tx, int(x1 // 32) + 1)):
                xa, ya = 32.0 * c, 16.0 * r
                left = sum(1 for t in ts if H.tile_lists(t, xa, ya))
                right = sum(1 for t in ts if H.tile_lists(t, xa + 16, ya))
                if not left and not right:
                    continue
                if left and right:
                    dw = 2 if left == PER and right == PER else 3
                else:
                    dw = 2 if max(left, right) <= 2 else 3
                ents.append((c, r, dw))
        out[b] = ents
    return out


def mtile(w, h, c, r):
    tx, ty, n, mx, my = H.tiling(w, h)
    return (c // mx) * n + r // my


def replay(w, h, ents, lag):
    """Page counts: the TA writes object b to the global list just before it tiles object
    b - lag (lag 0: before tiling b itself).  Returns (S {k: pages before global page k},
    opens {object: blocks opened}, pages after tiling each object)."""
    used = {}; blocks = {}; mt_blocks = {}; pages = 1; S = {}; opens = {}; after = []
    gk = {bk(k): k for k in range(2, 12)}
    writes = {}
    for b in range(OBJS):
        writes.setdefault(max(0, b - lag), []).append(b)
    for t in range(OBJS):
        for b in writes.get(t, []):
            if b in gk:
                S[gk[b]] = pages; pages += 1
        o = 0
        for c, r, dw in ents[t]:
            dw += 1 if t in gk else 0
            key = (c, r)
            if key not in used or used[key] + dw > CAP:
                used[key] = 0; o += 1
                m = mtile(w, h, c, r)
                nb = mt_blocks.get(m, 0)
                if nb % BPP == 0:
                    pages += 1
                mt_blocks[m] = nb + 1
            used[key] += dw
        opens[t] = o
        after.append(pages)
    return S, opens, after
