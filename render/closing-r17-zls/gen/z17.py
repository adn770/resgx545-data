# SPDX-License-Identifier: MIT
"""z17.py: r17-zls's rows and frozen rivals (round 17 plan closing17/plan/rank-round17.md section 2
"r17-zls", decisions R17-1 (a), R17-5 (a), R17-6 (a); tool t10, resgx545 a581c06 sgxfive-test.c).
Round 16's r16-zls (render/closing-r16-zls gen/z16.py, E1059, E1063, E1064) is the direct
predecessor: its helpers are copied here, not imported, so this file alone is frozen. A row's name
prefix names its record: zo2- (zovp2 and zovs2) E1068 (Q299), zb20- E1069 (Q071). Kept records are
read at the frozen data commit (gen/pins.py, KEPT below).

Part zovp2 (Q299, E1068; stage zovp2, the depth store): the depth load pass over overlapping
tiles WITH EDGE TILES. E1064 loaded and passed whole tiles only (64 x 32 G 0, 160 x 48 G 2); E1041
and E1051 stored over edge tiles with no load. Shapes (both have slots shared by two tiles and
edge tiles, tests/test_gen.py checks it by E465's slot map and E996's header order):
  65 x 33 G 1   3 x 3 tiles, pitch 2: slots 2 and 4 shared (tiles (0,2)-(1,0) and (1,2)-(2,0));
                the last tile column and row are one pixel wide and high (E1041's zo-65-ov shape)
  63 x 31 G 0   2 x 2 tiles, pitch 1: slot 1 shared by the two edge tiles (0,1) and (1,0); the
                last column is 31 pixels wide and the last row 15 high
(README deviation 1: the plan names 161 x 49 G 2 as the second shape; no kept plane reference
exists there, so the frozen drawn counts would need an extra reference job; 63 x 31 G 0 has E1041's
kept zo-63-f0 and the other edge-tile geometry.) E996's plane (z 0, ZX, 1 at (0,0), (2W,0),
(0,2H)), the depth loaded from a buffer filled 0.2f (0x3e4ccccd) and stored, depth less, 20 pages
explicit; the plane's float at each pixel is the kept full-pitch reference's (E1041's zo-65-f0 at
G 2, zo-63-f0 at G 1; H-PASS-TWIN [infer], E1059):
  H-OVL-PASS-EDGE  each tile, edge tiles included, loads its slot (E465; a shared slot's dwords
                   for every tile sharing it) and passes as E1050 over the whole 32 x 16 tile; a
                   shared store slot holds the tile visited last in region header order (E996,
                   E1064, E1041); the pixels beyond the extent are tested like the others
  H-OVL-FIRST      the same with the slot holding the tile visited first (E1064 refuted it on
                   whole tiles)
  H-EDGE-SKIP      an edge tile takes no load (starts from the clear 1.0)
  H-EDGE-EXT       the load reaches the pixels inside the extent only: those beyond start from the
                   clear 1.0
  H-EDGE-CLIP      the pass tests the pixels inside the extent only: those beyond keep their load
The stencil rows (stage zovs2, the stencil store: E988's st1 form at the same shapes, `bytes`
load) have the same models but H-OVL-FIRST (a shared slot loads the same bytes for every tile, so
first and last store the same: E1064 deviation 4). The stencil of an edge tile beyond the extent
is tested [infer: tri-full covers the whole tile area at both shapes].
Controls (can fail): zo2-c-160 (E1064's zo-p-160 rerun, its kept store byte for byte), zo2-c-65
(the 65 x 33 G 1 no-load store, the store form of E1041's kept zo-65-ov: its first 3584 dwords
and E996's owner rule), zo2-c-63 (the 63 x 31 G 0 no-load store: E996's owner rule from the kept
reference), zo2-c-s160 (E1064's zo-s-160 rerun, its kept stencil store byte for byte).

Part zb20 (Q071, E1069; stage zb20, the depth dump and the stencil store): bit 20 cleared on
formats 6 and 7 at other sizes. E1063 saw (post hoc, one size, 64 x 32 G 1) the per-tile records
packed one after another from dword 2048 instead of at their slots' starts, dwords 2048 to 2223
(format 6, 44 a tile) and 2048 to 2095 (format 7, 24 in each of the first two tiles), in tile
order. Each row runs beside its bit-20-set twin at the same size (the records of the twin are the
row's expected content), 128 x 64 G 3 and 96 x 48 G 2, no overlap (G = tiles across - 1), 32
pages explicit:
  H-PACK2048    the twin's tile records, one after another in slot order, from dword 2048
  H-PACK-AFTER  from the end of the last slot: 512 x (rows x (G + 1)) (2048 at 64 x 32 G 1)
  H-PACK-SCALE  from 1024 x (G + 1), an offset scaling with the pitch (2048 at 64 x 32 G 1)
the three agree at E1063's size; at 128 x 64 G 3 they are 2048, 8192 and 4096, at 96 x 48 G 2
2048, 4608 and 3072. The record of a tile is its slot's dwords other than the fill 0xdeadbeef in
the twin; the tile order is the slot order (E996's header order is raster at both sizes, checked
in tests/test_gen.py). Every other dword of the row's depth dump keeps its fill, the stencil store
keeps its fill (as the twin's, E1031), and the drawn count is the target's pixels (tri-full).
Control (can fail): zb20-c-f6, E1063's zb4-c-f6 (E1031's zf-flat-f6 rerun: its kept depth dump and
stencil store byte for byte, 176 dwords changed)."""
import math
import struct

MAIN = "tri --keep-going --wait-ms 20000"
TILE_DW = 512
FILL_DEAD = 0xDEADBEEF
CLEAR = 0x3F800000
LESS = 0x00400200
TRI_COLOUR = 0xFF00FF00

R10X = "render/closing-r10-x/out/20261113-101116/zov/"
R13Z = "render/closing-r13-zls/out/20261113-213117/"
R14Z = "render/closing-r14-zls/out/20261114-054846/"
R16Z = "render/closing-r16-zls/out/20261114-092344/"
# key: the kept record (data:PATH, a .gz the pins unpack)
KEPT = {
    "zo-65-f0.dep": R14Z + "zodd/zo-65-f0.depth.1.bin.gz",                 # E1041
    "zo-65-f0.txt": R14Z + "zodd/zo-65-f0.txt.gz",
    "zo-65-ov.dep": R14Z + "zodd/zo-65-ov.depth.1.bin.gz",                 # E1041
    "zo-65-ov.txt": R14Z + "zodd/zo-65-ov.txt.gz",
    "zo-63-f0.dep": R14Z + "zodd/zo-63-f0.depth.1.bin.gz",                 # E1041
    "zo-63-f0.txt": R14Z + "zodd/zo-63-f0.txt.gz",
    "zo-p-160.dst": R16Z + "zovp/zo-p-160.depth-store.1.bin.gz",           # E1064
    "zo-p-160.txt": R16Z + "zovp/zo-p-160.txt.gz",
    "zov-160x48-ctl.dep": R10X + "zov-160x48-ctl.depth.1.bin.gz",          # E996
    "zo-s-160.sst": R16Z + "zbits4/zo-s-160.stencil-store.1.bin.gz",       # E1064
    "zo-s-160.txt": R16Z + "zbits4/zo-s-160.txt.gz",
    "zf-flat-f6.sst": R13Z + "zfmt/zf-flat-f6.stencil-store.1.bin.gz",     # E1031
    "zf-flat-f6.dep": R13Z + "zfmt/zf-flat-f6.depth.1.bin.gz",
    "zf-flat-f6.txt": R13Z + "zfmt/zf-flat-f6.txt.gz",
    "zf-7k-3f.sst": R13Z + "zfmt/zf-7k-3f.stencil-store.1.bin.gz",         # E1031
    "zf-7k-3f.dep": R13Z + "zfmt/zf-7k-3f.depth.1.bin.gz",
    "zf-7k-3f.txt": R13Z + "zfmt/zf-7k-3f.txt.gz",
    "zb4-20-f6.dep": R16Z + "zbits4/zb4-20-f6.depth.1.bin.gz",             # E1063
    "zb4-20-f6.sst": R16Z + "zbits4/zb4-20-f6.stencil-store.1.bin.gz",
    "zb4-20-f6.txt": R16Z + "zbits4/zb4-20-f6.txt.gz",
    "zb4-20-f7.dep": R16Z + "zbits4/zb4-20-f7.depth.1.bin.gz",             # E1063
    "zb4-20-f7.sst": R16Z + "zbits4/zb4-20-f7.stencil-store.1.bin.gz",
    "zb4-20-f7.txt": R16Z + "zbits4/zb4-20-f7.txt.gz",
}
# the kept tables whose rows the replicated rows are (tests/test_gen.py)
TABLES = ("render/closing-r16-zls/tables/zovp.txt", "render/closing-r16-zls/tables/zbits4.txt",
          "render/closing-r14-zls/tables/zodd.txt", "render/closing-r13-zls/tables/zfmt.txt",
          "render/closing-r10-x/tables/zov.txt")


def kept(key):
    import pins
    return pins.blob("data:" + KEPT[key])


# ---- shared (z16's helpers) ------------------------------------------------------------------


def size(w, h):
    return f"--width {w} --height {h} --max-width {w} --max-height {h}"


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def f32(u):
    """the float of the word u with its sign cleared"""
    return struct.unpack("<f", struct.pack("<I", u & 0x7FFFFFFF))[0]


def in_tile_index(x, y):
    """E465: the dword of pixel (x, y) in its 32 x 16 tile, y0 x0 y1 x1 y2 x2 y3 x3 x4"""
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def slot(x, y, g):
    """E465: the slot of pixel (x, y)'s tile at pitch G"""
    return (y >> 4) * (g + 1) + (x >> 5)


def store_dword(x, y, g):
    return TILE_DW * slot(x, y, g) + in_tile_index(x, y)


def st_pos(x, y, g=1):
    """E988: the stencil byte of pixel (x, y): 512 bytes a tile at the slot, the in-tile index"""
    return TILE_DW * slot(x, y, g) + in_tile_index(x, y)


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
    return fill_at(f, b // 4) >> (8 * (b % 4)) & 0xFF


def with_g(ctl, g):
    return (ctl & ~0xFF8) | g << 3


def less(a, b):
    """E995: the depth test less on two words, each compared with its sign cleared (NaN above)"""
    fa, fb = f32(a), f32(b)
    if math.isnan(fb):
        return not math.isnan(fa)
    return fa < fb


def zx(h):
    """The largest power of two at most 1/(2H) (r10-x gen/z.py)."""
    v = 1.0
    while v > 1 / (2 * h):
        v /= 2
    return v


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


def owners(w, h, g, late=True):
    """{slot: the tile that owns it}: visited last (late) or first in header order"""
    rank = header_rank(w, h)
    best = {}
    for t, k in rank.items():
        s = t[1] * (g + 1) + t[0]
        if s not in best or (k > rank[best[s]] if late else k < rank[best[s]]):
            best[s] = t
    return best


def shared_slots(w, h, g):
    seen = {}
    for t in header_rank(w, h):
        seen.setdefault(t[1] * (g + 1) + t[0], []).append(t)
    return {s for s, ts in seen.items() if len(ts) > 1}


def is_edge(c, r, w, h):
    """a tile that does not lie whole inside the w x h target"""
    return 32 * (c + 1) > w or 16 * (r + 1) > h


# ---- zovp2 and zovs2 -------------------------------------------------------------------------
ZP_CTL = 0x0017500E                         # depth loaded (1, 14) and stored, G 1 (E1029, E1050)
ST_CTL = 0x0017300E                         # E988's st1: stencil loaded (1, 13) and stored, G 1
ISP2_B0 = 0x040501FF
OVL_FILL = "0x3e4ccccd"                     # 0.2f
OVL_MODELS = ("H-OVL-PASS-EDGE", "H-OVL-FIRST", "H-EDGE-SKIP", "H-EDGE-EXT")
OVS_MODELS = ("H-OVL-PASS-EDGE", "H-EDGE-SKIP", "H-EDGE-EXT", "H-EDGE-CLIP")
PAGES2 = 20
# name: (w, h, g, the kept full-pitch reference, its pitch)
OVP_ROWS = {"zo2-p-65": (65, 33, 1, "zo-65-f0", 2), "zo2-p-63": (63, 31, 0, "zo-63-f0", 1)}
OVS_ROWS = {"zo2-s-65": (65, 33, 1), "zo2-s-63": (63, 31, 0)}
# the no-load store controls: (w, h, g, reference, its pitch)
OVC_ROWS = {"zo2-c-65": (65, 33, 1, "zo-65-f0", 2), "zo2-c-63": (63, 31, 0, "zo-63-f0", 1)}
# the replicated controls: kept row of table, kept store key, drawn, dst or sst changed
C160 = {"zo2-c-160": ("zovp.txt", "zo-p-160", "zo-p-160.dst"),
        "zo2-c-s160": ("zbits4.txt", "zo-s-160", "zo-s-160.sst")}


def ovp_args(w, h, ctl, fill=OVL_FILL, pages=PAGES2):
    return (f"{MAIN} {size(w, h)} --tri-v 0,0,{512 * w},0,0,{512 * h} --tri-z 0,{zx(h)!r},1 "
            f"--depth --depth-ctl {ctl:#010x} --depth-fill {fill} --depth-store --depth-store-fill "
            f'{FILL_DEAD:#010x} --depth-pages {pages} --depth-dump "$W" --poke blk:1={LESS:#010x} '
            f"--pixels")


def st_args(ctl, w=64, h=32, sfill="bytes", isp2=ISP2_B0, pages=None):
    """E988's st1 form (zb2-c-base's argv); pages only where the row names them"""
    return (f"{MAIN} --tri-full {size(w, h)} --depth --depth-ctl {ctl:#010x} --depth-fill "
            f"0x3f800000 --stencil --stencil-fill {sfill} --stencil-store --isp2 {isp2:#010x} "
            + (f"--depth-pages {pages} " if pages else "") + '--depth-dump "$W" --pixels')


def ovp_predict(full, w, h, g, gref, model, fill=OVL_FILL, load=True):
    """({store dword: value}, drawn) of the depth pass at an overlapping pitch under model: the
    plane's float of pixel (x, y) is the reference's dword at pitch gref; the start the load's
    dword at the tile's slot (sign cleared) or the clear 1.0; every dword of a tile's slot is the
    tile's own (the whole 32 x 16 tile, E1041); drawn counts the pixels inside the target"""
    tw, th = tiles(w, h)
    own = owners(w, h, g, late=model != "H-OVL-FIRST")
    out, drawn = {}, 0
    for r in range(th):
        for c in range(tw):
            s = r * (g + 1) + c
            edge = is_edge(c, r, w, h)
            for yy in range(16):
                for xx in range(32):
                    x, y = 32 * c + xx, 16 * r + yy
                    inside = x < w and y < h
                    d = TILE_DW * s + in_tile_index(x, y)
                    p = full[store_dword(x, y, gref)]
                    if not load or (model == "H-EDGE-SKIP" and edge) or (
                            model == "H-EDGE-EXT" and not inside):
                        start = CLEAR
                    else:
                        start = fill_at(fill, d) & 0x7FFFFFFF
                    passed = less(p, start) and not (model == "H-EDGE-CLIP" and not inside)
                    drawn += passed and inside
                    if own[s] == (c, r):
                        out[d] = p if passed else start
    return out, drawn


def ovs_predict(w, h, g, model):
    """({stencil-store byte: value}, drawn) of the stencil pass at an overlapping pitch: each tile
    reads its slot's loaded byte (E988), 0 where the model has it skip the load; the test passes
    where the byte's bit 0 is 0 and stores it inverted, else the byte; the owner is the tile
    visited last (first and last store the same bytes: the load is the slot's for every tile)"""
    tw, th = tiles(w, h)
    own = owners(w, h, g)
    out, drawn = {}, 0
    for r in range(th):
        for c in range(tw):
            s = r * (g + 1) + c
            edge = is_edge(c, r, w, h)
            for yy in range(16):
                for xx in range(32):
                    x, y = 32 * c + xx, 16 * r + yy
                    inside = x < w and y < h
                    p = st_pos(x, y, g)
                    rd = fill_byte("bytes", p)
                    if (model == "H-EDGE-SKIP" and edge) or (model == "H-EDGE-EXT" and not inside):
                        rd = 0
                    passed = rd & 1 == 0 and not (model == "H-EDGE-CLIP" and not inside)
                    drawn += passed and inside
                    if own[s] == (c, r):
                        out[p] = rd ^ 0xFF if passed else rd
    return out, drawn


def inside_positions(w, h, g, stencil):
    """the set of store positions (dwords, or bytes for the stencil) of the owner tiles' pixels
    inside the w x h target: the scorer's reading splits the fit by it"""
    tw, th = tiles(w, h)
    own = owners(w, h, g)
    f = st_pos if stencil else store_dword
    return {f(x, y, g) for y in range(h) for x in range(w)
            if own[(y >> 4) * (g + 1) + (x >> 5)] == (x >> 5, y >> 4)}


ZO2_ARGS = {}
for _n, (_w, _h, _g, _r, _gr) in OVP_ROWS.items():
    ZO2_ARGS[_n] = ovp_args(_w, _h, with_g(ZP_CTL, _g))
for _n, (_w, _h, _g, _r, _gr) in OVC_ROWS.items():
    ZO2_ARGS[_n] = ovp_args(_w, _h, with_g(0x00171004, _g))
for _n, (_w, _h, _g) in OVS_ROWS.items():
    ZO2_ARGS[_n] = st_args(with_g(ST_CTL, _g), _w, _h, pages=PAGES2)
# E1064's zo-p-160 and zo-s-160, byte for byte (tests/test_gen.py reads them from the kept tables)
ZO2_ARGS["zo2-c-160"] = ovp_args(160, 48, with_g(ZP_CTL, 2))
ZO2_ARGS["zo2-c-s160"] = st_args(with_g(ST_CTL, 2), 160, 48)


def kept_count(key, what):
    """the count of `tri WxH #1: N triangle` (what 'drawn') or of `NAME #1: D dwords, N changed`"""
    import re
    t = kept(key + ".txt").decode()
    if what == "drawn":
        return int(re.search(r"^tri \d+x\d+ #1: (\d+) triangle", t, re.M).group(1))
    return int(re.search(r"^%s #1: \d+ dwords, (\d+) changed" % what, t, re.M).group(1))


def ovc_expect(n):
    """(frozen drawn, frozen dst_changed) of the no-load control n: E996's owner rule on the kept
    reference (H-OVL-PASS-EDGE with the load off)"""
    w, h, g, ref, gref = OVC_ROWS[n]
    pred, drawn = ovp_predict(dwords(kept(ref + ".dep")), w, h, g, gref, "H-OVL-PASS-EDGE", load=False)
    return drawn, len(pred)


# ---- zb20 ------------------------------------------------------------------------------------
F6_CTL, F7_CTL = 0x0617300E, 0x0717300E
PACK_MODELS = ("H-PACK2048", "H-PACK-AFTER", "H-PACK-SCALE")
PAGES20 = 32
# name: (format, w, h, G); the twin of a row is its name with zb20-t- for zb20-b- (bit 20 set)
ZB20_ROWS = {"zb20-b-6-96": (6, 96, 48, 2), "zb20-b-7-96": (7, 96, 48, 2),
             "zb20-b-6-128": (6, 128, 64, 3), "zb20-b-7-128": (7, 128, 64, 3)}
ZB20_CTL = {"zb20-c-f6": ("zf-flat-f6", 176)}


def zf_args(ctl, w, h, z, sfill="index", pages=None):
    """E1031's zfmt form (zf-flat-f6, zf-7k-3f), sized"""
    return (f"{MAIN} {size(w, h)} --tri-full --tri-z {z} --depth --depth-ctl {ctl:#010x} "
            f"--depth-fill 0xdeadbeef " + (f"--depth-pages {pages} " if pages else "")
            + f'--stencil --stencil-fill {sfill} --stencil-store --depth-dump "$W" '
            f"--poke blk:1={LESS:#010x}")


def zb20_form(fmt):
    return (F6_CTL, "0.5,0.5,0.5", "index") if fmt == 6 else (F7_CTL, "0.25,0.75,0.25", "0x3f3f3f3f")


def zb20_args(name):
    """the row (bit 20 cleared) or its twin (bit 20 set: zb20-t-...) of a zb20 name"""
    fmt, w, h, g = ZB20_ROWS[name.replace("-t-", "-b-")]
    ctl, z, sf = zb20_form(fmt)
    ctl = with_g(ctl, g)
    if "-b-" in name:
        ctl &= ~(1 << 20)
    return zf_args(ctl, w, h, z, sf, PAGES20)


def pack_start(model, w, h, g):
    th = tiles(w, h)[1]
    return {"H-PACK2048": 2048, "H-PACK-AFTER": TILE_DW * th * (g + 1),
            "H-PACK-SCALE": 1024 * (g + 1)}[model]


def records(twin, nslots):
    """the twin's per-tile records in slot order: each slot's dwords other than the fill"""
    return [[v for v in twin[TILE_DW * s:TILE_DW * s + TILE_DW] if v != FILL_DEAD]
            for s in range(nslots)]


def pack_predict(twin, w, h, g, model):
    """{dword: value} of the bit-20-cleared row: the twin's records one after another from the
    model's start; every other dword keeps its fill"""
    th = tiles(w, h)[1]
    start, out = pack_start(model, w, h, g), {}
    i = start
    for rec in records(twin, th * (g + 1)):
        for v in rec:
            out[i] = v
            i += 1
    return out


def prefix_records(twin, nslots):
    """True when every slot's records are a prefix of its block (contiguous from the start)"""
    for s in range(nslots):
        blk = twin[TILE_DW * s:TILE_DW * s + TILE_DW]
        n = sum(v != FILL_DEAD for v in blk)
        if any(v == FILL_DEAD for v in blk[:n]) or any(v != FILL_DEAD for v in blk[n:]):
            return False
    return True


# ---- the rows --------------------------------------------------------------------------------
# A stage's rows all write the dump its scorer reads (REQUIRED is per stage): zovp2 the depth
# store, zovs2 the stencil store, zb20 the depth dump and the stencil store. Rows reaching a
# range never run are last: zb20's 128 x 64 pair (the packed records up to dword 8192 of the
# buffer and the 32-page buffers); zb20's stop ends the session.
STAGE_ROWS = {
    "zovp2": ["zo2-c-160", "zo2-c-65", "zo2-c-63", "zo2-p-65", "zo2-p-63"],
    "zovs2": ["zo2-c-s160", "zo2-s-65", "zo2-s-63"],
    "zb20": ["zb20-c-f6", "zb20-t-6-96", "zb20-b-6-96", "zb20-t-7-96", "zb20-b-7-96",
             "zb20-t-6-128", "zb20-b-6-128", "zb20-t-7-128", "zb20-b-7-128"],
}
ARGS = dict(ZO2_ARGS)
ARGS["zb20-c-f6"] = zf_args(F6_CTL, 64, 32, "0.5,0.5,0.5")      # E1031's zf-flat-f6, byte for byte
for _n in STAGE_ROWS["zb20"]:
    if _n != "zb20-c-f6":
        ARGS[_n] = zb20_args(_n)
STAGE_OF = {n: s for s, ns in STAGE_ROWS.items() for n in ns}


def zb20_twin_of(name):
    return name.replace("-b-", "-t-")


def row(n):
    """(set, knobs, {quantity: {model: value}}) of row n"""
    if n in C160:
        _, kr, ks = C160[n]
        q = "dst_changed" if n == "zo2-c-160" else "sst_changed"
        return "control", f"expectdiff reads:drawn,{q}", {
            "store": {"H-KEPT": "kept:" + ks}, "drawn": {"H-KEPT": str(kept_count(kr, "drawn"))},
            q: {"H-KEPT": str(kept_count(kr, "depth store" if n == "zo2-c-160" else "stencil store"))}}
    if n in OVC_ROWS:
        drawn, ch = ovc_expect(n)
        q = {"store": {"H-KEPT": "rule:E996 owner" + (", kept:zo-65-ov first 3584 dwords"
                                                      if n == "zo2-c-65" else "")},
             "drawn": {"H-KEPT": str(drawn)}, "dst_changed": {"H-KEPT": str(ch)}}
        return "control", "expectdiff reads:drawn,dst_changed", q
    if n in OVP_ROWS:
        w, h, g, ref, gref = OVP_ROWS[n]
        full = dwords(kept(ref + ".dep"))
        return "heldout", "expectdiff", {
            "store": {m: "rule" for m in OVL_MODELS},
            "drawn": {m: str(ovp_predict(full, w, h, g, gref, m)[1]) for m in OVL_MODELS}}
    if n in OVS_ROWS:
        return "heldout", "expectdiff", {
            "stencil": {m: "rule" for m in OVS_MODELS},
            "drawn": {m: str(ovs_predict(*OVS_ROWS[n], m)[1]) for m in OVS_MODELS}}
    if n == "zb20-c-f6":
        return "control", "expectdiff reads:depth_changed,sst_changed", {
            "depth_changed": {"H-KEPT": "176"}, "dumps": {"H-KEPT": "kept:zf-flat-f6"}}
    fmt, w, h, g = ZB20_ROWS[n.replace("-t-", "-b-")]
    if "-t-" in n:
        return "reading", "expectdiff", {}
    return "heldout", "expectdiff", {
        "dump": {m: f"records from dword {pack_start(m, w, h, g)}" for m in PACK_MODELS},
        "drawn": {m: str(w * h) for m in PACK_MODELS}}


def jobs():
    """[(stage, name, set, knobs, args, {quantity: {model: value}})] in run order"""
    return [(st, n, *row(n)[:2], ARGS[n], row(n)[2]) for st, ns in STAGE_ROWS.items() for n in ns]
