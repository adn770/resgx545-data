"""q107_rule.py: FROZEN rule for check C3 (Q107/Q038), written before any G = 1 dump was read.
Data read before this freeze: cases.tsv of depth-safe.c1 and c26 (job metadata only); ONE dump
(c1/dp-z05-g33-0x30-r1.depth.1.bin.gz, and its G = 1 twin, for LENGTH only = 802816 dwords each,
first 4 dwords of the G = 33 one = zero); E996 record, E628, E629 text; r10-x gen/z.py.

Prediction (RULE, H-LATE/HDR): the G = 1 job's depth dump at the 1024 x 768 grid (32 x 48 tiles of
32 x 16) holds, in every 512-dword slot s = ty * (G + 1) + tx (G = 1), the 512 dwords of the tile
the 3D visits last in region-header order among the tiles that map to s, each tile taken as it
stands in the G = 33 dump of the same scene and P (slot 34 * ty + tx, 512 dwords, zero tiles and
half-zero tiles included, dword for dword, sign bit as stored there: E629 says the sign is set
exactly when the first abort's threshold was raised, which is the same in both G, 5 of 5 cells).
Scored dwords: slots 0 .. 125 (the slots any tile maps to at G = 1), 64512 dwords. Dwords at slots
126 and above (not named by any tile) are reported apart, not scored.
Rivals, all scored the same way:
  R-FIRST:  first visited in header order wins the slot.
  R-RASTER: last in raster order wins (ty * 32 + tx).
  R-ZEROFIX: zero region fixed in slot space: predicted dword is 0 where the G = 33 dump holds 0
            at the SAME dword index, else the RULE's value.
Pass criterion per dump: RULE held iff all 64512 scored dwords equal (full 32-bit); also counted
per slot and per dword. A masked comparison (low 31 bits) is reported as a secondary line.
Control (non overflow, E489): same RULE on fit-1024x768-G{0,1,2}-ramp{x,y} from G33 same axis.
"""
import gzip
import struct

W, H = 1024, 768
TX, TY = 32, 48


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def macro(w, h):
    tx, ty = tiles(w, h)
    n = 4 if w * h >= 640 * 480 else 2
    return n, ((tx + n - 1) // n + 3) & ~3, ((ty + n - 1) // n + 3) & ~3


def header_rank(w, h):
    """copy of r10-x gen/z.py header_rank (sgx-pipe ta.rs header_order)."""
    n, mx, my = macro(w, h)
    tx, ty = tiles(w, h)
    order = sorted(range(mx * my), key=lambda i: (i // mx // 4, i % mx // 4, i // mx % 4, i % mx % 4))
    rank, k = {}, 0
    for m in range(n * n):
        for i in order:
            c, r = (m // n) * mx + i % mx, (m % n) * my + i // mx
            if c < tx and r < ty:
                rank[(c, r)] = k
                k += 1
    return rank


def raster_rank(w, h):
    tx, ty = tiles(w, h)
    return {(c, r): r * tx + c for r in range(ty) for c in range(tx)}


def owners(w, h, g, rank, late):
    best = {}
    for t, k in rank.items():
        s = t[1] * (g + 1) + t[0]
        if s not in best or (k > rank[best[s]] if late else k < rank[best[s]]):
            best[s] = t
    return best


def load(path):
    b = gzip.open(path).read()
    return struct.unpack("<%dI" % (len(b) // 4), b)


def predict(g33, w, h, g, model, g33_pitch=33):
    """{dword index: value}. g33 = dword tuple of the G = 33 dump (or the control's G 33)."""
    tx, _ = tiles(w, h)
    if model == "RULE":
        own = owners(w, h, g, header_rank(w, h), True)
    elif model == "R-FIRST":
        own = owners(w, h, g, header_rank(w, h), False)
    elif model == "R-RASTER":
        own = owners(w, h, g, raster_rank(w, h), True)
    elif model == "R-ZEROFIX":
        own = owners(w, h, g, header_rank(w, h), True)
    else:
        raise ValueError(model)
    out = {}
    for s, (c, r) in own.items():
        src = 512 * (r * (g33_pitch + 1) + c)
        for k in range(512):
            v = g33[src + k]
            if model == "R-ZEROFIX" and g33[512 * s + k] == 0:
                v = 0
            out[512 * s + k] = v
    return out
