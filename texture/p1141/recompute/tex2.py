"""A second sampler model for the p1141 checks, built on p1132's texmodel.Tex (imported
unchanged): the tile law, the operand pairing, two-stage bilinear, sRGB-to-half, the T3
address model and an ETC1 decode, each a named option. Written from the words of
opus/texture.md and the landed records; nothing copied from its scratch scripts."""
import math, struct
from lib import *

OPT = dict(t3chain="wh", t3e="all", etc_order="morton", srgb_pre=False, foot=None, frac="trunc", tile=True, pair=False, two_stage=False, srgb=False, t3model=False, lodsel=False,
           P=64, order="xy", etc1=False, rtypes=False, rnd="half")


def half_bits(f):
    """nearest-even IEEE half of a float, as 16 bits."""
    try:
        return struct.unpack("<H", struct.pack("<e", f))[0]
    except OverflowError:
        return 0x7C00


def s2l(b):
    c = b / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def srgb_word(v):
    return half_bits(s2l(v >> 8 & 255)) << 16 | half_bits(s2l(v & 255))


def lerp(a, b, f, P):
    sh = P.bit_length() - 1
    return (a * (P - f) + b * f + (P // 2 if OPT["rnd"] == "half" else 0)) >> sh


def etc1_block(hi, lo):
    """Khronos OES_compressed_ETC1_RGB8 decode of the 64-bit block hi:lo (hi = bits 63:32).
    Returns 16 (r,g,b) in x-major order (index x*4+y), a texel at (x, y) of the block."""
    diff, flip = hi >> 1 & 1, hi & 1
    t1, t2 = hi >> 5 & 7, hi >> 2 & 7
    if diff:
        r1, g1, b1 = hi >> 27 & 31, hi >> 19 & 31, hi >> 11 & 31
        dr, dg, db = [(v if v < 4 else v - 8) for v in (hi >> 24 & 7, hi >> 16 & 7, hi >> 8 & 7)]
        r2, g2, b2 = r1 + dr, g1 + dg, b1 + db
        if not (0 <= r2 < 32 and 0 <= g2 < 32 and 0 <= b2 < 32):
            r2, g2, b2 = [min(max(v, 0), 31) for v in (r2, g2, b2)]
        e = lambda v: v << 3 | v >> 2
        c1 = (e(r1), e(g1), e(b1)); c2 = (e(r2), e(g2), e(b2))
    else:
        c1 = tuple((v << 4 | v) for v in (hi >> 28 & 15, hi >> 20 & 15, hi >> 12 & 15))
        c2 = tuple((v << 4 | v) for v in (hi >> 24 & 15, hi >> 16 & 15, hi >> 8 & 15))
    T = [[2, 8], [5, 17], [9, 29], [13, 42], [18, 60], [24, 80], [33, 106], [47, 183]]
    out = []
    for x in range(4):
        for y in range(4):
            i = x * 4 + y
            msb, lsb = lo >> (16 + i) & 1, lo >> i & 1
            sub = (x < 2) if not flip else (y < 2)
            tab = T[t1 if sub else t2]
            base = c1 if sub else c2
            mod = {(0, 0): tab[0], (0, 1): tab[1], (1, 0): -tab[0], (1, 1): -tab[1]}[(msb, lsb)]
            out.append(tuple(min(max(c + mod, 0), 255) for c in base))
    return out


class Tex2(tm.Tex):
    def level_read(self, u, v, l, bilinear):
        if bilinear and OPT["srgb_pre"]:
            lw, lh, _ = self.level_geom(l)
            x, y = u * lw - 0.5, v * lh - 0.5
            x0, y0 = math.floor(x), math.floor(y)
            fx, fy = int((x - x0) * 64) / 64, int((y - y0) * 64) / 64
            t = [self.fetch(x0 + dx, y0 + dy, l) for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
            out = 0
            for c in (0, 1):
                b = [s2l(t[k] >> 8 * c & 255) for k in range(4)]
                top = b[0] * (1 - fx) + b[1] * fx
                bot = b[2] * (1 - fx) + b[3] * fx
                out |= half_bits(top * (1 - fy) + bot * fy) << (16 * c)
            return out
        if not bilinear or not OPT["two_stage"]:
            return super().level_read(u, v, l, bilinear)
        lw, lh, _ = self.level_geom(l)
        x, y = u * lw - 0.5, v * lh - 0.5
        x0, y0 = math.floor(x), math.floor(y)
        fx, fy = int((x - x0) * 64), int((y - y0) * 64)
        P = OPT["P"]
        if P != 64:
            fx, fy = int((x - x0) * P), int((y - y0) * P)
        t = [self.fetch(x0 + dx, y0 + dy, l) for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
        out = 0
        for c in range(4):
            b = [(t[k] >> 8 * c) & 255 for k in range(4)]
            if OPT["order"] == "xy":
                top, bot = lerp(b[0], b[1], fx, P), lerp(b[2], b[3], fx, P)
                r = lerp(top, bot, fy, P)
            else:
                lef, rig = lerp(b[0], b[2], fy, P), lerp(b[1], b[3], fy, P)
                r = lerp(lef, rig, fx, P)
            out |= r << 8 * c
        return out

    def sample(self, u, v, lod):
        """tm.Tex.sample with the fraction rounding of OPT["frac"] (trunc as the model, or round)."""
        if OPT["frac"] == "trunc" or self.ty == 6:
            return super().sample(u, v, lod)
        t0 = self.t0
        mag = (t0 >> 12 & 3) in (1, 2)
        mn = (t0 >> 10 & 3) in (1, 2)
        top, mx = t0 >> 21 & 0x3F, t0 >> 17 & 15
        n = len(tm.chain(self.w, self.h, self.rules["chain"]))
        if top == 0 or mx in (0, 15) or not lod > -math.inf:
            return super().sample(u, v, lod)
        le = lod + (top - 63) / 8.0
        if le <= 0 or t0 >> 9 & 1 == 0:
            return super().sample(u, v, lod)
        lc = min(le, min(mx, n - 1))
        lo = math.floor(lc)
        f = min(int((lc - lo) * 64 + 0.5), 64)
        if f == 0:
            return self.level_read(u, v, lo, mn)
        a, b = self.level_read(u, v, lo, mn), self.level_read(u, v, min(lo + 1, min(mx, n - 1)), mn)
        return sum((((a >> 8 * c & 255) * (64 - f) + (b >> 8 * c & 255) * f + 32) >> 6) << 8 * c
                   for c in range(4))

    def fetch(self, x, y, l=0):
        if self.fmt == 27 and OPT["etc1"]:
            return self.etc(x, y)
        if not OPT["t3model"] or self.ty == 6 and False:
            return super().fetch(x, y, l)
        lw, lh, _ = self.level_geom(l) if self.ty != 6 else (self.w, self.h, 0)
        t3 = self.t3
        sx, sy = tm.s4(t3 >> 4 & 15), tm.s4(t3 & 15)
        if self.ty == 6:
            cl = lambda v, n: min(max(v, 0), n - 1)
            X, Y = cl(x, lw) + sx, cl(y, lh) + sy
            X, Y = cl(X, lw), cl(Y, lh)
            # strided textures: the offset applied after clamping, as in the model it extends
        else:
            X = self.axis(x + sx, lw, self.t0 >> 6 & 7)
            Y = self.axis(y + sy, lh, self.t0 >> 3 & 7)
        if X < 0 or Y < 0:
            return 0x0B0DE000
        L, e = t3 >> 27 & 3, t3 >> 18 & 3
        if t3 >> 10 & 1:
            return self.rd(self.base)
        off = 0
        for k in range(L):
            off += (self.stride if OPT["t3chain"] == "stride" and self.ty == 6 else max(1, self.w >> k)) \
                * max(1, self.h >> k)
        Xl, Yl = X >> L, Y >> L
        if self.ty == 6:
            idx = Xl + self.stride * Yl
        else:
            wl, hl = max(1, self.w >> L), max(1, self.h >> L)
            idx = tile_index(Xl, Yl, wl, hl)
        if OPT["t3e"] == "idx":
            return self.rd(self.base + off + (idx << e))
        return self.rd(self.base + ((off + idx) << e))

    def etc(self, x, y):
        x = self.axis(x, self.w, self.t0 >> 6 & 7)
        y = self.axis(y, self.h, self.t0 >> 3 & 7)
        bx, by = x >> 2, y >> 2
        nbx = self.w // 4
        # blocks in Morton order, y in the low bit (fit rule of the report; one size)
        nby = max(1, self.h // 4)
        c = min(nbx.bit_length() - 1, nby.bit_length() - 1)
        i = 0
        if OPT["etc_order"] == "raster":
            i = by * nbx + bx
        else:
            for b in range(c):
                if OPT["etc_order"] == "morton":
                    i |= (by >> b & 1) << (2 * b) | (bx >> b & 1) << (2 * b + 1)
                else:
                    i |= (bx >> b & 1) << (2 * b) | (by >> b & 1) << (2 * b + 1)
            i |= (bx if nbx > nby else by) >> c << (2 * c)
        d0, d1 = self.rd(self.base + 2 * i), self.rd(self.base + 2 * i + 1)
        r, g, b = etc1_block(d0, d1)[(x & 3) * 4 + (y & 3)]
        return 0xFF000000 | ETC_ORDER[0](r, g, b)


ETC_ORDER = [lambda r, g, b: r << 16 | g << 8 | b]   # B8G8R8A8: byte0 = blue


def foot(name, g, lw, lh):
    o0, o1, o2, o3 = g      # program order; P pairs (0,2) and (1,3) as vectors
    h = math.hypot
    if name == "P":
        return max(h(o0 * lw, o2 * lh), h(o1 * lw, o3 * lh))
    if name == "O":
        return max(h(o0 * lw, o1 * lh), h(o2 * lw, o3 * lh))
    if name == "Mp":
        return max(abs(o0) * lw, abs(o1) * lw, abs(o2) * lh, abs(o3) * lh)
    if name == "Mo":
        return max(abs(o0) * lw, abs(o1) * lh, abs(o2) * lw, abs(o3) * lh)
    if name == "F":
        return math.sqrt((sum((o0 * lw) ** 2 for _ in [0]) + (o1 * lw) ** 2 + (o2 * lh) ** 2 + (o3 * lh) ** 2) / 2)
    if name == "S":
        return max(abs(o0) * lw + abs(o2) * lh, abs(o1) * lw + abs(o3) * lh)
    raise ValueError(name)


def pair_lod(g, lw, lh, rule):
    if OPT["foot"]:
        rho = foot(OPT["foot"], g, lw, lh)
        return -math.inf if rho == 0 else math.log2(rho)
    a, b, c, d = g          # program order: op0..op3 ; pairing (0,2) and (1,3) as vectors
    return _orig_lod((a, c, b, d), lw, lh, rule)


_orig_lod = tm.lod_of


def lod_pair_on(on):
    tm.lod_of = pair_lod if on else _orig_lod


def render(name, rules=None, **opt):
    return predict(SPECS[name]["spec"], rules, **opt)


def predict(spec, rules=None, **opt):
    """Pixels of a case spec under the options (OPT defaults plus opt)."""
    old = dict(OPT)
    OPT.update(opt)
    sp = {"spec": spec}
    if OPT["foot"]:
        OPT["pair"] = True
    use_tile_law(OPT["tile"])
    lod_pair_on(OPT["pair"])
    old_tex = tm.Tex
    tm.Tex = Tex2
    try:
        px = render_spec(sp["spec"], rules or {})
    finally:
        tm.Tex = old_tex
        lod_pair_on(False)
        use_tile_law(False)
        OPT.clear(); OPT.update(old)
    return px


def render_spec(spec, rules):
    r = dict(tm.RULES); r.update(spec.get("rules", {})); r.update(rules)
    px = tm.render(spec, rules)
    if px is None:
        return None
    if OPT["srgb"] and spec["t0"] >> 27 & 1 and not OPT["srgb_pre"]:
        px = [srgb_word(v) if v < 0xD0000000 or True else v for v in px]
    return px
