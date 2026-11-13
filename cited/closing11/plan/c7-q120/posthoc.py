"""posthoc.py [post hoc]: fitted AFTER block 1 / block 2 of z2y-f6 were read (not held out).
Rule B = RULE_F6C with a row that holds a mode value v for 32 - n pixels and v + 1 (one unit of
the last place, up) for n pixels at the largest x: record float = v, mask word =
0x3f000000 | 1 << (24 - n) (n = 0: 0x3f000000 as before).  Scored on every group of z2y-f6
whose rows all fit that form and whose earlier groups do."""
import struct
from lib import *
import c7_rule as R
import zst2 as Z


def row_form(vals):
    """vals: 32 x-ordered dwords -> (v, n, tail_ok) if v for x < 32 - n and v + 1 after"""
    v = vals[0]
    n = sum(1 for a in vals if a != v)
    if all(a == v for a in vals[:32 - n]) and all(a == v + 1 for a in vals[32 - n:]):
        return v, n
    return None


def groupB(forms):
    v = [f[0] for f in forms]
    p = bytearray(struct.pack("<12I", *R.f6c_group(v)))
    for r in range(4):
        i = 4 * R.MASKDW[r]
        p[i:i + 4] = struct.pack("<I", 0x3f000000 | (1 << (24 - forms[r][1]) if forms[r][1] else 0))
    return list(struct.unpack("<12I", bytes(p)))


d = dw("zst2", "z2y-f6")
ref = dw("zst2", "z2y-f0")
tw = 2
for ty in range(2):
    for tx in range(2):
        blk = 2 * tw * (ty >> 1) + 2 * tx + (ty & 1)
        slot = ty * tw + tx
        data = d[512 * blk:512 * blk + 512]
        res = []
        for q in range(4):
            fs = []
            for r in range(4 * q, 4 * q + 4):
                vals = [ref[512 * slot + Z.in_tile_index(x, r)] for x in range(32)]
                fs.append(row_form(vals))
            if None in fs:
                break
            res.append(data[12 * q:12 * q + 12] == groupB(fs))
        chg = sum(v != FILL for v in data)
        print(f"tile ({tx},{ty}) block {blk}: changed {chg}; groups fitting form B {len(res)}; "
              f"held {sum(res)}, failed {len(res) - sum(res)}; decoded dwords {12 * sum(res)}")
