# SPDX-License-Identifier: MIT
"""z14.py: r14-zls's rows and frozen rivals (round 14 plan closing14/plan/rank-round14.md sections
2 and 3, decisions R14-1 (a), R14-7 (a), R14-9 (a); tool t10, resgx545 a581c06 sgxfive-test.c).
Round 13's r13-zls (render/closing-r13-zls gen/z13.py, E1029 to E1031) is the direct predecessor:
its forms are copied here, not imported, so this file alone is frozen. The plan's four parts are
described below by record; the stages that run them group the rows by the dump their scorer reads
(STAGE_ROWS at the end), and a row's name prefix names its record.

Part zgran (Q243, record E1040; rows zg-). E1029's zbase form (64 x 32, --tri-full at 0.5, ZLS control
0x0017500e: depth loaded and stored, G 1; depth test never by `--poke blk:1=0x00000200`, so the
store holds what was loaded; depth buffer `index`, a store buffer of its own filled 0x3e800000,
`--depth-pages 20`: depth 0x3e001000, store 0x3e015000, base 0x3e000000) with
`--kpoke-render 1:rd:12=0x1000 + m` after depth_arm's own pokes (E1029's lead/dryrun_checks.out).
Granule rows m = +8, +16, +32, +0x1008, +0x1020: the store's dword k holds the depth buffer's
dword k + d, d = (floor((0x1000 + m) / g) g - 0x1000) / 4 under G8, G16, G32, G64 (E1029's post
hoc granules) and d = m / 4 under H-BYTE (refuted by E1029's zb-m4, kept as a negative).
Integer rows (H-MOVED-INT): formats 1 and 2 (0x0117500e, 0x0217500e) with m = +0x1000 and the
depth buffer filled `bit:10` (dword i holds 0.75 if bit 10 of i is set, else 0.25): E977 read an
integer format's load as the dword's float and stored it by the floor rule (z243-f1-less stored
0, z243-f2-less 0x80008000), so the store holds floor(L * 2^24) (format 1, E465's layout) or its
>> 8 two rows a dword (format 2, E490's layout) of the float L each pixel loads. The load reads:
  I-MOVED-L32    E465's 32-bit layout (512 dwords a tile) from the moved base (d = 1024)
  I-MOVED-L16    format 2 only: E490's 16-bit layout (256 dwords a tile, the pixel's pair dword)
  I-UNMOVED-L32, I-UNMOVED-L16   the same from the unmoved base (the poke does not reach it)
  I-STOREBASE    the store buffer (filled 0.5 in these two rows: neither of bit:10's floats)
Stencil row (zg-s14): E988's st1 form (64 x 32, the stencil loaded and stored, ISP word 2 EQUAL
against mask 0x01 with SOP3 invert, `--isp2 0x040501ff`) with the stencil filled `index` and the
stencil load base (render details dword 14, depth_arm's `rd:14 = 0x80000000 | (stencil - base)`,
sgxfive-test.c line 2739) moved by +0x1000: `--kpoke-render 1:rd:14=0x80014000` (the stencil at
0x3e013000, 18 pages). Read model-free (E1030's fold/look.py): the loaded byte of pixel (x, y) is
the stored byte at E988's position (512 slot + in-tile index) XOR 0xff where the pixel drew.
S-MOVED (the byte at 0x1000 + position), S-UNMOVED (at the position), S-STOREBASE (the stencil
store's fill 0xdeadbeef).
Controls (can fail): zg-c-ctl (E977's z243-ctl with rd:12 its own: drawn 2048, the store byte for
byte E977's kept dump), zg-c-m4 and zg-c-m40 (E1029's zb-m4 and zb-m40 replicates: their kept
stores byte for byte), zg-c-sid (the stencil row with rd:14 its own: S-UNMOVED at every pixel).

Part zodd (Q242, record E1041; rows zo-). E996's plane (r10-x gen/z.py zov_args: z 0, ZX, 1 at (0,0),
(2W,0), (0,2H), ZX the largest power of two at most 1/(2H)) at 63 x 31 (G 1) and 65 x 33 (G 2),
whose edge tiles hold E831's band past the target. Format 0 rows (reading rows: the references)
give each pixel's float; formats 1 and 2 at the same size store, past the target in the edge
tiles:
  INT-FLOOR-EXT   E991's floor rule of the float the same pixel stores in format 0
  INT-ZERO-PAST   0
  INT-EDGE-CLAMP  the floor rule of the nearest pixel inside the target
(inside the target every model is E977's floor rule; format 2 two rows a dword, E490).
Overlap rows: 65 x 33 at G 1 (edge tiles share slots) and 640 x 480 at G 2 (four macrotiles a
side, libsgxfive render.c sgxfive_tiling: n = 4 from 640 x 480) from their full-pitch references
(zo-65-f0, zo-640-f0): H-LATE/HDR (E996), H-EARLY/HDR, H-LATE/RASTER, H-EARLY/RASTER.
E411's G 3 row (zo-g3): 64 x 64, control 0x0017101c, the store base rd:13 = 0xd000 (E411's,
page 12 of the 20-page buffer), --depth-pages 20: H-NEXTTILE (E465: tile rows 0 to 3 at buffer
pages 12, 14, 16 and 18, 1024 dwords each) against H-STRAY (pages 16 to 19 unwritten).
Control (can fail): zo-c-ov, E996's zov-64x32-g0 rerun (its kept dump byte for byte).

Part zbits2 (Q071, record E1042; rows zb2-). E988's stencil row (st1-b0, 0x0017300e, bytes fill) with each
bit of the set half (15, 21, 22, 23, 27 to 31) set alone (9) and the groups 21-23 and 27-31 (2):
Z-ONE-k (only rows setting k draw 2048: the test reads 0), Z-GRP-21-23, Z-GRP-27-31 (only that
group's row), Z-GROUP (no row: it takes both groups or more), Z-ANY (every row). The linear
stencil images (E1030, post hoc at 64 x 32 G 1): bit 12 cleared (the load linear) and bit 16
cleared (the store linear) at 96 x 32 G 2 and 64 x 32 G 2, rows P bytes apart: P-64, P-W (the
width), P-G (32 (G + 1)); the tiled half at E988's position with slot ty (G + 1) + tx [infer].
Bit 12 cleared with a depth load (zb2-d12: the zgran form, rd:12 its own): H-DEPTH-UNCH (the
identity, E467) against H-DEPTH-LIN (pixel (x, y) loads dword 64 y + x, E997's rows of
32 (G + 1)). Bit 16 cleared on the 16-bit format (zb2-f2-16: E977's z242-c-f2 with 0x02161014):
L16-TILED (E977's kept dump), L16-PAIR (dword 96 (y >> 1) + x holds rows 2j and 2j + 1),
L16-HALF (halfword 96 y + x), L16-DW (dword 96 y + x holds the 16-bit value), values from E977's
kept z242-c-f2. Controls (can fail): zb2-c-base (1024 drawn), zb2-c-set (2048, every stored byte
0xff: E1030's zbs-set), zb2-c-r16 (E1030's zbr-c16: E997's linear zb-clr-f0 byte for byte).

Part zflat (Q120, record E1043; rows zl-). E1031's zf-flat-f6 form (64 x 32, the stencil loaded `index`
and stored, less) at flat depths 0.25, 0.75, 0.1234 (four distinct float bytes), 1.0 (fails less
against the clear 1.0: the background) and 0.0. No rule of E1031's 44 dwords was fitted (builder,
offline, gen/flat_fit.py): its 16 0x9e bytes are one a tile row and its first 16 bytes are
E1015's F6C group 0 for v = 0.5 (row 0's record 0x9e v 0x00 at byte 6, the words 0x3f000000 at
dwords 0 and 3). Frozen: FL-HEAD (the first 4 dwords are F6C group 0's for v), FL-CONST (the 44
dwords do not depend on v: E1031's), FL-SHAPE (44 changed dwords a block, the four blocks alike,
16 0x9e bytes at E1031's places). Format 7 under the index stencil on the flat 0.5 (zl-f7-idx):
F7I-COMMON (the 771 dwords E986's z2y-f7 and z2d-f7 share hold here too), F7I-COUNT (784 changed,
392 in each of blocks 0 and 1). Format 5 on the flat 0.5 (zl-f5-flat): F5-EQ-F6 (E1031's format 6
dump byte for byte). Controls (can fail): zl-c-flat (E1031's zf-flat-f6, byte for byte), zl-c-y6
(E986's z2y-f6, byte for byte)."""
import struct

MAIN = "tri --keep-going --wait-ms 20000"
TILE_DW = 512
FILL_DEAD = 0xDEADBEEF
NEVER, LESS = 0x00000200, 0x00400200
TRI_COLOUR = 0xFF00FF00

# ---- shared ----------------------------------------------------------------------------------


def size(w, h):
    return f"--width {w} --height {h} --max-width {w} --max-height {h}"


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def f32(u):
    return struct.unpack("<f", struct.pack("<I", u & 0x7FFFFFFF))[0]


def floor24(u):
    """E977/E991: the 24-bit format of the float u (its sign cleared, E987)"""
    return min(int(f32(u) * 16777216.0), 0xFFFFFF)


def in_tile_index(x, y):
    """E465: the dword of pixel (x, y) in its 32 x 16 tile, y0 x0 y1 x1 y2 x2 y3 x3 x4"""
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def in_tile_index16(x, y):
    """E490 (sgx-pipe zls.rs in_tile_index16): the dword of a 256-dword 16-bit slot, x0 y1 x1 y2
    x2 y3 x3 x4; y0 picks the half (the even row low)"""
    x, y = x & 31, y & 15
    k = 0
    for b in range(4):
        k |= (x >> b & 1) << (2 * b)
        if b < 3:
            k |= (y >> (b + 1) & 1) << (2 * b + 1)
    return k | (x >> 4 & 1) << 7


def slot(x, y, g):
    return (y >> 4) * (g + 1) + (x >> 5)


def store_dword(x, y, g):
    return TILE_DW * slot(x, y, g) + in_tile_index(x, y)


def store_dword16(x, y, g):
    return 256 * slot(x, y, g) + in_tile_index16(x, y)


def dwords(b):
    return None if b is None else list(struct.unpack("<%dI" % (len(b) // 4), b[:len(b) // 4 * 4]))


def fill_at(f, i):
    """t10's fill_at (sgxfive-test.c line 304): a value, index, bit:K, bytes[:S]"""
    if f == "index":
        return i & 0xFFFFFFFF
    if f.startswith("bit:"):
        return 0x3F400000 if i >> int(f[4:]) & 1 else 0x3E800000
    if f.startswith("bytes"):
        s = int(f.split(":")[1]) if ":" in f else 0
        b = 4 * i + s
        return (b & 0xFF) | ((b + 1) & 0xFF) << 8 | ((b + 2) & 0xFF) << 16 | ((b + 3) & 0xFF) << 24
    return int(f, 0)


def fill_byte(f, b):
    """byte b of a buffer filled by t10's fill f"""
    return fill_at(f, b // 4) >> (8 * (b % 4)) & 0xFF


# ---- zgran -----------------------------------------------------------------------------------
ZB_CTL = 0x0017500E
ZB_PAGES = 20
ZB_BASE = 0x3E000000
ZB_DEPTH = 0x3E001000
ZB_STORE = ZB_DEPTH + ZB_PAGES * 4096      # 0x3e015000
ZB_OWN = ZB_DEPTH - ZB_BASE                # 0x1000: depth_arm's rd:12
ZB_N = 2048                                # 64 x 32: 4 tiles of 512 dwords (G 1)
ZB_SFILL = 0x3E800000
Z243_CTL = (f"{MAIN} {size(64, 32)} --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl 0x0017500e "
            '--depth-fill 0x3f400000 --depth-store --depth-dump "$W" --poke blk:1=0x00400200 '
            "--pixels")
GRAN_MODELS = ("G8", "G16", "G32", "G64", "H-BYTE")
GRAN_MOVES = {"zg-m8": 0x8, "zg-m10": 0x10, "zg-m20": 0x20, "zg-m1008": 0x1008, "zg-m1020": 0x1020}
INT_MOVE = 0x1000
INT_FILL = "bit:10"
INT_SFILL = 0x3F000000                     # 0.5: the store's fill, neither of bit:10's floats
INT_ROWS = {"zg-f1": 1, "zg-f2": 2}
INT_MODELS = {1: ("I-MOVED-L32", "I-UNMOVED-L32", "I-STOREBASE"),
              2: ("I-MOVED-L32", "I-MOVED-L16", "I-UNMOVED-L32", "I-UNMOVED-L16", "I-STOREBASE")}
ST_CTL = 0x0017300E                        # E988's st1: stencil loaded (1, 13) and stored, G 1
ISP2_B0 = 2 << 25 | 5 << 16 | 0x01 << 8 | 0xFF     # EQUAL, SOP3 invert, mask 0x01: 0x040501ff
ST_DEPTH, ST_STENCIL, ST_SSTORE = 0x3E001000, 0x3E013000, 0x3E025000   # 18 pages each (E988)
ST_OWN14 = 0x80000000 | (ST_STENCIL - ZB_BASE)                        # 0x80013000
S_MOVE = 0x1000
S_MODELS = ("S-MOVED", "S-UNMOVED", "S-STOREBASE")


def zb_args(rd12, ctl=ZB_CTL, dfill="index", sfill=ZB_SFILL):
    return (f"{MAIN} {size(64, 32)} --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl {ctl:#010x} "
            f"--depth-fill {dfill} --depth-store --depth-store-fill {sfill:#010x} --depth-pages "
            f'{ZB_PAGES} --depth-dump "$W" --poke blk:1={NEVER:#010x} --pixels --kpoke-render '
            f"1:rd:12={rd12:#x}")


def st_args(ctl, w=64, sfill="bytes", extra=""):
    return (f"{MAIN} --tri-full {size(w, 32)} --depth --depth-ctl {ctl:#010x} --depth-fill "
            f"0x3f800000 --stencil --stencil-fill {sfill} --stencil-store --isp2 {ISP2_B0:#010x} "
            f'--depth-dump "$W" --pixels{extra}')


def gran_offset(model, m):
    if model == "H-BYTE":
        return m // 4
    g = int(model[1:])
    return ((ZB_OWN + m) // g * g - ZB_OWN) // 4


def gran_predict(model, m):
    d = gran_offset(model, m)
    return [k + d for k in range(ZB_N)]


def int_predict(fmt, model):
    """{store dword: value} of an integer row under model (the rest keeps the store's fill)"""
    def loaded(x, y):
        if model == "I-STOREBASE":
            return INT_SFILL
        d = INT_MOVE // 4 if "MOVED" in model and "UNMOVED" not in model else 0
        k = store_dword16(x, y, 1) if model.endswith("L16") else store_dword(x, y, 1)
        return fill_at(INT_FILL, k + d)
    out = {}
    if fmt == 1:
        for y in range(32):
            for x in range(64):
                out[store_dword(x, y, 1)] = floor24(loaded(x, y))
    else:
        for y in range(0, 32, 2):
            for x in range(64):
                out[store_dword16(x, y, 1)] = (floor24(loaded(x, y)) >> 8
                                               | (floor24(loaded(x, y + 1)) >> 8) << 16)
    return out


def st_pos(x, y, g=1):
    """E988: the stencil byte of pixel (x, y): 512 bytes a tile at the slot, the in-tile index"""
    return TILE_DW * slot(x, y, g) + in_tile_index(x, y)


def s_loaded(model, x, y, sfill="index"):
    if model == "S-STOREBASE":
        return fill_byte(f"{FILL_DEAD:#010x}", st_pos(x, y))
    return fill_byte(sfill, st_pos(x, y) + (S_MOVE if model == "S-MOVED" else 0))


ZGRAN = {
    "zg-c-ctl": Z243_CTL + f" --kpoke-render 1:rd:12={ZB_OWN:#x}",
    "zg-c-m4": zb_args(ZB_OWN + 4),
    "zg-c-m40": zb_args(ZB_OWN + 0x40),
    "zg-c-sid": st_args(ST_CTL, sfill="index", extra=f" --kpoke-render 1:rd:14={ST_OWN14:#x}"),
}
for _n, _m in GRAN_MOVES.items():
    ZGRAN[_n] = zb_args(ZB_OWN + _m)
for _n, _f in INT_ROWS.items():
    ZGRAN[_n] = zb_args(ZB_OWN + INT_MOVE, ctl=ZB_CTL | _f << 24, dfill=INT_FILL, sfill=INT_SFILL)
ZGRAN["zg-s14"] = st_args(ST_CTL, sfill="index",
                          extra=f" --kpoke-render 1:rd:14={ST_OWN14 + S_MOVE:#x}")
ZG_CONTROL = {"zg-c-ctl": "drawn,dst_changed", "zg-c-m4": "dst_changed",
              "zg-c-m40": "dst_changed", "zg-c-sid": "drawn,sst_changed"}

# ---- zodd ------------------------------------------------------------------------------------
STORE = 0x00171004


def zctl(g, fmt=0):
    return STORE | g << 3 | fmt << 24


def zx(h):
    """The largest power of two at most 1/(2H) (r10-x gen/z.py)."""
    v = 1.0
    while v > 1 / (2 * h):
        v /= 2
    return v


def zov_args(w, h, g, fmt=0):
    return (f"{MAIN} {size(w, h)} --tri-v 0,0,{512 * w},0,0,{512 * h} --tri-z 0,{zx(h)!r},1 "
            f"--depth --depth-ctl {zctl(g, fmt):#010x} --depth-fill {FILL_DEAD:#010x} "
            f'--depth-dump "$W" --poke blk:1={LESS:#010x}')


ODD = {"63": (63, 31, 1), "65": (65, 33, 2)}
INT_PAST_MODELS = ("INT-FLOOR-EXT", "INT-ZERO-PAST", "INT-EDGE-CLAMP")
OV_MODELS = ("H-LATE/HDR", "H-EARLY/HDR", "H-LATE/RASTER", "H-EARLY/RASTER")
OV_ROWS = {"zo-65-ov": (65, 33, 1, "zo-65-f0"), "zo-640-ov": (640, 480, 2, "zo-640-f0")}
G3_CTL = 0x0017101C
G3_RD13 = 0xD000
G3_MODELS = ("H-NEXTTILE", "H-STRAY")
ZODD = {"zo-c-ov": zov_args(64, 32, 0)}
ZODD_SET = {"zo-c-ov": "control"}
for _k, (_w, _h, _g) in ODD.items():
    for _f in (0, 1, 2):
        ZODD[f"zo-{_k}-f{_f}"] = zov_args(_w, _h, _g, _f)
        ZODD_SET[f"zo-{_k}-f{_f}"] = "reading" if _f == 0 else "heldout"
ZODD["zo-65-ov"] = zov_args(65, 33, 1)
ZODD_SET["zo-65-ov"] = "heldout"
ZODD["zo-640-f0"] = zov_args(640, 480, 19)
ZODD_SET["zo-640-f0"] = "reading"
ZODD["zo-640-ov"] = zov_args(640, 480, 2)
ZODD_SET["zo-640-ov"] = "heldout"
ZODD["zo-g3"] = (f"{MAIN} {size(64, 64)} --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl "
                 f"{G3_CTL:#010x} --depth-fill {FILL_DEAD:#010x} --depth-pages {ZB_PAGES} "
                 f'--depth-dump "$W" --poke blk:1={LESS:#010x} --kpoke-render 1:rd:13={G3_RD13:#x}')
ZODD_SET["zo-g3"] = "heldout"
ZO_OV_CHANGED = 1536                       # E996's zov-64x32-g0: depth #1 changed dwords


def int_past_predict(ref, w, h, g, fmt, model):
    """{dword: value} of an integer row over its whole tiles from the format-0 reference dump
    `ref` (dwords, at the same pitch): E977's floor rule inside the target, the model past it"""
    tw, th = tiles(w, h)

    def val(x, y):
        inside = x < w and y < h
        if inside or model == "INT-FLOOR-EXT":
            return floor24(ref[store_dword(x, y, g)])
        if model == "INT-ZERO-PAST":
            return 0
        return floor24(ref[store_dword(min(x, w - 1), min(y, h - 1), g)])
    out = {}
    if fmt == 1:
        for y in range(16 * th):
            for x in range(32 * tw):
                out[store_dword(x, y, g)] = val(x, y)
    else:
        for y in range(0, 16 * th, 2):
            for x in range(32 * tw):
                out[store_dword16(x, y, g)] = val(x, y) >> 8 | (val(x, y + 1) >> 8) << 16
    return out


def macro(w, h):
    """libsgxfive render.c sgxfive_tiling (r10-x gen/z.py): n macrotiles a side, mx x my regions"""
    tx, ty = tiles(w, h)
    n = 4 if w * h >= 640 * 480 else 2
    return n, ((tx + n - 1) // n + 3) & ~3, ((ty + n - 1) // n + 3) & ~3


def header_rank(w, h):
    """{(tx, ty): its place in the region header order} (r10-x gen/z.py, sgx-pipe ta.rs)"""
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


def owners(w, h, g, model):
    late = model.startswith("H-LATE")
    rank = header_rank(w, h) if "/HDR" in model else raster_rank(w, h)
    best = {}
    for t, k in rank.items():
        s = t[1] * (g + 1) + t[0]
        if s not in best or (k > rank[best[s]] if late else k < rank[best[s]]):
            best[s] = t
    return best


def ov_predict(full, w, h, g, model):
    """{dword: value} the overlapping store holds: the owner tile's 512 dwords of the full-pitch
    reference `full` (r10-x gen/z.py zov_predict, format 0)"""
    tx, _ = tiles(w, h)
    out = {}
    for s, (c, r) in owners(w, h, g, model).items():
        src = TILE_DW * (r * tx + c)
        for k in range(TILE_DW):
            out[TILE_DW * s + k] = full[src + k]
    return out


def g3_pages(model):
    """the buffer pages (of 20) holding the tile rows under model, 1024 dwords each"""
    base = (G3_RD13 - ZB_OWN) // 4096            # page 12
    rows = {(base * 1024 + TILE_DW * (ty * 4)) // 1024 for ty in range(4)}
    return sorted(rows if model == "H-NEXTTILE" else {p for p in rows if p < 16})


# ---- zbits2 ----------------------------------------------------------------------------------
SET_BITS = (15, 21, 22, 23, 27, 28, 29, 30, 31)
SET_MASK = sum(1 << b for b in SET_BITS)    # 0xf8e08000
GROUPS = {"zb2-g21-23": (21, 22, 23), "zb2-g27-31": (27, 28, 29, 30, 31)}
RAMP_CTL = 0x00171014
DRAWN_LOADED, DRAWN_ZERO = 1024, 2048
P_MODELS = ("P-64", "P-W", "P-G")
PITCH_ROWS = {"zb2-p12-96": (96, 12), "zb2-p16-96": (96, 16), "zb2-p12-64g2": (64, 12),
              "zb2-p16-64g2": (64, 16)}
P_G = 2
ST_CTL_G2 = (ST_CTL & ~0xFF8) | P_G << 3    # 0x00173016
D12_CTL = ZB_CTL & ~(1 << 12)               # 0x0017400e
D12_MODELS = ("H-DEPTH-UNCH", "H-DEPTH-LIN")
F2_16_CTL = 0x02171014 & ~(1 << 16)         # 0x02161014
L16_MODELS = ("L16-TILED", "L16-PAIR", "L16-HALF", "L16-DW")


def ramp_args(ctl):
    return (f"{MAIN} {size(80, 40)} --tri-v 0,0,40960,0,0,20480 --tri-z 1,0,1 --depth --depth-ctl "
            f'{ctl:#010x} --depth-fill 0xdeadbeef --depth-dump "$W" --poke blk:1={LESS:#010x}')


def z_models():
    return ([f"Z-ONE-{k}" for k in SET_BITS] + ["Z-GRP-21-23", "Z-GRP-27-31", "Z-GROUP", "Z-ANY"])


def z_bits(name):
    return GROUPS.get(name) or (int(name.split("-b")[1]),)


def z_predict(name, model):
    bits = z_bits(name)
    if model == "Z-ANY":
        on = True
    elif model == "Z-GROUP":
        on = False
    elif model.startswith("Z-GRP-"):
        on = name == "zb2-g" + model[6:]
    else:
        on = int(model[6:]) in bits
    return DRAWN_ZERO if on else DRAWN_LOADED


def pitch(model, w, g=P_G):
    return {"P-64": 64, "P-W": w, "P-G": 32 * (g + 1)}[model]


def pitch_check(stored, drawn, w, bit, model, sfill="bytes", g=P_G):
    """(bytes explained, bytes checked) of a pitch row: bit 12 cleared, the load reads the linear
    image (byte P y + x) and the store is E988's; bit 16 cleared, the load is E988's and the
    store linear (a byte two pixels write explains either)"""
    p = pitch(model, w, g)
    ok = n = 0
    writers = {}
    for y in range(32):
        for x in range(w):
            inv = 0xFF if (x, y) in drawn else 0
            if bit == 12:
                n += 1
                ok += stored[st_pos(x, y, g)] ^ inv == fill_byte(sfill, p * y + x)
            else:
                writers.setdefault(p * y + x, []).append(fill_byte(sfill, st_pos(x, y, g)) ^ inv)
    for b, vs in writers.items():
        n += 1
        ok += stored[b] in vs
    return ok, n


def d12_predict(model):
    if model == "H-DEPTH-UNCH":
        return list(range(ZB_N))
    out = [0] * ZB_N
    for y in range(32):
        for x in range(64):
            out[store_dword(x, y, 1)] = 64 * y + x
    return out


def l16_predict(model, f2):
    """{dword: value} of zb2-f2-16 under model; f2 the kept z242-c-f2 dump (dwords, G 2)"""
    tw, th = tiles(80, 40)
    if model == "L16-TILED":
        return {i: v for i, v in enumerate(f2) if v != FILL_DEAD}
    v16 = {}
    for y in range(16 * th):
        for x in range(32 * tw):
            v16[(x, y)] = f2[store_dword16(x, y, 2)] >> (16 * (y & 1)) & 0xFFFF
    pw = 32 * (2 + 1)
    out = {}
    for (x, y), v in v16.items():
        if model == "L16-PAIR":
            k = pw * (y >> 1) + x
            out[k] = out.get(k, 0) | v << (16 * (y & 1))
        elif model == "L16-HALF":
            k = (pw * y + x) >> 1
            out[k] = out.get(k, 0) | v << (16 * ((pw * y + x) & 1))
        else:
            out[pw * y + x] = v
    return out


ZBITS2 = {"zb2-c-base": st_args(ST_CTL), "zb2-c-set": st_args(ST_CTL | SET_MASK),
          "zb2-c-r16": ramp_args(RAMP_CTL & ~(1 << 16))}
for _b in SET_BITS:
    ZBITS2[f"zb2-b{_b}"] = st_args(ST_CTL | 1 << _b)
for _n, _bs in GROUPS.items():
    ZBITS2[_n] = st_args(ST_CTL | sum(1 << b for b in _bs))
for _n, (_w, _bit) in PITCH_ROWS.items():
    ZBITS2[_n] = st_args(ST_CTL_G2 & ~(1 << _bit), w=_w)
ZBITS2["zb2-d12"] = zb_args(ZB_OWN, ctl=D12_CTL)
ZBITS2["zb2-f2-16"] = ramp_args(F2_16_CTL)
ZB2_CONTROL = {"zb2-c-base": ("drawn", DRAWN_LOADED), "zb2-c-set": ("drawn", DRAWN_ZERO),
               "zb2-c-r16": ("depth_changed", 4608)}
ZB2_READS = {"zb2-c-base": "drawn", "zb2-c-set": "drawn,sst_changed", "zb2-c-r16": "depth_changed"}

# ---- zflat -----------------------------------------------------------------------------------
F5_CTL, F6_CTL, F7_CTL = 0x0517300E, 0x0617300E, 0x0717300E
FLAT_DEPTHS = {"zl-f6-0p25": "0.25", "zl-f6-0p75": "0.75", "zl-f6-0p1234": "0.1234",
               "zl-f6-1p0": "1.0", "zl-f6-0p0": "0.0"}
FL_MODELS = ("FL-HEAD", "FL-CONST", "FL-SHAPE")
F7I_MODELS = ("F7I-COMMON", "F7I-COUNT")
F5_MODELS = ("F5-EQ-F6",)
FLAT_N = 44                                 # E1031: 44 dwords at the start of each 512-dword block
ZL_CHANGED = {"zl-c-flat": 176, "zl-c-y6": 212}


def zf_args(ctl, z, sfill="index"):
    return (f"{MAIN} {size(64, 32)} --tri-full --tri-z {z} --depth --depth-ctl {ctl:#010x} "
            f"--depth-fill 0xdeadbeef --stencil --stencil-fill {sfill} --stencil-store --depth-dump "
            f'"$W" --poke blk:1={LESS:#010x}')


def f32_bits(s):
    """the float32 the tool's strtof gives a --tri-z word (round to nearest)"""
    return struct.unpack("<I", struct.pack("<f", float(s)))[0]


def flat_v(name):
    """the stored float of a flat row: the triangle's depth, or the clear 1.0 where less fails"""
    z = FLAT_DEPTHS[name]
    return f32_bits(z) if float(z) < 1.0 else 0x3F800000


def f6c_head(v):
    """E1015's F6C group 0, its first 4 dwords (row 0's record at byte 6, the words 0x3f000000 at
    dwords 0 and 3), for one depth v (c7_rule.py, bytes 0 to 15)"""
    b = bytearray(16)
    b[6:12] = bytes([0x9E]) + struct.pack("<I", v) + b"\x00"
    b[0:4] = b[12:16] = struct.pack("<I", 0x3F000000)
    return list(struct.unpack("<4I", bytes(b)))


ZFLAT = {"zl-c-flat": zf_args(F6_CTL, "0.5,0.5,0.5"), "zl-c-y6": zf_args(F6_CTL, "0.25,0.25,0.75")}
for _n, _z in FLAT_DEPTHS.items():
    ZFLAT[_n] = zf_args(F6_CTL, f"{_z},{_z},{_z}")
ZFLAT["zl-f7-idx"] = zf_args(F7_CTL, "0.5,0.5,0.5")
ZFLAT["zl-f5-flat"] = zf_args(F5_CTL, "0.5,0.5,0.5")


# ---- the rows --------------------------------------------------------------------------------
# A stage's rows all write the dump its scorer reads (REQUIRED is per row: a row without it stops
# the runner, rc 23, and a fixed file of a row a stopped stage never ran stops the driver, 43),
# so the rows are grouped by that dump, not by record; the name's prefix is the record's:
# zg- E1040 (Q243), zo- E1041 (Q242), zb2- E1042 (Q071), zl- E1043 (Q120).
#   zgran   the depth-store rows (E1029's zbase form): E1040's granule and integer rows, E1042's
#           zb2-d12
#   zodd    the depth rows (E996's plane, E977's ramp): E1041's rows, E1042's zb2-c-r16 and
#           zb2-f2-16 before zo-g3 (last)
#   zbits2  the stencil-store rows (E988's st1 form): E1042's set-half and pitch rows, E1040's
#           zg-c-sid and zg-s14 (last)
#   zflat   E1043
STAGE_ROWS = {
    "zgran": ["zg-c-ctl", "zg-c-m4", "zg-c-m40", *GRAN_MOVES, *INT_ROWS, "zb2-d12"],
    "zodd": [n for n in ZODD if n != "zo-g3"] + ["zb2-c-r16", "zb2-f2-16", "zo-g3"],
    "zbits2": ["zb2-c-base", "zb2-c-set", "zg-c-sid", *(f"zb2-b{b}" for b in SET_BITS), *GROUPS,
               *PITCH_ROWS, "zg-s14"],
    "zflat": list(ZFLAT),
}
ARGS = {**ZGRAN, **ZODD, **ZBITS2, **ZFLAT}


def row(n):
    """(set, knobs, {quantity: {model: value}}) of row n"""
    if n in ZG_CONTROL:
        q = {"stencil": {"S-UNMOVED": "rule"}} if n == "zg-c-sid" else {"store": {"H-KEPT": "kept"}}
        if n == "zg-c-ctl":
            q["drawn"] = {"H-E977": "2048"}
        return "control", f"expectdiff reads:{ZG_CONTROL[n]}", q
    if n in GRAN_MOVES:
        return "heldout", "expectdiff", {"store": {m: f"d={gran_offset(m, GRAN_MOVES[n])}"
                                                   for m in GRAN_MODELS}}
    if n in INT_ROWS:
        return "heldout", "expectdiff", {"store": {m: "rule" for m in INT_MODELS[INT_ROWS[n]]}}
    if n == "zg-s14":
        return "heldout", "expectdiff", {"stencil": {m: "rule" for m in S_MODELS}}
    if n in ZODD:
        s = ZODD_SET[n]
        if s == "control":
            return s, "expectdiff reads:depth_changed", {
                "depth_changed": {"H-E996": str(ZO_OV_CHANGED)}, "dump": {"H-E996": "kept"}}
        if s == "reading":
            return s, "expectdiff", {}
        if n in OV_ROWS:
            return s, "expectdiff", {"dwords": {m: f"rule:{OV_ROWS[n][3]}" for m in OV_MODELS}}
        if n == "zo-g3":
            return s, "expectdiff", {"pages": {m: ",".join(map(str, g3_pages(m)))
                                               for m in G3_MODELS}}
        return s, "expectdiff", {"dwords": {m: f"rule:{n[:-1]}0" for m in INT_PAST_MODELS}}
    if n in ZB2_CONTROL:
        k, v = ZB2_CONTROL[n]
        return "control", f"expectdiff reads:{ZB2_READS[n]}", {k: {"H-E1030": str(v)}}
    if n in PITCH_ROWS:
        return "heldout", "expectdiff", {"stencil": {m: f"P={pitch(m, PITCH_ROWS[n][0])}"
                                                     for m in P_MODELS}}
    if n == "zb2-d12":
        return "heldout", "expectdiff", {"store": {m: "rule" for m in D12_MODELS}}
    if n == "zb2-f2-16":
        return "heldout", "expectdiff", {"dump": {m: "rule:z242-c-f2" for m in L16_MODELS}}
    if n in ZBITS2:
        return "heldout", "expectdiff", {"drawn": {m: str(z_predict(n, m)) for m in z_models()}}
    if n in ZL_CHANGED:
        return "control", "expectdiff reads:depth_changed", {
            "depth_changed": {"H-KEPT": str(ZL_CHANGED[n])}, "dump": {"H-KEPT": "kept"}}
    if n in FLAT_DEPTHS:
        return "heldout", "expectdiff", {"block": {m: f"v={flat_v(n):#010x}" for m in FL_MODELS}}
    if n == "zl-f7-idx":
        return "heldout", "expectdiff", {"dump": {m: "rule" for m in F7I_MODELS}}
    return "heldout", "expectdiff", {"dump": {m: "kept:zl-c-flat" for m in F5_MODELS}}


def jobs():
    """[(stage, name, set, knobs, args, {quantity: {model: value}})] in run order"""
    return [(st, n, *row(n)[:2], ARGS[n], row(n)[2]) for st, ns in STAGE_ROWS.items() for n in ns]
