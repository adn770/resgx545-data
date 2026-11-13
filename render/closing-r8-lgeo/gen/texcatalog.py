# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""The 11.32 cases: every job of every script as a spec (see recompute/texmodel.py), its group,
its set (control, fit, heldout, explore), its risk and the hypotheses whose predictions are declared.

A spec is a dict: t0, t1, t3 (the state words), base (the texture's first dword in the scratch
buffer), u and v (coordinate rules), ins (replace, grad, auto, bias, 3d, none), lod or grad or w,
and optionally inject {dword: value} (written by the program before the sample), csc, pokes.
Nothing here computes a texel: predictions come from texmodel.py, the programs from build.py.
"""
from __future__ import annotations

import random
import struct

LOD_NAMES = ()


def fbits(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", x))[0]


def lg(n: int) -> int:
    return n.bit_length() - 1


def t1tw(w: int, h: int, fmt: int = 12, ty: int = 0) -> int:
    return ty << 29 | fmt << 24 | (w - 1) << 12 | (h - 1)


def t0stride(s: int, extra: int = 0) -> int:
    v = s - 1
    return (v & 7) << 9 | (v >> 3) << 17 | extra


T0_REP = 0x07FE0000        # point filters, repeat, bits 26:21 = 0x3f, maximum level 15 (level 0 only)
T0_MIP = 0x07FC0000        # the same with a maximum level of 14: the whole chain
T3_TW = 0x00800800
T3_ST = 0xA0800000


def mapx(a, off=0, exp=0x3F800000):
    return ("map", "x", a, off, exp)


def mapy(b, off=0, exp=0x3F800000):
    return ("map", "y", b, off, exp)


def linx(k, c=0.0):
    return ("lin", "x", fbits(k), fbits(c))


def liny(k, c=0.0):
    return ("lin", "y", fbits(k), fbits(c))


def const(f):
    return ("bits", fbits(f))


ZERO = ("bits", 0)


def swin(w0, h0):
    """u, v rules that put texel (x, y) of a w0 x h0 texture at pixel (x, y) for coordinates in
    [0, 1) (a strided texture clamps, so the window of window() would read its last texel):
    u = (x + 1/2) / w0 and v = (y + 1/2) / h0, x < 64 and y < 32 (w0 and h0 powers of two)."""
    ku, kv = 64.0 / w0, 32.0 / h0
    return linx(ku, -ku + 0.5 / w0), liny(kv, -kv + 0.5 / h0)


def case(group, name, spec, st, risk="safe", label="", hyps=None, doc=""):
    spec = dict(spec)
    spec.setdefault("base", 0)
    spec.setdefault("t3", T3_TW)
    return {"group": group, "name": name, "spec": spec, "set": st, "risk": risk,
            "label": label or name, "hyps": hyps or [{}], "doc": doc}


def window(w0, h0, xo=0, yo=0):
    """u and v rules that put texel (X0 + x, Y0 + y) of a w0 x h0 level 0 at pixel (x, y)."""
    return mapx(lg(w0), xo), mapy(lg(h0), yo)


# --------------------------------------------------------------------------------------- gate
def gate():
    out = []
    u, v = window(16, 16)
    out.append(case("gate", "g1-tw16", dict(t0=T0_REP, t1=t1tw(16, 16), u=u, v=v, ins="replace",
                                            lod=ZERO), "control"))
    u, v = swin(64, 32)
    out.append(case("gate", "g2-st64x32", dict(t0=t0stride(64, 0), t1=t1tw(64, 32, 12, 6), u=u, v=v,
                                               ins="none", t3=T3_ST), "control"))
    out.append(case("gate", "g3-tw16-lod2", dict(t0=T0_MIP, t1=t1tw(16, 16), u=window(16, 16)[0],
                                                 v=window(16, 16)[1], ins="replace", lod=const(2.0)),
                    "control"))
    out.append(case("gate", "g4-tw16-u-mirror",
                    dict(t0=T0_REP | 1 << 6 | 2 << 3, t1=t1tw(16, 16), u=linx(4.0, -5.46875),
                         v=liny(1.0, -1.0), ins="none"), "control"))
    return out


# ------------------------------------------------------------------------------------ shapes
CHAINS = [{"chain": "A"}, {"chain": "B"}, {"chain": "D"}]


def shapes():
    out = []
    plan = [  # (w, h, levels to ask 0..n, set)
        (32, 16, 8, "fit"), (32, 32, 7, "control"), (128, 16, 9, "heldout"), (16, 32, 7, "heldout"),
        (64, 4, 8, "heldout"), (8, 64, 8, "heldout")]
    for w, h, nl, st in plan:
        for lod in range(nl):
            for xo in range(0, w, 64):
                for yo in range(0, h, 32):
                    u, v = window(w, h, xo, yo)
                    nm = f"shp-{w}x{h}-l{lod}" + (f"-x{xo}" if w > 64 else "") + (f"-y{yo}" if h > 32 else "")
                    out.append(case("shapes", nm, dict(t0=T0_MIP, t1=t1tw(w, h), u=u, v=v, ins="replace",
                                                       lod=const(float(lod))), st, hyps=CHAINS))
    return out


def fields():
    out = []
    for w, h, st, lod, maxes, biases, blend_lods in (
            (32, 16, "fit", 5.0, (0, 1, 2, 3, 4, 5, 6, 15), (0x00, 0x22, 0x23, 0x2B, 0x33, 0x3B, 0x3F),
             (0.25, 0.5, 0.75, 1.25, 2.5, 4.75, 5.5)),
            (128, 16, "heldout", 7.0, (0, 1, 3, 5, 7, 8, 14, 15), (0x00, 0x22, 0x23, 0x2B, 0x33, 0x3B, 0x3F),
             (0.25, 0.5, 0.75, 1.25, 2.5, 6.75, 7.5))):
        u, v = window(w, h)
        for m in maxes:
            out.append(case("fields", f"fld-{w}x{h}-max{m}",
                            dict(t0=0x07E00000 | m << 17, t1=t1tw(w, h), u=u, v=v, ins="replace",
                                 lod=const(lod)), st, hyps=CHAINS))
        for b in biases:
            out.append(case("fields", f"fld-{w}x{h}-bias{b:02x}",
                            dict(t0=b << 21 | 0xE << 17, t1=t1tw(w, h), u=u, v=v,
                                 ins="replace", lod=const(lod - 2.0)), st, hyps=CHAINS))
        for lo in blend_lods:
            out.append(case("fields", f"fld-{w}x{h}-mf{int(lo * 100)}",
                            dict(t0=T0_MIP | 1 << 9, t1=t1tw(w, h), u=u, v=v, ins="replace",
                                 lod=const(lo)), st, hyps=CHAINS))
    return out


# ----------------------------------------------------------------------------------- twiddle
def twiddle():
    out = []
    sizes = [(16, 16, "control"), (32, 32, "fit"), (64, 32, "fit"), (64, 16, "fit"),
             (64, 64, "heldout"), (128, 16, "heldout"), (128, 32, "heldout"), (32, 128, "heldout"),
             (128, 128, "heldout"), (16, 64, "heldout"), (8, 128, "heldout")]
    for w, h, st in sizes:
        for yo in range(0, h, 32):
            for xo in range(0, w, 64):
                u, v = window(w, h, xo, yo)
                out.append(case("twiddle", f"twd-{w}x{h}-x{xo}-y{yo}",
                                dict(t0=T0_REP, t1=t1tw(w, h), u=u, v=v, ins="replace", lod=ZERO), st))
    return out


# ----------------------------------------------------------------------------------- lod
LODF = [{"lodf": f} for f in ("max4", "euc", "min", "pwl_max4", "pwl_euc")]
T0_GRAD = T0_MIP | 1 << 9        # a chain, point filters, MIPFILTER: the fraction is the blend
W64 = t1tw(64, 64)


def lod_grad():
    out = []
    u, v = window(64, 64)

    def gx(k, sign=1.0):
        return linx(sign * 2.0 ** (k - 6))

    def gy(k, sign=1.0):
        return liny(sign * 2.0 ** (k - 6))

    for k in range(6):
        out.append(case("lod-grad", f"gr-diag-k{k}", dict(t0=T0_GRAD, t1=W64, u=u, v=v, ins="grad",
                                                          grad=[gx(k), ZERO, ZERO, gx(k)]), "fit", hyps=LODF))
    for k in range(6):
        out.append(case("lod-grad", f"gr-xy-k{k}", dict(t0=T0_GRAD, t1=W64, u=u, v=v, ins="grad",
                                                        grad=[gx(k), ZERO, ZERO, gy(k)]), "fit", hyps=LODF))
    k = 2
    sets = {"swap": [ZERO, gx(k), gx(k), ZERO], "vx": [gx(k), gx(k), ZERO, ZERO],
            "uu": [gx(k), ZERO, gx(k), ZERO], "vv": [ZERO, gx(k), ZERO, gx(k)],
            "all": [gx(k), gx(k), gx(k), gx(k)], "neg": [gx(k), gx(k, -1.0), ZERO, gx(k)],
            "uvy": [gx(k), ZERO, gy(k), ZERO]}
    for nm, g in sets.items():
        out.append(case("lod-grad", f"gr-{nm}-k2", dict(t0=T0_GRAD, t1=W64, u=u, v=v, ins="grad", grad=g),
                        "fit" if nm in ("swap", "vx") else "heldout", hyps=LODF))
    for nm, g in (("vx", [gx(4), gx(4), ZERO, ZERO]), ("all", [gx(4), gx(4), gx(4), gx(4)])):
        out.append(case("lod-grad", f"gr-{nm}-k4", dict(t0=T0_GRAD, t1=W64, u=u, v=v, ins="grad", grad=g),
                        "heldout", hyps=LODF))
    return out


def lod_auto():
    out = []
    pairs = [(1, 0.5), (2, 1), (4, 2), (8, 4), (16, 8), (32, 16), (8, 0.5), (1, 4), (8, 2), (4, 4)]
    for ku, kv in pairs:
        st = "fit" if ku == 2 * kv else "heldout"
        out.append(case("lod-auto", f"au-u{ku}-v{kv}", dict(t0=T0_GRAD, t1=W64, u=linx(float(ku)),
                                                            v=liny(float(kv)), ins="auto"), st, hyps=LODF))
    for nm, uu, vv, st in (("vx", linx(2.0), linx(2.0), "fit"), ("vy", liny(1.0), liny(1.0), "heldout"),
                           ("vx4", linx(4.0), linx(2.0), "heldout")):
        out.append(case("lod-auto", f"au-{nm}", dict(t0=T0_GRAD, t1=W64, u=uu, v=vv, ins="auto"), st, hyps=LODF))
    for ku, kv in ((1, 2), (4, 1), (2, 2), (1, 8)):
        out.append(case("lod-auto", f"au-rot-u{ku}-v{kv}", dict(t0=T0_GRAD, t1=W64, u=liny(float(ku)),
                                                                v=linx(float(kv)), ins="auto"),
                        "heldout", hyps=LODF))
    for b in (0.5, 1.0, -1.0, 2.0):
        out.append(case("lod-auto", f"bi-{int(b * 10)}", dict(t0=T0_GRAD, t1=W64, u=linx(4.0), v=liny(2.0),
                                                              ins="bias", lod=const(b)), "heldout", hyps=LODF))
    for top in (0x3B, 0x37, 0x43):
        out.append(case("lod-auto", f"ab-t{top:02x}", dict(t0=T0_GRAD & ~(0x3F << 21) | top << 21, t1=W64,
                                                          u=linx(4.0), v=liny(2.0), ins="auto"),
                        "heldout", hyps=LODF))
    return out


def afilt():
    out = []
    u, v = window(64, 64)
    T0 = T0_MIP | 1 << 12 | 1 << 10            # bilinear magnification and minification
    for k in (1, 2, 3, 4, 5):
        out.append(case("afilt", f"an-r{k}", dict(t0=T0, t1=W64, u=u, v=v, ins="grad",
                                                  grad=[linx(2.0 ** (k - 6)), ZERO, ZERO, const(2.0 / 64)]),
                        "fit", hyps=[{"lodf": f} for f in ("max4", "euc", "min")]))
    base = dict(t0=T0, t1=W64, u=u, v=v, ins="grad", grad=[linx(2.0 ** -3), ZERO, ZERO, const(2.0 / 64)])
    out.append(case("afilt", "an-ctl", base, "control", hyps=[{"lodf": f} for f in ("max4", "euc", "min")]))
    for b in (27, 30, 14, 15, 16, 28, 29):
        s = dict(base)
        s["t0"] = T0 ^ 1 << b
        out.append(case("afilt", f"an-t0b{b}", s, "explore", hyps=[{"lodf": "max4"}]))
    for b in (8, 9, 11, 12, 15, 20, 21, 22):
        s = dict(base)
        s["t3"] = T3_TW ^ 1 << b
        out.append(case("afilt", f"an-t3b{b}", s, "explore", hyps=[{"lodf": "max4"}]))
    return out


# ----------------------------------------------------------------------------------- border
M47 = [{"mode47": "clamp"}, {"mode47": "nomask"}, {"mode47": "border"}]


def border():
    out = []
    ux = linx(4.0, -5.5 + 1 / 32)            # -1.5 + (x + 0.5) / 16
    vy = liny(4.0, -5.5 + 1 / 16)            # -1.5 + (y + 0.5) / 8
    u01, v01 = linx(1.0, -1.0), liny(1.0, -1.0)     # x / 64 and y / 32
    for m in range(8):
        st = "control" if m < 4 else "explore"
        base = dict(t1=t1tw(16, 16), ins="none")
        out.append(case("border", f"bd-u{m}", dict(base, t0=T0_REP | m << 6 | 2 << 3, u=ux, v=v01), st, hyps=M47))
        out.append(case("border", f"bd-v{m}", dict(base, t0=T0_REP | 2 << 6 | m << 3, u=u01, v=vy), st, hyps=M47))
        out.append(case("border", f"bd-uv{m}", dict(base, t0=T0_REP | m << 6 | m << 3, u=ux, v=vy), st, hyps=M47))
    for m in range(4, 8):
        out.append(case("border", f"bd-hb-u{m}", dict(t1=t1tw(16, 16), ins="none", base=1024,
                                                      t0=T0_REP | m << 6 | 2 << 3, u=ux, v=v01),
                        "heldout", hyps=M47))
        out.append(case("border", f"bd-hb-ns-uv{m}", dict(t1=t1tw(32, 8), ins="none",
                                                          t0=T0_REP | m << 6 | m << 3, u=ux, v=vy),
                        "heldout", hyps=M47))
    for m in (0, 4, 5, 6, 7):
        out.append(case("border", f"bd-st-u{m}", dict(t1=t1tw(64, 32, 12, 6), ins="none", t3=T3_ST,
                                                      t0=t0stride(64, m << 6 | 2 << 3), u=ux, v=v01),
                        "heldout", hyps=M47))
    return out


# ------------------------------------------------------------------------------------- T3 bits
T3H = [{"t3off": "pre", "t3rows": "after"}, {"t3off": "pre", "t3rows": "fixed"},
       {"t3off": "post", "t3rows": "after"}]


def t3bits():
    out = []
    u, v = swin(64, 32)
    st64 = dict(t0=t0stride(64), t1=t1tw(64, 32, 12, 6), u=u, v=v, ins="none", t3=T3_ST)
    bits = list(range(8)) + [8, 9, 10, 11, 12, 14, 18, 20, 21, 22, 27, 28]
    out.append(case("t3bits", "s64x32-ctl", st64, "control", hyps=T3H))
    for b in bits:
        s = dict(st64, t3=T3_ST ^ 1 << b)
        out.append(case("t3bits", f"s64x32-t3b{b}", s, "fit", hyps=T3H))
    for b in (27, 30):
        out.append(case("t3bits", f"s64x32-t0b{b}", dict(st64, t0=t0stride(64) | 1 << b), "fit", hyps=T3H))
    u16, v16 = swin(64, 16)
    s16 = dict(t0=t0stride(64), t1=t1tw(64, 16, 12, 6), u=u16, v=v16, ins="none", t3=T3_ST)
    out.append(case("t3bits", "s64x16-ctl", s16, "control", hyps=T3H))
    for b in (10, 14, 18, 27, 28):
        out.append(case("t3bits", f"s64x16-t3b{b}", dict(s16, t3=T3_ST ^ 1 << b), "heldout", hyps=T3H))
    u32, v32 = swin(32, 32)
    s32 = dict(t0=t0stride(64), t1=t1tw(32, 32, 12, 6), u=u32, v=v32, ins="none", t3=T3_ST)
    for b in (14, 18, 27, 28):
        out.append(case("t3bits", f"s32x32-t3b{b}", dict(s32, t3=T3_ST ^ 1 << b), "heldout", hyps=T3H))
    uw32, vw32 = window(32, 32)
    t32 = dict(t0=T0_REP, t1=t1tw(32, 32), u=uw32, v=vw32, ins="none", t3=T3_TW)
    out.append(case("t3bits", "tw32-ctl", t32, "control", hyps=T3H))
    for b in (0, 4, 10, 14, 18, 27, 28):
        out.append(case("t3bits", f"tw32-t3b{b}", dict(t32, t3=T3_TW ^ 1 << b), "heldout", hyps=T3H))
    return out


def t3vals():
    out = []
    u, v = swin(64, 32)
    st64 = dict(t0=t0stride(64), t1=t1tw(64, 32, 12, 6), u=u, v=v, ins="none")
    vals = [n for n in range(1, 16)] + [n << 4 for n in range(1, 16)]
    rnd = random.Random(1132)
    combos = [rnd.randrange(1, 256) for _ in range(16)]
    for n in vals:
        out.append(case("t3vals", f"sv-{n:02x}", dict(st64, t3=T3_ST | n), "fit", hyps=T3H[:1] + T3H[2:]))
    for n in combos:
        out.append(case("t3vals", f"sc-{n:02x}", dict(st64, t3=T3_ST | n), "fit", hyps=T3H[:1] + T3H[2:]))
    u32, v32 = window(32, 32)
    for mode, vv in ((0, [0x11, 0x2F, 0xF1, 0x8F, 0x79, 0xA5, 0x3C, 0xC3, 0x08, 0x80, 0xFF, 0x01]),
                     (1, [0x11, 0x8F, 0x79, 0xF1, 0x3C, 0xC3]), (2, [0x11, 0x8F, 0x79, 0xF1, 0x3C, 0xC3])):
        for n in vv:
            out.append(case("t3vals", f"tv-m{mode}-{n:02x}",
                            dict(t0=T0_REP | mode << 6 | mode << 3, t1=t1tw(32, 32), u=u32, v=v32, ins="none",
                                 t3=T3_TW | n), "heldout", hyps=T3H[:1] + T3H[2:]))
    return out


def t3risky():
    out = []
    u, v = swin(64, 32)
    st64 = dict(t0=t0stride(64), t1=t1tw(64, 32, 12, 6), u=u, v=v, ins="none")
    for nm, b in (("b19", 1 << 19), ("b13", 1 << 13), ("b18-19", 3 << 18), ("b27-28", 3 << 27),
                  ("b10-14", 1 << 10 | 1 << 14)):
        out.append(case("t3risky", f"r-{nm}", dict(st64, t3=T3_ST ^ b), "explore", risk="risky",
                        hyps=T3H[:1]))
    return out


# ------------------------------------------------------------------------------------- types
def types():
    out = []
    u, v = window(16, 16)
    base = dict(t0=T0_REP, u=u, v=v)
    out.append(case("types", "ty0-2d", dict(base, t1=t1tw(16, 16), ins="none"), "control"))
    for w in (0.0, 0.5, 1.0, 1.5, -0.5, 4.0):
        out.append(case("types", f"ty0-3d-w{int(w * 10)}", dict(base, t1=t1tw(16, 16), ins="3d", w=const(w)),
                        "fit", hyps=[{"w3d": "ignore"}]))
    us, vs = swin(64, 32)
    st = dict(t0=t0stride(64), u=us, v=vs, t3=T3_ST)
    out.append(case("types", "ty6-2d", dict(st, t1=t1tw(64, 32, 12, 6), ins="none"), "control"))
    for w in (0.0, 1.0):
        out.append(case("types", f"ty6-3d-w{int(w * 10)}", dict(st, t1=t1tw(64, 32, 12, 6), ins="3d",
                                                              w=const(w)), "fit", hyps=[{"w3d": "ignore"}]))
    out.append(case("types", "ty3-2d", dict(base, t1=t1tw(16, 16, 12, 3), ins="none"), "explore"))
    for w in (0.0, 1.0):
        out.append(case("types", f"ty3-3d-w{int(w * 10)}", dict(base, t1=t1tw(16, 16, 12, 3), ins="3d",
                                                              w=const(w)), "explore", hyps=[{"w3d": "ignore"}]))
    b3 = dict(base, t1=t1tw(16, 16), ins="3d", w=const(0.625))
    out.append(case("types", "ind-ctl", b3, "control", hyps=[{"w3d": "ignore"}]))
    for b in (10, 14, 18, 27, 28):
        out.append(case("types", f"ind-t3b{b}", dict(b3, t3=T3_TW ^ 1 << b), "explore", hyps=[{"w3d": "ignore"}]))
    for b in (27, 30):
        out.append(case("types", f"ind-t0b{b}", dict(b3, t0=T0_REP ^ 1 << b), "explore", hyps=[{"w3d": "ignore"}]))
    sw = dict(t0=T0_REP, u=u, v=const(0.53125), ins="3d", w=liny(2.0, -2.0))
    for ty in (0, 3):
        out.append(case("types", f"wsw-ty{ty}", dict(sw, t1=t1tw(16, 16, 12, ty)), "explore",
                        hyps=[{"w3d": "ignore"}]))
    out.append(case("types", "wsw-ty6", dict(sw, t0=t0stride(64), t1=t1tw(64, 32, 12, 6), u=us, t3=T3_ST),
                    "explore", hyps=[{"w3d": "ignore"}]))
    return out


def types_risky():
    out = []
    u, v = window(16, 16)
    for ty in (1, 2, 4, 5, 7):
        base = dict(t0=T0_REP, u=u, v=v, t1=t1tw(16, 16, 12, ty))
        out.append(case("types-risky", f"rt{ty}-2d", dict(base, ins="none"), "explore", risk="risky"))
        out.append(case("types-risky", f"rt{ty}-3d-w5", dict(base, ins="3d", w=const(0.5)), "explore", risk="risky"))
        out.append(case("types-risky", f"rt{ty}-3d-w15", dict(base, ins="3d", w=const(1.5)), "explore", risk="risky"))
    return out


# ----------------------------------------------------------------------------------- formats
def stads(words: dict) -> dict:
    return {str(k): v for k, v in words.items()}


def formats_names():
    out = []
    u, v = window(16, 16)
    for f in (23, 24, 25, 26, 27):
        out.append(case("formats-names", f"fn-{f}", dict(t0=T0_REP, t1=t1tw(16, 16, f), u=u, v=v, ins="none"),
                        "explore"))
    us, vs = window(64, 32)
    for f in (28, 29):
        out.append(case("formats-names", f"fn-{f}", dict(t0=T0_REP, t1=t1tw(64, 32, f, 3), u=us, v=vs, ins="none"),
                        "explore"))
    return out


def blocks(kind: str) -> dict:
    base = 0x5A3C9E71
    d = {}
    for i in range(16):
        if kind == "base":
            d[2 * i], d[2 * i + 1] = base, 0
        elif kind == "ordA":
            d[2 * i], d[2 * i + 1] = i * 0x11111111, 0
        elif kind == "ordB":
            d[2 * i], d[2 * i + 1] = ((5 * i + 3) % 16) * 0x11111111, 0
        elif kind == "lo":
            d[2 * i], d[2 * i + 1] = base, 1 << i
        else:
            d[2 * i], d[2 * i + 1] = base, 1 << (16 + i)
    return d


def formats_blocks():
    out = []
    u, v = window(16, 16)
    for f in (23, 24, 27):
        for kind in ("base", "ordA", "ordB", "lo", "hi"):
            out.append(case("formats-blocks", f"fb-{f}-{kind}",
                            dict(t0=T0_REP, t1=t1tw(16, 16, f), u=u, v=v, ins="none", inject=stads(blocks(kind))),
                            "explore"))
    return out


def yuv_words(pat: int) -> dict:
    rnd = random.Random(2800 + pat)
    if pat == 0:
        return {j: (0x20 + 0x18 * j) | (0x70 + 0x0B * j) << 8 | (0x40 + 0x1C * j) << 16 | (0x90 + 0x07 * j) << 24
                for j in range(8)}
    return {j: rnd.getrandbits(32) for j in range(8)}


def formats_yuv():
    out = []
    u, v = mapx(4), const(0.0078125)
    for f in (28, 29):
        for pat in (0, 1):
            for csc in (False, True):
                nm = f"fy-{f}-p{pat}-{'csc' if csc else 'nocsc'}"
                out.append(case("formats-yuv-csc" if csc else "formats-yuv-nocsc", nm,
                                dict(t0=T0_REP, t1=t1tw(16, 1, f, 3), u=u, v=v, ins="none", inject=stads(yuv_words(pat)),
                                     csc=csc), "explore" if pat else "fit"))
    return out


GROUPS = {
    "gate": gate, "shapes": shapes, "fields": fields, "twiddle": twiddle, "lod-grad": lod_grad,
    "lod-auto": lod_auto, "afilt": afilt, "border": border, "t3bits": t3bits, "t3vals": t3vals,
    "t3risky": t3risky, "types": types, "types-risky": types_risky, "formats-names": formats_names,
    "formats-blocks": formats_blocks, "formats-yuv": formats_yuv,
}
