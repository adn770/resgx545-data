# SPDX-License-Identifier: MIT
"""tw17.py: stage tw17 (r17-tw, Q078: T3 bit 14 under a bilinear sample at a twiddled texture's
left and right edges, on and off the 1/4096 grid; closing17/plan/rank-round17.md sections 2 and 3
"r17-tw", decisions R17-1 to R17-4 (a) of closing17/DECISIONS-R17.md: SAFE CLASS, H-WIDE frozen
after the builder re-derives it from the kept files (gen/derive.py), the left wrap decided by the
pre-declared exact-byte rule, the widths never run with bit 14 last, on_stop = "end").

E1047's, E1049's and E1058's form (r16-tw gen/tw16.py, published): E566's tx_map on named memory
(scratch dword i reads 0xD0000000 | i), a twiddled 32-bit texture at the scratch's first dword, T0
0x07FE0000 (point) or 0x07FE1400 (bilinear, E1027), T3 0x00800800 | bit 14, T1 = 12 << 24 | (W -
1) << 12 | (H - 1), t14's `probe --temps 32 --coords --pixels --scratch-pages 256` (dwords 0 to
262143). u and v are float32-exact "lin" ramps (tex.lin), u at most one texel a pixel, v in (0, 1].

Notation: fr = frac(u), W' = W + 4096, th = min(H, 16), tile(c, t) = law.morton(c mod 16, t mod th,
16, th) + 16 th (c div 16 + (W' / 16) (t div th)) (E561's tiles, a tile row of W' texels, E1058).
m = floor(4096 fr), X = floor(W fr - 1/2) (E1049's), fy = H v - 1/2, y0 = floor(fy), ky = 64 (fy -
y0), rows r0 = y0 mod H and r1 = (y0 + 1) mod H (E1058: the v edge's second row wraps to row 0).

Frozen, bilinear rows (texmodel's blend in 64ths of four tap names, each byte within 1):
  H-WIDE       (post hoc on E1049 and E1058: gen/derive.py, 16384 of 16384 kept pixels): the
               sample is taken over a texture W' texels wide at fr: fx = W' fr - 1/2, x0 = floor(fx),
               kx = 64 (fx - x0), columns x0 mod W' and (x0 + 1) mod W' (column -1 reads W' - 1,
               column W' reads 0)
  H-WIDE-G     H-WIDE with column -1 at W - 1 (E1058's wrap): names 65536 dwords apart, so it parts
               from H-WIDE by exact bytes only; decided by the LEFT-WRAP rule (score.py), not by
               its within-1 image
  H-WIDE-NEXT  H-WIDE with column W' unwrapped (the next tile row's first column); parts by names
  UNWRAP-G     E1058's post hoc reading: columns X + m and X + 1 + m, kx = 64 (W fr - 1/2 - X),
               column -1 at W - 1, the right column unwrapped
  F-FRAC       E1049's form (refuted by E1058, carried): columns X mod W + m and X + 1 + m, kx as
               UNWRAP-G
  H-POINT      the filter dropped: H-WIDE-PT's point image
Frozen, point rows (exact names):
  H-WIDE-PT    column floor(W' fr), row floor(H v) mod H (H-WIDE's point form)
  H-TWP        column floor(W fr) + m (E1049's and E1058's H-TWP-H); on the 1/4096 grid it is
               H-WIDE-PT (gen/derive.py: every kept point pixel), off it they part
Every bilinear row has whole-64th weights under every form (tests): no rounding rule is assumed.

Controls that can fail: bl64leftr (E1058's bl64left program byte for byte, its kept image within
1 a byte: the bit-14 bilinear read replicates), ref256, ref512h16 and ref2048h16 (the bit-clear
images of the new widths, E561's law, point read across the u edge; each gates its width's rows
and carries a sentinel, run/hooks.sh). A held-out row is cannot tell unless bl64leftr and its
width's reference passed (GATE)."""
from fractions import Fraction as F

import law
import pins
import tex

STAGE = "tw17"
B14 = 1 << 14
PAGES = 256
SCRATCH_DW = PAGES * 1024
T0_PT, T0_BL = 0x07FE0000, 0x07FE1400
T3 = 0x00800800
FMT32 = 12
WIDEN = 4096
R16 = "data:render/closing-r16-tw/"
KEPT16 = R16 + "out/20261114-093404/tw16/"
BL64L_BIN = R16 + "bins/bl64left.bin"
CTL_REP = "bl64leftr"
ARGS = 'probe --temps 32 --coords --pixels --scratch-pages {pages} "$S/bins/{row}.bin"'

BIL = ("H-WIDE", "H-WIDE-G", "H-WIDE-NEXT", "UNWRAP-G", "F-FRAC", "H-POINT")
POINT = ("H-WIDE-PT", "H-TWP")
MAIN_BIL, MAIN_PT = "H-WIDE", "H-WIDE-PT"


def ulin(scale, offset):
    return tex.lin("x", F(scale), F(offset))


def vlin(scale, offset):
    return tex.lin("y", F(scale), F(offset))


V32 = vlin(F(1, 32), F(3, 128))          # H 32 bilinear: fy = y + 1/4 (ky 16), rows 0 to 31
V16 = vlin(F(1, 32), F(1, 32))           # H 16 bilinear: fy = y / 2 (ky 0, 32)
VP32 = vlin(F(1, 32), F(1, 64))          # point, H 32: t = y
VP16 = vlin(F(1, 32), F(1, 64))          # point, H 16: t = y div 2
VEDGE = vlin(F(1, 2048), F(63, 64))      # H 32, y0 = 31 on every pixel: the v edge (r1 = 0)

# name, set, W, H, kind (ref / point / bil), bit 14, u spec, v spec; run order is this list's
ROWS = [
    # the bit-14 bilinear control first: E1058's bl64left, byte for byte
    ("bl64leftr", "control", 64, 32, "bil", True, ulin(F(1, 4096), 2 + F(1, 4096)), V32),
    # held out, W <= 128 (widths E1049 and E1058 ran with bit 14)
    ("bl16left", "heldout", 16, 32, "bil", True, ulin(F(1, 1024), 1), V32),
    ("bl64grid", "heldout", 64, 32, "bil", True, ulin(F(1, 4096), 3 - F(40, 4096)), V32),
    ("bl128off3", "heldout", 128, 32, "bil", True, ulin(F(3, 8192), 1 - F(96, 8192)), V32),
    ("pt128off", "heldout", 128, 32, "point", True, ulin(F(1, 8192), 1 + F(1, 8192)), VP32),
    # the bit-clear references of the new widths (point, across the u edge), then their rows
    ("ref256", "control", 256, 32, "ref", False, ulin(F(1, 256), 3 - F(32, 256)), VP32),
    ("ref512h16", "control", 512, 16, "ref", False, ulin(F(1, 512), 1 - F(32, 512)), VP16),
    ("pt256off", "heldout", 256, 16, "point", True, ulin(F(3, 16384), 2 + F(1, 16384)), VP16),
    ("pt512off", "heldout", 512, 16, "point", True, ulin(F(5, 32768), F(3, 32768)), VP16),
    ("bl256edge", "heldout", 256, 32, "bil", True, ulin(F(1, 16384), 3 - F(16, 16384)), V32),
    ("bl512edge", "heldout", 512, 32, "bil", True, ulin(F(1, 32768), 1 - F(24, 32768)), V32),
    ("bl256corner", "heldout", 256, 32, "bil", True, ulin(F(1, 16384), 3 - F(16, 16384)), VEDGE),
    # the plan's [check]: a wider right-wrap band (W 2048: kx steps 3, 10 or 11 pixels a row in each band)
    ("ref2048h16", "control", 2048, 16, "ref", False, ulin(F(1, 2048), 1 - F(32, 2048)), VP16),
    ("bl2048edge", "heldout", 2048, 16, "bil", True, ulin(F(1, 131072), 2 - F(32, 131072)), V16),
]
REF_OF = {256: "ref256", 512: "ref512h16", 2048: "ref2048h16"}
GATE = {r[0]: REF_OF.get(r[2]) for r in ROWS if r[1] == "heldout"}
# hook_check: a reference must print its farthest dword (its sentinel) before its width's rows run
SENTINEL_ROWS = ("ref256", "ref512h16", "ref2048h16")


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


def tile(c, t, w, h):
    """E561's tiles of 16 x min(H, 16) texels with a tile row of W' = W + 4096 texels; c may pass
    W' (H-WIDE-NEXT's column)."""
    th, wp = min(h, 16), w + WIDEN
    assert c >= 0 and wp % 16 == 0
    return law.morton(c % 16, t % th, 16, th) + 16 * th * (c // 16 + (wp // 16) * (t // th))


def frac(u):
    return F(u) - fl(u)


def mv(u):
    return fl(4096 * frac(u))


def point_index(model, u, v, w, h):
    t = fl(F(v) * h) % h
    if model == "REF":
        return law.index(fl(F(u) * w) % w, t, w, h)
    if model == "H-WIDE-PT":
        return tile(fl((w + WIDEN) * frac(u)), t, w, h)
    if model == "H-TWP":
        return tile(fl(w * frac(u)) + mv(u), t, w, h)
    raise ValueError(model)


def columns(model, u, w):
    """(c0, c1, kx, x0): the two tap columns of a bilinear form, its weight kx (a Fraction) and
    its unwrapped left column x0 (-1 at the left wrap)."""
    fr = frac(u)
    wp = w + WIDEN
    if model in ("H-WIDE", "H-WIDE-G", "H-WIDE-NEXT"):
        fx = wp * fr - F(1, 2)
        x0 = fl(fx)
        kx = 64 * (fx - x0)
        c0 = x0 % wp if (x0 >= 0 or model != "H-WIDE-G") else x0 % w
        c1 = x0 + 1 if model == "H-WIDE-NEXT" else (x0 + 1) % wp
        return c0, c1, kx, x0
    fx = w * fr - F(1, 2)
    big_x = fl(fx)
    kx = 64 * (fx - big_x)
    m = mv(u)
    if model == "UNWRAP-G":
        x0 = big_x + m
        return (x0 if x0 >= 0 else x0 % w), x0 + 1, kx, x0
    if model == "F-FRAC":
        return big_x % w + m, big_x + 1 + m, kx, big_x + m
    raise ValueError(model)


def taps(model, u, v, w, h):
    """The four tap indices (00, 10, 01, 11) of a bilinear sample, kx, ky (whole 64ths)."""
    c0, c1, kx, _ = columns(model, u, w)
    fy = F(v) * h - F(1, 2)
    y0 = fl(fy)
    ky = 64 * (fy - y0)
    assert kx.denominator == 1 and ky.denominator == 1, (model, u, v)
    rows_ = (y0 % h, (y0 + 1) % h)
    return [tile(c, r, w, h) for r in rows_ for c in (c0, c1)], int(kx), int(ky)


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


def bil_value(model, u, v, w, h):
    if model == "H-POINT":
        return name_of(point_index("H-WIDE-PT", u, v, w, h))
    t, kx, ky = taps(model, u, v, w, h)
    return blend([name_of(i) for i in t], kx, ky)


def pixels():
    return [(x, y) for y in range(32) for x in range(64)]


def models(name):
    kind = row(name)[4]
    if name == CTL_REP:
        return ("H-E1058",)
    return {"ref": ("REF",), "bil": BIL, "point": POINT}[kind]


def reads(name, model):
    """[the dwords one pixel reads] for each of the 2048 pixels, raster order (bl64leftr: every
    bilinear form's taps and H-POINT's texel)."""
    _, _, w, h, kind, _, _, _ = row(name)
    out = []
    for x, y in pixels():
        u, v = uv(name, x, y)
        if model == "H-E1058":
            out.append(sorted({i for m in BIL if m != "H-POINT" for i in taps(m, u, v, w, h)[0]}
                              | {point_index("H-WIDE-PT", u, v, w, h)}))
        elif kind == "bil" and model != "H-POINT":
            out.append(taps(model, u, v, w, h)[0])
        else:
            out.append([point_index("H-WIDE-PT" if model == "H-POINT" else model, u, v, w, h)])
    return out


def tok(val):
    return "t:" + ",".join(str(val >> 8 * c & 255) for c in range(4))


def tokens(name, model):
    """The frozen image of a row under a model: 2048 tokens (`XXXXXXXX` exact, `t:B0,B1,B2,B3`
    the exact blend, scored each byte within 1; the LEFT-WRAP rule scores it exactly)."""
    _, _, w, h, kind, _, _, _ = row(name)
    out = []
    for x, y in pixels():
        u, v = uv(name, x, y)
        if kind == "bil":
            out.append(tok(bil_value(model, u, v, w, h)))
        else:
            out.append("%08x" % name_of(point_index(model, u, v, w, h)))
    return out


def kept16(name):
    """A kept output of r16-tw (E1058), its 2048 pixels."""
    return pins.kept_pixels(KEPT16 + name + ".txt.gz")


def rep_tokens():
    """bl64leftr's frozen image: E1058's kept bl64left image, each byte within 1."""
    return [tok(v) for v in kept16("bl64left")]


def tw16():
    """r16-tw's published generator (E1058's rows), on this session's law, pins and tex (the same
    files: tests/test_gen.py)."""
    return pins.module(R16 + "gen/tw16.py", "tw16")


def reach(name, model=None):
    """The farthest dword a frozen model (default: any) of the row reads."""
    ms = (model,) if model else models(name)
    return max(max(r) for m in ms for r in reads(name, m))


def sentinel(name):
    """A reference's farthest dword, as the probe prints it."""
    return "%08x" % name_of(reach(name, "REF"))


def leftwrap(name):
    """The pixels (raster index) where H-WIDE's left column wraps (x0 = -1)."""
    _, _, w, _, _, _, _, _ = row(name)
    return [i for i, (x, y) in enumerate(pixels()) if columns("H-WIDE", uv(name, x, y)[0], w)[3] < 0]


def rightwrap(name):
    """The pixels where H-WIDE's right column wraps (x0 + 1 = W')."""
    _, _, w, _, _, _, _, _ = row(name)
    return [i for i, (x, y) in enumerate(pixels())
            if columns("H-WIDE", uv(name, x, y)[0], w)[3] + 1 == w + WIDEN]


def args(name):
    return ARGS.format(pages=PAGES, row=name)


def jobs():
    """[(name, set, knobs, spec, {model: tokens})], run order (ROWS)."""
    out = []
    for n, sset, *_ in ROWS:
        knobs = "reads:pixels" if sset == "control" else "-"
        im = {"H-E1058": rep_tokens()} if n == CTL_REP else {m: tokens(n, m) for m in models(n)}
        out.append((n, sset, knobs, spec(n), im))
    return out
