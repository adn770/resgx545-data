# SPDX-License-Identifier: MIT
"""z2.py: r9-z2's one stage (ranking plan R9c-F / X-3, Q101): what bit 19 of CR_ISP_ZLSCTL (the
negated stored depth, E466/E490) does with the integer formats 1 and 2 when the depth is negative.

How a negative depth reaches the store. The tool's --tri-z sets the clip z 2t - 1 of each vertex;
the MTE clips at clip z = -w and w (E287), so a vertex depth below 0 (t9's wider --tri-z, -1 to 2)
only cuts the triangle where its clip z passes -1: no pixel of negative depth is drawn that way. The
viewport's z offset comes after the clip and is not clipped (E287: offsets -0.5 to 1.5 draw whole;
3d.md: state-block words 10 and 11 are the viewport's z offset and z scale, E797), so the rows
keep --tri-z in [0, 1] and set the offset with --poke blk:10: depth = offset + 0.5 (2t - 1). A
negative depth compares as 0 (E287 [infer]), so it passes less against the clear depth 1.0.

Rows (256 x 128, G 7, E466's store control 0x0017110c with G 7, depth less with depth written,
ISP word 0 0x00400200 as E466): the triangle (0,0) (2W,0) (0,2H) at depths 0, 1, 0, so t = x / 512
over the target, with two offsets:
  A  offset +0.25: depth -0.25 + t, from -0.25 to +0.25 (crosses 0: the positive half is E490's)
  B  offset -0.25: depth -0.75 + t, from -0.75 to -0.25 (all negative)
each in format 0 (the reference and the control: every dword of the 64 tiles leaves the fill,
E831) and in formats 1 and 2 without and with bit 19 (8 rows). Frozen per dword, from the format-0
reference's float z of the same ramp (score.py applies them; enc is round(z * 0xffffff), E466,
and its >> 8 for format 2 in E490's layout):
  H-ABS    enc(|z|), bit 19 or not
  H-CLAMP  enc(max(z, 0)), bit 19 or not
  H-WRAP   floor(z * 0xffffff + 0.5) in 24-bit two's complement (>> 8 for format 2), bit 19 or not
  H-B19    bit 19 clear: enc(max(z, 0)); set: enc(|z|) (bit 19 matters only below 0)
E490 (bit 19 changes nothing over a positive ramp) holds in all four. If the reference stores
negative depths as 0 (or clamps them), the rivals collapse onto it: a reading, stated in the fold."""
STAGE = "z2"
MAIN = "tri --keep-going --wait-ms 20000"
W, H, G = 256, 128, 7
STORE = 0x00171004 | G << 3
LESS = 0x00400200
FILL = 0xDEADBEEF
B19 = 1 << 19
RAMPS = [("a", 0x3E800000), ("b", 0xBE800000)]     # z offset +0.25, -0.25 (float32 bits)
MODELS = ("H-ABS", "H-CLAMP", "H-WRAP", "H-B19")


def ctl(fmt, b19):
    return STORE | fmt << 24 | (B19 if b19 else 0)


def args(fmt, b19, off):
    return (f"{MAIN} --width {W} --height {H} --max-width {W} --max-height {H} --tri-v "
            f"0,0,{512 * W},0,0,{512 * H} --tri-z 0,1,0 --depth --depth-ctl {ctl(fmt, b19):#010x} "
            f'--depth-fill {FILL:#010x} --depth-dump "$W" --poke blk:1={LESS:#010x} '
            f"--poke blk:10={off:#010x}")


def jobs():
    """[(name, set, knobs, args, {quantity: {model: value}})]"""
    out = []
    tiles = (W // 32) * (H // 16)
    for r, off in RAMPS:
        out.append((f"z2-{r}-f0", "control", "expectdiff reads:depth_changed", args(0, False, off),
                    {"depth_changed": {"H-E831": str(512 * tiles)}}))
        for fmt in (1, 2):
            for b in (False, True):
                out.append((f"z2-{r}-f{fmt}{'-b19' if b else ''}", "heldout", "expectdiff",
                            args(fmt, b, off), {"dwords": {m: f"rule:z2-{r}-f0" for m in MODELS}}))
    return out


def enc(z):
    return int(z * 16777215 + 0.5)


def rival(model, z, b19):
    """the 24-bit value a model stores for float z (a Python float of a float32)"""
    if model == "H-ABS" or (model == "H-B19" and b19):
        return enc(abs(z))
    if model in ("H-CLAMP", "H-B19"):
        return enc(max(z, 0.0))
    if model == "H-WRAP":
        import math
        return math.floor(z * 16777215 + 0.5) & 0xFFFFFF
    raise ValueError(model)


# ---- the ZLS layouts (sgx-pipe zls.rs, E465/E490) ---------------------------------------------
def in_tile_index(x, y):
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def in_tile_pixel(k):
    x, y = (k >> 8 & 1) << 4, 0
    for b in range(4):
        y |= (k >> (2 * b) & 1) << b
        x |= (k >> (2 * b + 1) & 1) << b
    return x, y


def in_tile_index16(x, y):
    x, y = x & 31, y & 15
    k = 0
    for b in range(4):
        k |= (x >> b & 1) << (2 * b)
        if b < 3:
            k |= (y >> (b + 1) & 1) << (2 * b + 1)
    return k | (x >> 4 & 1) << 7


def predict(z0, fmt, b19, model):
    """{dword index: value} over the target from the format-0 reference dump z0 (dwords)."""
    import struct
    f = lambda v: struct.unpack("<f", struct.pack("<I", v))[0]
    z = {}
    for ty in range(H // 16):
        for tx in range(W // 32):
            for k in range(512):
                x, y = in_tile_pixel(k)
                z[(32 * tx + x, 16 * ty + y)] = f(z0[512 * (ty * (G + 1) + tx) + k])
    if fmt == 1:
        return {512 * ((y >> 4) * (G + 1) + (x >> 5)) + in_tile_index(x, y): rival(model, z[(x, y)], b19)
                for y in range(H) for x in range(W)}
    return {256 * ((y >> 4) * (G + 1) + (x >> 5)) + in_tile_index16(x, y):
            rival(model, z[(x, y)], b19) >> 8 | (rival(model, z[(x, y + 1)], b19) >> 8) << 16
            for y in range(0, H, 2) for x in range(W)}
