# SPDX-License-Identifier: MIT
"""zbg.py: stages zbgc, zbg and zw (seeds plan closing10/seeds/exp-seeds-r10.md section 6, decision
R10-4 (a), Q101): the background depth route to a negative stored depth, and state-block word 10.

zbgc and zbg (tool t9, r9-z2's form): 256 x 128 (G 7), E466's store control without a load,
depth less with writes (ISP word 0 0x00400200), the buffer filled 0xdeadbeef and dumped; one small
triangle (0,0) (128,0) (0,64) at depth 0.5, so most pixels are background. The render details'
dword 16 (CR_ISP_BGOBJDEPTH, 3d.md; fork 2a650d74 sgx_render.c `rd[SGX_RENDER_RD_BGDEPTH / 4]`,
0x3f800000 by default, sgx_tri.c) is written before the render with `--kpoke-render 1:rd:16=V`.
Without a load the pass starts from that clear value (sgx-pipe zls.rs) and the store writes it at
every undrawn pixel, without the ISP's arithmetic (E981 clamps a computed depth at 0).

  zbgc (controls, can fail; zbg's gate):
    zbg-c1   rd:16 = 0x3f800000 (the default, explicit): background 1.0 at every background pixel
    zbg-c25  rd:16 = 0x3e800000 (0.25): the premise that dword 16 is the background depth
  zbg (held out; runs only when both controls pass), rd:16 = 0xbe800000 (-0.25) in formats 0, 1
    and 2, each without and with bit 19, and rd:16 = 0x80000000 (-0.0) in format 1:
    H-RAW      the word stored as it is: f0 0xbe800000, bit 19 0x3e800000 (E466's negation); the
               integers floor(z 2^24) in 24 bits (0xc00000; >> 8 for f2), bit 19 changing no
               integer dword (E490, E981)
    H-CLAMP0   clamped to 0 first: f0 0, bit 19 0x80000000 (the negation of 0.0), integers 0
    H-CLAMP0P  +0 in every format, bit 19 or not
    H-ABS      the sign cleared (as E467's load): f0 0x3e800000, bit 19 0xbe800000, 0x400000
    H-B19-INT  H-RAW, but bit 19 negates before the integer conversion (0x400000 with bit 19)
    H-ZERO     (-0.0 row) 0 at every background pixel
  Scored on the background pixels: centre (x + 0.5) / 128 + (y + 0.5) / 64 >= 1.05 (inside the
  target), a margin off the triangle's edge; the triangle's pixels are a reading.

zw (tool t9, r9-z2's ramp a, E977's z242-a): 256 x 128, the triangle (0,0) (512,0) (0,256) at
depths 0, 1, 0, format 0, word 10 of the state block poked (`--poke blk:10=V`):
  zw-c50   V = 0.5, the default made explicit (a control): byte for byte E977's kept z242-a-f0
           (which ran without the poke; z = (x + 0.5) / 512 at every dword)
  zw-075, zw-100, zw-0125   V = 0.75, 1.0, 0.125, held out. Frozen per dword, with
           t = (x + 0.5) / 512 and f(w) the factor on t:
    H-LIN   f = 1.6 w + 0.2 (the line through w = 0.5 (E977, factor 1) and w = 0.25 (E981's
            ramp a, factor 0.6), seeds plan finding 6 [fitted, 2 points])
    H-HYP   f = 0.375 / (0.875 - w) (the hyperbola through the same two points), clamped at 0
    H-OFF   z = max(0, t + w - 0.5) (word 10 as the viewport's z offset, 3d.md; E981 refuted it
            at 0.25 and -0.25: kept as a rival that can fail again)
  Scored where (x + 0.5) / 512 + (y + 0.5) / 256 <= 0.5: E981's ramp a held 0.6 t within one
  ulp there and left it beyond 0.81 (post hoc, lead/w10_look.py); a dword is at the model when
  |z - z_model| <= 1e-5 z_model (+ 1e-9). The rest of the target is a reading."""
MAIN = "tri --keep-going --wait-ms 20000"
W, H, G = 256, 128, 7
STORE = 0x00171004 | G << 3
LESS = 0x00400200
FILL = 0xDEADBEEF
B19 = 1 << 19
SIGN = 0x80000000
TRI = "--tri-v 0,0,32768,0,0,16384 --tri-z 0.5,0.5,0.5"
RAMP = "--tri-v 0,0,131072,0,0,65536 --tri-z 0,1,0"
BG_MARGIN = 1.05
W10_MASK = 0.5
W10_REL, W10_ABS = 1e-5, 1e-9
CONTROLS = {"zbg-c1": 0x3F800000, "zbg-c25": 0x3E800000}
NEG = 0xBE800000
NEGZ = 0x80000000
BG_MODELS = ("H-RAW", "H-CLAMP0", "H-CLAMP0P", "H-ABS", "H-B19-INT")
W10 = {"zw-075": 0x3F400000, "zw-100": 0x3F800000, "zw-0125": 0x3E000000}
W10_C50 = 0x3F000000
W10_MODELS = ("H-LIN", "H-HYP", "H-OFF")
E977_REF = "render/closing-r9-x/out/20261113-081821/zls/z242-a-f0.depth.1.bin.gz"


def ctl(fmt, b19=False):
    return STORE | fmt << 24 | (B19 if b19 else 0)


def bg_args(fmt, b19, v):
    return (f"{MAIN} --width {W} --height {H} --max-width {W} --max-height {H} {TRI} --depth "
            f"--depth-ctl {ctl(fmt, b19):#010x} --depth-fill {FILL:#010x} --depth-dump \"$W\" "
            f"--poke blk:1={LESS:#010x} --kpoke-render 1:rd:16={v:#010x}")


def w10_args(v):
    return (f"{MAIN} --width {W} --height {H} --max-width {W} --max-height {H} {RAMP} --depth "
            f"--depth-ctl {ctl(0):#010x} --depth-fill {FILL:#010x} --depth-dump \"$W\" "
            f"--poke blk:1={LESS:#010x} --poke blk:10={v:#010x}")


def bg_value(model, fmt, b19, v):
    """the dword a background pixel is stored as (f2: the pair of rows, both background)"""
    if v == NEGZ:
        return 0 if model == "H-ZERO" else None
    z = fbits(v)
    neg_f0 = lambda bits: bits ^ (SIGN if b19 else 0)  # noqa: E731
    if model in ("H-RAW", "H-B19-INT"):
        if fmt == 0:
            return neg_f0(v)
        if model == "H-B19-INT" and b19:
            i = int(-z * 16777216) & 0xFFFFFF
        else:
            import math
            i = math.floor(z * 16777216) & 0xFFFFFF
    elif model == "H-CLAMP0":
        if fmt == 0:
            return neg_f0(0)
        i = 0
    elif model == "H-CLAMP0P":
        return 0
    elif model == "H-ABS":
        a = v & ~SIGN
        if fmt == 0:
            return neg_f0(a)
        i = int(fbits(a) * 16777216) & 0xFFFFFF
    else:
        raise ValueError(model)
    return i if fmt == 1 else (i >> 8) | (i >> 8) << 16



def fbits(v):
    import struct
    return struct.unpack("<f", struct.pack("<I", v))[0]


def jobs(stage):
    """[(name, set, knobs, args, {quantity: {model: value}})]"""
    tiles = (W // 32) * (H // 16)
    if stage == "zbgc":
        return [(n, "control", "expectdiff reads:depth_changed", bg_args(0, False, v),
                 {"depth_changed": {"H-E831": str(512 * tiles)}, "bg": {"H-BGDEPTH": f"{v:#010x}"}})
                for n, v in CONTROLS.items()]
    if stage == "zbg":
        out = []
        for fmt in (0, 1, 2):
            for b in (False, True):
                out.append((f"zbg-n-f{fmt}{'-b19' if b else ''}", "heldout", "expectdiff",
                            bg_args(fmt, b, NEG),
                            {"bg": {m: f"{bg_value(m, fmt, b, NEG):#010x}" for m in BG_MODELS}}))
        out.append(("zbg-z-f1", "heldout", "expectdiff", bg_args(1, False, NEGZ),
                    {"bg": {"H-ZERO": "0x00000000"}}))
        return out
    if stage == "zw":
        out = [("zw-c50", "control", "expectdiff reads:depth_changed", w10_args(W10_C50),
                {"depth_changed": {"H-E831": str(512 * tiles)}, "dwords": {"H-E977": "same:" + E977_REF}})]
        for n, v in W10.items():
            out.append((n, "heldout", "expectdiff", w10_args(v),
                        {"factor": {m: frozen(m, fbits(v)) for m in W10_MODELS}}))
        return out
    raise ValueError(stage)


def factor(model, w):
    """the factor on t a model gives (H-OFF: None, it is no factor)"""
    if model == "H-LIN":
        return round(1.6 * w + 0.2, 12)
    if model == "H-HYP":
        return round(0.375 / (0.875 - w), 12)
    return None


def frozen(model, w):
    """the predictions' value: the factor on t, or H-OFF's offset added to t"""
    return f"offset:{w - 0.5!r}" if model == "H-OFF" else f"{factor(model, w)!r}"


def w10_z(model, w, x):
    t = (x + 0.5) / 512
    if model == "H-OFF":
        return max(0.0, t + w - 0.5)
    return max(0.0, factor(model, w) * t)


# ---- the layouts (sgx-pipe zls.rs, E465/E490) --------------------------------------------------
def in_tile_index(x, y):
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def in_tile_index16(x, y):
    x, y = x & 31, y & 15
    k = 0
    for b in range(4):
        k |= (x >> b & 1) << (2 * b)
        if b < 3:
            k |= (y >> (b + 1) & 1) << (2 * b + 1)
    return k | (x >> 4 & 1) << 7


def is_bg(x, y):
    return (x + 0.5) / 128 + (y + 0.5) / 64 >= BG_MARGIN


def is_tri(x, y):
    return (x + 0.5) / 128 + (y + 0.5) / 64 <= 2 - BG_MARGIN


def bg_dwords(fmt):
    """{dword index: [pixels]} of the background mask in a format's layout"""
    out = {}
    if fmt in (0, 1):
        for y in range(H):
            for x in range(W):
                if is_bg(x, y):
                    out[512 * ((y >> 4) * (G + 1) + (x >> 5)) + in_tile_index(x, y)] = [(x, y)]
        return out
    for y in range(0, H, 2):
        for x in range(W):
            if is_bg(x, y) and is_bg(x, y + 1):
                out[256 * ((y >> 4) * (G + 1) + (x >> 5)) + in_tile_index16(x, y)] = [(x, y), (x, y + 1)]
    return out


def f0_index(x, y):
    return 512 * ((y >> 4) * (G + 1) + (x >> 5)) + in_tile_index(x, y)


def w10_pixels():
    return [(x, y) for y in range(H) for x in range(W) if (x + 0.5) / 512 + (y + 0.5) / 256 <= W10_MASK]


def w10_at(z, zm):
    return abs(z - zm) <= W10_REL * abs(zm) + W10_ABS
