# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""The texture jobs of p1141/tex: every case a spec (p1132's catalog vocabulary), a set, a risk and the
hypotheses whose images are frozen by hash. Predictions come from recompute/tex2.py (my model, written
for this check); the programs from p1132's gen/build.py. Nothing here reads a result."""
from __future__ import annotations

import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
P1132 = pathlib.Path.home() / "src/sgxhumation/debug/wt-phase10/debug/phase11/p1132"
sys.path.insert(0, str(P1132 / "gen"))
sys.path.insert(0, str(HERE.parent / "recompute"))
import catalog as cc  # noqa: E402
from catalog import ZERO, const, linx, liny, mapx, mapy, swin, window, t1tw, t0stride  # noqa: E402

T0_GRAD, W64 = cc.T0_GRAD, cc.W64
T3_TW, T3_ST = cc.T3_TW, cc.T3_ST
FOOT = ["P", "O", "Mp", "Mo", "F", "S"]
MENU = {"Z": ZERO}
for _j in (6, 7, 8, 9):
    MENU[f"x{_j}"], MENU[f"y{_j}"], MENU[f"c{_j}"] = linx(2.0 ** -_j), liny(2.0 ** -_j), const(2.0 ** -_j)


def H(label, rules=None, **opts):
    return (label, rules or {}, opts)


def case(script, group, name, spec, st, risk="safe", hyps=None, tmpl="tx_map.s", label=""):
    spec = dict(spec)
    spec.setdefault("base", 0)
    spec.setdefault("t3", T3_TW)
    if "inject" in spec:
        spec["inject"] = {str(k): v for k, v in spec["inject"].items()}
    return dict(script=script, group=group, name=name, spec=spec, set=st, risk=risk, hyps=hyps or [],
                tmpl=tmpl, label=label or name, kind="probe")


# ------------------------------------------------------------------------------------ tex-a-lod
def lodg():
    out = []
    hy = [H(f"foot={f}", {"lodf": "euc"}, foot=f) for f in FOOT]
    sq = [("lg-sq1", ["x8", "x7", "c6", "c6"]), ("lg-sq2", ["y6", "x7", "y6", "x9"]),
          ("lg-sq3", ["x6", "c6", "c7", "y8"]), ("lg-sq4", ["c7", "y7", "y8", "y6"])]
    ns = [("lg-ns1", ["x8", "x7", "c7", "y6"]), ("lg-ns2", ["c8", "x7", "x6", "x6"]),
          ("lg-ns3", ["c7", "c6", "x6", "x6"]), ("lg-ns4", ["y8", "c6", "c7", "c6"])]
    for nm, ops in sq:
        u, v = window(64, 64)
        out.append(case("tex-a-lod", "lodg", nm, dict(t0=T0_GRAD, t1=W64, u=u, v=v, ins="grad",
                                                      grad=[MENU[o] for o in ops]), "heldout", hyps=hy))
    for nm, ops in ns:
        u, v = window(128, 32)
        out.append(case("tex-a-lod", "lodg", nm, dict(t0=T0_GRAD, t1=t1tw(128, 32), u=u, v=v, ins="grad",
                                                      grad=[MENU[o] for o in ops]), "heldout", hyps=hy))
    # fine ladders: one operand, rho from r0 to r0 * 1.0615 over the 64 columns (a column is ~0.09 of
    # a 1/64 step of LOD): where the fraction changes, truncation and rounding place it differently
    hf = [H("frac=trunc", {"lodf": "euc"}, foot="P", frac="trunc"),
          H("frac=round", {"lodf": "euc"}, foot="P", frac="round")]
    for r0 in (2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0):
        K = r0 / 64 / 16
        C = r0 / 64 - K
        u, v = window(64, 64)
        out.append(case("tex-a-lod", "lodg", f"lf-r{int(r0)}", dict(
            t0=T0_GRAD, t1=W64, u=u, v=v, ins="grad", grad=[("lin", "x", cc.fbits(K), cc.fbits(C)), ZERO, ZERO, ZERO]),
            "heldout", hyps=hf))
    return out


# ---------------------------------------------------------------------------------- tex-b-bilin
def rnd_dwords(seed, n):
    r = random.Random(seed)
    return {i: r.getrandbits(32) for i in range(n)}


def bilin():
    out = []
    hy = [H("joint", {}, two_stage=False), H("two-stage xy", {}, two_stage=True, order="xy"),
          H("two-stage yx", {}, two_stage=True, order="yx"),
          H("two-stage xy floor", {}, two_stage=True, order="xy", rnd="floor")]
    u = linx(0.125, 0.25)
    for seed in (11, 12, 13):
        for half, cy in (("lo", 0.3125), ("hi", 0.375)):
            out.append(case("tex-b-bilin", "bilin", f"bl-st{seed}-{half}", dict(
                t0=t0stride(8, 1 << 12 | 1 << 10), t1=t1tw(8, 8, 12, 6), t3=T3_ST, u=u, v=liny(0.0625, cy),
                ins="none", inject=rnd_dwords(seed, 64)), "heldout", hyps=hy))
    for seed in (14, 15):
        out.append(case("tex-b-bilin", "bilin", f"bl-tw{seed}-lo", dict(
            t0=cc.T0_REP | 1 << 12 | 1 << 10, t1=t1tw(8, 8), u=u, v=liny(0.0625, 0.3125), ins="none",
            inject=rnd_dwords(seed, 64)), "heldout", hyps=hy))
    return out


# ----------------------------------------------------------------------------------- tex-c-addr
def addr():
    out = []
    hy = [H("A4", {"t3off": "pre"}, t3model=True),
          H("A4 stride chain", {"t3off": "pre"}, t3model=True, t3chain="stride"),
          H("A4 shift idx only", {"t3off": "pre"}, t3model=True, t3e="idx")]

    def tw(w, h):
        u, v = window(w, h)
        return dict(t0=cc.T0_REP, t1=t1tw(w, h), u=u, v=v, ins="none")

    def st(w, h):
        u, v = swin(w, h)
        return dict(t0=t0stride(w), t1=t1tw(w, h, 12, 6), u=u, v=v, ins="none")

    def t3(L=0, e=0, b10=0, tw_=True):
        return (T3_TW if tw_ else T3_ST) | L << 27 | e << 18 | b10 << 10

    rows = [("tw64x64", tw(64, 64), True, [(1, 0, 0), (2, 0, 0), (3, 0, 0), (1, 1, 0), (2, 2, 0), (3, 3, 0), (0, 0, 1)]),
            ("tw32x64", tw(32, 64), True, [(1, 0, 0), (2, 1, 0)]),
            ("tw128x32", tw(128, 32), True, [(1, 0, 0), (0, 2, 0)]),
            ("st128x32", st(128, 32), False, [(1, 0, 0), (2, 1, 0), (3, 2, 0), (0, 0, 1)]),
            ("st32x64", st(32, 64), False, [(1, 0, 0)])]
    for nm, sp, is_tw, combos in rows:
        for L, e, b10 in combos:
            out.append(case("tex-c-addr", "addr", f"ad-{nm}-L{L}e{e}" + ("b10" if b10 else ""),
                            dict(sp, t3=t3(L, e, b10, is_tw)), "heldout", hyps=hy))
    return out


# ----------------------------------------------------------------------------------- tex-d-t0b27
def strat(seed, n):
    """n dwords whose bytes 0 and 1 are stratified over 0..255 and bytes 2, 3 random."""
    r = random.Random(seed)
    b0 = [8 * i + r.randrange(8) for i in range(n)] if n == 32 else [4 * i + r.randrange(4) for i in range(n)]
    b1 = b0[::-1]
    r.shuffle(b1)
    return {i: b0[i] | b1[i] << 8 | r.getrandbits(16) << 16 for i in range(n)}


def t0b27():
    out = []
    hy = [H("srgb to half", {}, srgb=True)]
    u8x4, v8x4 = swin(8, 4)
    st84 = dict(t0=t0stride(8) | 1 << 27, t1=t1tw(8, 4, 12, 6), t3=T3_ST, u=u8x4, v=v8x4, ins="none",
                inject=strat(21, 32))
    uw, vw = window(8, 8)
    tw88 = dict(t0=cc.T0_REP | 1 << 27, t1=t1tw(8, 8), u=uw, v=vw, ins="none", inject=strat(22, 64))
    u32, v32 = window(32, 32)
    tw32 = dict(t0=cc.T0_REP | 1 << 27, t1=t1tw(32, 32), u=u32, v=v32, ins="none")
    out.append(case("tex-d-t0b27", "t0b27", "g-st8x4", st84, "heldout", hyps=hy))
    out.append(case("tex-d-t0b27", "t0b27", "g-tw8x8", tw88, "heldout", hyps=hy))
    out.append(case("tex-d-t0b27", "t0b27", "g-tw32x32", tw32, "heldout", hyps=hy))
    out.append(case("tex-d-t0b27", "t0b27", "g-tw8x8-s2", dict(tw88, inject=strat(23, 64)), "heldout", hyps=hy))
    out.append(case("tex-d-t0b27", "t0b27", "g-st8x4-r11", st84, "explore", tmpl="tx_map_r11.s"))
    out.append(case("tex-d-t0b27", "t0b27", "g-tw8x8-r11", tw88, "explore", tmpl="tx_map_r11.s"))
    ub = linx(0.125, 0.25)
    hb = [H("filter then decode", {}, srgb=True, two_stage=True), H("decode then filter", {}, srgb=True, srgb_pre=True)]
    bl = dict(t0=t0stride(8, 1 << 12 | 1 << 10) | 1 << 27, t1=t1tw(8, 8, 12, 6), t3=T3_ST, u=ub,
              v=liny(0.0625, 0.3125), ins="none")
    out.append(case("tex-d-t0b27", "t0b27", "g-bl-st-a", dict(bl, inject=strat(24, 64)), "heldout", hyps=hb))
    out.append(case("tex-d-t0b27", "t0b27", "g-bl-st-b", dict(bl, inject=strat(25, 64)), "heldout", hyps=hb))
    return out


# ------------------------------------------------------------------------------------ tex-e-etc1
def etc_blocks(seed, nblocks):
    """valid ETC1 blocks (random, differential ones kept inside 0..31), two dwords each."""
    r = random.Random(seed)
    d = {}
    for b in range(nblocks):
        hi, lo = r.getrandbits(32), r.getrandbits(32)
        if hi >> 1 & 1:
            for sh in (27, 19, 11):
                base = hi >> sh & 31
                dd = hi >> (sh - 3) & 7
                dd = dd if dd < 4 else dd - 8
                if not 0 <= base + dd < 32:
                    hi = hi & ~(7 << (sh - 3)) | 0 << (sh - 3)
        d[2 * b], d[2 * b + 1] = hi, lo
    return d


def etc1():
    out = []
    hy = [H("morton y-low", {}, etc1=True, etc_order="morton"), H("raster", {}, etc1=True, etc_order="raster"),
          H("morton x-low", {}, etc1=True, etc_order="mortonx")]
    for nm, w, h, seed in (("e16a", 16, 16, 31), ("e16b", 16, 16, 32), ("e32x16", 32, 16, 33),
                           ("e16x32", 16, 32, 34), ("e8x16", 8, 16, 35), ("e8x8", 8, 8, 36)):
        u, v = window(w, h)
        out.append(case("tex-e-etc1", "etc1", nm, dict(
            t0=cc.T0_REP, t1=t1tw(w, h, 27), u=u, v=v, ins="none", inject=etc_blocks(seed, (w // 4) * (h // 4))),
            "heldout", hyps=hy))
    return out


# ---------------------------------------------------------------------------------------- types
def types_pred(ty, w, h):
    """pixel (x, y) of the 64 x 32 fill -> dword, per hypothesis (a function of the 2D window)."""
    def mk(f):
        return [0xD0000000 | f(x % w, y % h) for y in range(32) for x in range(64)]
    s = 2 if ty == 4 else 1
    return {"fixed 16": mk(lambda x, y: (y % 16) * 16 * s + x % 16),
            "raster w": mk(lambda x, y: y * w * s + x),
            "raster 16 wrap": mk(lambda x, y: (y % 16) * 16 * s + x % 16) if False else
            [0xD0000000 | ((y % h) % 16 * w * s + (x % w) % 16) for y in range(32) for x in range(64)]}


def types(script, tys, risk):
    out = []
    for ty in tys:
        for w, h in ((8, 8), (32, 32), (32, 16), (16, 32)):
            u, v = window(w, h)
            c = case(script, "types", f"ty{ty}-{w}x{h}", dict(t0=cc.T0_REP, t1=t1tw(w, h, 12, ty), u=u, v=v, ins="none"),
                     "heldout", risk=risk)
            c["pred_pixels"] = types_pred(ty, w, h)
            out.append(c)
    return out


def cube():
    out = []
    a, b = cc.linx(1.5, -2.25), cc.liny(1.5, -2.25)
    base = dict(t0=cc.T0_REP, t1=t1tw(16, 16, 12, 2), t3=T3_TW, ins="3d")
    for sign, nm in ((1.0, "p"), (-1.0, "n")):
        k = const(sign)
        for axis, (u, v, w) in {"z": (a, b, k), "x": (k, a, b), "y": (a, k, b)}.items():
            out.append(case("tex-h-cube", "cube", f"cu-{axis}{nm}", dict(base, u=u, v=v, w=w), "explore", risk="risky"))
    uu = mapx(4)
    for nm, w in (("w02", liny(2.0, -2.0)), ("w11", liny(2.0, -3.0))):
        out.append(case("tex-h-cube", "cube", f"cu-{nm}", dict(base, u=uu, v=const(0.53125), w=w), "explore", risk="risky"))
    return out


def all_texture():
    return (lodg() + bilin() + addr() + t0b27() + etc1() + types("tex-f-types", (3,), "safe")
            + types("tex-g-types-risky", (1, 4), "risky") + cube())
