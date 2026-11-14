# SPDX-License-Identifier: MIT
"""tw16.py: stage tw16 (r16-tw, Q078: T3 bit 14 on twiddled textures, the post hoc bilinear form of
E1049 held out, and point reads at heights 8, 16 and 64; closing16/plan/rank-round16.md section 2
"r16-tw", decision R16-2 a: SAFE CLASS, no bilinear row above H 32, the H 64 rows last with frac(u)
<= 0.4, rows in reach order, on_stop = "end").

E1047's and E1049's form (r15-tw gen/tw.py, published): E566's tx_map on named memory (scratch
dword i reads 0xD0000000 | i), a twiddled texture (type 0) at the scratch's first dword, T0
0x07FE0000 (point) or 0x07FE1400 (bilinear, E1027), T3 0x00800800 | bit 14, T1 = 12 << 24 | (W - 1)
<< 12 | (H - 1) (32-bit), t14's `probe --temps 32 --coords --pixels --scratch-pages 256` (dwords 0
to 262143). u and v are "lin" ramps (tex.lin) exact in float32; u steps at most one texel a pixel
and v at most one texel a pixel row (LOD 0 or below, as E1047's and E1049's rows), v stays in (0, 1].

Notation: s = floor(W u) mod W, t = floor(H v) mod H, fr = frac(u), m = floor(4096 fr). E561's
tiles are min(W, 16) x min(H, 16) texels (law.index; every W here is at least 16), so at H 8 a tile
is 16 x 8. tile(c, t, P, th) = law.morton(c mod 16, t mod th, 16, th) + 16 th (c div 16 + (P / 16)
(t div th)): tiles of 16 x th texels with a tile row of P texels.

Frozen, point rows (each image a dword name a pixel, exact):
  H-TWP-H     tile(s + m, t, W + 4096, min(H, 16)): E1049's H-TWP with E561's tile height (16 x 8
              at H 8; tile rows t div 16 at H 64) [infer: fitted at H 32 only]
  H-TWP-T16   tile(s + m, t, W + 4096, 16): the wide layout keeps 16 x 16 tiles at any H (parts
              at H 8 only)
  H-MOVEH     tile(s + floor(128 H fr), t, W + 128 H, min(H, 16)): the move and the widening scale
              with the height (4096 = 128 x 32) [infer]; scored at H 8 and 16 only (at H 64 its
              reach passes the scratch: the H 16 sentinel stops the session first, SENTINEL)
  H-TWP-V32   H-TWP-H with t mod 32: the wide layout spans 32 texel rows (parts at H 64)
  H-TWP-STRIP the 4096 added once per texture: (s + m) < W reads the bit-clear texel, a column past
              W reads W H + law.index(s + m - W, t, 4096, H), one strip of 4096 x H texels after
              the texture [infer; the plan's "one strip of (W + 4096) H texels"; E1049's kept H 32
              images refute it already: carried as the plan's rival, tests/test_gen.py]
  H-TWP4128   H-TWP-H with a constant 4128-texel tile row (E1049 refuted it at H 32: carried)
  REF         the bit-clear image, law.index(s, t, W, H) (the controls)
At H 8 and 16 (one tile row) H-TWP-STRIP, H-TWP4128 and H-TWP-V32 are H-TWP-H; at H 16 and 64
H-TWP-T16 is. Each held-out row parts H-TWP-H from at least one rival on 1024 or more pixels.

Frozen, bilinear rows (texmodel's blend in 64ths, each byte within 1, r13-tex t3c's form): fx = W u
- 1/2, x0 = floor(fx), X = floor(W fr - 1/2) (= x0 - W floor(u)), fy = H v - 1/2, y0 = floor(fy),
kx = 64 (fx - x0), ky = 64 (fy - y0) (integers: the coordinates are chosen so), rows r0 = y0 mod H
and r1; each tap at tile(column, row, W + 4096, min(H, 16)):
  F-FRAC        columns X mod W + m and X + 1 + m, r1 = (y0 + 1) mod H (V-WRAP): E1049's post hoc
                form (fold/bilin_forms.py "H-FOOT-FR", 2048 of 2048 on tw-bl32 and tw-bl16)
  F-VNEXT       F-FRAC with r1 = (y0 mod H) + 1: at the v edge the second row is row H, the next
                tile row of the wide layout (V-NEXT)
  H-FOOT-SHIFT  columns x0 mod W + m and x0 mod W + 1 + m (E1049, 1 of 2); parts from F-FRAC only
                where X = -1 (the left edge)
  H-FOOT-TW     columns x0 mod W + m and (x0 + 1) mod W + m (E1049, 0 of 2); parts from F-FRAC
                only where X = W - 1 (the right edge). The plan's F-WRAP2 (both columns wrapped,
                X mod W and (X + 1) mod W) is this form exactly (x0 = X mod W): one law
  H-POINT       the filter dropped: H-TWP-H's point image
On a footprint inside the texture F-FRAC, H-FOOT-SHIFT and H-FOOT-TW are one image; only H-POINT
(and F-VNEXT on the v edge's rows) part there.

Controls that can fail: ref32h8 and ref16h64 (the bit-clear images of the new heights, E561's law;
the H 8 one is E561's 16 x 8 tile, the plan's [check]) and bl32r (E1049's tw-bl32 program byte for
byte, its kept image, each byte within 1): the bit-14 bilinear read replicates. A held-out row is
cannot tell unless bl32r and its height's reference (H 8, H 64) passed (GATE)."""
from fractions import Fraction as F

import law
import pins
import tex

STAGE = "tw16"
B14 = 1 << 14
PAGES = 256
SCRATCH_DW = PAGES * 1024
T0_PT, T0_BL = 0x07FE0000, 0x07FE1400
T3 = 0x00800800
FMT32 = 12
R15 = "data:render/closing-r15-tw/"
KEPT15 = R15 + "out/20261114-074356/tw14/"
BL32_BIN = R15 + "bins/tw-bl32.bin"
BL32 = "bl32r"
ARGS = 'probe --temps 32 --coords --pixels --scratch-pages {pages} "$S/bins/{row}.bin"'

POINT = ("H-TWP-H", "H-TWP-T16", "H-MOVEH", "H-TWP-V32", "H-TWP-STRIP", "H-TWP4128")
BIL = ("F-FRAC", "F-VNEXT", "H-FOOT-SHIFT", "H-FOOT-TW", "H-POINT")


def ulin(scale, offset):
    return tex.lin("x", F(scale), F(offset))


def vlin(scale, offset):
    return tex.lin("y", F(scale), F(offset))


# name, set, W, H, kind (ref / point / bil), bit 14, u spec, v spec
ROWS = [
    # controls: the bit-clear images of the new heights (the coordinates of the rows they gate)
    ("ref32h8", "control", 32, 8, "ref", False, ulin(F(1, 64), 1 + F(1, 128)),
     vlin(F(1, 32), F(1, 64))),
    ("ref16h64", "control", 16, 64, "ref", False, ulin(F(3, 512), F(1, 1024)),
     vlin(F(1, 64), F(1, 2) + F(1, 128))),
    # point rows, H 8 and 16 (one tile row): t = floor(H v) over every texel row, v in (0, 1)
    ("pt32h8", "heldout", 32, 8, "point", True, ulin(F(1, 64), 1 + F(1, 128)),
     vlin(F(1, 32), F(1, 64))),
    ("pt128h8", "heldout", 128, 8, "point", True, ulin(F(1, 128), F(1, 256)),
     vlin(F(1, 32), F(1, 64))),
    ("pt32h16", "heldout", 32, 16, "point", True, ulin(F(1, 64), F(1, 128)),
     vlin(F(1, 32), F(1, 64))),
    ("pt128h16", "heldout", 128, 16, "point", True, ulin(F(1, 128), 2 + F(1, 256)),
     vlin(F(1, 32), F(1, 64))),
    # bilinear rows, H 32 and 16
    ("bl64in", "heldout", 64, 32, "bil", True, ulin(F(1, 256), F(1, 4)),
     vlin(F(1, 32), F(3, 128))),
    ("bl64left", "heldout", 64, 32, "bil", True, ulin(F(1, 4096), 2 + F(1, 4096)),
     vlin(F(1, 32), F(3, 128))),
    ("bl128right", "heldout", 128, 32, "bil", True, ulin(F(1, 8192), 2 - F(32, 8192)),
     vlin(F(1, 32), F(3, 128))),
    ("bl128vedge", "heldout", 128, 32, "bil", True, ulin(F(1, 512), F(1, 4)),
     vlin(F(1, 2048), F(63, 64))),
    ("bl16h16in", "heldout", 16, 16, "bil", True, ulin(F(1, 256), F(1, 4)),
     vlin(F(1, 32), F(1, 32))),
    ("bl128h16right", "heldout", 128, 16, "bil", True, ulin(F(1, 8192), 2 - F(32, 8192)),
     vlin(F(1, 32), F(1, 32))),
    # bl32r: E1049's tw-bl32 (r15-tw gen/tw.py), its program rebuilt byte for byte (tests)
    ("bl32r", "control", 32, 32, "bil", True, ulin(F(1, 2048), F(63, 64)),
     vlin(F(1, 32), F(3, 128))),
    # point rows, H 64 (tile rows 2 and 3: t = 32 + y), frac(u) <= 0.4, last
    ("pt16h64u0", "heldout", 16, 64, "point", True, ulin(F(3, 512), F(1, 1024)),
     vlin(F(1, 64), F(1, 2) + F(1, 128))),
    ("pt16h64u1", "heldout", 16, 64, "point", True, ulin(F(3, 512), 1 + F(1, 1024)),
     vlin(F(1, 64), F(1, 2) + F(1, 128))),
    ("pt64h64u0", "heldout", 64, 64, "point", True, ulin(F(3, 512), F(1, 1024)),
     vlin(F(1, 64), F(1, 2) + F(1, 128))),
    ("pt64h64u1", "heldout", 64, 64, "point", True, ulin(F(3, 512), 1 + F(1, 1024)),
     vlin(F(1, 64), F(1, 2) + F(1, 128))),
]
GATE = {r[0]: {8: "ref32h8", 64: "ref16h64"}.get(r[3]) for r in ROWS if r[1] == "heldout"}
# H-MOVEH is scored where its reach is inside the scratch (H 8, 16); the H 16 rows' sentinel (the
# farthest dword H-TWP-H names, no other frozen image of the row names it) must be printed, else
# hook_check stops the stage before any row that reads farther (on_stop = "end").
SENTINEL_ROWS = ("pt32h16", "pt128h16")


def row(name):
    return next(r for r in ROWS if r[0] == name)


def fl(q):
    return int(F(q).__floor__())


def spec(name):
    _, _, w, h, kind, b14, u, v = row(name)
    t1 = FMT32 << 24 | (w - 1) << 12 | (h - 1)
    return dict(base=0, ins="none", t0=T0_BL if kind == "bil" else T0_PT, t1=t1,
                t3=T3 | (B14 if b14 else 0), u=u, v=v)


def uv(name, x, y):
    sp = spec(name)
    return tex.coord(sp["u"], x, y), tex.coord(sp["v"], x, y)


def tile(c, t, pitch, th):
    """Tiles of 16 x th texels (E561's interleave, texmodel's morton), a tile row of `pitch` texels;
    c may pass the width."""
    assert pitch % 16 == 0 and th in (8, 16)
    return law.morton(c % 16, t % th, 16, th) + 16 * th * (c // 16 + (pitch // 16) * (t // th))


def mv(u):
    return fl(4096 * (F(u) - fl(u)))


def point_index(model, u, v, w, h):
    s, t = fl(F(u) * w) % w, fl(F(v) * h) % h
    th = min(h, 16)
    if model == "REF":
        return law.index(s, t, w, h)
    if model == "H-TWP-H":
        return tile(s + mv(u), t, w + 4096, th)
    if model == "H-TWP-T16":
        return tile(s + mv(u), t, w + 4096, 16)
    if model == "H-MOVEH":
        return tile(s + fl(128 * h * (F(u) - fl(u))), t, w + 128 * h, th)
    if model == "H-TWP-V32":
        return tile(s + mv(u), t % 32, w + 4096, th)
    if model == "H-TWP4128":
        return tile(s + mv(u), t, 4128, th)
    if model == "H-TWP-STRIP":
        c = s + mv(u)
        return law.index(c, t, w, h) if c < w else w * h + law.index(c - w, t, 4096, h)
    raise ValueError(model)


def taps(model, u, v, w, h):
    """The four tap indices (00, 10, 01, 11) of a bilinear sample, kx, ky."""
    fx, fy = F(u) * w - F(1, 2), F(v) * h - F(1, 2)
    x0, y0 = fl(fx), fl(fy)
    kx, ky = 64 * (fx - x0), 64 * (fy - y0)
    assert kx.denominator == 1 and ky.denominator == 1, (u, v)
    m = mv(u)
    big_x = fl(w * (F(u) - fl(u)) - F(1, 2))
    if model in ("F-FRAC", "F-VNEXT"):
        cols = (big_x % w + m, big_x + 1 + m)
    elif model == "H-FOOT-SHIFT":
        cols = (x0 % w + m, x0 % w + 1 + m)
    elif model == "H-FOOT-TW":
        cols = (x0 % w + m, (x0 + 1) % w + m)
    elif model == "F-WRAP2":
        cols = (big_x % w + m, (big_x + 1) % w + m)
    else:
        raise ValueError(model)
    r0 = y0 % h
    r1 = r0 + 1 if model == "F-VNEXT" else (y0 + 1) % h
    th = min(h, 16)
    out = [tile(c, r, w + 4096, th) for r in (r0, r1) for c in cols]
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


def pixels():
    return [(x, y) for y in range(32) for x in range(64)]


def models(name):
    _, _, _, h, kind, _, _, _ = row(name)
    if name == BL32:
        return ("H-E1049",)
    if kind == "ref":
        return ("REF",)
    if kind == "bil":
        return BIL
    return POINT if h <= 16 else tuple(m for m in POINT if m != "H-MOVEH")


def reads(name, model):
    """[the dwords one pixel reads] for each of the 2048 pixels, raster order."""
    _, _, w, h, kind, _, _, _ = row(name)
    out = []
    for x, y in pixels():
        u, v = uv(name, x, y)
        if model == "H-E1049":
            out.append(sorted({i for m in BIL if m != "H-POINT" for i in taps(m, u, v, w, h)[0]}
                              | {point_index("H-TWP-H", u, v, w, h)}))
        elif kind == "bil" and model != "H-POINT":
            out.append(taps(model, u, v, w, h)[0])
        else:
            out.append([point_index("H-TWP-H" if model == "H-POINT" else model, u, v, w, h)])
    return out


def tokens(name, model):
    """The frozen image of a row under a model: 2048 tokens (`XXXXXXXX` exact, `t:B0,B1,B2,B3`
    each byte within 1)."""
    _, _, w, h, kind, _, _, _ = row(name)
    out = []
    for x, y in pixels():
        u, v = uv(name, x, y)
        if kind == "bil":
            if model == "H-POINT":
                val = name_of(point_index("H-TWP-H", u, v, w, h))
            else:
                t, kx, ky = taps(model, u, v, w, h)
                val = blend([name_of(i) for i in t], kx, ky)
            out.append("t:" + ",".join(str(val >> 8 * c & 255) for c in range(4)))
        else:
            out.append("%08x" % name_of(point_index(model, u, v, w, h)))
    return out


def kept15(name):
    """A kept output of r15-tw (E1049), its 2048 pixels."""
    return pins.kept_pixels(KEPT15 + name + ".txt.gz")


def bl32_tokens():
    """bl32r's frozen image: E1049's kept tw-bl32 image, each byte within 1."""
    return ["t:" + ",".join(str(v >> 8 * c & 255) for c in range(4)) for v in kept15("tw-bl32")]


def sentinel(name):
    """The farthest dword H-TWP-H reads on a sentinel row, as the probe prints it."""
    return "%08x" % name_of(max(r[0] for r in reads(name, "H-TWP-H")))


def tw15():
    """r15-tw's published generator (E1049's rows, models and reach), on this session's law, pins
    and tex (the same files: tests/test_gen.py)."""
    return pins.module(R15 + "gen/tw.py", "tw15")


def reach(name):
    """The farthest dword any frozen model of the row reads (bl32r: every bilinear model of this
    stage and of E1049, r15-tw's reach of tw-bl32)."""
    own = max(max(r) for m in models(name) for r in reads(name, m))
    return max(own, tw15().reach("tw-bl32")) if name == BL32 else own


def order():
    """Run order: ascending reach over every frozen model of the row."""
    names = [r[0] for r in ROWS]
    return sorted(names, key=lambda n: (reach(n), n))


def args(name):
    return ARGS.format(pages=PAGES, row=name)


def jobs():
    """[(name, set, knobs, spec, {model: tokens})], run order. bl32r's image is E1049's kept one
    and its program E1049's published tw-bl32.bin (the spec rebuilds it byte for byte)."""
    out = []
    for n in order():
        sset = row(n)[1]
        knobs = "reads:pixels" if sset == "control" else "-"
        im = {"H-E1049": bl32_tokens()} if n == BL32 else {m: tokens(n, m) for m in models(n)}
        out.append((n, sset, knobs, spec(n), im))
    return out
