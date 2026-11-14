# SPDX-License-Identifier: MIT
"""z15.py: r15-zls's rows and frozen rivals (round 15 plan closing15/plan/rank-round15.md sections
2 and 3, decisions R15-1 (a), R15-6 (a), R15-7 (a), R15-8 (a); tool t10, resgx545 a581c06
sgxfive-test.c). Round 14's r14-zls (render/closing-r14-zls gen/z14.py, E1040 to E1043) is the
direct predecessor: its helpers are copied here, not imported, so this file alone is frozen. The
stages group the rows by the dump their scorer reads (STAGE_ROWS at the end); a row's name prefix
names its record: zp- E1050 (Q297), zv- E1051 (Q298), zb3- E1053 (Q071), zl2- E1054 (Q120).

Part zpass (Q297, E1050; rows zp-). E1029's zbase form (--tri-full, --depth-store, 20 pages, the
load and store enables 0x0017500e at G 1) with the depth buffer filled `bit:K` (0.75f where bit K
of the dword index is set, else 0.25f) and the depth test less (blk:1 0x00400200) or never
(0x00000200). A pass model gives, for every pixel of the target's tiles, the start value (the
loaded dword with its sign cleared, E467, or the clear 1.0 without a load), whether the full-screen
triangle covers it (E831's band: x + 0.5 < 1.25 W and y + 0.5 < 1.25 H; every pixel of whole
tiles) and whether the test passes (less: the triangle's depth below the start's float, exact,
E995), and the store's encoding (float, bit 19 negated, E977's floor rule, E490's 16-bit layout).
  H-EDGE        at 34 x 18 (edge tiles, G 1, bit:3) the load, test and store act per dword as on
                whole tiles: the band's pixels are tested against the loaded depth, the pixels
                past the band keep the loaded depth (E988's stencil at 40 x 20, post hoc) [infer]
  H-EDGE-CLEAR  past the band the clear 1.0 (the store's band without a load, E831)
  H-EDGE-SKIP   the edge tiles take no load (the band's pixels against 1.0, 1.0 past it)
  H-19-RENEG    bit 19 (0x001f500e): a kept pixel stores its loaded depth (sign cleared) negated,
                a drawn one -z (E411's bit 19) [infer]; H-19-ABS the kept pixel unnegated
  H-INT-PASS    formats 1 and 2 (0x0117500e, 0x0217500e): the test compares the loaded dword as a
                float (E977, E1040's I-MOVED-L32) and the store takes E991's floor rule of the
                float that passed or was kept; H-INT-WORD the test compares the word's low 24
                bits as the integer depth (the kept pixel stored by the floor rule all the same)
  H-PASS-Z      triangle depths 0.0, 0.125, 0.75 and 1.0 over bit:9's tile halves (0.25 at even
                slots, 0.75 at odd) under less, strict (E995); H-PASS-LE the test passes equal
                depths too (parts at 0.75)
The plan's 0.1 and 0.3 are 0.125 and 0.375 here (deviation, README): a dyadic flat depth is the
same float at every pixel, so a frozen exact store holds; zflat2's twins test the non-dyadic
planes. Controls (can fail): zp-c-id (E1029's zb-c-id, its kept store byte for byte), zp-c-467
(E467's pass on t10: 256 x 128 G 7, bit:9, 16384 drawn, the store by H-EDGE's whole-tile rule)
and zp-c-band (34 x 18 without a load: E831's band, 0.5 inside it and 1.0 past it, 612 drawn).
The stencil edge row zp-e-st (E988's st1 form at 34 x 18) writes the stencil store, so it runs in
zbits3 (the stencil-store stage): H-EDGE (past the band the loaded byte), H-EDGE-CLEAR (0, the
stencil's clear), H-EDGE-SKIP (edge tiles start from 0).

Part zbits3 (Q071, E1053; rows zb3-). E988's st1-b0 form (64 x 32, the stencil loaded from the
`bytes` fill and stored, ISP word 2 0x040501ff: EQUAL against the reference with mask 0x01, invert
on pass). The byte the test reads at pixel (x, y) is read(x, y); the pixel draws where read & 1
equals the reference's bit 0 and stores read ^ 0xff, else stores read (E988, E1042's look).
  H15-FAIL      bit 15 alone: the test fails at every pixel, the loaded bytes stored unchanged
                (E1042's zb2-b15 post hoc), at 96 x 32 G 2 and under the reference flipped
                (`--poke blk:1^=0x1`: ISP word 0 bits 7:0, E284)
  H15-READFF    the test reads 0xff: fails against reference 0 (E1042 alike), passes every pixel
                against reference 1 (2048 drawn, stored 0x00) [infer]
  H23-MOD16     bit 23 alone: read(x, y) = COL23[x % 16] (E1042's zb2-b23 post hoc), whatever the
                loaded byte: at 96 x 32 G 2 and at 64 x 32 over the `index` fill
  H23-LOADED    read(x, y) = g(the loaded byte), g E1042's map from the bytes fill's byte to the
                read one (a function there: the score fits it on the kept dump)
  H-PAIR-23     bits 21 + 23 and 22 + 23 read as 23 alone; H-PAIR-ZERO read 0 (2048 drawn, as 21
                to 23 together, E1042); H-PAIR-BASE read the loaded byte (1024, E988)
Controls (can fail): zb3-c-base, zb3-c-set and zb3-c-b23 (E1042's zb2-c-base, zb2-c-set, zb2-b23
reruns, their kept stencil stores byte for byte), zb3-c-ref1 (st1-b0 with the reference flipped:
E988's rule against 1, 1024 drawn, the complement image).

Part zflat2 (Q120, E1054; rows zl2-). E1031's zf-flat-f6 form (64 x 32, the stencil loaded `index`
and stored, less, control 0x0617300e) on flat planes. FL-REC0 (E1043 post hoc): a flat format-6
tile stores E1031's 44 dwords a block, the four blocks alike, with row 0's record (bytes 7 to 10)
the depth v and nothing else changed; held out at 0.375, 0.625, 0.9375 and 0.0625 (low 16 bits
zero). Rows 0.1, 0.3 and 0.5 + 2^-20 (low 16 bits set) with a format-0 twin each (0x0017300e,
the per-pixel floats; reading rows):
  H-LOW16       FL-REC0 with the float of the depth iff its low 16 bits are zero, else not FL-REC0
  H-FLATPLANE   FL-REC0 with the twin's value iff the twin stores one value at all 2048 pixels,
                else not FL-REC0 (E1043's [infer])
Controls (can fail): zl2-c-flat (E1031's zf-flat-f6), zl2-c-y6 (E986's z2y-f6) and zl2-c-f5
(E1043's zl-f5-flat), each its kept dump byte for byte.

Part zovl (Q298, E1051; rows zv-). Overlapping stores (E996's plane, G below the tiles across
minus one) in format 2 at 64 x 32 G 0 and 160 x 48 G 2 and in format 1 at 65 x 33 G 1 and
640 x 480 G 2, each from a kept full-pitch format-0 reference (E996's zov-64x32-ctl and
zov-160x48-ctl, E1041's zo-65-f0 and zo-640-f0) by E991's floor rule: H-LATE/HDR (E996, E1041)
and H-EARLY/HDR, H-LATE/RASTER, H-EARLY/RASTER. Integer depths outside 0 to 1: the flat 0.5 under
depth always (blk:1 0x01c00200) with the viewport's z offset (blk:10, E987: the depth is
t + w - 0.5 from w 0.5 up, E287: not clipped) at 1.25 and -0.25 in formats 1 and 2:
  H-INT-SAT     min(floor(z 2^24), 0xffffff) above 1, a negative depth 0 (E981)
  H-INT-WRAP    floor(z 2^24) modulo 2^24 (format 2: that >> 8)
  H-INT-SIGN    the magnitude converted (-0.25 as 0.25)
E411's arrangement (64 x 64, the store base rd:13 = 0xd000, page 12 of the depth buffer) at the
pitches that faulted with 16 pages (G 5, 9, 17) with the buffer sized past their extent (24, 32,
44 pages), and E411's bit-25 row (format 2 at G 1, 20 pages):
  H-E465-EXT    tile row ty at page 12 + (G + 1) ty / 2, 1024 dwords of 0.5 each (E465, E991)
  H-STOP16      only the pages below 16 (the old buffer's bound)
  H-B25-FLOOR   bit 25: pages 12 and 13 hold E991's 16-bit floor of 0.5, 0x80008000
  H-B25-FF      pages 12 and 13 hold 0xffffffff (as E411 saw)
Controls (can fail): zv-c-ov (E996's zov-64x32-g0, its kept dump), zv-c-g3 (E1041's zo-g3, its
kept dump) and zv-c-075 (format 1 at the offset 0.75: E987's H-OFF depth 0.75 by E977's floor
rule, 0x00c00000 at all 2048 dwords). zv-r-hi (format 0 at the offset 1.25) is a reading row: the
float the conversion meets above 1 (E287 and E987's H-OFF say 1.25, 0x3fa00000) [infer]."""
import math
import struct

MAIN = "tri --keep-going --wait-ms 20000"
TILE_DW = 512
FILL_DEAD = 0xDEADBEEF
CLEAR = 0x3F800000
NEVER, LESS, ALWAYS = 0x00000200, 0x00400200, 0x01C00200
TRI_COLOUR = 0xFF00FF00

# ---- shared (z14's helpers) ------------------------------------------------------------------


def size(w, h):
    return f"--width {w} --height {h} --max-width {w} --max-height {h}"


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def f32(u):
    return struct.unpack("<f", struct.pack("<I", u & 0x7FFFFFFF))[0]


def f32s(u):
    """the signed float of the word u"""
    return struct.unpack("<f", struct.pack("<I", u))[0]


def f32_bits(s):
    """the float32 the tool's strtof gives a --tri-z word (round to nearest)"""
    return struct.unpack("<I", struct.pack("<f", float(s)))[0]


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


def in_band(x, y, w, h):
    """E831 (sgx-pipe zls.rs in_band): x + 0.5 < 1.25 W and y + 0.5 < 1.25 H"""
    return 4 * x + 2 < 5 * w and 4 * y + 2 < 5 * h


def dwords(b):
    return None if b is None else list(struct.unpack("<%dI" % (len(b) // 4), b[:len(b) // 4 * 4]))


def fill_at(f, i):
    """t10's fill_at (sgxfive-test.c): a value, index, bit:K, bytes[:S]"""
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


# ---- zpass -----------------------------------------------------------------------------------
ZP_CTL = 0x0017500E                         # depth loaded (1, 14) and stored, G 1 (E1029)
ZP_PAGES = 20
ZP_ID_ARGS = ('tri --keep-going --wait-ms 20000 --width 64 --height 32 --max-width 64 '
              '--max-height 32 --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl 0x0017500e '
              '--depth-fill index --depth-store --depth-store-fill 0x3e800000 --depth-pages 20 '
              '--depth-dump "$W" --poke blk:1=0x00000200 --pixels --kpoke-render 1:rd:12=0x1000')
EDGE_MODELS = ("H-EDGE", "H-EDGE-CLEAR", "H-EDGE-SKIP")
B19_MODELS = ("H-19-RENEG", "H-19-ABS")
INT_MODELS = ("H-INT-PASS", "H-INT-WORD")
Z_MODELS = ("H-PASS-Z", "H-PASS-LE")


def zp_args(w, h, ctl, dfill, z, test, pages=ZP_PAGES):
    return (f"{MAIN} {size(w, h)} --tri-full --tri-z {z},{z},{z} --depth --depth-ctl {ctl:#010x} "
            f"--depth-fill {dfill} --depth-store --depth-store-fill {FILL_DEAD:#010x} "
            f'--depth-pages {pages} --depth-dump "$W" --poke blk:1={test:#010x} --pixels')


# name: (w, h, ctl, fill, z, test, pages, set, models)
ZPASS = {
    "zp-c-467": (256, 128, 0x0017503E, "bit:9", "0.5", LESS, 40, "control", ("H-EDGE",)),
    "zp-c-band": (34, 18, 0x0017100C, "bit:3", "0.5", LESS, ZP_PAGES, "control", ("H-EDGE",)),
    "zp-e-dp": (34, 18, ZP_CTL, "bit:3", "0.5", LESS, ZP_PAGES, "heldout", EDGE_MODELS),
    "zp-19-nv": (64, 32, ZP_CTL | 1 << 19, "bit:9", "0.5", NEVER, ZP_PAGES, "heldout", B19_MODELS),
    "zp-19-ls": (64, 32, ZP_CTL | 1 << 19, "bit:9", "0.5", LESS, ZP_PAGES, "heldout", B19_MODELS),
    "zp-f1": (64, 32, ZP_CTL | 1 << 24, "bit:9", "0.375", LESS, ZP_PAGES, "heldout", INT_MODELS),
    "zp-f2": (64, 32, ZP_CTL | 2 << 24, "bit:9", "0.375", LESS, ZP_PAGES, "heldout", INT_MODELS),
    "zp-z0": (64, 32, ZP_CTL, "bit:9", "0", LESS, ZP_PAGES, "heldout", Z_MODELS),
    "zp-z125": (64, 32, ZP_CTL, "bit:9", "0.125", LESS, ZP_PAGES, "heldout", Z_MODELS),
    "zp-z75": (64, 32, ZP_CTL, "bit:9", "0.75", LESS, ZP_PAGES, "heldout", Z_MODELS),
    "zp-z1": (64, 32, ZP_CTL, "bit:9", "1", LESS, ZP_PAGES, "heldout", Z_MODELS),
}
ZP_ARGS = {"zp-c-id": ZP_ID_ARGS}
for _n, (_w, _h, _c, _f, _z, _t, _p, _s, _m) in ZPASS.items():
    ZP_ARGS[_n] = zp_args(_w, _h, _c, _f, _z, _t, _p)
ZP_CONTROL = {"zp-c-id": "dst_changed", "zp-c-467": "drawn,dst_changed",
              "zp-c-band": "drawn,dst_changed"}


def ctl_g(ctl):
    return ctl >> 3 & 0x1FF


def pass_predict(name, model):
    """({store dword: value}, drawn) of a zpass row under model: every dword of the target's tiles
    (the 16-bit layout's 256 a slot in format 2); the rest of the store keeps its fill"""
    return pass_model(*ZPASS[name][:6], model)


def pass_model(w, h, ctl, fill, z, test, model):
    """pass_predict's rule for any zbase-form row (tests replay it on kept rows)"""
    g, fmt, neg = ctl_g(ctl), ctl >> 24 & 7, bool(ctl >> 19 & 1)
    load = ctl & 0x4002 == 0x4002
    zb = f32_bits(z)
    tw, th = tiles(w, h)
    val, drawn = {}, 0
    for y in range(16 * th):
        for x in range(32 * tw):
            edge_tile = (32 * (x // 32 + 1) > w) or (16 * (y // 16 + 1) > h)
            band = in_band(x, y, w, h)
            if load and not (model == "H-EDGE-SKIP" and edge_tile):
                start = fill_at(fill, store_dword(x, y, g)) & 0x7FFFFFFF
            else:
                start = CLEAR
            if model == "H-EDGE-CLEAR" and not band:
                start = CLEAR
            if model == "H-INT-WORD":
                ref = (start & 0xFFFFFF) / 16777216.0
            else:
                ref = f32(start)
            zf = f32(zb)
            passed = band and (test == LESS and (zf < ref or (model == "H-PASS-LE" and zf == ref)))
            v = zb if passed else start
            drawn += passed and x < w and y < h
            if fmt == 0:
                if neg and (passed or model != "H-19-ABS"):
                    v |= 0x80000000
                val[(x, y)] = v
            else:
                val[(x, y)] = floor24(v)
    out = {}
    if fmt == 2:
        for y in range(0, 16 * th, 2):
            for x in range(32 * tw):
                out[store_dword16(x, y, g)] = val[(x, y)] >> 8 | (val[(x, y + 1)] >> 8) << 16
    else:
        for (x, y), v in val.items():
            out[store_dword(x, y, g)] = v
    return out, drawn


# ---- zbits3 ----------------------------------------------------------------------------------
ST_CTL = 0x0017300E                        # E988's st1: stencil loaded (1, 13) and stored, G 1
ST_CTL_G2 = (ST_CTL & ~0xFF8) | 2 << 3     # 0x00173016
ISP2_B0 = 2 << 25 | 5 << 16 | 0x01 << 8 | 0xFF     # EQUAL, invert on pass, mask 0x01: 0x040501ff
REF1 = " --poke blk:1^=0x1"
# E1042's zb2-b23 (fold/look.py): the byte the test read by x mod 16, every row alike
COL23 = (0x3F, 0x80, 0x00, 0x00, 0x80, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x3F, 0x80, 0x00, 0x3F,
         0x80, 0x00)
B15_MODELS = ("H15-FAIL", "H15-READFF")
B23_MODELS = ("H23-MOD16", "H23-LOADED")
PAIR_MODELS = ("H-PAIR-23", "H-PAIR-ZERO", "H-PAIR-BASE")


def st_args(ctl, w=64, h=32, sfill="bytes", extra=""):
    return (f"{MAIN} --tri-full {size(w, h)} --depth --depth-ctl {ctl:#010x} --depth-fill "
            f"0x3f800000 --stencil --stencil-fill {sfill} --stencil-store --isp2 {ISP2_B0:#010x} "
            f'--depth-dump "$W" --pixels{extra}')


# name: (w, h, ctl, fill, ref, set, models)
ZBITS3 = {
    "zb3-c-base": (64, 32, ST_CTL, "bytes", 0, "control", ()),
    "zb3-c-set": (64, 32, 0xF8F7B00E, "bytes", 0, "control", ()),
    "zb3-c-b23": (64, 32, ST_CTL | 1 << 23, "bytes", 0, "control", ()),
    "zb3-c-ref1": (64, 32, ST_CTL, "bytes", 1, "control", ()),
    "zb3-b15-96": (96, 32, ST_CTL_G2 | 1 << 15, "bytes", 0, "heldout", B15_MODELS),
    "zb3-b15-r1": (64, 32, ST_CTL | 1 << 15, "bytes", 1, "heldout", B15_MODELS),
    "zb3-b23-96": (96, 32, ST_CTL_G2 | 1 << 23, "bytes", 0, "heldout", B23_MODELS),
    "zb3-b23-idx": (64, 32, ST_CTL | 1 << 23, "index", 0, "heldout", B23_MODELS),
    "zb3-p21-23": (64, 32, ST_CTL | 1 << 21 | 1 << 23, "bytes", 0, "heldout", PAIR_MODELS),
    "zb3-p22-23": (64, 32, ST_CTL | 1 << 22 | 1 << 23, "bytes", 0, "heldout", PAIR_MODELS),
    "zp-e-st": (34, 18, ST_CTL, "bytes", 0, "heldout", EDGE_MODELS),
}
ZB3_ARGS = {}
for _n, (_w, _h, _c, _f, _r, _s, _m) in ZBITS3.items():
    ZB3_ARGS[_n] = st_args(_c, _w, _h, _f, (REF1 if _r else "")
                           + (" --depth-pages 16" if _h % 16 or _w % 32 else ""))
ZB3_CONTROL = {"zb3-c-base": ("drawn", 1024), "zb3-c-set": ("drawn", 2048),
               "zb3-c-b23": ("drawn", 1536), "zb3-c-ref1": ("drawn", 1024)}
ZB3_READS = {"zb3-c-base": "drawn", "zb3-c-set": "drawn,sst_changed", "zb3-c-b23": "drawn",
             "zb3-c-ref1": "drawn"}


def st_pos(x, y, g=1):
    """E988: the stencil byte of pixel (x, y): 512 bytes a tile at the slot, the in-tile index"""
    return TILE_DW * slot(x, y, g) + in_tile_index(x, y)


def stencil_predict(name, model, g23=None):
    """({stencil-store byte: value}, drawn, pixels drawn) of a zbits3 row under model (the
    target's tiles; g23 the read map H23-LOADED fits on E1042's kept zb2-b23, {loaded: read})"""
    return stencil_model(*ZBITS3[name][:5], model, g23)


def stencil_model(w, h, ctl, fill, ref, model, g23=None):
    """stencil_predict's rule for any st1-form row (tests replay it on kept rows)"""
    g = ctl_g(ctl)
    tw, th = tiles(w, h)
    out, drawn = {}, set()
    for y in range(16 * th):
        for x in range(32 * tw):
            p = st_pos(x, y, g)
            loaded = fill_byte(fill, p)
            band = in_band(x, y, w, h)
            edge_tile = (32 * (x // 32 + 1) > w) or (16 * (y // 16 + 1) > h)
            fail = False
            if model == "H15-FAIL":
                read, fail = loaded, True
            elif model == "H15-READFF":
                read = 0xFF
            elif model in ("H23-MOD16", "H-PAIR-23"):
                read = COL23[x % 16]
            elif model == "H23-LOADED":
                read = g23[loaded]
            elif model == "H-PAIR-ZERO":
                read = 0
            elif model == "H-EDGE-SKIP" and edge_tile:
                read = 0
            else:
                read = loaded
            if model == "H-EDGE-CLEAR" and not band:
                read = 0
            passed = band and not fail and (read & 1) == ref
            if passed:
                out[p] = read ^ 0xFF
                if x < w and y < h:
                    drawn.add((x, y))
            else:
                out[p] = loaded if model == "H15-READFF" else read
    return out, len(drawn), drawn


# ---- zflat2 ----------------------------------------------------------------------------------
F0_CTL, F5_CTL, F6_CTL = 0x0017300E, 0x0517300E, 0x0617300E
FLAT_N = 44                                 # E1031: 44 dwords at the start of each 512-dword block
REC0_DEPTHS = {"zl2-f6-0p375": "0.375", "zl2-f6-0p625": "0.625", "zl2-f6-0p9375": "0.9375",
               "zl2-f6-0p0625": "0.0625"}
TWIN_DEPTHS = {"0p1": "0.1", "0p3": "0.3", "0p5e20": "0.50000095367431640625"}
FLAT_MODELS = ("H-LOW16", "H-FLATPLANE")
ZL2_CHANGED = {"zl2-c-flat": 176, "zl2-c-y6": 212, "zl2-c-f5": 944}


def zf_args(ctl, z, sfill="index"):
    return (f"{MAIN} {size(64, 32)} --tri-full --tri-z {z} --depth --depth-ctl {ctl:#010x} "
            f"--depth-fill 0xdeadbeef --stencil --stencil-fill {sfill} --stencil-store --depth-dump "
            f'"$W" --poke blk:1={LESS:#010x}')


def flat_depth(name):
    if name in REC0_DEPTHS:
        return REC0_DEPTHS[name]
    return TWIN_DEPTHS[name.split("-")[-1]]


def rec0_block(ref176, v):
    """E1031's 44-dword block (ref176, its bytes) with row 0's record (bytes 7 to 10) at v"""
    b = bytearray(ref176)
    b[7:11] = struct.pack("<I", v)
    return bytes(b)


def rec0_check(dump, ref176, v):
    """(held, text): the four blocks E1031's with v at bytes 7 to 10, nothing else changed"""
    if dump is None:
        return None, "no dump"
    want = rec0_block(ref176, v)
    blocks = sum(dump[2048 * k:2048 * k + 176] == want for k in range(4))
    dw = dwords(dump)
    other = sum(1 for i, x in enumerate(dw) if x != FILL_DEAD and not (i < 2048 and i % 512 < FLAT_N))
    return blocks == 4 and not other, f"{blocks}/4 blocks at v {v:#010x}, {other} other dwords"


def rec0_any(dump, ref176):
    """the v whose FL-REC0 form the dump holds (block 0's bytes 7 to 10), or None"""
    if dump is None or len(dump) < 2048 * 4:
        return None
    v = struct.unpack("<I", dump[7:11])[0]
    return v if rec0_check(dump, ref176, v)[0] else None


ZFLAT2 = {"zl2-c-flat": zf_args(F6_CTL, "0.5,0.5,0.5"),
          "zl2-c-y6": zf_args(F6_CTL, "0.25,0.25,0.75"),
          "zl2-c-f5": zf_args(F5_CTL, "0.5,0.5,0.5")}
for _n, _z in REC0_DEPTHS.items():
    ZFLAT2[_n] = zf_args(F6_CTL, f"{_z},{_z},{_z}")
for _k, _z in TWIN_DEPTHS.items():
    ZFLAT2[f"zl2-f0-{_k}"] = zf_args(F0_CTL, f"{_z},{_z},{_z}")
    ZFLAT2[f"zl2-f6-{_k}"] = zf_args(F6_CTL, f"{_z},{_z},{_z}")


# ---- zovl ------------------------------------------------------------------------------------
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


OV_MODELS = ("H-LATE/HDR", "H-EARLY/HDR", "H-LATE/RASTER", "H-EARLY/RASTER")
# name: (w, h, g, format, the kept full-pitch format-0 reference, its pitch)
OV_ROWS = {"zv-ov-64-f2": (64, 32, 0, 2, "zov-64x32-ctl", 1),
           "zv-ov-160-f2": (160, 48, 2, 2, "zov-160x48-ctl", 4),
           "zv-ov-65-f1": (65, 33, 1, 1, "zo-65-f0", 2),
           "zv-ov-640-f1": (640, 480, 2, 1, "zo-640-f0", 19)}


def ov_predict(full, w, h, g, fmt, gref, model):
    """{dword: value} the overlapping store holds in format fmt: each slot the owner tile's
    pixels, from the full-pitch float reference `full` (pitch gref) by E991's floor rule"""
    out = {}
    for s, (c, r) in owners(w, h, g, model).items():
        for yy in range(0, 16, 1 if fmt == 1 else 2):
            for xx in range(32):
                x, y = 32 * c + xx, 16 * r + yy
                v = floor24(full[store_dword(x, y, gref)])
                if fmt == 1:
                    out[TILE_DW * s + in_tile_index(x, y)] = v
                else:
                    v2 = floor24(full[store_dword(x, y + 1, gref)])
                    out[256 * s + in_tile_index16(x, y)] = v >> 8 | (v2 >> 8) << 16
    return out


INT_OUT_MODELS = ("H-INT-SAT", "H-INT-WRAP", "H-INT-SIGN")
OFF_HI, OFF_LO, OFF_C = 0x3FA00000, 0xBE800000, 0x3F400000   # z offsets 1.25, -0.25, 0.75 (blk:10)


def zi_args(fmt, off):
    return (f"{MAIN} {size(64, 32)} --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl "
            f"{zctl(1, fmt):#010x} --depth-fill {FILL_DEAD:#010x} --depth-dump \"$W\" --poke "
            f"blk:1={ALWAYS:#010x} --poke blk:10={off:#010x}")


INT_OUT = {"zv-i125-f1": (1, OFF_HI), "zv-i125-f2": (2, OFF_HI), "zv-im25-f1": (1, OFF_LO),
           "zv-im25-f2": (2, OFF_LO)}


def int_out_word(fmt, z, model):
    """the dword every pixel (pair) stores at window depth z under model"""
    if model == "H-INT-WRAP":
        v = math.floor(z * 16777216.0) % 16777216
    elif model == "H-INT-SIGN":
        v = min(int(abs(z) * 16777216.0), 0xFFFFFF)
    else:
        v = 0 if z < 0 else min(int(z * 16777216.0), 0xFFFFFF)
    return v if fmt == 1 else (v >> 8) | (v >> 8) << 16


def int_out_predict(name, model):
    fmt, off = INT_OUT[name]
    z = 0.5 + f32s(off) - 0.5                 # E987's H-OFF: t + w - 0.5 at t = 0.5
    n = 2048 if fmt == 1 else 1024
    word = int_out_word(fmt, z, model)
    return {i: word for i in range(n)}


G_CTLS = {"zv-b25": (0x0217100C, 20), "zv-g5": (zctl(5), 24), "zv-g9": (zctl(9), 32),
          "zv-g17": (zctl(17), 44)}
RD13 = 0xD000
G_BASE_PAGE = (RD13 - 0x1000) // 4096        # page 12 of the depth buffer (depth at base + 0x1000)
G_MODELS = ("H-E465-EXT", "H-STOP16")
B25_MODELS = ("H-B25-FLOOR", "H-B25-FF")


def g_args(ctl, pages):
    return (f"{MAIN} {size(64, 64)} --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl "
            f"{ctl:#010x} --depth-fill {FILL_DEAD:#010x} --depth-pages {pages} --depth-dump "
            f'"$W" --poke blk:1={LESS:#010x} --kpoke-render 1:rd:13={RD13:#x}')


def g_pages(name, model):
    """{page: (dwords, value)} of the depth buffer under model"""
    ctl, _ = G_CTLS[name]
    g = ctl_g(ctl)
    if name == "zv-b25":
        v = 0x80008000 if model == "H-B25-FLOOR" else 0xFFFFFFFF
        return {G_BASE_PAGE: (1024, v), G_BASE_PAGE + 1: (1024, v)}
    rows = {G_BASE_PAGE + (g + 1) * ty // 2: (1024, 0x3F000000) for ty in range(4)}
    return rows if model == "H-E465-EXT" else {p: c for p, c in rows.items() if p < 16}


ZOVL = {"zv-c-ov": zov_args(64, 32, 0)}
for _n, (_w, _h, _g, _f, _r, _gr) in OV_ROWS.items():
    # a size that is not whole tiles passes --depth-pages (HACKING "Known tool weaknesses")
    ZOVL[_n] = zov_args(_w, _h, _g, _f) + (" --depth-pages 20" if _w % 32 or _h % 16 else "")
ZOVL["zv-c-075"] = zi_args(1, OFF_C)
ZOVL["zv-r-hi"] = zi_args(0, OFF_HI)
for _n, (_f, _o) in INT_OUT.items():
    ZOVL[_n] = zi_args(_f, _o)
ZOVL["zv-c-g3"] = g_args(0x0017101C, 20)
for _n, (_c, _p) in G_CTLS.items():
    ZOVL[_n] = g_args(_c, _p)
ZV_CONTROL = {"zv-c-ov": 1536, "zv-c-075": 2048, "zv-c-g3": 4096}
ZV_C075 = 0x00C00000                         # floor(0.75 2^24)


# ---- the rows --------------------------------------------------------------------------------
# A stage's rows all write the dump its scorer reads (REQUIRED is per row), so zp-e-st (E1050's
# stencil edge row) runs in zbits3, the stencil-store stage. zovl's sized rows are last, in
# ascending extent (session.toml: on_stop = "end").
STAGE_ROWS = {
    "zpass": ["zp-c-id", "zp-c-467", "zp-c-band", "zp-e-dp", "zp-19-nv", "zp-19-ls", "zp-f1",
              "zp-f2", "zp-z0", "zp-z125", "zp-z75", "zp-z1"],
    "zbits3": ["zb3-c-base", "zb3-c-set", "zb3-c-b23", "zb3-c-ref1", "zb3-b15-96", "zb3-b15-r1",
               "zb3-b23-96", "zb3-b23-idx", "zb3-p21-23", "zb3-p22-23", "zp-e-st"],
    "zflat2": ["zl2-c-flat", "zl2-c-y6", "zl2-c-f5", *REC0_DEPTHS,
               *(f"zl2-{f}-{k}" for k in TWIN_DEPTHS for f in ("f0", "f6"))],
    "zovl": ["zv-c-ov", *OV_ROWS, "zv-c-075", "zv-r-hi", *INT_OUT, "zv-c-g3", "zv-b25", "zv-g5", "zv-g9",
             "zv-g17"],
}
ARGS = {**ZP_ARGS, **ZB3_ARGS, **ZFLAT2, **ZOVL}


def row(n):
    """(set, knobs, {quantity: {model: value}}) of row n"""
    if n in ZP_CONTROL:
        q = {"store": {"H-KEPT" if n == "zp-c-id" else "H-EDGE": "kept" if n == "zp-c-id" else "rule"}}
        if n != "zp-c-id":
            q["drawn"] = {"H-EDGE": str(pass_predict(n, "H-EDGE")[1])}
        return "control", f"expectdiff reads:{ZP_CONTROL[n]}", q
    if n in ZPASS:
        ms = ZPASS[n][8]
        return "heldout", "expectdiff", {"store": {m: "rule" for m in ms},
                                         "drawn": {m: str(pass_predict(n, m)[1]) for m in ms}}
    if n in ZB3_CONTROL:
        k, v = ZB3_CONTROL[n]
        return "control", f"expectdiff reads:{ZB3_READS[n]}", {k: {"H-E1042": str(v)},
                                                               "stencil": {"H-E1042": "kept" if n != "zb3-c-ref1" else "rule"}}
    if n in ZBITS3:
        ms = ZBITS3[n][6]
        return "heldout", "expectdiff", {"stencil": {m: "rule" for m in ms},
                                         "drawn": {m: str(stencil_predict(n, m, g23=G23_STUB)[1])
                                                   if m != "H23-LOADED" else "rule" for m in ms}}
    if n in ZL2_CHANGED:
        return "control", "expectdiff reads:depth_changed", {
            "depth_changed": {"H-KEPT": str(ZL2_CHANGED[n])}, "dump": {"H-KEPT": "kept"}}
    if n in REC0_DEPTHS:
        return "heldout", "expectdiff", {"block": {"FL-REC0": f"v={f32_bits(REC0_DEPTHS[n]):#010x}"}}
    if n.startswith("zl2-f0-") or n == "zv-r-hi":
        return "reading", "expectdiff", {}
    if n.startswith("zl2-f6-"):
        v = f32_bits(flat_depth(n))
        return "heldout", "expectdiff", {"block": {
            "H-LOW16": f"v={v:#010x}" if v & 0xFFFF == 0 else "not-rec0",
            "H-FLATPLANE": f"rule:zl2-f0-{n.split('-')[-1]}"}}
    if n in ZV_CONTROL:
        return "control", "expectdiff reads:depth_changed", {
            "depth_changed": {"H-KEPT": str(ZV_CONTROL[n])},
            "dump": {"H-KEPT": "kept" if n != "zv-c-075" else f"all {ZV_C075:#010x}"}}
    if n in OV_ROWS:
        return "heldout", "expectdiff", {"dwords": {m: f"rule:{OV_ROWS[n][4]}" for m in OV_MODELS}}
    if n in INT_OUT:
        return "heldout", "expectdiff", {"dwords": {
            m: f"all {int_out_predict(n, m)[0]:#010x}" for m in INT_OUT_MODELS}}
    ms = B25_MODELS if n == "zv-b25" else G_MODELS
    return "heldout", "expectdiff", {"pages": {
        m: ",".join(f"{p}:{c}x{v:#010x}" for p, (c, v) in sorted(g_pages(n, m).items())) for m in ms}}


# the drawn counts of the models that do not read the loaded byte (H23-LOADED's is the score's)
G23_STUB = {b: b for b in range(256)}


def jobs():
    """[(stage, name, set, knobs, args, {quantity: {model: value}})] in run order"""
    return [(st, n, *row(n)[:2], ARGS[n], row(n)[2]) for st, ns in STAGE_ROWS.items() for n in ns]
