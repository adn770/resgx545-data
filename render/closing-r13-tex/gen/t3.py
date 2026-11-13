# SPDX-License-Identifier: MIT
"""t3.py: stage t3c (r13-tex, Q078 bits 11, 12 and 14; closing13/plan/rank-round13.md section 2
"t3c", from closing11 c8's list, resgx545-data cited/closing11/plan/c8-q078/NOTE.md).

Twiddled chains on the counting fill (dword i = 0xD0000000 | i: every texel names itself), the
p1132 tx-aniso form of E564 (u, v on level 0's texel centres, `map` coordinates; T0 0x07fc1400:
top 0x3f, max level 14, nearest level, bilinear), with smp2dreplace (the LOD a constant) in place
of E564's gradient. The image of a level is the published 11.32 sampler model's (texmodel.py,
pinned) only for the coordinates and the bilinear blend: the address is E561's tile law
(gen/addr.py's index; texmodel's plain Morton order differs above 16 a side) over E722's chain
offsets (tests/test_gen.py: level 0 is E564's an-t3b11 2048 of 2048, levels 3 and 4 E564's an-ctl
within 1). Level 0 at texel centres is a name (exact `XXXXXXXX` tokens), a higher level is a blend
(`t:` tokens, each byte within 1, as r10-tex's cube3 edges).

Frozen (c8 fitted its B11-LEVEL0 / B12-LAST post hoc on E564's two jobs; nothing here has run):
  bits 12:11, H-LODMODE [infer, c8]: 00 level 0, 01 the LOD's level (the normal path), 11 the
  last level; 10 is not frozen, each rival's reading is (AS-00, AS-01, AS-11).
  bit 11 clear (00):  B11-LEVEL0 (H-LODMODE), B11-NORMAL (bit 11 changes nothing: the LOD's
                      level), B11-BIAS (the LOD less 3.5, c8's least bias that fits E564)
  bit 12 set (11):    B12-CAPLVL (H-LODMODE's last level as T0's max level caps it), B12-CHAINLAST
                      (the chain's 1 x 1 level whatever T0 says), B12-ADDR (the constant dword
                      5460, E564's 64 x 64 chain's last), B12-BIAS (the LOD plus 2.5, capped),
                      B12-NORMAL (bit 12 changes nothing)
  bit 14 bilinear (strided 64 x 32, stride 64, E1003's move floor(4096 clamp(u, 0, 1)) texels):
                      H-FOOT (every tap moved by the sample's u) against H-TAP (each tap moved by
                      its own texel centre's u); the row is followed by its bit-clear reference
                      (H-BILIN: the four taps blended, each byte within 1), which gates it.
Control that can fail: E564's an-t3b11 rerun (its kept image; r9-x replicated it byte for byte)."""
import json
import math

import addr as A
import pins
import tex

STAGE = "t3c"
E564 = "data:texture/p1132/tx-lod/%s.txt.gz"
T0 = 0x07FC1400                  # E564's an-ctl: top 0x3f, max level 14, nearest level, bilinear
T1_64 = 0x0C03F03F               # twiddled 64 x 64, format 12
T1_32 = 0x0C01F01F               # twiddled 32 x 32
T3_CTL = 0x00800800              # bits 12:11 = 01 (E564's control)
T3_B11 = 0x00800000              # 00
T3_B12 = 0x00801800              # 11
T3_10 = 0x00801000               # 10
ADDR_LAST64 = 5460
MAP64 = (["map", "x", 6, 0, 0x3F800000], ["map", "y", 6, 0, 0x3F800000])
MAP32 = (["map", "x", 5, 0, 0x3F800000], ["map", "y", 5, 0, 0x3F800000])
B14 = 1 << 14


def _bits(v):
    import struct
    return struct.unpack("<I", struct.pack("<f", float(v)))[0]


def rspec(t1, t3, lod, mx=14, top=0x3F, coords=MAP64):
    t0 = (T0 & ~(0x3F << 21) & ~(15 << 17)) | top << 21 | mx << 17
    return dict(base=0, ins="replace", t0=t0, t1=t1, t3=t3, u=coords[0], v=coords[1],
                lod=["bits", _bits(lod)])


def level_image(sp, level, mx=None):
    """The image of the spec read at `level` of its chain: E561's tile law (addr.index, tiles of
    16 x 16; texmodel's plain Morton order differs above 16 a side, so it is not used for the
    address), the chain's levels one after another (E722's offsets), address mode 0 (repeat),
    texmodel's bilinear blend (the T0 filters of every row are bilinear), the coordinates
    texmodel's ev() of the spec. mx is unused (the level is given)."""
    tm = pins.module(tex.TEXMODEL)
    side = (sp["t1"] >> 12 & 0xFFF) + 1
    n, off = side >> level, sum((side >> i) ** 2 for i in range(level))
    out = []
    for y in range(32):
        for x in range(64):
            u, v = tm.ev(sp["u"], x, y), tm.ev(sp["v"], x, y)
            fx, fy = u * n - 0.5, v * n - 0.5
            x0, y0 = math.floor(fx), math.floor(fy)
            kx, ky = int((fx - x0) * 64), int((fy - y0) * 64)
            t = [0xD0000000 | (off + A.index((x0 + dx) % n, (y0 + dy) % n, n, n))
                 for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))]
            out.append(blend(t, kx, ky))
    return out


def const_image(dword):
    return [0xD0000000 | dword] * 2048


def tokens(img, names):
    """Exact tokens where the image is a name of the scratch (texel centres at one texel),
    `t:` byte tokens elsewhere."""
    out = []
    for v, nm in zip(img, names):
        out.append("%08x" % v if nm else "t:" + ",".join(str(v >> 8 * c & 255) for c in range(4)))
    return out


def is_name(level, sp):
    """Level 0 on its texel centres reads one texel (a name); a 1 x 1 level too."""
    side = (sp["t1"] >> 12 & 0xFFF) + 1
    return level == 0 or side >> level <= 1


def cap(sp):
    side = (sp["t1"] >> 12 & 0xFFF) + 1
    return min(sp["t0"] >> 17 & 15, side.bit_length() - 1)


def last(sp):
    return ((sp["t1"] >> 12 & 0xFFF) + 1).bit_length() - 1


def nearest(le, sp):
    """The nearest level of LOD le (T0 bit 9 clear), capped; level 0 with mips off (T0's top
    field 0, texmodel's sample)."""
    if sp["t0"] >> 21 & 0x3F == 0:
        return 0
    return max(0, min(math.floor(le + 0.5), cap(sp)))


def lod_models(sp, lod, kind):
    """{model: (level or ("addr", dword), tokens)} of a bit-11 / bit-12 / 10 row."""
    L = float(lod)
    m = {}
    if kind == "b11":
        m = {"B11-LEVEL0": 0, "B11-NORMAL": nearest(L, sp), "B11-BIAS": nearest(L - 3.5, sp)}
    elif kind == "b12":
        m = {"B12-CAPLVL": cap(sp), "B12-CHAINLAST": ("chain", last(sp)),
             "B12-ADDR": ("addr", ADDR_LAST64), "B12-BIAS": nearest(L + 2.5, sp),
             "B12-NORMAL": nearest(L, sp)}
    elif kind == "10":
        m = {"AS-00": 0, "AS-01": nearest(L, sp), "AS-11": cap(sp)}
    out = {}
    for name, lv in m.items():
        if isinstance(lv, tuple) and lv[0] == "addr":
            img, names = const_image(lv[1]), [True] * 2048
        elif isinstance(lv, tuple):
            img, names = level_image(sp, lv[1], mx=14), [True] * 2048
        else:
            img, names = level_image(sp, lv), [is_name(lv, sp)] * 2048
        out[name] = tokens(img, names)
    return out


# ---- bit 14 under a bilinear sample on a strided texture -------------------------------------
B14_W, B14_H, B14_S = 64, 32, 64
B14_T0 = 0x00001400               # bilinear (bits 12, 10), the stride from tex.strided
B14_U = tex.lin("x", tex.F(1, 64), tex.F(3, 256))      # u = (x + 3/4) / 64: kx 16
B14_V = tex.lin("y", tex.F(1, 32), tex.F(3, 128))      # v = (y + 3/4) / 32: ky 16


def b14_spec(t3):
    t0, t1, _ = tex.strided(B14_W, B14_H, B14_S, t0=B14_T0)
    return dict(base=0, ins="none", t0=t0, t1=t1, t3=t3, u=B14_U, v=B14_V)


def blend(t, kx, ky):
    """texmodel's bilinear on four dwords (00, 10, 01, 11), weights in 64ths."""
    wt = [(64 - kx) * (64 - ky), kx * (64 - ky), (64 - kx) * ky, kx * ky]
    out = 0
    for c in range(4):
        s = sum((t[k] >> (8 * c) & 255) * wt[k] for k in range(4))
        out |= ((s + 2048) >> 12) << (8 * c)
    return out


def b14_image(model):
    out = []
    for p in range(2048):
        x, y = p % 64, p // 64
        u = tex.coord(B14_U, x, y)
        v = tex.coord(B14_V, x, y)
        fx, fy = u * B14_W - tex.F(1, 2), v * B14_H - tex.F(1, 2)
        x0, y0 = math.floor(fx), math.floor(fy)
        kx, ky = 64 * (fx - x0), 64 * (fy - y0)
        assert kx.denominator == 1 and ky.denominator == 1
        t = []
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            cx = min(max(x0 + dx, 0), B14_W - 1)
            cy = min(max(y0 + dy, 0), B14_H - 1)
            i = cy * B14_S + cx
            if model == "H-FOOT":
                i += math.floor(4096 * min(max(u, 0), 1))
            elif model == "H-TAP":
                i += math.floor(4096 * min(max(tex.F(2 * cx + 1, 2 * B14_W), 0), 1))
            t.append(0xD0000000 | i)
        out.append(blend(t, int(kx), int(ky)))
    return out


def b14_tokens(img):
    return ["t:" + ",".join(str(v >> 8 * c & 255) for c in range(4)) for v in img]


def pages(top_dword):
    n = max(16, (top_dword + 1 + 1023) // 1024 + 1)
    assert n <= 64
    return n


# name, set, spec, kind
def rows():
    r = [("t3c-b11-l%d" % L, rspec(T1_64, T3_B11, L), L, "b11") for L in range(7)]
    r += [("t3c-b12-m3", rspec(T1_64, T3_B12, 0, mx=3), 0, "b12"),
          ("t3c-b12-m5", rspec(T1_64, T3_B12, 0, mx=5), 0, "b12"),
          ("t3c-b10", rspec(T1_64, T3_10, 2), 2, "10"),
          ("t3c-b11-32", rspec(T1_32, T3_B11, 3, coords=MAP32), 3, "b11"),
          ("t3c-b12-32", rspec(T1_32, T3_B12, 0, coords=MAP32), 0, "b12"),
          ("t3c-b11-nomip", rspec(T1_64, T3_B11, 3, top=0), 3, "b11")]
    return r


def jobs():
    """[(name, set, knobs, spec, {model: tokens}, scratch pages)] in run order."""
    specs = json.loads(pins.blob(tex.SPECS))
    out = [("t3c-ctl", "control", "reads:pixels", specs["an-t3b11"]["spec"],
            {"H-E564": ["%08x" % v for v in pins.kept_pixels(E564 % "an-t3b11")]}, None)]
    for name, sp, lod, kind in rows():
        out.append((name, "heldout", "-", sp, lod_models(sp, lod, kind), None))
    sp = b14_spec(0xA0800000 | B14)
    m = {k: b14_image(k) for k in ("H-FOOT", "H-TAP")}
    out.append(("t3c-b14bl", "heldout", "-", sp, {k: b14_tokens(v) for k, v in m.items()},
                pages(B14_H * B14_S + 4096 + B14_S)))
    ref = b14_image("REF")
    out.append(("t3c-b14bl-ref", "reference", "-", b14_spec(0xA0800000),
                {"H-BILIN": b14_tokens(ref)}, None))
    return out
