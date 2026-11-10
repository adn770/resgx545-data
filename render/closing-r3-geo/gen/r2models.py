"""R2 offline models (pure functions, no I/O): everything r1models.py has (imported unchanged) plus

  T3  homogeneous clipping with w != 1: Sutherland-Hodgman in (x, y, z, w) against z <= w and z >= -w, the strip
      zigzag, the window position x/w, the made vertices' 1/w by two candidates (HI-w: the reciprocal of the made
      w; HI-rhw: the made vertex's 1/w interpolated linearly with the same edge parameter), depth words
  T4  the depth word of a vertex of clip depth Z and w = W (z/w in (-1, -0.5]) by six candidate formulas
  C   the raise rule at the measured limit C = 0x371 (R1: raise iff thr0 + 0x20 <= C), the frozen C3 and C2 rows

float32 arithmetic is exact-rational with an explicit rounding (rz toward zero, rn to nearest even), never numpy's.
Every number is a prediction from data measured BEFORE this file (R1 and S1/S1b): a fit; the runs hold it out.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import struct  # noqa: E402
from fractions import Fraction  # noqa: E402

import r1models as M  # noqa: E402  (unchanged copy of closing2/r1-pixgeo/gen/r1models.py)

bits, fval = M.bits, M.fval

C_MEASURED = 0x371                  # R1 g-c1 + g-c1f: raise at P = 0x373 (thr0 + 0x20 = 0x371), none at P = 0x374
P_STAR = 0x374                      # the first silent P at 4096x4096


# ------------------------------------------------------------------------------------------------ float32 rounding
def _quant(x: Fraction) -> Fraction:
    ax = abs(x)
    e = ax.numerator.bit_length() - ax.denominator.bit_length()
    if Fraction(2) ** e > ax:
        e -= 1
    return Fraction(2) ** (e - 23)


def rz(x: Fraction) -> Fraction:
    """x toward zero as a float32 value (normal range)."""
    if x == 0:
        return Fraction(0)
    q = _quant(x)
    n = abs(x) / q
    return (1 if x > 0 else -1) * (n.numerator // n.denominator) * q


def rn(x: Fraction) -> Fraction:
    """x to nearest even as a float32 value (normal range)."""
    if x == 0:
        return Fraction(0)
    q = _quant(x)
    n = abs(x) / q
    f = n.numerator // n.denominator
    r = n - f
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and f % 2):
        f += 1
    return (1 if x > 0 else -1) * f * q


def word(x: Fraction) -> int:
    """float32 word of an exactly representable value."""
    w = struct.unpack("<I", struct.pack("<f", float(x)))[0]
    assert Fraction(struct.unpack("<f", struct.pack("<I", w))[0]) == x, f"{x} is not a float32"
    return w


def f32(x: float) -> Fraction:
    return rn(Fraction(x))


# ------------------------------------------------------------------------------------------------ T4
DEPTH_CANDS = [
    ("D1", "0.5 + 0.5 (Z * RZ(1/W)), the product rounded to nearest"),
    ("D2", "0.5 + 0.5 RZ(Z/W)"),
    ("D3", "0.5 + 0.5 RN(Z/W)"),
    ("D5", "0.5 + 0.5 RZ(Z * RZ(1/W))"),
    ("D6", "RN(RN(Z + W) / (2 W))"),
    ("D7", "0.5 + 0.5 (Z * RN(1/W)), the product rounded to nearest"),
]


def depth_words(Z: float, W: float) -> dict[str, int]:
    """{candidate: stored depth word} for clip depth Z and w = W (both float32 values; z/w in (-1, -0.5] keeps every
    step exact: 0.5 q is exact and 0.5 - 0.5 |q| is exact by Sterbenz, so the candidates differ only in q)."""
    z, w = f32(Z), f32(W)
    half = Fraction(1, 2)
    rhw_rz, rhw_rn = rz(1 / w), rn(1 / w)
    q = {"D1": rn(z * rhw_rz), "D2": rz(z / w), "D3": rn(z / w), "D5": rz(z * rhw_rz), "D7": rn(z * rhw_rn)}
    out = {k: word(rn(half + half * v)) for k, v in q.items()}
    out["D6"] = word(rn(rn(z + w) / (2 * w)))
    return out


def rhw_words(W: float) -> tuple[int, int]:
    """(RZ, RN) float32 words of 1/W."""
    w = f32(W)
    return word(rz(1 / w)), word(rn(1 / w))


# ------------------------------------------------------------------------------------------------ T3
def _sh(poly, d):
    """Sutherland-Hodgman against d(p) >= 0 over the closed polygon (end vertex when inside, the crossing when it
    changes sides), points are 4-tuples (x, y, z, w) of Fractions; also returns each made vertex's edge parameter."""
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        da, db = d(a), d(b)
        ia, ib = da >= 0, db >= 0
        if ia != ib:
            t = da / (da - db)
            c = tuple(p + t * (q - p) for p, q in zip(a, b))
            out.append((c, (a, b, t)))
        if ib:
            out.append((b, None))
    return out


def predict_zwclip(A, B, C, D, plane_order=("+w", "-w")):
    """The object of the vertex program z = A x + B, w = C x + D (x, y unscaled, window = 32 + 32 x/w) over the
    three vertices of r1models.CLIP.  Returns dict(nv, xy (stored order), made (bool each), rhw_w (HI-w words),
    rhw_lerp (HI-rhw words), depth_made (words of the made vertices, None for originals), prims)."""
    A, B, C, D = (Fraction(v) for v in (A, B, C, D))
    pts = []
    for x, y in M.CLIP:
        x, y = Fraction(x), Fraction(y)
        pts.append((x, y, A * x + B, C * x + D))
    poly = [(p, None) for p in pts]
    clipped = False
    for nm in plane_order:
        if not poly:
            break
        sgn = 1 if nm == "+w" else -1
        d = (lambda p: p[3] - p[2]) if nm == "+w" else (lambda p: p[3] + p[2])
        if all(d(p) >= 0 for p, _ in poly):
            continue
        res = _sh([p for p, _ in poly], d)
        poly, clipped = res, True
    n = len(poly)
    zz = M.zigzag(n) if clipped else list(range(n))
    stored = [poly[i] for i in zz]
    pos = {pi: si for si, pi in enumerate(zz)}
    bnd = {frozenset((pos[i], pos[(i + 1) % n])) for i in range(n)}
    prims = []
    for t in M.strip_tris(n):
        prims.append(tuple(t[k] | (16 if frozenset((t[k], t[(k + 1) % 3])) in bnd else 0) for k in range(3)))
    xy, made, rw, rl, dm = [], [], [], [], []
    for p, info in stored:
        x, y, z, w = p
        xy.append((float(32 + 32 * x / w), float(32 + 32 * y / w)))
        made.append(info is not None)
        rw.append(word(rz(1 / w)))                                                 # RZ of the exact 1/w
        if info is None:
            rl.append(word(rz(1 / w)))
            dm.append(None)
        else:
            a, b, t = info
            rl.append(word(rz((1 / a[3]) + t * ((1 / b[3]) - (1 / a[3])))))    # the lerp of 1/w with the edge parameter
            dm.append(word(Fraction(1)) if (w - z) == 0 else word(Fraction(0)))   # z = +w -> depth 1.0, z = -w -> 0.0
    return dict(nv=n, xy=xy, made=made, rhw_w=rw, rhw_lerp=rl, depth_made=dm, prims=prims)


def depth_original(z, w):
    """The stored depth candidates of an unclipped vertex: not scored in T3 (T4 decides the formula)."""
    return depth_words(float(z), float(w))
