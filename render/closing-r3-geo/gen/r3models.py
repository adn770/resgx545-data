"""R3 offline models (pure functions, no I/O): the frozen rules of the geometry session r3-geo.

  depth   the stored depth word at w != 1.  d = Rsum(0.5 + 0.5 q') with q' = rule(z, w) on p = z * RZ(1/w): the six candidate
          rules of the design note (D1, D2, D5, the thresholds T26 and T27, K23) plus the direction variants T26d and T27d
          (the same threshold read on the floor fraction: they agree on negative products and differ on positive ones),
          three roundings of the sum (nearest even, toward zero, half up), and the viewport z words (offset, scale)
  C       the layout arithmetic of the fork's sgx_render_layout, LT (the last raise thr0 proportional to the region count) and the
          affine laws through two exact points (regions, tail-pointer side squared, macrotile area)
  H-last  dword 36 = max(count before the LAST abort - 2, 0)

float32 arithmetic is exact rational with an explicit rounding, never numpy's.  EVERYTHING here is a FIT to data measured before
this file (E783's six words, E782's four vertices, E774/E785/E786's limits, 49 kept timelines): the runs hold it out.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import struct  # noqa: E402
from fractions import Fraction as F  # noqa: E402

H = F(1, 2)


# ------------------------------------------------------------------------------------------------ float32 helpers
def f32(x) -> F:
    return F(struct.unpack("<f", struct.pack("<f", float(x)))[0])


def wordval(w: int) -> F:
    return F(struct.unpack("<f", struct.pack("<I", w))[0])


def word(x: F) -> int:
    w = struct.unpack("<I", struct.pack("<f", float(x)))[0]
    assert wordval(w) == x, f"{x} is not a float32"
    return w


def ulp(x: F) -> F:
    ax = abs(x)
    e = ax.numerator.bit_length() - ax.denominator.bit_length()
    if F(2) ** e > ax:
        e -= 1
    return F(2) ** (e - 23)


def rnd(x: F, mode: str) -> F:
    """float32 rounding of an exact rational: rz toward zero, rn nearest even, rh nearest ties up (away for x > 0), ra away."""
    if x == 0:
        return F(0)
    q = ulp(x)
    n = abs(x) / q
    f = n.numerator // n.denominator
    r = n - f
    s = 1 if x > 0 else -1
    if mode == "ra":
        f += 1 if r else 0
    elif mode == "rn":
        if r > H or (r == H and f % 2):
            f += 1
    elif mode == "rh":
        if r >= H:
            f += 1
    elif mode != "rz":
        raise ValueError(mode)
    return s * f * q


def rprec(x: F, bits: int, mode: str) -> F:
    """round to `bits` significant bits (24 = float32)."""
    if x == 0:
        return x
    u = ulp(x) * F(2) ** (24 - bits)
    n = abs(x) / u
    f = n.numerator // n.denominator
    r = n - f
    s = 1 if x > 0 else -1
    if mode == "ra":
        f += 1 if r else 0
    elif mode == "rn":
        if r > H or (r == H and f % 2):
            f += 1
    elif mode == "rh":
        if r >= H:
            f += 1
    elif mode != "rz":
        raise ValueError(mode)
    return s * f * u


def rsum(x: F, mode: str) -> F:
    """The rounding of the stored depth's sum: rn (nearest even), rz (toward zero), rh (half up)."""
    return rnd(x, mode)


def rz_recip(w: F) -> F:
    return rnd(1 / w, "rz")


def thr_mag(x: F, t: F) -> F:
    """24-bit rounding of x by the fraction of |x| in its ulp: away from zero iff the fraction exceeds t (else toward zero)."""
    if x == 0:
        return x
    u = ulp(x)
    n = abs(x) / u
    f = n.numerator // n.denominator
    if n - f > t:
        f += 1
    return (1 if x > 0 else -1) * f * u


def thr_dir(x: F, td: F) -> F:
    """24-bit rounding of x by the FLOOR fraction g of x in its ulp: toward +infinity iff g > td (else toward -infinity).
    On a negative x it is thr_mag with t = 1 - td; on a positive one it differs (the g-db separation)."""
    if x == 0:
        return x
    u = ulp(x)
    n = x / u
    f = n.numerator // n.denominator
    if n - f > td:
        f += 1
    return f * u


def grid_round(x: F, step: F, kind: str, t: F | None = None) -> F:
    """x on a multiple of `step` (the grid of the sum): kind rn / rz / mag (thr_mag with t)."""
    n = abs(x) / step
    f = n.numerator // n.denominator
    r = n - f
    s = 1 if x > 0 else -1
    if kind == "rn":
        f += 1 if (r > H or (r == H and f % 2)) else 0
    elif kind == "mag":
        f += 1 if r > t else 0
    elif kind != "rz":
        raise ValueError(kind)
    return s * f * step


def frac(z: F, w: F) -> F:
    """Position of |z RZ(1/w)| in its ulp (the variable the threshold family acts on)."""
    p = z * rz_recip(w)
    n = abs(p) / ulp(p)
    return n - (n.numerator // n.denominator)


# ------------------------------------------------------------------------------------------------ depth rules
RULES = {
    "D1": lambda z, w: rnd(z * rz_recip(w), "rn"),
    "D2": lambda z, w: rnd(z / w, "rz"),
    "D5": lambda z, w: rnd(z * rz_recip(w), "rz"),
    "T26": lambda z, w: thr_mag(z * rz_recip(w), F(3, 8)),
    "T27": lambda z, w: thr_mag(z * rz_recip(w), F(7, 16)),
    "K23": lambda z, w: rprec(rprec(z, 23, "rz") * rz_recip(w), 24, "ra"),
    "T26d": lambda z, w: thr_dir(z * rz_recip(w), F(5, 8)),
    "T27d": lambda z, w: thr_dir(z * rz_recip(w), F(9, 16)),
}
RULE_TEXT = {
    "D1": "RN(z RZ(1/w)), the product to nearest",
    "D2": "RZ(z/w)",
    "D5": "RZ(z RZ(1/w)), the product toward zero",
    "T26": "|z RZ(1/w)| rounded away from zero iff its fraction exceeds 3/8 (rounding at 26 bits then half up)",
    "T27": "the same with 7/16 (27 bits then half up)",
    "K23": "z cut to 23 bits, the product rounded away from zero",
    "T26d": "the 3/8 threshold read on the floor fraction (toward +inf iff it exceeds 5/8): equals T26 on negatives",
    "T27d": "the 7/16 threshold read on the floor fraction (toward +inf iff it exceeds 9/16)",
}


def depth_word(z: F, w: F, rule: str, sum_mode: str = "rn") -> int:
    """The stored depth word of clip depth z, w = w: Rsum(1/2 + 1/2 q') with q' = the rule's rounding of the product."""
    return word(rsum(H + H * RULES[rule](z, w), sum_mode))


def words_of(z: F, w: F, rules, sum_mode: str = "rn") -> dict:
    return {r: depth_word(z, w, r, sum_mode) for r in rules}


# the g-db q-precision candidates: the product rounded at the float32 precision of q (then the sum rounded) against the
# product kept on the grid of the sum (0.5 + 0.5 q' exact: q' a multiple of 2^-23 for |q| in (0.25, 0.5))
def q_candidates(z: F, w: F, rule: str, grid: bool, sum_mode: str = "rn") -> int:
    p = z * rz_recip(w)
    if not grid:
        return depth_word(z, w, rule, sum_mode)
    step = F(1, 2 ** 23)
    kind, t = {"D1": ("rn", None), "D5": ("rz", None), "T26": ("mag", F(3, 8)), "T27": ("mag", F(7, 16))}[rule]
    return word(H + H * grid_round(p, step, kind, t))


# ------------------------------------------------------------------------------------------------ viewport z words (g-dc)
# stored depth = offset (block word 10, vp4) + scale (block word 11, vp5) * z/w: E193 reads vp4 as the offset and vp5 as
# the scale; which is which is the library's order and not separated by one slope [infer]
def vp_words(z: F, w: F, off: F, scale: F, kind: str) -> int:
    """kind: fma (q' = z/w rounded by D1, then RN(off + scale q') single rounding), two (RN(off + RN(scale q'))),
    ZS (RN(off + RN(RN(z scale) RZ(1/w)))), swap (offset and scale exchanged, fma)."""
    rw = rz_recip(w)
    q = rnd(z * rw, "rn")
    if kind == "fma":
        return word(rnd(off + scale * q, "rn"))
    if kind == "two":
        return word(rnd(off + rnd(scale * q, "rn"), "rn"))
    if kind == "ZS":
        return word(rnd(off + rnd(rnd(z * scale, "rn") * rw, "rn"), "rn"))
    if kind == "swap":
        return word(rnd(scale + off * q, "rn"))
    raise ValueError(kind)


VP_KINDS = {
    "VF": ("fma", "offset (blk 10) + scale (blk 11) x ((z RZ(1/w)) to nearest), one rounding of the sum"),
    "VT": ("two", "the same with the scale product rounded first, then the sum"),
    "VZ": ("ZS", "(z x scale) rounded, times RZ(1/w) rounded, then the sum"),
    "VS": ("swap", "blk 10 is the scale and blk 11 the offset (order swapped), one rounding of the sum"),
}


def vp_cands(z: F, w: F, off: F, scale: F) -> dict:
    return {k: vp_words(z, w, off, scale, kind) for k, (kind, _) in VP_KINDS.items()}


# ------------------------------------------------------------------------------------------------ made vertices (g-dd)
def made_w_candidates(rw_word: int, span: int = 8):
    """The float32 w whose RZ reciprocal is the stored 1/w word (design 1.1)."""
    r = wordval(rw_word)
    base = word(rnd(1 / r, "rn"))
    return [base + k for k in range(-span, span + 1) if rz_recip(wordval(base + k)) == r]


def made_cut_w(A, B, C, D, plane: str) -> F:
    """w of the cut of z = A x + B against the plane z = +w or z = -w with w = C x + D (exact)."""
    A, B, C, D = (F(v) for v in (A, B, C, D))
    s = 1 if plane == "+w" else -1
    x = (s * D - B) / (A - s * C)
    return C * x + D, x


# ------------------------------------------------------------------------------------------------ C by target
LT_T4 = 0x351                   # E774: the last raise at 4096x4096 has thr0 = 0x351 (C = 0x371 = thr0 + 0x20)
C_4096 = 0x371


def layout(w: int, h: int) -> dict:
    tx, ty = -(-w // 32), -(-h // 16)
    n = 4 if w * h >= 640 * 480 else 2
    ru = lambda v, m: -(-v // m) * m
    mx, my = ru(-(-tx // n), 4), ru(-(-ty // n), 4)
    span, side = max(n * mx, n * my), 1
    while side < span:
        side <<= 1
    return dict(R=tx * ty, mt=mx * my, side=side)


def lt_last_thr0(w: int, h: int) -> int:
    """LT: the last raising thr0 = floor(0x351 R / 32768)."""
    return LT_T4 * layout(w, h)["R"] // layout(4096, 4096)["R"]


def affine_C(w: int, h: int, c2048: int, key: str) -> int:
    """The affine law through (2048x2048, c2048) and (4096x4096, 0x371) in the feature `key` (R, side2, mt), as the raised
    threshold C, rounded down."""
    f = {"R": lambda d: d["R"], "side2": lambda d: d["side"] ** 2, "mt": lambda d: d["mt"]}[key]
    L, L4, L2 = layout(w, h), layout(4096, 4096), layout(2048, 2048)
    a = F(C_4096 - c2048) / (f(L4) - f(L2))
    v = c2048 + a * (f(L) - f(L2))
    return v.numerator // v.denominator


def affine_brackets(w: int, h: int, c2048_range=(0xe0, 0x11f)) -> dict:
    """{feature: (lo, hi)} of the last raising thr0 (C - 0x20) the affine law gives at the ends of the 2048x2048 bracket."""
    out = {}
    for key in ("R", "side2", "mt"):
        v = [affine_C(w, h, c, key) - 0x20 for c in c2048_range]
        out[key] = (min(v), max(v))
    return out


def c5_fixed_cells(w: int, h: int) -> list:
    """The five fixed thr0 cells of a g-c5 target: the ends of the affine-in-regions bracket (last raise at the low end,
    first silent above the high end) and LT's flip pair."""
    lo, hi = affine_brackets(w, h)["R"]
    lt = lt_last_thr0(w, h)
    return sorted({lo, lt, lt + 1, hi, hi + 1})


# ------------------------------------------------------------------------------------------------ H-last
def hlast(counts_before_each_abort) -> int:
    """dword 36 under H-last: the count before the LAST abort less 2, floor 0; no abort reads 0."""
    c = list(counts_before_each_abort)
    return max(c[-1] - 2, 0) if c else 0
