# SPDX-License-Identifier: MIT
"""tw.py: stage tw14 (r15-tw, Q078 T3 bit 14 on twiddled textures at widths 16, 64 and 128, u
past 1, a 16-bit format and bilinear samples; closing15/plan/rank-round15.md section 2 "r15-tw",
decision R15-2 a: SAFE CLASS, H at most 32, rows in reach order, any fault ends the session).

E1047's form (r14-flag f1): E566's tx_map on named memory (scratch dword i reads 0xD0000000 | i,
so every read names its dword), a twiddled texture (type 0) at the scratch's first dword, T0 and
T3 E566's tw32-ctl words (T0 0x07FE0000 point, T3 0x00800800; bilinear rows T0 | 0x1400, E1027's
filter bits), t14's `probe --temps 32 --coords --pixels --scratch-pages 256` (1 MiB, dwords 0 to
262143). T1 = FMT << 24 | (W - 1) << 12 | (H - 1), FMT 12 (32-bit) or 9 (u16, returned as the
half: E1003, E1026). Every texture is W x 32 (two tile rows), v = (y + 1/2) / 32 on texel row y
(bilinear: (y + 3/4) / 32), u a "lin" ramp in x of at most one texel a pixel (so the gradient's
LOD is 0 or below, as in E1047's rows [infer: a LOD above 0 would select a level of a chain that
is not there]).

Notation: s = floor(W u) mod W, t = floor(32 v) mod 32 (the bit-clear texel, repeat), fr = u -
floor(u), tl(c, t, P) = E561's 16 x 16 tile law with a tile row of P texels (law.morton of the
tile's texel + 256 (c div 16 + (P / 16)(t div 16))), REF = law.index(s, t, W, 32).

Frozen, point rows (32-bit; each image a dword name a pixel, exact):
  H-TWP      tl(s + floor(4096 fr), t, W + 4096): E1047's H-TWP4128 read as W + 4096 [infer,
             fitted at W = 32 only]
  H-TWP4128  tl(s + floor(4096 fr), t, 4128): a constant tile row of 4128 texels
  H-CLAMP1   tl(s + floor(4096 clamp(u, 0, 1)), t, W + 4096): u past 1 clamped (column s + 4096
             for u >= 1), E1003's strided clamp [refuted at W = 32 by E1047's f1-tw32, u in (1, 2):
             carried as the plan's rival; tests/test_gen.py replays it on E1047's kept images]
  H-WRAPW    tl(s + (floor(128 W u) mod 4096), t, W + 4096): the move is the texel coordinate W u
             in 1/128 texel kept to 12 bits, i.e. 4096 frac(u W / 32) [infer: the plan's "fraction
             of u W / 4096 cycles"; equal to H-TWP at W = 32, so E1047 holds it too]
  H-TWP4096  tl(s + floor(4096 fr), t, 4096): E1047's refuted pitch, a negative
  REF        the bit-clear image (the controls)
16-bit row (32 x 32, FMT 9; a pixel is the low 16 bits of the read, texel T the half T & 1 of
dword T >> 1, E1003's and E1026's u16 reading; `h:XXXX` tokens):
  U16-TX     H-TWP in texels: tl(s + floor(4096 fr), t, W + 4096) of 16 x 16 texel tiles (E1026:
             E561's tiles are texels in u16)
  U16-T32    tiles of 16 x 16 dwords, each dword two horizontally adjacent texels (32 x 16
             texels a tile): texel 2 tl(c >> 1, t, (W + 4096) / 2) + (c & 1) [the plan's second
             tile rival; tiles of 32 x 16 texels under E561's interleave are E561's 16 x 16 tiles
             in raster order, one law, so the rival is the dword-pair layout; E1026's held u16 row
             is evidence against it, not a test]
  U16-DW     the move and the widening counted in dwords: tl(s + 2 floor(4096 fr), t, W + 8192)
             of 16 x 16 texel tiles (E1003 measured texels on a strided u16 texture)
Bilinear rows (32-bit, texmodel's blend in 64ths: `t:B0,B1,B2,B3` tokens, each byte within 1,
r13-tex t3c's form): taps (x0 + i, y0 + j), x0 = floor(W u - 1/2), y0 = floor(32 v - 1/2), m =
floor(4096 fr) (the sample's u, E1027's H-FOOT). Both rows put every footprint across the
texture's right edge (x0 mod W = W - 1, kx = x on pixel x, so the second column wraps on every
pixel): tw-bl32 u = 63/64 + x / 2048 (around u = 1), tw-bl16 u = 1 + 31/32 + x / 1024 (around u =
2) [deviation from the plan's u in (0, 1) and (1, 2): with u a ramp of x alone, a spread of u puts
only 2 pixels a row on the edge, and the rivals part only there (tests/test_gen.py)]:
  H-FOOT-TW     every tap tl((x0 + i) mod W + m, (y0 + j) mod 32, W + 4096): each tap the bit-14
                address of its own wrapped bit-clear texel
  H-FOOT-SHIFT  the same with the second column unwrapped: (x0 mod W) + i + m, so where x0 mod W
                is W - 1 the right taps read column W + m
  H-POINT       the filter dropped: H-TWP's point image
Controls that can fail: the bit-clear reference of each new shape (16 x 32, 64 x 32, 128 x 32 and
the u16 32 x 32: E561's tile law, frozen image) and E1047's f1-zero rerun byte for byte (its kept
image, the bit-14 control of every row). A held-out row is cannot tell unless its shape's
reference and tw-zero passed."""
import gzip
from fractions import Fraction as F

import law
import pins
import tex

STAGE = "tw14"
B14 = 1 << 14
PAGES = 256
SCRATCH_DW = PAGES * 1024
H = 32
T0_PT, T0_BL = 0x07FE0000, 0x07FE1400
T3 = 0x00800800
FMT32, FMT16 = 12, 9
R14 = "data:render/closing-r14-flag/"
KEPT = R14 + "out/20261114-060824/f1/"
ZERO_BIN = R14 + "bins/f1-zero.bin"
ARGS = 'probe --temps 32 --coords --pixels --scratch-pages {pages} "$S/bins/{row}.bin"'

POINT = ("H-TWP", "H-TWP4128", "H-CLAMP1", "H-WRAPW", "H-TWP4096")
U16 = ("U16-TX", "U16-T32", "U16-DW")
BIL = ("H-FOOT-TW", "H-FOOT-SHIFT", "H-POINT")


def ulin(scale, offset):
    return tex.lin("x", F(scale), F(offset))


V_PT = tex.lin("y", F(1, 32), F(1, 64))         # (y + 1/2) / 32: texel row y
V_BL = tex.lin("y", F(1, 32), F(3, 128))        # (y + 3/4) / 32: fy = y + 1/4, ky 16

# name, set, W, FMT, kind (ref / point / u16 / bil), bit 14, u spec
ROWS = [
    ("tw-ref16", "control", 16, FMT32, "ref", False, ulin(F(1, 64), F(1, 128))),
    ("tw-ref64", "control", 64, FMT32, "ref", False, ulin(F(1, 64), F(1, 128))),
    ("tw-ref128", "control", 128, FMT32, "ref", False, ulin(F(1, 128), F(1, 256))),
    ("tw-refu16", "control", 32, FMT16, "ref", False, ulin(F(1, 64), F(1, 128))),
    ("tw16-u0", "heldout", 16, FMT32, "point", True, ulin(F(1, 64), F(1, 128))),
    ("tw16-u1", "heldout", 16, FMT32, "point", True, ulin(F(1, 64), 1 + F(1, 128))),
    ("tw64-u0", "heldout", 64, FMT32, "point", True, ulin(F(1, 64), F(1, 128))),
    ("tw64-u2", "heldout", 64, FMT32, "point", True, ulin(F(1, 64), 2 + F(1, 128))),
    ("tw128-u0", "heldout", 128, FMT32, "point", True, ulin(F(1, 128), F(1, 256))),
    ("tw128-u2", "heldout", 128, FMT32, "point", True, ulin(F(1, 128), 2 + F(1, 256))),
    ("tw-u16", "heldout", 32, FMT16, "u16", True, ulin(F(1, 64), F(1, 128))),
    ("tw-bl32", "heldout", 32, FMT32, "bil", True, ulin(F(1, 2048), F(63, 64))),
    ("tw-bl16", "heldout", 16, FMT32, "bil", True, ulin(F(1, 1024), 1 + F(31, 32))),
]
ZERO = "tw-zero"                 # E1047's f1-zero, byte for byte
GATE = {"tw16-u0": "tw-ref16", "tw16-u1": "tw-ref16", "tw-bl16": "tw-ref16",
        "tw64-u0": "tw-ref64", "tw64-u2": "tw-ref64", "tw128-u0": "tw-ref128",
        "tw128-u2": "tw-ref128", "tw-u16": "tw-refu16", "tw-bl32": None}


def row(name):
    return next(r for r in ROWS if r[0] == name)


def fl(q):
    return int(F(q).__floor__())


def spec(name):
    _, _, w, fmt, kind, b14, u = row(name)
    t1 = fmt << 24 | (w - 1) << 12 | (H - 1)
    return dict(base=0, ins="none", t0=T0_BL if kind == "bil" else T0_PT, t1=t1,
                t3=T3 | (B14 if b14 else 0), u=u, v=V_BL if kind == "bil" else V_PT)


def uv(name, x, y):
    sp = spec(name)
    return tex.coord(sp["u"], x, y), tex.coord(sp["v"], x, y)


def tl(c, t, pitch):
    """E561's 16 x 16 tile law with a tile row of `pitch` texels; c may pass the width."""
    assert pitch % 16 == 0
    return law.morton(c % 16, t % 16, 16, 16) + 256 * (c // 16 + (pitch // 16) * (t // 16))


def tl32(c, t, pitch):
    """Tiles of 16 x 16 dwords, each dword two horizontally adjacent u16 texels (32 x 16 texels a
    tile): the texel 2 tl(c >> 1, t, pitch / 2) + (c & 1). (Tiles of 32 x 16 texels under E561's
    interleave are E561's 16 x 16 tiles in raster order, one law: not a rival.)"""
    assert pitch % 32 == 0
    return 2 * tl(c >> 1, t, pitch // 2) + (c & 1)


def move(model, u, w):
    fr = F(u) - fl(u)
    if model == "H-CLAMP1":
        return fl(4096 * min(max(F(u), F(0)), F(1)))
    if model == "H-WRAPW":
        return fl(128 * w * F(u)) % 4096
    return fl(4096 * fr)


def point_index(model, u, v, w):
    """The texel index (dword at 32 bits) a point sample reads under a point or u16 model."""
    s, t = fl(u * w) % w, fl(v * H) % H
    if model == "REF":
        return law.index(s, t, w, H)
    if model in ("H-TWP", "H-CLAMP1", "H-WRAPW", "U16-TX"):
        return tl(s + move(model, u, w), t, w + 4096)
    if model == "H-TWP4128":
        return tl(s + move(model, u, w), t, 4128)
    if model == "H-TWP4096":
        return tl(s + move(model, u, w), t, 4096)
    if model == "U16-T32":
        return tl32(s + move(model, u, w), t, w + 4096)
    if model == "U16-DW":
        return tl(s + 2 * move(model, u, w), t, w + 8192)
    raise ValueError(model)


def taps(model, u, v, w):
    """The four (index, weight-pair) taps of a bilinear sample: [(i00, i10, i01, i11)], kx, ky."""
    fx, fy = F(u) * w - F(1, 2), F(v) * H - F(1, 2)
    x0, y0 = fl(fx), fl(fy)
    kx, ky = 64 * (fx - x0), 64 * (fy - y0)
    assert kx.denominator == 1 and ky.denominator == 1, (u, v)
    m = move("H-TWP", u, w)
    out = []
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        ty = (y0 + dy) % H
        if model == "H-FOOT-TW":
            c = (x0 + dx) % w + m
        elif model == "H-FOOT-SHIFT":
            c = x0 % w + dx + m
        elif model == "REF-BIL":
            out.append(law.index((x0 + dx) % w, ty, w, H))
            continue
        else:
            raise ValueError(model)
        out.append(tl(c, ty, w + 4096))
    return out, int(kx), int(ky)


def blend(t, kx, ky):
    """texmodel's bilinear on four dwords (00, 10, 01, 11), weights in 64ths (r13-tex t3c)."""
    wt = [(64 - kx) * (64 - ky), kx * (64 - ky), (64 - kx) * ky, kx * ky]
    out = 0
    for c in range(4):
        s = sum((t[k] >> (8 * c) & 255) * wt[k] for k in range(4))
        out |= ((s + 2048) >> 12) << (8 * c)
    return out


def name_of(i):
    return 0xD0000000 | i


def half16(texel):
    d = name_of(texel >> 1)
    return (d >> 16 if texel & 1 else d) & 0xFFFF


def pixels():
    return [(x, y) for y in range(32) for x in range(64)]


def reads(name, model):
    """[the dwords one pixel reads] for each of the 2048 pixels, raster order."""
    _, _, w, fmt, kind, _, _ = row(name)
    out = []
    for x, y in pixels():
        u, v = uv(name, x, y)
        if kind == "bil" and model in ("H-FOOT-TW", "H-FOOT-SHIFT", "REF-BIL"):
            out.append(taps(model, u, v, w)[0])
        else:
            i = point_index("H-TWP" if model == "H-POINT" else model, u, v, w)
            out.append([i >> 1 if fmt == FMT16 else i])
    return out


def tokens(name, model):
    """The frozen image of a row under a model: 2048 tokens (`XXXXXXXX`, `h:XXXX`, `t:...`)."""
    _, _, w, fmt, kind, _, _ = row(name)
    out = []
    for x, y in pixels():
        u, v = uv(name, x, y)
        if fmt == FMT16:
            out.append("h:%04x" % half16(point_index(model, u, v, w)))
        elif kind == "bil":
            if model == "H-POINT":
                val = name_of(point_index("H-TWP", u, v, w))
            else:
                t, kx, ky = taps(model, u, v, w)
                val = blend([name_of(i) for i in t], kx, ky)
            out.append("t:" + ",".join(str(val >> 8 * c & 255) for c in range(4)))
        else:
            out.append("%08x" % name_of(point_index(model, u, v, w)))
    return out


def models(name):
    kind = row(name)[4]
    return {"ref": ("REF",), "point": POINT, "u16": U16, "bil": BIL}[kind]


def kept_zero():
    return ["%08x" % v for v in pins.pixels(gzip.decompress(pins.blob(KEPT + "f1-zero.txt.gz"))
                                            .decode(errors="replace"), 2048)]


def reach(name):
    """The farthest dword any frozen model of the row reads (tw-zero: E1047's kept image's)."""
    if name == ZERO:
        return max(int(t, 16) & 0x0FFFFFFF for t in kept_zero())
    return max(max(r) for m in models(name) for r in reads(name, m))


def order():
    """Run order: ascending reach over every frozen model (controls first: their reach is the
    texture's own; tw-zero, the bit-14 control, before every bit-14 held-out row)."""
    names = [r[0] for r in ROWS] + [ZERO]
    return sorted(names, key=lambda n: (reach(n), n))


def args(name):
    return ARGS.format(pages=PAGES, row=name)


def jobs():
    """[(name, set, knobs, program bytes or None (assemble the spec), {model: tokens})], run
    order. tw-zero's program is E1047's published f1-zero.bin byte for byte."""
    out = []
    for n in order():
        if n == ZERO:
            out.append((n, "control", "reads:pixels", None, {"H-E1047": kept_zero()}))
            continue
        _, sset, _, _, kind, _, _ = row(n)
        knobs = "reads:pixels" if sset == "control" else "-"
        out.append((n, sset, knobs, spec(n), {m: tokens(n, m) for m in models(n)}))
    return out
