# SPDX-License-Identifier: MIT
"""t3.py: stage t3b (S10-tex, Q078, seeds plan closing10/seeds/exp-seeds-r10.md section 4): T3
bit 14 in smp on named memory (E566's tx_map form, r9-x's gen/t3.py copied and cut to bit 14:
scratch dword i reads 0xD0000000 | i, so every read names its dword).

E975 (r9-x stage t3): the read under bit 14 is the bit-clear dword i plus a number of dwords set by
u alone, clamped to [0, 1]; post hoc floor(4096 clamp(u, 0, 1)) on every pixel of six rows, all
32-bit, strided, u on the 1/64 grid and S * S = 4096 wherever H-U01 held. Frozen here, per pixel,
nothing fitted on the new rows:
  R-4096    i + floor(4096 clamp(u, 0, 1)) dwords (E975's post hoc reading)
  R-4096TX  the same number of texels (= R-4096 on 32-bit texels; on the 16-bit row 2048 dwords)
  R-ROUND   i + floor(4096 clamp(u, 0, 1) + 1/2) (round, not floor)
  H-U01     i + floor(S * S * clamp(u, 0, 1)) (E968/E975's frozen rival, S the stride)
  H-UV      on the v-ramp row: i + floor(4096 clamp(v, 0, 1)) (the moving coordinate) [infer]
  H-URAW    on the clamp row: i + floor(4096 u), unclamped (E975's rival with S * S = 4096)
i is the reference's dword (texmodel, bit 14 clear, rendered by the pinned
texture/p1141/support/texmodel.py; on the 16-bit row the half of dword x >> 1, x & 1 the half
[infer]), measured by each pair's `-ref` row. Every bit-14 row is followed by its reference; the
scorer gates a pair on its reference (a reference off its prediction makes the pair cannot tell).
Controls (can fail): E566's s64x32-ctl and s64x32-t3b14 rerun (their kept images, pinned).
Replicate: E975's b14-u01 (its kept image, pinned, = R-4096). The scratch pages hold every rival's
reads plus a page (16 to 64) and no rival reads below the scratch (the clamp row's texture sits at
dword 2048)."""
import math

import pins
import tex

STAGE = "t3b"
E566 = "data:texture/p1132/tx-t3/%s.txt.gz"
E975_U01 = "data:render/closing-r9-x/out/20261113-081821/t3/b14-u01.txt.gz"
F = tex.F
U64 = tex.lin("x", F(1, 64), F(1, 128))       # u = (x + 0.5) / 64
V32 = tex.lin("y", F(1, 32), F(1, 64))        # v = (y + 0.5) / 32
B14 = 1 << 14
T3W = 0xA0800000
FMT16 = 9                                     # T1 28:24: u16, returned as the half (usse_isa.md)

# name, W, H, S, u, v, base, format: the six held-out geometries (the seeds plan's six pairs)
PAIRS = [
    # S 256 (S * S = 65536), u over [0, 1/4) so that H-U01's reads stay inside 64 pages
    ("t3b-s256", 64, 8, 256, tex.lin("x", F(1, 256), F(1, 512)), V32, 0, 12),
    # S 16, W 16, H 64 (S * S = 256)
    ("t3b-s16h64", 16, 64, 16, U64, V32, 0, 12),
    # u off the 1/128 grid: 4096 u = 64 x + 3/4 (floor 64 x, round 64 x + 1)
    ("t3b-offgrid", 64, 32, 64, tex.lin("x", F(1, 64), F(3, 16384)), V32, 0, 12),
    # u from -0.5 to 1.5: both clamps; the texture at dword 2048 so that H-URAW stays inside
    ("t3b-clamp", 32, 32, 64, tex.lin("x", F(1, 32), F(1, 64) - F(1, 2)), V32, 2048, 12),
    # u fixed at 5/16 (4096 u = 1280), v a ramp
    ("t3b-vramp", 64, 32, 64, tex.lin("x", 0, F(5, 16)), V32, 0, 12),
    # a 16-bit format (u16) at S 64, v on row 0: 4096 dwords against 4096 texels
    ("t3b-f16", 64, 32, 64, U64, tex.lin("y", 0, F(1, 64)), 0, FMT16),
]


def spec(w, h, s, u, v, base, fmt, t3):
    t0, t1, t3 = tex.strided(w, h, s, t3=t3)
    t1 = (t1 & ~(31 << 24)) | fmt << 24
    return dict(base=base, ins="none", t0=t0, t1=t1, t3=t3, u=u, v=v)


def specs():
    import json
    return json.loads(pins.blob(tex.SPECS))


def u_of(sp, x, y):
    return tex.coord(sp["u"], x, y)


def clamp01(q):
    return min(max(q, F(0)), F(1))


def reference(sp):
    """[2048 values] of the bit-clear spec: texmodel's image (32-bit), or on the 16-bit row the
    half of dword x >> 1 named by x & 1 (`h` tokens: the low 16 bits of the read) [infer]."""
    if sp["t1"] >> 24 & 31 == FMT16:
        out = []
        for p in range(2048):
            x, y = p % 64, p // 64
            tx = math.floor(u_of(sp, x, y) * 64)
            out.append(half16(sp["base"], tx))
        return out
    tm = pins.module(tex.TEXMODEL)
    return tm.render(dict(sp, pages=64), {})


def half16(base, texel):
    d = 0xD0000000 | (base + (texel >> 1))
    return (d >> 16 if texel & 1 else d) & 0xFFFF


def models(sp, ref_sp):
    """{model: [2048 values]} for a bit-14 spec from its bit-clear reference's image."""
    name_models = ["R-4096", "R-4096TX", "R-ROUND", "H-U01"]
    s = ((sp["t0"] >> 9 & 7) | (sp["t0"] >> 17 & 0x3FF) << 3) + 1
    vramp = sp["u"][2] == 0                     # u fixed (K = 0)
    clamp = sp["base"] != 0
    if vramp:
        name_models.append("H-UV")
    if clamp:
        name_models.append("H-URAW")
    f16 = sp["t1"] >> 24 & 31 == FMT16
    base = reference(ref_sp)
    out = {m: [] for m in name_models}
    for p, cv in enumerate(base):
        x, y = p % 64, p // 64
        u = u_of(sp, x, y)
        v = tex.coord(sp["v"], x, y)
        off = {"R-4096": math.floor(4096 * clamp01(u)),
               "R-ROUND": math.floor(4096 * clamp01(u) + F(1, 2)),
               "H-U01": math.floor(s * s * clamp01(u)),
               "H-UV": math.floor(4096 * clamp01(v)),
               "H-URAW": math.floor(4096 * u)}
        off["R-4096TX"] = off["R-4096"]
        for m in name_models:
            if f16:
                tx = math.floor(u * 64)
                if m == "R-4096TX":
                    out[m].append(half16(sp["base"], tx + off[m]))
                else:
                    out[m].append(half16(sp["base"] + off[m], tx))
            else:
                out[m].append(0xD0000000 | ((cv & 0x0FFFFFFF) + off[m]))
    return out


def pages(*images, f16=False):
    """The scratch pages that hold every dword the images read, with one page over (16 to 64)."""
    if f16:
        return 16
    idx = [v & 0x0FFFFFFF for im in images for v in im]
    assert min(idx) >= 0
    n = max(16, (max(idx) + 1 + 1023) // 1024 + 1)
    assert n <= 64, max(idx)
    return n


def f16_extent(sp, ims):
    """The largest dword a 16-bit row's rivals read (the generator's page check)."""
    top = 0
    for p in range(2048):
        x, y = p % 64, p // 64
        u = u_of(sp, x, y)
        tx = math.floor(u * 64)
        o = math.floor(4096 * clamp01(u))
        top = max(top, sp["base"] + (tx >> 1) + o, sp["base"] + ((tx + o) >> 1))
    return top


def jobs():
    """[(name, set, knobs, spec, {model: image}, kind, scratch pages)]; kind "dword" or "half"
    (the 16-bit rows: `h` tokens, the low 16 bits)."""
    S = specs()
    out = []
    ctl = pins.kept_pixels(E566 % "s64x32-ctl")
    ref = pins.kept_pixels(E566 % "s64x32-t3b14")
    out.append(("t3b-ctl", "control", "reads:pixels", S["s64x32-ctl"]["spec"], {"H-E566": ctl},
                "dword", pages(ctl)))
    out.append(("t3b-b14ref", "control", "reads:pixels", S["s64x32-t3b14"]["spec"],
                {"H-E566": ref}, "dword", pages(ref)))
    sp = spec(32, 32, 64, U64, V32, 0, 12, T3W | B14)
    m = models(sp, dict(sp, t3=T3W))
    m["H-E975"] = pins.kept_pixels(E975_U01)
    out.append(("t3b-u01", "replicate", "-", sp, m, "dword", pages(*m.values())))
    for name, w, h, s, u, v, base, fmt in PAIRS:
        sp = spec(w, h, s, u, v, base, fmt, T3W | B14)
        rsp = spec(w, h, s, u, v, base, fmt, T3W)
        f16 = fmt == FMT16
        m = models(sp, rsp)
        im = reference(rsp)
        kind = "half" if f16 else "dword"
        if f16:
            assert f16_extent(sp, m) < 15 * 1024
        out.append((name, "heldout", "-", sp, m, kind, pages(*m.values(), f16=f16)))
        out.append((name + "-ref", "reference", "-", rsp, {"H-TEXMODEL": im}, kind,
                    pages(im, f16=f16)))
    return out
