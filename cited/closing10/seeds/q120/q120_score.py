#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Round 10 seeds, Q120/Q121 offline decode of the r9-x zst dumps (E978): packed depth formats 3 to 7 and
the stencil in-tile order. Reads only the published dumps. Fit on 64 x 32 ('s'), then checks that
frozen_rules.md still has its recorded sha256 and scores 96 x 48 ('m'). Run with python -I -B."""
import gzip
import hashlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D = "/Users/jtorra/src/resgx545-data/render/closing-r9-x/out/20261113-081821/zst"
SIGN = 0x80000000
FILL = 0xDEADBEEF
SIZES = {"s": (64, 32), "m": (96, 48)}


def ld(name, kind, sz):
    return np.frombuffer(gzip.open(f"{D}/z120-{name}-{sz}.{kind}.1.bin.gz").read(), dtype="<u4")


def in_tile_index(x, y):
    j = 0
    for i in range(4):
        j |= ((y >> i) & 1) << (2 * i) | ((x >> i) & 1) << (2 * i + 1)
    return j | ((x >> 4) & 1) << 8


def j_depthord(x, y):
    return in_tile_index(x, y)


def j_raster(x, y):
    return 32 * y + x


def j_f2ord(x, y):  # y0 y1 x0 y2 x1 y3 x2 x3 x4 from the lowest bit
    bits = [y & 1, y >> 1 & 1, x & 1, y >> 2 & 1, x >> 1 & 1, y >> 3 & 1, x >> 2 & 1, x >> 3 & 1, x >> 4 & 1]
    return sum(b << i for i, b in enumerate(bits))


RIVALS = {"H-DEPTHORD": j_depthord, "H-RASTER": j_raster, "H-F2ORD": j_f2ord}


def stencil_byte(x, y, slot, jf=j_depthord):
    j = jf(x, y)
    i = slot * 128 + (j >> 2)
    return (i & 0xFF, (i >> 8) & 0xFF, 0, 0)[j & 3]


def block(tx, ty, tw):
    return 2 * tw * (ty >> 1) + 2 * tx + (ty & 1)


def addr(m, q):
    """address in a chunk of record m, byte q (the rule of frozen_rules.md)."""
    g = m // 3
    a = 1 + 17 * g + 5 * (2 - m % 3) + q
    return a - 32 if a >= 16 * (g + 1) else a


def ctl_depth(ctl, tx, ty, tw, x, y):
    return int(ctl[512 * (ty * tw + tx) + in_tile_index(x, y)])


def predict(fmt, ctl, W, H):
    tw, th = (W + 31) // 32, (H + 15) // 16
    pred = {}  # byte offset -> value
    for ty in range(th):
        for tx in range(tw):
            slot = ty * tw + tx
            bl = block(tx, ty, tw)
            if fmt in (3, 5):
                base = bl * 2560
                for r in range(16):
                    for x in range(32):
                        d = ctl_depth(ctl, tx, ty, tw, x, r) | SIGN
                        rec = list(d.to_bytes(4, "little")) + [stencil_byte(x, r, slot)]
                        for q in range(5):
                            pred[base + r * 160 + addr(x, q)] = rec[q]
            elif fmt == 6:
                base = bl * 2048
                for r in range(16):
                    for x in range(32):
                        d = ctl_depth(ctl, tx, ty, tw, x, r) | SIGN
                        for q in range(4):
                            pred[base + (r * 32 + x) * 4 + q] = (d >> (8 * q)) & 0xFF
            elif fmt == 4:
                base = bl * 1024
                for n in range(8):
                    for yy in range(2):
                        for qd in range(8):
                            m = 8 * yy + qd
                            y = 2 * n + yy
                            rec = [0xF0] + [stencil_byte(4 * qd + k, y, slot) for k in (3, 2, 1, 0)]
                            for q in range(5):
                                pred[base + 80 * n + addr(m, q)] = rec[q]
    return pred


def score(fmt, sz):
    W, H = SIZES[sz]
    ctl = ld("ctl", "depth", sz)
    d = ld(f"f{fmt}", "depth", sz)
    got = d.tobytes()
    pred = predict(fmt, ctl, W, H)
    ok = sum(1 for o, v in pred.items() if got[o] == v)
    changed = [o for o in range(len(got)) if d[o >> 2] != FILL]
    cb = np.frombuffer(got, dtype=np.uint8)
    nz = {o for o in range(len(got)) if d[o >> 2] != FILL}
    # changed dwords: every one whose four bytes are all predicted and equal
    dw_ok = dw_n = 0
    for k in np.nonzero(d != FILL)[0]:
        dw_n += 1
        offs = range(4 * k, 4 * k + 4)
        if all(o in pred and cb[o] == pred[o] for o in offs):
            dw_ok += 1
    stray = sum(1 for o in pred if d[o >> 2] == FILL)
    return ok, len(pred), dw_ok, dw_n, stray


def check_freeze():
    want = open(os.path.join(HERE, "frozen_rules.sha256")).read().split()[0]
    have = hashlib.sha256(open(os.path.join(HERE, "frozen_rules.md"), "rb").read()).hexdigest()
    return want == have, have


def rivals(sz):
    """H-* test on the stencil byte of the pixels whose record is NOT displaced (P mod 3 != 0 and the
    stencil byte at the depth's b2 byte + 2, b2 unique per x: rival neutral address). Per tile: the
    chunk -> row map and the slot are free; report whether a row for every chunk exists (bijection) and the
    pixels matched."""
    W, H = SIZES[sz]
    tw, th = (W + 31) // 32, (H + 15) // 16
    ctl = ld("ctl", "depth", sz)
    got = ld("f3", "depth", sz).tobytes()
    P_set = [1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 20, 23, 26, 29]
    out = {}
    for name, jf in RIVALS.items():
        res = []
        for ty in range(th):
            for tx in range(tw):
                bl = block(tx, ty, tw)
                base = bl * 2560
                # rival neutral s position: the byte 2 after the unique b2 byte of the pixel's depth in chunk 1
                pos = {}
                for P in P_set:
                    dv = (ctl_depth(ctl, tx, ty, tw, P, 0) | SIGN).to_bytes(4, "little")
                    cand = [i for i in range(156) if got[base + 160 + i:base + 160 + i + 4] == dv]
                    assert len(cand) == 1, (sz, tx, ty, P, cand)
                    pos[P] = cand[0] + 4
                obs = [[got[base + r * 160 + pos[P]] for P in P_set] for r in range(16)]
                best_slots = []
                for slot in range(tw * th):
                    rows = []
                    for r in range(16):
                        ys = [y for y in range(16)
                              if all(stencil_byte(P, y, slot, jf) == obs[r][i] for i, P in enumerate(P_set))]
                        rows.append(ys)
                    nzr = [r for r in range(16) if any(obs[r])]
                    nonempty = sum(1 for r in nzr if rows[r])
                    best_slots.append((nonempty, slot, rows))
                best_slots.sort(key=lambda t: -t[0])
                ne, slot, rows = best_slots[0]
                nzr = [r for r in range(16) if any(obs[r])]
                ident = sum(1 for r in nzr if r in rows[r])
                res.append((len(nzr), ne, slot, ident))
        out[name] = res
    return out


def main():
    for fmt in (3, 5, 6, 4):
        ok, n, dok, dn, stray = score(fmt, "s")
        print(f"FIT 64x32 f{fmt}: predicted bytes matched {ok}/{n}; changed dwords matched {dok}/{dn}; "
              f"predicted bytes left at the fill {stray}")
    f, h = check_freeze()
    print("frozen_rules.md sha256", h, "matches record:", f)
    if not f:
        sys.exit("rules changed after the freeze: not scoring 96 x 48")
    for fmt in (3, 5, 6, 4):
        ok, n, dok, dn, stray = score(fmt, "m")
        print(f"CHECK 96x48 f{fmt}: predicted bytes matched {ok}/{n}; changed dwords matched {dok}/{dn}; "
              f"predicted bytes left at the fill {stray}")
    for sz in ("s", "m"):
        r = rivals(sz)
        for name, res in r.items():
            print(f"RIVAL {name} {sz}: per tile (chunks with a nonzero stencil byte, of them with a matching row, best slot, of them with y == r): {res}")


if __name__ == "__main__":
    main()
