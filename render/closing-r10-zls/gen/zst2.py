# SPDX-License-Identifier: MIT
"""zst2.py: stage zst2 (seeds plan closing10/seeds/exp-seeds-r10.md section 5, decision R10-4 (a),
Q120): E978's stored formats 3 to 7 again, now with E985's offline layouts frozen per byte.

Every row is r9-x's zst form (gen/zls.py there; E978): `tri --depth` with E466/E467's store
control (G = tiles across - 1, the format in bits 26:24), the stencil loaded (bits 1 and 13) and
stored (bit 17) into `--stencil-store`, depth less with writes (ISP word 0 0x00400200), every
buffer dumped. Four depth planes, each with its own format-0 reference (a control: every dword of
the target's tiles stored, E831's count, and the loaded stencil copied, E467's count):

  x  E978's x ramp, `--tri-full --tri-z 0.25,0.75,0.25`, 64 x 32 (G 1): its reference reruns
     E978's z120-ctl-s; z2x-f4 replicates z120-f4-s (a control: 640 changed dwords, E978) and is
     scored on E985's f4 layout too (E985's fit set: not counted as held out); formats 3, 4 and
     7 with the stencil fills 0x00000000, 0xffffffff and 0xa5a5a5a5 (lanes 1 to 3 of every byte
     and f7's dependence on the data); E978's other index-fill rows are not rerun
  y  a y ramp, `--tri-full --tri-z 0.25,0.25,0.75`, formats 3 to 7 (f6's row order; 3 against 5)
  d  the depth range 0 to 1 over the target: the triangle (0,0) (2W,0) (0,2H) at depths 0, 1, 1,
     so z = x / 2W + y / 2H (formats 3 to 7: the depth coding of f4's 0xf0 and of f7's marks)
  e  40 x 20 (edge tiles, G 1), the x ramp, `--depth-pages 16` (the known weakness
     depth_min_pages: explicit, above every format's whole-tile extent), formats 3 and 6

Frozen (closing10/seeds/q120/frozen_rules.md, sha256 86f0701a..., E985 [SEMI]; this module is its
code, frozen with the session), per byte of the stored buffer, from the row's own format-0
reference and its own kept stencil dump (the loaded stencil):
  TILES  tile (tx, ty) in block 2 tw (ty >> 1) + 2 tx + (ty & 1), tw = G + 1, of 640 (f3, f5),
         512 (f6) or 256 (f4) dwords
  F3/F5  a tile is 16 chunks of 160 bytes, chunk r = row y; pixel x is the record (the reference
         float with the sign bit set, little endian, then its stencil byte) at the address rule
  F4     8 groups of 80 bytes (rows 2n, 2n + 1); record m = 8 (y & 1) + x div 4 is [0xf0, the
         stencil bytes of x = 4 qd + 3, + 2, + 1, + 0] at the same address rule
  F6     dword 32 r + x of the tile's 512: the reference float of (x, y = r) with the sign set
The stencil byte a pixel pairs with: byte j of its tile slot's 512 (slot = ty tw + tx), j by
  H-DEPTHORD  j = y0 x0 y1 x1 y2 x2 y3 x3 x4 (E985's reading; the frozen layouts' own)
  H-RASTER    j = 32 y + x,  H-F2ORD  j = y0 y1 x0 y2 x1 y3 x2 x3 x4 (E985: 0 of 13 tiles)
Rivals for f6's rows: H-F6ITI (dword = the depth in-tile index of the pixel, E465's order).
Every format 3 to 7 leaves the stencil store unwritten (H-E978: sst_changed 0).
f7 is a reading (changed dwords, its dwords that equal f4's of the same plane and fill).
A model holds on a row when every byte it predicts matches and every changed dword of the
buffer is one it predicts whole. z2e-f0's control is E831's count alone (E977 held it at edge
tiles); its stencil store count is a reading (E467 ran whole tiles)."""
STORE = 0x00171004       # E466/E467's 0x0017110c without G (bits 11:3)
LESS = 0x00400200
FILL = 0xDEADBEEF
SIGN = 0x80000000
LOAD_STENCIL = 0x2002    # bits 1 and 13 (E467)
MAIN = "tri --keep-going --wait-ms 20000"
STAGE = "zst2"
FROZEN_RULES_SHA = "86f0701a5dda0cd9947fa18fe386de81a21f5d4cafde8cf1550f6b04dfa1de55"
EDGE_PAGES = 16

# plane: (W, H, geometry args, extra args)
PLANES = {
    "x": (64, 32, "--tri-full --tri-z 0.25,0.75,0.25", ""),
    "y": (64, 32, "--tri-full --tri-z 0.25,0.25,0.75", ""),
    "d": (64, 32, "--tri-v 0,0,32768,0,0,16384 --tri-z 0,1,1", ""),
    "e": (40, 20, "--tri-full --tri-z 0.25,0.75,0.25", f"--depth-pages {EDGE_PAGES}"),
}
FILLS = {"s00": "0x00000000", "sff": "0xffffffff", "sa5": "0xa5a5a5a5"}
ORDERS = ("H-DEPTHORD", "H-RASTER", "H-F2ORD")
F4_E978 = 640            # z120-f4-s's changed dwords (E978, 64 x 32)


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def ctl(w, h, fmt):
    tx, _ = tiles(w, h)
    return STORE | (tx - 1) << 3 | fmt << 24 | LOAD_STENCIL


def args(plane, fmt, fill="index"):
    w, h, geo, extra = PLANES[plane]
    a = (f"{MAIN} --width {w} --height {h} --max-width {w} --max-height {h} {geo} --depth "
         f"--depth-ctl {ctl(w, h, fmt):#010x} --depth-fill {FILL:#010x} --stencil --stencil-fill "
         f'{fill} --stencil-store --depth-dump "$W" --poke blk:1={LESS:#010x}')
    return a + (" " + extra if extra else "")


def ref_of(name):
    """the format-0 reference row of a row: z2P-f0"""
    return name.split("-")[0] + "-f0"


def fmt_of(name):
    return int(name.split("-")[1][1:])


def plane_of(name):
    return name.split("-")[0][2:]


def models(fmt, fill):
    if fmt in (3, 4, 5):
        return ("H-E985",) + (("H-E985/H-RASTER", "H-E985/H-F2ORD") if fill == "index" else ())
    if fmt == 6:
        return ("H-E985", "H-F6ITI")
    return ()


def jobs():
    """[(name, set, knobs, args, {quantity: {model: value}})] in run order"""
    out = []
    for p in ("x", "y", "d", "e"):
        w, h, _, _ = PLANES[p]
        tx, ty = tiles(w, h)
        q0 = {"depth_changed": {"H-E831": str(512 * tx * ty)}}
        if p != "e":        # E467's stencil copy ran on whole tiles only: at 40 x 20 a reading
            q0["sst_changed"] = {"H-E467": str(128 * tx * ty)}
        out.append((f"z2{p}-f0", "control", "expectdiff reads:depth_changed,sst_changed",
                    args(p, 0), q0))
        fmts = {"e": (3, 6), "x": (4,)}.get(p, (3, 4, 5, 6, 7))   # x: E978's own (fit) rows
        for f in fmts:
            n = f"z2{p}-f{f}"
            q = {"sst_changed": {"H-E978": "0"}}
            if f != 7:
                q["bytes"] = {m: f"rule:{ref_of(n)}" for m in models(f, "index")}
            if p == "x" and f == 4:
                q["depth_changed"] = {"H-E978": str(F4_E978)}
                out.append((n, "control", "expectdiff reads:depth_changed", args(p, f), q))
            else:
                out.append((n, "heldout" if f != 7 else "reading", "expectdiff", args(p, f), q))
        if p == "x":
            for s, v in FILLS.items():
                for f in (3, 4, 7):
                    n = f"z2x-f{f}-{s}"
                    q = {"sst_changed": {"H-E978": "0"}}
                    if f != 7:
                        q["bytes"] = {m: f"rule:{ref_of(n)}" for m in models(f, v)}
                    out.append((n, "heldout" if f != 7 else "reading", "expectdiff",
                                args("x", f, v), q))
    return out


# ---- the layouts (E465, and E985's frozen rules) -------------------------------------------------
def in_tile_index(x, y):
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def j_order(order, x, y):
    if order == "H-DEPTHORD":
        return in_tile_index(x, y)
    if order == "H-RASTER":
        return 32 * y + x
    if order == "H-F2ORD":
        bits = [y & 1, y >> 1 & 1, x & 1, y >> 2 & 1, x >> 1 & 1, y >> 3 & 1, x >> 2 & 1,
                x >> 3 & 1, x >> 4 & 1]
        return sum(b << i for i, b in enumerate(bits))
    raise ValueError(order)


def block(tx, ty, tw):
    return 2 * tw * (ty >> 1) + 2 * tx + (ty & 1)


def addr(m, q):
    """the address in a chunk (f3, f5) or group (f4) of record m, byte q (E985)"""
    g = m // 3
    a = 1 + 17 * g + 5 * (2 - m % 3) + q
    return a - 32 if a >= 16 * (g + 1) else a


def predict(fmt, model, ref, sten, w, h):
    """{byte offset: value} of the stored buffer under a model, from the format-0 reference
    (dwords) and the loaded stencil (bytes) of the same row's plane."""
    tw, th = tiles(w, h)
    order = model.split("/")[1] if "/" in model else "H-DEPTHORD"
    pred = {}

    def depth(tx, ty, x, y):
        return ref[512 * (ty * tw + tx) + in_tile_index(x, y)] | SIGN

    def sbyte(slot, x, y):
        return sten[slot * 512 + j_order(order, x, y)]

    for ty in range(th):
        for tx in range(tw):
            slot = ty * tw + tx
            bl = block(tx, ty, tw)
            if fmt in (3, 5):
                base = bl * 2560
                for r in range(16):
                    for x in range(32):
                        rec = list(depth(tx, ty, x, r).to_bytes(4, "little")) + [sbyte(slot, x, r)]
                        for q in range(5):
                            pred[base + 160 * r + addr(x, q)] = rec[q]
            elif fmt == 6:
                base = bl * 2048
                for r in range(16):
                    for x in range(32):
                        d = depth(tx, ty, x, r)
                        k = 32 * r + x if model == "H-E985" else in_tile_index(x, r)
                        for q in range(4):
                            pred[base + 4 * k + q] = d >> (8 * q) & 0xFF
            elif fmt == 4:
                base = bl * 1024
                for n in range(8):
                    for yy in range(2):
                        y = 2 * n + yy
                        for qd in range(8):
                            m = 8 * yy + qd
                            rec = [0xF0] + [sbyte(slot, 4 * qd + k, y) for k in (3, 2, 1, 0)]
                            for q in range(5):
                                pred[base + 80 * n + addr(m, q)] = rec[q]
            else:
                raise ValueError(fmt)
    return pred


def check(pred, dump):
    """(held, bytes matched, bytes predicted, changed dwords, changed dwords predicted whole)"""
    b = bytes(dump) if isinstance(dump, (bytes, bytearray)) else b"".join(
        v.to_bytes(4, "little") for v in dump)
    ok = sum(1 for o, v in pred.items() if o < len(b) and b[o] == v)
    changed = [k for k in range(len(b) // 4) if int.from_bytes(b[4 * k:4 * k + 4], "little") != FILL]
    whole = sum(1 for k in changed if all(4 * k + q in pred for q in range(4)))
    return ok == len(pred) and whole == len(changed), ok, len(pred), len(changed), whole
