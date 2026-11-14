# SPDX-License-Identifier: MIT
"""chain.py: stage chain (r15-tex, Q104; closing15/plan/rank-round15.md section 2 "chain"): E562's
generator (p1132 tx-shapes: the scratch buffer as the texture, dword i = 0xD0000000 | i, each texel
naming its dword) on mip chains E562 did not reach: a 1D texture (smp1dreplace on 64 x 1), a side of
1 at level 0 (1 x 32, 32 x 1), a 16-bit format (u16, T1 format 9: 32 x 16, 16 x 64) and long sides
past E562's (64 x 32, 256 x 32), with T0's maximum (bits 20:17), bias (bits 26:21) and MIPFILTER
(bit 9) as E441 and E562 varied them. Standard library only, so score/score.py and the tests read it
without the generator's pins.

The fill (64 x 32 pixels, pa0 = (y << 16) | x) samples one point a pixel:
  u = v = (32 x + 17) / 2048 (the diagonal, `lin`: every pixel inside the texture, more than 1/128
          texel from a texel edge at every level, as E562's windows), or 1/2 on a side of 1 (`bits`); smp1d reads u only;
  LOD = (y >> 2) + c (the `step` axis, gen/texprog2.py: rows 4k to 4k + 3 alike, k = 0 to 7), c = 0
          (whole LODs), 1/2 (half LODs: round half up, E441) or 3/2 (256 x 32's second set).
The texel read at level l is (floor(u w_l), floor(v h_l)), repeat (T0 modes 0), E561's tile law
inside a level (gen/addr.py's index(): plain Morton below 32 a side), level 0 at dword 0 (T2
0x5CAF0000, the scratch's first dword).

Frozen (E562's three chains, texmodel.py's chain() rule names; level by E441 and E276: level 0 if the
bias field is 0 or the maximum is 0 or 15, else le = LOD + (bias - 63) / 8, level 0 if le <= 0, else
min(floor(le + 1/2), maximum, last); with MIPFILTER the two levels around min(le, cap) blended per
byte with f = floor(64 frac), texmodel's lerp):
  A   both sides halve to 1, levels back to back (E562: 8 of 8 fit, 49 of 49 held out)
  B   the chain stops when the short side is 1 (a side of 1: one level)
  D   A with each level square-padded (max(w, h)^2 dwords) [not on 256 x 32: its level 1 starts at
      dword 65536, past t10's 64 pages; E562 refuted D on 43 of 49 held-out jobs]
16-bit rows: the texel t of the level is the half t & 1 of a dword (E1003, E1026: texels, the high
half of a name is 0xD000), the level offsets counted
  -TX in texels (the chain packed as 16-bit texels: dword (off + i) >> 1, half (off + i) & 1)
  -DW in dwords, each level as if 32-bit (dword off + (i >> 1), half i & 1)
and the MIPFILTER row's blend of two halves
  -BL8 per byte (texmodel's 32-bit lerp on the half's two bytes; A-TX-BL8 is the tested form)
  -BL16 one 16-bit lerp (a (64 - f) + b f + 32) >> 6."""
import fractions
import math
import struct

import addr as A

F = fractions.Fraction
W, H = 64, 32
FMT32, FMT16 = 12, 9
T0_MIP = 0x07FC0000          # point, repeat, bias field 63 (none), maximum 14: the whole chain
T3 = 0x00800800              # E562's (T3_TW)
PAGES = 16                   # the probe's default scratch: 16384 dwords
SMP2 = "smp2dreplace r10, r24, r20, r26, drc0"
SMP1 = "smp1dreplace r10, r24, r20, r26, drc0"
CHAINS32 = ("A", "B", "D")
CHAINS16 = ("A-TX", "A-DW", "B-TX", "D-TX")
BLENDS16 = ("A-TX-BL8", "A-TX-BL16", "A-DW-BL8", "B-TX-BL8", "D-TX-BL8")


def fbits(b):
    return struct.unpack("<f", struct.pack("<I", b))[0]


def bits(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def t1(w, h, fmt):
    return fmt << 24 | (w - 1) << 12 | (h - 1)


def lin_axis(ax, scale, offset):
    """("lin", ax, K, C): K (1 + i / 64 or / 32) + C = scale i + offset, exact in float32."""
    k = F(scale) * (64 if ax == "x" else 32)
    c = F(offset) - k
    assert F(fbits(bits(float(k)))) == k and F(fbits(bits(float(c)))) == c, (ax, scale, offset)
    return ("lin", ax, bits(float(k)), bits(float(c)))


DIAG = lin_axis("x", F(1, 64), F(17, 2048))          # (32 x + 17) / 2048
HALF = ("bits", bits(0.5))


def step_axis(c):
    """("step", K, C): K (1 + (y >> 2) / 8) + C = (y >> 2) + c with K = 8, C = c - 8."""
    assert F(fbits(bits(float(F(c) - 8)))) == F(c) - 8
    return ("step", bits(8.0), bits(float(F(c) - 8)))


def coord(spec, x, y):
    """The exact value (a Fraction) the program computes for pixel (x, y)."""
    k = spec[0]
    if k == "bits":
        return F(fbits(spec[1]))
    if k == "lin":
        _, ax, kb, cb = spec
        return (1 + (F(x, 64) if ax == "x" else F(y, 32))) * F(fbits(kb)) + F(fbits(cb))
    if k == "map":
        _, ax, a, off, exp = spec
        q = ((x if ax == "x" else y) | off) & ((1 << a) - 1)
        return F(fbits(exp | ((2 * q + 1) << (22 - a))))
    if k == "step":
        _, kb, cb = spec
        return (1 + F(y >> 2, 8)) * F(fbits(kb)) + F(fbits(cb))
    raise ValueError(spec)


# ---- the chain ----------------------------------------------------------------------------------
def levels(w, h, rule):
    """[(w_l, h_l, offset)] of the chain, level 0 first; the offset counts the units the levels are
    packed in (dwords at 32 bits, texels under -TX, dwords of a 32-bit chain under -DW)."""
    r = rule[0]
    if r == "B":
        n = min(w, h).bit_length()
        dims = [(w >> l, h >> l) for l in range(n)]
    else:
        n = max(w, h).bit_length()
        dims = [(max(1, w >> l), max(1, h >> l)) for l in range(n)]
    out, off = [], 0
    for dw, dh in dims:
        out.append((dw, dh, off))
        off += max(dw, dh) ** 2 if r == "D" else dw * dh
    return out


def pick(t0, lod, n):
    """(level, None) for a point read, (lo, hi, f) for a MIPFILTER blend (E441, E276, texmodel)."""
    top, mx = t0 >> 21 & 0x3F, t0 >> 17 & 15
    if top == 0 or mx in (0, 15):
        return (0, None)
    le = F(lod) + F(top - 63, 8)
    if le <= 0:
        return (0, None)
    cap = min(mx, n - 1)
    if not t0 >> 9 & 1:
        return (min(math.floor(le + F(1, 2)), cap), None)
    lc = min(le, cap)
    lo = math.floor(lc)
    f = int((lc - lo) * 64)
    if f == 0:
        return (lo, None)
    return (lo, (min(lo + 1, cap), f))


def lerp8(a, b, f, nbytes):
    return sum((((a >> 8 * c & 255) * (64 - f) + (b >> 8 * c & 255) * f + 32) >> 6) << 8 * c
               for c in range(nbytes))


def read(job, model, lv, u, v):
    """The value of a point read at level lv (a dword at 32 bits, the half at 16)."""
    w, h, fmt, one_d = job["w"], job["h"], job["fmt"], job["one_d"]
    lw, lh, off = levels(w, h, model)[lv]
    s = math.floor(u * lw) % lw
    t = 0 if one_d else math.floor(v * lh) % lh
    i = A.index(s, t, lw, lh)
    if fmt == FMT32:
        return 0xD0000000 | (off + i), off + i
    if "-DW" in model:
        d, half = off + (i >> 1), i & 1
    else:
        d, half = (off + i) >> 1, (off + i) & 1
    name = 0xD0000000 | d
    return (name >> 16 if half else name) & 0xFFFF, d


def pixel(job, model, x, y):
    """(value, the farthest dword the read touches)."""
    u, v, lod = (coord(job[k], x, y) for k in ("u", "v", "lod"))
    n = len(levels(job["w"], job["h"], model))
    lo, blend = pick(job["t0"], lod, n)
    a, da = read(job, model, lo, u, v)
    if blend is None:
        return a, da
    hi, f = blend
    b, db = read(job, model, hi, u, v)
    nb = 4 if job["fmt"] == FMT32 else 2
    if model.endswith("-BL16"):
        return (a * (64 - f) + b * f + 32) >> 6, max(da, db)
    return lerp8(a, b, f, nb), max(da, db)


def image(job, model):
    return [pixel(job, model, x, y)[0] for y in range(H) for x in range(W)]


def farthest(job, model):
    return max(pixel(job, model, x, y)[1] for y in range(H) for x in range(W))


def tokens(job, model):
    fmtw = "%08x" if job["fmt"] == FMT32 else "h:%04x"
    return [fmtw % v for v in image(job, model)]


# ---- the rows -----------------------------------------------------------------------------------
def job(name, w, h, fmt=FMT32, one_d=False, c=0, t0=T0_MIP, models=None, why=""):
    u = DIAG if w > 1 else HALF
    v = HALF if (one_d or h == 1) else DIAG
    if models is None:
        models = CHAINS32 if fmt == FMT32 else CHAINS16
    return dict(name=name, w=w, h=h, fmt=fmt, one_d=one_d, t0=t0, u=u, v=v, lod=step_axis(c),
                t1=t1(w, h, fmt), t3=T3, smp=SMP1 if one_d else SMP2, models=models, why=why)


T0_MAX3 = 0x07E00000 | 3 << 17           # bias field 63, maximum 3 (E562's fld-*-max rows)
T0_B33 = 0x33 << 21 | 0xE << 17          # bias field 0x33: -1.5 (E562's fld-*-bias33)
T0_MF = T0_MIP | 1 << 9                  # MIPFILTER (E562's fld-*-mf rows)

# run order (README.md "Deviations" 2: the smp1d rows last, the instruction never ran)
HELDOUT = [
    job("chain-1x32-lw", 1, 32, why="a side of 1 (w), whole LODs"),
    job("chain-1x32-lh", 1, 32, c=F(1, 2), why="a side of 1 (w), half LODs"),
    job("chain-32x1-lw", 32, 1, why="a side of 1 (h), whole LODs"),
    job("chain-32x1-lh", 32, 1, c=F(1, 2), why="a side of 1 (h), half LODs"),
    job("chain-32x1-b33", 32, 1, t0=T0_B33, why="a side of 1, bias field 0x33 (-1.5)"),
    job("chain-h32x16-lw", 32, 16, FMT16, why="u16, whole LODs"),
    job("chain-h32x16-lh", 32, 16, FMT16, c=F(1, 2), why="u16, half LODs"),
    job("chain-h16x64-lw", 16, 64, FMT16, why="u16, whole LODs"),
    job("chain-h16x64-lh", 16, 64, FMT16, c=F(1, 2), why="u16, half LODs"),
    job("chain-h32x16-mf", 32, 16, FMT16, c=F(1, 2), t0=T0_MF, models=BLENDS16,
        why="u16, MIPFILTER at fraction 1/2 (f 32)"),
    job("chain-64x32-lw", 64, 32, why="a short side of 32, whole LODs"),
    job("chain-256x32-lw", 256, 32, models=("A", "B"), why="a long side of 256, whole LODs"),
    job("chain-256x32-lb", 256, 32, c=F(3, 2), models=("A", "B"),
        why="a long side of 256, LODs 1.5 to 8.5"),
    job("chain-1d-lw", 64, 1, one_d=True, why="smp1d, whole LODs"),
    job("chain-1d-lh", 64, 1, one_d=True, c=F(1, 2), why="smp1d, half LODs"),
    job("chain-1d-max3", 64, 1, one_d=True, t0=T0_MAX3, why="smp1d, maximum field 3"),
]
# E562's kept jobs, rerun as controls that can fail (their published programs and kept images)
CONTROLS = [("chain-ctl32", "shp-32x16-l5"), ("chain-ctl128", "shp-128x16-l7-x0")]
SHAPES_BIN = "data:texture/p1132-recomp/raw/tx-shapes/bins/%s"
SHAPES_KEPT = "data:texture/p1132/tx-shapes/%s.txt.gz"


def spec_job(name, spec):
    """A job dict of a p1141 spec (E562's controls) for this model: twiddled 32-bit, 2D."""
    w, h = (spec["t1"] >> 12 & 0xFFF) + 1, (spec["t1"] & 0xFFF) + 1
    return dict(name=name, w=w, h=h, fmt=spec["t1"] >> 24 & 31, one_d=False, t0=spec["t0"],
                u=tuple(spec["u"]), v=tuple(spec["v"]), lod=tuple(spec["lod"]), t1=spec["t1"],
                t3=spec["t3"], smp=SMP2, models=CHAINS32, why="E562's kept job")


def parts(j, a, b):
    """Pixels where models a and b of a job differ."""
    return sum(p != q for p, q in zip(image(j, a), image(j, b)))
