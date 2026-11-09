# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""The 11.32 sampler model: what a job of tx_map.s would read back under a named hypothesis.

Inputs are a case spec (the coordinate rules, the four state words, the instruction) and a
rules dict of hypotheses; the output is the 2048 pixels of a 64 x 32 fill with pa0 = (y << 16) | x.
The scratch buffer is the host's: dword i is 0xD0000000 | i, so a texel read names its dword.

The model knows only what the landed records say (E033, E035, E041, E274, E276, E397, E441 and
doc/specs/usse_isa.md 7.37); everything else is a rule that a run may refute, named in RULES.
It shares no code with the generator's program builder: the builder writes instructions from a
spec, this file reads the same spec and computes the floats and the texels itself.
"""
from __future__ import annotations

import math
import struct

W, H = 64, 32                       # the fill
OOB = 0xDEADBEEF                    # a read outside the scratch buffer (the job would fault)

# The hypotheses and their names; a spec may override with its own "rules".
RULES = {
    "chain": "A",       # A: both sides halve to 1; B: stops when the short side is 1; D: A, square-padded
    "t3off": "pre",     # T3 7:0 offset before the address mode (pre) or clamped after it (post)
    "t3rows": "after",  # T3 27, 28: the rows come after the source's height (after) or are fixed 32 / 40
    "lodf": "max4",     # the LOD of gradients: max4, euc, min, pwl_max4, pwl_euc
    "w3d": "ignore",    # smp3d: the third coordinate is not read
    "mode47": "clamp",  # address modes 4 to 7: a named candidate, see addr()
    "twiddle": "plain",
}


def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def bits(f: float) -> int:
    return struct.unpack("<I", struct.pack("<f", f))[0]


def fb(b: int) -> float:
    return struct.unpack("<f", struct.pack("<I", b & 0xFFFFFFFF))[0]


def ev(spec, x: int, y: int) -> float:
    """One coordinate, gradient or bias of pixel (x, y), as the generator's rule says."""
    k = spec[0]
    if k == "bits":
        return fb(spec[1])
    if k == "map":                  # ("map", axis, a, offset, exponent bits)
        _, ax, a, off, exp = spec
        q = ((x if ax == "x" else y) | off) & ((1 << a) - 1)
        return fb(exp | ((2 * q + 1) << (22 - a)))
    if k == "lin":                  # ("lin", axis, K bits, C bits): (1 + p / 64 or 1 + p / 32) K + C
        _, ax, kb, cb = spec
        uf = fb(0x3F800000 | ((x << 17) if ax == "x" else (y << 18)))
        return f32(uf * fb(kb) + fb(cb))
    raise ValueError(spec)


def morton(x: int, y: int, w: int, h: int) -> int:
    bw, bh = max(w, 1).bit_length() - 1, max(h, 1).bit_length() - 1
    common = min(bw, bh)
    i = 0
    for b in range(common):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    rest = (x if bw > bh else y) >> common
    return i | rest << (2 * common)


def s4(v: int) -> int:
    return v - 16 if v & 8 else v


def chain(w: int, h: int, rule: str):
    """[(w, h, dword offset)] of the levels, level 0 first."""
    if rule == "B":
        n = min(w, h).bit_length()
        dims = [(w >> l, h >> l) for l in range(n)]
    else:
        n = max(w, h).bit_length()
        dims = [(max(1, w >> l), max(1, h >> l)) for l in range(n)]
    out, off = [], 0
    for dw, dh in dims:
        out.append((dw, dh, off))
        off += max(dw, dh) ** 2 if rule == "D" else dw * dh
    return out


class Tex:
    def __init__(self, t0: int, t1: int, base_dw: int, t3: int, pages: int, rules: dict,
                 inject: dict | None = None, csc: bool = False):
        self.t0, self.t1, self.t3, self.rules = t0, t1, t3, rules
        self.inject, self.csc = inject or {}, csc
        self.base, self.pages = base_dw, pages
        self.ty, self.fmt = t1 >> 29, t1 >> 24 & 31
        self.w, self.h = (t1 >> 12 & 0xFFF) + 1, (t1 & 0xFFF) + 1
        self.stride = ((t0 >> 9 & 7) | (t0 >> 17 & 0x3FF) << 3) + 1 if self.ty == 6 else 0
        self.bad = False

    # ---- memory
    def rd(self, idx: int) -> int:
        if not 0 <= idx < self.pages * 1024:
            self.bad = True
            return OOB
        if idx in self.inject:
            return self.inject[idx]
        return 0xD0000000 | idx

    # ---- addressing
    def axis(self, t: int, n: int, mode: int) -> int:
        clamp = lambda v: min(max(v, 0), n - 1)
        if self.ty == 6:
            return clamp(t)
        if mode == 0:
            return t % n
        if mode == 1:
            m = t % (2 * n)
            return 2 * n - 1 - m if m >= n else m
        if mode == 2:
            return clamp(t)
        if mode == 3:
            return clamp(-t - 1 if t < 0 else t)
        r = self.rules["mode47"]            # 4 to 7: candidates only
        if r == "clamp":
            return clamp(t)
        if r == "nomask":
            return t
        if r == "border":
            return -1                       # a texel the caller reads as "border"
        raise ValueError(r)

    def level_geom(self, l: int):
        if self.ty == 6:
            return (self.w, self.h, 0)
        return chain(self.w, self.h, self.rules["chain"])[l]

    def fetch(self, x: int, y: int, l: int = 0) -> int:
        lw, lh, off = self.level_geom(l)
        t3 = self.t3
        if self.fmt in (28, 29):
            return self.yuv(x, y)
        if self.ty == 3:                    # H: type 3 is a raster of 4-byte texels
            return self.rd(self.base + min(max(y, 0), lh - 1) * lw + min(max(x, 0), lw - 1))
        sx, sy = s4(t3 >> 4 & 15), s4(t3 & 15)
        clamp = lambda v, n: min(max(v, 0), n - 1)
        if self.ty == 6:
            x, y = clamp(clamp(x, lw) + sx, lw), clamp(clamp(y, lh) + sy, lh)
        elif self.rules["t3off"] == "pre":          # the offset, then the address mode
            x = self.axis(x + sx, lw, self.t0 >> 6 & 7)
            y = self.axis(y + sy, lh, self.t0 >> 3 & 7)
        else:                                       # the address mode, then the offset clamped
            x = self.axis(x, lw, self.t0 >> 6 & 7)
            y = self.axis(y, lh, self.t0 >> 3 & 7)
            if x >= 0 and y >= 0:
                x, y = clamp(x + sx, lw), clamp(y + sy, lh)
        if x < 0 or y < 0:
            return 0x0B0DE000                       # border marker (never a name)
        if t3 >> 10 & 1:
            x, y = 0, 0
        elif t3 >> 14 & 1:
            x, y = x + 32, y + x
        elif t3 >> 19 & 1:
            x, y = 4 * x, 4 * y
        elif t3 >> 18 & 1:
            x, y = 2 * x, 2 * y
        elif t3 >> 28 & 1:
            top = {"after": lh + lh // 4, "fixed": 40}[self.rules["t3rows"]]
            x, y = x // 4, top + y // 4
        elif t3 >> 27 & 1:
            top = {"after": lh, "fixed": 32}[self.rules["t3rows"]]
            x, y = x // 2, top + y // 2
        if self.ty == 6:
            return self.rd(self.base + y * self.stride + x)
        return self.rd(self.base + off + morton(x, y, lw, lh))

    def yuv(self, x: int, y: int) -> int:
        """Formats 28 (Y0 U Y1 V) and 29 (U Y0 V Y1), two texels a dword, a raster of w / 2
        dwords a row, through colour-space set 0 as E037 fits it when the job loaded it."""
        x, y = min(max(x, 0), self.w - 1), min(max(y, 0), self.h - 1)
        d = self.rd(self.base + y * (self.w // 2) + x // 2)
        b = [d >> (8 * k) & 255 for k in range(4)]
        if self.fmt == 28:
            yy, u, v = b[0 if x % 2 == 0 else 2], b[1], b[3]
        else:
            yy, u, v = b[1 if x % 2 == 0 else 3], b[0], b[2]
        if not self.csc:
            return 0xFF000000
        sat = lambda t: min(max(t, 0), 255)
        r = sat((149 * (yy - 16) + 204 * (v - 128)) >> 7)
        g = sat((149 * (yy - 16) - 50 * (u - 128) - 104 * (v - 128)) >> 7)
        bl = sat((149 * (yy - 16) + 258 * (u - 128)) >> 7)
        return 0xFF000000 | r << 16 | g << 8 | bl

    # ---- one level, point or bilinear
    def level_read(self, u: float, v: float, l: int, bilinear: bool) -> int:
        lw, lh, _ = self.level_geom(l)
        if not bilinear:
            return self.fetch(math.floor(u * lw), math.floor(v * lh), l)
        x, y = u * lw - 0.5, v * lh - 0.5
        x0, y0 = math.floor(x), math.floor(y)
        fx, fy = int((x - x0) * 64), int((y - y0) * 64)
        t = [self.fetch(x0 + dx, y0 + dy, l) for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
        wt = [(64 - fx) * (64 - fy), fx * (64 - fy), (64 - fx) * fy, fx * fy]
        out = 0
        for c in range(4):
            s = sum((t[k] >> (8 * c) & 255) * wt[k] for k in range(4))
            out |= ((s + 2048) >> 12) << (8 * c)
        return out

    # ---- the level choice (E276, E441)
    def sample(self, u: float, v: float, lod: float) -> int:
        t0 = self.t0
        mag = (t0 >> 12 & 3) in (1, 2)
        mn = (t0 >> 10 & 3) in (1, 2)
        if self.ty == 6:
            return self.level_read(u, v, 0, mag)
        top, mx = t0 >> 21 & 0x3F, t0 >> 17 & 15
        n = len(chain(self.w, self.h, self.rules["chain"]))
        last = n - 1
        if top == 0 or mx in (0, 15) or not lod > -math.inf:
            return self.level_read(u, v, 0, mag if lod <= 0 else mn)
        le = lod + (top - 63) / 8.0
        if le <= 0:
            return self.level_read(u, v, 0, mag)
        cap = min(mx, last)
        if t0 >> 9 & 1 == 0:
            lv = min(math.floor(le + 0.5), cap)
            return self.level_read(u, v, lv, mn)
        lc = min(le, cap)
        lo = math.floor(lc)
        f = int((lc - lo) * 64)
        if f == 0:
            return self.level_read(u, v, lo, mn)
        a, b = self.level_read(u, v, lo, mn), self.level_read(u, v, min(lo + 1, cap), mn)
        return sum((((a >> 8 * c & 255) * (64 - f) + (b >> 8 * c & 255) * f + 32) >> 6) << 8 * c
                   for c in range(4))


def lod_of(grad, lw: int, lh: int, rule: str) -> float:
    dudx, dvdx, dudy, dvdy = grad
    ax, ay = (dudx * lw, dvdx * lh), (dudy * lw, dvdy * lh)
    if rule.endswith("max4"):
        rho = max(abs(ax[0]), abs(ax[1]), abs(ay[0]), abs(ay[1]))
    elif rule.endswith("euc"):
        rho = max(math.hypot(*ax), math.hypot(*ay))
    elif rule == "min":
        rho = min(math.hypot(*ax), math.hypot(*ay))
    else:
        raise ValueError(rule)
    if rho == 0:
        return -math.inf
    if rule.startswith("pwl"):          # exponent plus the mantissa, linear
        e = math.floor(math.log2(rho))
        return e + (rho / 2.0 ** e - 1.0)
    return math.log2(rho)


def render(spec: dict, rules: dict | None = None):
    """The 2048 pixels (raster order) of a case, or None when the spec has no model."""
    r = dict(RULES)
    r.update(spec.get("rules", {}))
    r.update(rules or {})
    t0, t1, base, t3 = spec["t0"], spec["t1"], spec["base"], spec["t3"]
    inj = {int(k): v for k, v in spec.get("inject", {}).items()}
    tex = Tex(t0, t1, base, t3, spec.get("pages", 16), r, inj, spec.get("csc", False))
    out = []
    ins = spec["ins"]
    for y in range(H):
        for x in range(W):
            tex.bad = False
            u, v = ev(spec["u"], x, y), ev(spec["v"], x, y)
            if ins == "replace":
                lod = ev(spec["lod"], x, y)
            elif ins == "grad":
                g = [ev(s, x, y) for s in spec["grad"]]
                lod = lod_of(g, tex.w, tex.h, r["lodf"])
            elif ins in ("auto", "bias"):
                x0, y0 = x & ~1, y & ~1
                dudx = ev(spec["u"], x0 + 1, y0) - ev(spec["u"], x0, y0)
                dvdx = ev(spec["v"], x0 + 1, y0) - ev(spec["v"], x0, y0)
                dudy = ev(spec["u"], x0, y0 + 1) - ev(spec["u"], x0, y0)
                dvdy = ev(spec["v"], x0, y0 + 1) - ev(spec["v"], x0, y0)
                lod = lod_of((dudx, dvdx, dudy, dvdy), tex.w, tex.h, r["lodf"])
                if ins == "bias":
                    lod += ev(spec["lod"], x, y)
            elif ins in ("none", "3d"):
                lod = 0.0
            else:
                return None
            val = tex.sample(u, v, lod)
            out.append(OOB if tex.bad else val)
    return out


def digest(pix) -> str:
    import hashlib
    return hashlib.sha256(",".join(f"{v:08x}" for v in pix).encode()).hexdigest()
