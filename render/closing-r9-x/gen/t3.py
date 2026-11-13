# SPDX-License-Identifier: MIT
"""t3.py: stage t3 (R9-A, Q078): T3 bits 14, 11 and 12 in smp on named memory (E566's tx_map form:
scratch dword i reads 0xD0000000 | i, so every read names its dword).

Bit 14 (findings 1 of rank-round9.md, E968 offline): on E566's three kept jobs the read is the
control's dword i plus a whole number of stride rows per unit of u; post hoc, R-U (the row moves by
u * S, u the control column's centre) fits every in-range pixel, R-U01 (u clamped to [0, 1]) also
the pixels past the texture. Frozen here, per pixel, three rivals that the new geometries separate
(u off the texel centres, W != S, W not a power of two, u past the texture), each held-out row
followed by its reference (the same geometry with bit 14 clear, frozen as texmodel's image: the
dword i every rival adds to, measured):
  H-UCOL  i + floor(S * S * (2c + 1) / (2W)), c = the control's column (clamped to the texture)
  H-U01   i + floor(S * S * min(max(u, 0), 1)), u the pixel's raw coordinate
  H-URAW  i + floor(S * S * u)
i is the control's dword (texmodel, bit 14 clear), S the stride, W the width. Controls (can fail):
E566's s64x32-ctl and s64x32-t3b14 rerun (their kept images, pinned). Bits 11 and 12: E566's
strided 64 x 32 jobs rerun (frozen: the control's image, E566 saw no change) and E564's twiddled
64 x 64 chain (an-ctl a control, an-t3b11 and an-t3b12 E564's kept images as replicates; their
read-out is a reading table). The scratch extent of every rival is below the mapped pages
(--scratch-pages, 16 to 64): the plan's check 3."""
import math

import pins
import tex

STAGE = "t3"
E566 = "data:texture/p1132/tx-t3/%s.txt.gz"
E564 = "data:texture/p1132/tx-lod/%s.txt.gz"
U64 = tex.lin("x", tex.F(1, 64), tex.F(1, 128))      # u = (x + 0.5) / 64
U32 = tex.lin("x", tex.F(1, 32), tex.F(1, 64))       # u = (x + 0.5) / 32
V32 = tex.lin("y", tex.F(1, 32), tex.F(1, 64))       # v = (y + 0.5) / 32
B14 = 1 << 14
MODELS = ("H-UCOL", "H-U01", "H-URAW")

# name, set, W, H, S, u: the held-out bit 14 geometries (rank-round9.md R9-A)
B14ROWS = [
    ("b14-w16s64", 16, 32, 64, U64),     # W < S, u off the texel centres
    ("b14-w32s128", 32, 16, 128, U64),   # S = 4 W, H 16
    ("b14-w32s32", 32, 32, 32, U64),     # W = S (the multipliers agree), u off the centres
    ("b14-w48s64", 48, 32, 64, U64),     # W not a power of two
    ("b14-u01", 32, 32, 64, U64),        # u over [0, 1): no pixel past the texture
    ("b14-u02w16", 16, 32, 64, U32),     # u over [0, 2): half the pixels past the texture
]


def spec(w, h, s, u, t3):
    t0, t1, t3 = tex.strided(w, h, s, t3=t3)
    return dict(base=0, ins="none", t0=t0, t1=t1, t3=t3, u=u, v=V32)


def specs():
    import json
    return json.loads(pins.blob(tex.SPECS))


def models(sp):
    """{model: [2048 dwords]} for a bit-14 spec, from the control render of the same spec with bit
    14 clear."""
    tm = pins.module(tex.TEXMODEL)
    ctl = dict(sp, t3=sp["t3"] & ~B14)
    t = tm.Tex(ctl["t0"], ctl["t1"], 0, ctl["t3"], 16, dict(tm.RULES))
    w = t.w
    s = ((ctl["t0"] >> 9 & 7) | (ctl["t0"] >> 17 & 0x3FF) << 3) + 1
    base = tm.render(ctl, {})
    out = {m: [] for m in MODELS}
    for p, cv in enumerate(base):
        x, y = p % 64, p // 64
        i = cv & 0x0FFFFFFF
        c = i % s
        u = tex.coord(sp["u"], x, y)
        out["H-UCOL"].append(0xD0000000 | (i + s * s * (2 * c + 1) // (2 * w)))
        out["H-U01"].append(0xD0000000 | (i + math.floor(s * s * min(max(u, 0), 1))))
        out["H-URAW"].append(0xD0000000 | (i + math.floor(s * s * u)))
    return out, w, s


def pages(*images):
    """The scratch pages that hold every dword the images read, with one page over (16 to 64)."""
    top = max(v & 0x0FFFFFFF for im in images for v in im)
    n = max(16, (top + 1 + 1023) // 1024 + 1)
    assert n <= 64, top
    return n


def jobs():
    """[(name, set, knobs, spec, {model: image} or None, extra predictions, scratch pages)]"""
    S = specs()
    out = []
    ctl = pins.kept_pixels(E566 % "s64x32-ctl")
    ref = pins.kept_pixels(E566 % "s64x32-t3b14")
    out.append(("t3-ctl", "control", "reads:pixels", S["s64x32-ctl"]["spec"], {"H-E566": ctl},
                {}, pages(ctl)))
    out.append(("t3-b14ref", "control", "reads:pixels", S["s64x32-t3b14"]["spec"],
                {"H-E566": ref}, {}, pages(ref)))
    tm = pins.module(tex.TEXMODEL)
    for name, w, h, s, u in B14ROWS:
        sp = spec(w, h, s, u, 0xA0800000 | B14)
        m, _, _ = models(sp)
        out.append((name, "heldout", "-", sp, m, {}, pages(*m.values())))
        ref = spec(w, h, s, u, 0xA0800000)
        im = tm.render(ref, {})
        out.append((name + "-ref", "reference", "-", ref, {"H-TEXMODEL": im}, {}, pages(im)))
    for b in (11, 12):
        sp = S[f"s64x32-t3b{b}"]["spec"]
        out.append((f"b{b}-s64x32", "replicate", "-", sp, {"H-CTL": ctl}, {}, pages(ctl)))
    for n, st in (("an-ctl", "control"), ("an-t3b11", "replicate"), ("an-t3b12", "replicate")):
        im = pins.kept_pixels(E564 % n)
        extra = {"distinct": {"H-E564": str(len(set(im)))}}
        out.append((n, st, "reads:pixels" if st == "control" else "-", S[n]["spec"],
                    {"H-E564": im}, extra, None))
    return out
