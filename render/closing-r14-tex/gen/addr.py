# SPDX-License-Identifier: MIT
"""addr.py: stage addr4 (r13-tex, Q177; closing13/plan/rank-round13.md section 2 "addr4"):
r10-tex's gen/addr.py (resgx545-data render/closing-r10-tex/gen/addr.py) extended to shapes with
H > W, to the uv5 form (u and v both in mode 5, every region past the texture) and to a 16-bit
format. Standard library only.

Every texture sits at page 12 of a 32-page scratch buffer whose every dword is named (dword i =
0xD0000000 | i): T2 0x5CAFC000 and `probe --scratch-pages 32` on every row but the bd-uv5 replicate
(E565's own program: base 0, 16 pages). The index read is the value less 0xD0000000 less 12288.

Textures: twiddled, type 0, T1 = FMT << 24 | (W - 1) << 12 | (H - 1), FMT 12 (32-bit, E565's)
or 9 (u16, returned as the half: usse_isa.md 7 to 11, E1003's 16-bit row). The texel index is
E561's tile law (r10-tex's index(), held on E1000's eleven shapes).

Two coordinate forms:
  sweep  (r10-tex's): u over 128 positions at one texel a step (texels -64 to 63, p = x | (y & 1)
         << 6), v on texel H / 2's centre; u mode 4, 6 or 7, v mode 0.
  uv5    u and v both mode 5, both swept past both ends ("lin" coordinates):
         64 x 16: s = 2 x - 32 (-32 to 94), t = y - 8 (-8 to 23);
         16 x 64: s = x - 24 (-24 to 39), t = 4 y - 32 (-32 to 92).
         So every region holds pixels: inside, left / right (t inside), above / below (s
         inside), the four corners.

Frozen, nothing fitted on these shapes (E1000, E1017, closing11 c2's rule_a.py and post_a.py):
  sweep rows, the offset past E561's index: H-MAX 8 max(W, H) + 52, H-W 8 W + 52, H-H 8 H + 52
         (on the 16-bit row in texels: H-MAX-TX, H-W-TX, H-H-TX; the same count in dwords:
         H-MAX-DW, i.e. 2 (8 M + 52) texels [infer: the 16-bit row's tile law is in texels]).
  uv5 rows, one model a region (`-` on the other pixels), M one of max(W, H) / W / H:
    IN-M/W/H    s and t inside: index + 8 M + 52
    LR-M/W/H    s outside, t inside: 5 M + 52 + t left, 6 M + 52 + t right (E983, E1000)
    AB-M/W/H    s inside, t outside: 7 M + 52 + s above (t < 0), 4 M + 52 + s below (post hoc
                on bd-uv5 and bd-hb-ns-uv5, E1017)
    CO-WH2, CO-12M4, CO-12W4  the corners: c + 0 (above left), 1 (above right), 2 (below left),
                3 (below right), c = (W + H) / 2, 12 + M / 4 or 12 + W / 4 (E1017's candidates).
  REPEAT  the u mode 0 reading (no offset), printed as the reading's base (scorer)."""
import texprog as T

BASE_PAGE = 12
PAGES = 32
BASE = BASE_PAGE * 1024           # dwords
T0_BASE = 0x07fe0000
T2 = 0x5cafc000                   # SCRATCH_IMM | 0xC000: the scratch address + 12 pages
T3 = 0x00800800                   # E565's, every row
SMP = "smp2d r10, r24, r20, drc0"
FMT32, FMT16 = 12, 9

SWEEP = ("H-MAX", "H-W", "H-H")
SWEEP16 = ("H-MAX-TX", "H-W-TX", "H-H-TX", "H-MAX-DW")
UV5 = tuple(f"{r}-{m}" for r in ("IN", "LR", "AB") for m in ("M", "W", "H")) + (
    "CO-WH2", "CO-12M4", "CO-12W4")
# name, set, W, H, u mode, v mode, form, format
JOBS = [
    ("addr4-32x64-u4", "heldout", 32, 64, 4, 0, "sweep", FMT32),
    ("addr4-32x64-u6", "heldout", 32, 64, 6, 0, "sweep", FMT32),
    ("addr4-8x64-u4", "heldout", 8, 64, 4, 0, "sweep", FMT32),
    ("addr4-8x64-u6", "heldout", 8, 64, 6, 0, "sweep", FMT32),
    ("addr4-128x32-u4", "heldout", 128, 32, 4, 0, "sweep", FMT32),
    ("addr4-128x32-u6", "heldout", 128, 32, 6, 0, "sweep", FMT32),
    ("addr4-64x16-uv5", "heldout", 64, 16, 5, 5, "uv5", FMT32),
    ("addr4-16x64-uv5", "heldout", 16, 64, 5, 5, "uv5", FMT32),
    ("addr4-32x64-u7", "heldout", 32, 64, 7, 0, "sweep", FMT32),
    ("addr4-32x64-u4-h16", "heldout", 32, 64, 4, 0, "sweep", FMT16),
]
# the rows whose rivals part max(W, H) from W (H > W) and from H (W > H)
PARTS_W = ("addr4-32x64-u4", "addr4-32x64-u6", "addr4-8x64-u4", "addr4-8x64-u6",
           "addr4-16x64-uv5", "addr4-32x64-u7", "addr4-32x64-u4-h16")
PARTS_H = ("addr4-128x32-u4", "addr4-128x32-u6", "addr4-64x16-uv5")


def t1(w, h, fmt=FMT32):
    return fmt << 24 | (w - 1) << 12 | (h - 1)


def sweep(w):
    """("p7", K, C): u = K (1 + p / 128) + C = (p - 64 + 1/2) / w."""
    return ("p7", T.bits(128.0 / w), T.bits(-191.5 / w))


def centre(h):
    return ("bits", T.bits((h // 2 + 0.5) / h))


def lin(ax, scale, offset):
    """("lin", ax, K, C): K (1 + i / 64 or / 32) + C = scale * i + offset, exact in float32."""
    k = scale * (64 if ax == "x" else 32)
    spec = ("lin", ax, T.bits(k), T.bits(offset - k))
    assert T.exact_f32(k) and T.exact_f32(offset - k)
    return spec


UV5_FORM = {(64, 16): ((2, -32), (1, -8)), (16, 64): ((1, -24), (4, -32))}


def coords(w, h, form):
    if form == "sweep":
        return (sweep(w), centre(h))
    (ks, cs), (kt, ct) = UV5_FORM[(w, h)]
    # s = ks x + cs at the texel centre: u = (ks x + cs + 1/2) / w
    return (lin("x", T.F(ks, w), T.F(2 * cs + 1, 2 * w)),
            lin("y", T.F(kt, h), T.F(2 * ct + 1, 2 * h)))


def twords(w, h, umode, vmode, fmt=FMT32):
    return (T0_BASE | umode << 6 | vmode << 3, t1(w, h, fmt), T2, T3)


def morton(x, y, w, h):
    """texmodel's morton (y in bit 0, the longer side's extra bits above)."""
    bw, bh = max(w, 1).bit_length() - 1, max(h, 1).bit_length() - 1
    common = min(bw, bh)
    i = 0
    for b in range(common):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    rest = (x if bw > bh else y) >> common
    return i | rest << (2 * common)


def index(s, t, w, h):
    """E561's tile law: tiles of min(w, 16) x min(h, 16), interleaved, in raster order s first."""
    tw, th = min(w, 16), min(h, 16)
    return morton(s % tw, t % th, tw, th) + tw * th * (s // tw + (w // tw) * (t // th))


def wrap(v, mode, n):
    if mode in (0, 4, 5):
        return v % n
    return min(max(v, 0), n - 1)


def texel(w, h, form, x, y):
    """(s, t) of the pixel, unwrapped."""
    cs = [T.coord(c, x, y) for c in coords(w, h, form)]
    return int((cs[0] * w).__floor__()), int((cs[1] * h).__floor__())


def side(m, w, h):
    return {"M": max(w, h), "W": w, "H": h}[m]


def sweep_offset(model, w, h):
    """The offset (in the format's units, texels) past the index, or the REPEAT 0."""
    if model == "REPEAT":
        return 0
    key = model.split("-")[1]
    n = 8 * side("M" if key == "MAX" else key, w, h) + 52
    return 2 * n if model.endswith("-DW") else n


def predict(job, model, x, y):
    """The texel index read (less the base, in texels), or None where the model says nothing."""
    name, st, w, h, um, vm, form, fmt = job
    s, t = texel(w, h, form, x, y)
    if form == "sweep":
        return index(wrap(s, um, w), wrap(t, vm, h), w, h) + sweep_offset(model, w, h)
    sin, tin = 0 <= s < w, 0 <= t < h
    region, _, key = model.partition("-")
    if region == "IN":
        return index(s, t, w, h) + 8 * side(key, w, h) + 52 if sin and tin else None
    if region == "LR":
        return (5 if s < 0 else 6) * side(key, w, h) + 52 + t if not sin and tin else None
    if region == "AB":
        return (7 if t < 0 else 4) * side(key, w, h) + 52 + s if sin and not tin else None
    if region == "CO":
        if sin or tin:
            return None
        c = {"WH2": (w + h) // 2, "12M4": 12 + max(w, h) // 4, "12W4": 12 + w // 4}[key]
        return c + (0 if t < 0 else 2) + (0 if s < 0 else 1)
    raise ValueError(model)


def models(job):
    return SWEEP16 if job[7] == FMT16 else SWEEP if job[6] == "sweep" else UV5


def value(fmt, texel_index):
    """The pixel the read gives: the dword (32-bit) or the low 16 bits of the half (u16, texel
    t is the half t & 1 of dword t >> 1, E1003's 16-bit row)."""
    if fmt == FMT32:
        return 0xD0000000 | (BASE + texel_index)
    d = 0xD0000000 | (BASE + (texel_index >> 1))
    return (d >> 16 if texel_index & 1 else d) & 0xFFFF


def image(job, model):
    """[2048 values or None] raster order."""
    out = []
    for y in range(T.H):
        for x in range(T.W):
            i = predict(job, model, x, y)
            out.append(None if i is None else value(job[7], i))
    return out


def regions(job):
    """{region: pixel count} of a uv5 job (tests: every region holds pixels)."""
    _, _, w, h, _, _, form, _ = job
    c = {}
    for y in range(T.H):
        for x in range(T.W):
            s, t = texel(w, h, form, x, y)
            k = ("I" if 0 <= s < w else "O") + ("I" if 0 <= t < h else "O")
            c[k] = c.get(k, 0) + 1
    return c


def farthest(job):
    """The largest texel index (less the base) any model of the job reads."""
    return max(i for m in models(job) for i in
               (predict(job, m, x, y) for y in range(T.H) for x in range(T.W)) if i is not None)


def jobs():
    """[(job tuple, {model: [values or None]})] in table order (the replicates are make.py's)."""
    return [(j, {m: image(j, m) for m in models(j)}) for j in JOBS]
