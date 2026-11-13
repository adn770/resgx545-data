# SPDX-License-Identifier: MIT
"""z.py: r10-x's `tri --depth` stages, all in the form of E977's rows (closing9/r9-x gen/zls.py:
CR_ISP_ZLSCTL through --depth-ctl, ISP word 0 through --poke blk:1, the buffers dumped with
--depth-dump), 64 x 32 to 256 x 64.

The control word: E466/E467's store control without its pitch, 0x00171004, with the pitch G (bits
11:3), the format (bits 26:24) and the loads (bit 1 with 14 depth, E467). ISP word 0: the depth
compare in bits 24:22 (E282's order: 0 never, 1 less, 4 greater, 7 always measured; 2 equal, 3
lequal, 5 notequal, 6 gequal read from the stencil compare's order) with 0x200 (E977's 0x00400200
is less with the depth written). ISP word 1 is the state block's word 2 (libsgxfive render.c
sgxfive_tri_block: blk[1] isp0 0x01d00200, blk[2] isp1 0x10f0; lead/dryrun_checks.out check 2).

dcmp (R10-A: Q241, Q243; rank-round10.md dcmp_table.py): E977's z243 rows (64 x 32, one flat
--tri-full triangle at depth t, a depth buffer filled with L, loaded with bits 1 and 14 and stored
with --depth-store), the reading the drawn count of 2048. Rows: modes 0 to 7 at L = t = 0.5 (eq),
modes 2, 3, 5, 6 at one ulp above (up1) and below (dn1), NaN under 2, 3, 5, 6, and ten rows where a
negative loaded depth parts the value rivals. Frozen: H-GL (E282's GL order, the compare exact) on
the mode rows; on the NaN and value rows H-UBITS (an unsigned compare of the bit patterns, E977's
[infer]), H-ABS (the sign cleared first, E664's refusal note), H-IEEE (a float compare, NaN
unordered), H-CLAMP0 (a negative loaded depth read as 0.0, E287's triangle side). Controls that can
fail: E977's z243-ctl (0.75 under less: 2048), eq-m0 (0) and eq-m7 (2048).

zov (R10-C: Q242, overlapping tiles): a plane rising in x and y over whole-tile targets, stored at
the full pitch (the control: every dword of the tiles a distinct float, E831's count) and at a
pitch under the tiles across (G 0, 1, 1, 2, 3), so tiles share slots. The plan's plane (z 0, 1,
0.5 at (0,0), (2W,0), (0,2H)) gives equal depths along diagonals at 64 x 32, so here z = 0, ZX, 1
with ZX = the largest power of two at most 1/(2H): the y step 1/(2H) exceeds the whole x range of
a row, every pixel of the tile area has its own float (tests/test_gen.py). Frozen per shared slot
from the control's floats (each float names its pixel, so its tile): H-LATE / H-EARLY (the tile the
3D visits later or first owns the slot) in the region header order of sgx-pipe ta.rs
(header_order: macrotiles column-major, 4 x 4-region blocks raster inside) and in raster order;
the format-1 row from the same floats by O10-2's floor rule (E977).

zbits (R10-D: Q071): E977's z242-c geometry (80 x 40, G 2, the ramp 1, 0, 1) and its z243-ctl
load row with the control's inert bits (E411's single flips) together: bits 15, 21 to 23, 27 to
31 set and 12, 16, 20 cleared (formats 0, 1 and the load row), each half alone (format 0), and bit
0 with format 0, 1, 2 and the load row. Frozen per row: the depth dumps (sha256) of E977's kept
z242-c-f0/f1/f2 and z243-ctl jobs (H-INERT; bit 0: H-E665, the stores as without bit 0 and no
colour pixel), the drawn count and the target hash. Controls that can fail: the z242-c-f0 and -f1
reruns (E977's kept dumps).

isp0x (R10-E: Q241): z242-c-f0 with ISP word 0 bits 15, 16, 17 and ISP word 1 bits 3 (visibility
test) and 23 (polygon offset) flipped one at a time; bit 18 is not run (E065: it faulted the job,
and round 10 is safe class only). Frozen: H-NULL (E282's null: E977's kept z242-c-f0 dump, drawn
count and hash); a reading otherwise. Control: the unpoked z242-c-f0 rerun."""
import struct

STORE = 0x00171004
LOAD_D = 0x4002                 # bits 1 and 14: load the depth (E467)
LESS, GREATER = 0x00400200, 0x01000200
FILL = 0xDEADBEEF
MAIN = "tri --keep-going --wait-ms 20000"
SET_BITS = 0xF8E08000           # 15, 21-23, 27-31
CLR_BITS = 0x00111000           # 12, 16, 20
HASH_C = "0xafb12e5a2a9a6725"   # E977 z242-c-f0/f1/f2 target hash (r9-x out/20261113-081821/zls)
HASH_L = "0xfc73845f9e506325"   # E977 z243-ctl


def isp0(mode):
    return mode << 22 | 0x200


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def ctl(w, h, fmt, load=0, g=None):
    tx, _ = tiles(w, h)
    g = tx - 1 if g is None else g
    return STORE | g << 3 | fmt << 24 | load


def size(w, h):
    return f"--width {w} --height {h} --max-width {w} --max-height {h}"


def f32(u):
    return struct.unpack("<f", struct.pack("<I", u))[0]


# ---- dcmp ----------------------------------------------------------------------------------
OPS = {0: lambda a, b: False, 1: lambda a, b: a < b, 2: lambda a, b: a == b,
       3: lambda a, b: a <= b, 4: lambda a, b: a > b, 5: lambda a, b: a != b,
       6: lambda a, b: a >= b, 7: lambda a, b: True}


def _ieee(m, t, L):
    a, b = f32(t), f32(L)
    if b != b:
        return m in (5, 7)
    return OPS[m](a, b)


RIVALS = {
    "H-UBITS": lambda m, t, L: OPS[m](t, L),
    "H-ABS": lambda m, t, L: OPS[m](t & 0x7FFFFFFF, L & 0x7FFFFFFF),
    "H-IEEE": _ieee,
    "H-CLAMP0": lambda m, t, L: _ieee(m, t, 0 if L >> 31 else L),
}
HALF, ZERO = 0x3F000000, 0x00000000


def dcmp_rows():
    """[(name, set, mode, t bits, L bits, models)]: models {model: drawn}."""
    out = [("z243-ctl", "control", 1, HALF, 0x3F400000, {"H-E467": 2048})]
    for m in range(8):
        st = "control" if m in (0, 7) else "heldout"
        out.append((f"eq-m{m}", st, m, HALF, HALF, {"H-GL": 2048 if OPS[m](1, 1) else 0}))
    for tag, L in (("up1", 0x3F000001), ("dn1", 0x3EFFFFFF)):
        for m in (2, 3, 5, 6):
            out.append((f"{tag}-m{m}", "heldout", m, HALF, L,
                        {"H-GL": 2048 if OPS[m](f32(HALF), f32(L)) else 0}))
    val = [("nan", HALF, 0x7FC00000, (2, 3, 5, 6)), ("neg25", HALF, 0xBE800000, (1, 4)),
           ("neg75", HALF, 0xBF400000, (1, 4)), ("z0-neg25", ZERO, 0xBE800000, (1, 2, 4)),
           ("z0-negz", ZERO, 0x80000000, (1, 2, 4))]
    for tag, t, L, modes in val:
        for m in modes:
            out.append((f"{tag}-m{m}", "heldout", m, t, L,
                        {k: 2048 if r(m, t, L) else 0 for k, r in RIVALS.items()}))
    return out


def dcmp_jobs():
    out = []
    for name, st, m, t, L, models in dcmp_rows():
        z = "0.5" if t == HALF else "0"
        args = (f"{MAIN} {size(64, 32)} --tri-full --tri-z {z},{z},{z} --depth --depth-ctl "
                f"{ctl(64, 32, 0, LOAD_D):#010x} --depth-fill {L:#010x} --depth-store "
                f'--depth-dump "$W" --poke blk:1={isp0(m):#010x} --pixels')
        out.append((name, st, "expectdiff" + (" reads:drawn" if st == "control" else ""), args,
                    {"drawn": {k: str(v) for k, v in models.items()}}))
    return out


# ---- zov -----------------------------------------------------------------------------------
ZOV = [(64, 32, 0), (128, 32, 1), (96, 48, 1), (160, 48, 2), (256, 64, 3)]
ZOV_MODELS = ("H-LATE/HDR", "H-EARLY/HDR", "H-LATE/RASTER", "H-EARLY/RASTER")


def zx(h):
    """The largest power of two at most 1/(2H)."""
    v = 1.0
    while v > 1 / (2 * h):
        v /= 2
    return v


def zov_args(w, h, g, fmt=0):
    return (f"{MAIN} {size(w, h)} --tri-v 0,0,{512 * w},0,0,{512 * h} --tri-z 0,{zx(h)!r},1 "
            f"--depth --depth-ctl {ctl(w, h, fmt, g=g):#010x} --depth-fill {FILL:#010x} "
            f'--depth-dump "$W" --poke blk:1={LESS:#010x}')


def zov_jobs():
    out = []
    for w, h, g in ZOV:
        tx, ty = tiles(w, h)
        n = 512 * tx * ty
        out.append((f"zov-{w}x{h}-ctl", "control", "expectdiff reads:depth_changed",
                    zov_args(w, h, tx - 1), {"depth_changed": {"H-E831": str(n)},
                                             "distinct": {"H-PLANE": str(n)}}))
    for w, h, g in ZOV:
        out.append((f"zov-{w}x{h}-g{g}", "heldout", "expectdiff", zov_args(w, h, g),
                    {"dwords": {m: f"rule:zov-{w}x{h}-ctl" for m in ZOV_MODELS}}))
    out.append(("zov-64x32-g0-f1", "heldout", "expectdiff", zov_args(64, 32, 0, 1),
                {"dwords": {m + "/H-EXT": "rule:zov-64x32-ctl" for m in ZOV_MODELS}}))
    return out


def macro(w, h):
    """libsgxfive render.c sgxfive_tiling: n macrotiles a side, mx x my regions each."""
    tx, ty = tiles(w, h)
    n = 4 if w * h >= 640 * 480 else 2
    return n, ((tx + n - 1) // n + 3) & ~3, ((ty + n - 1) // n + 3) & ~3


def header_rank(w, h):
    """{(tx, ty): its place in the region header order} (sgx-pipe ta.rs headers/header_order:
    macrotile m at column m / n and row m % n, its regions in 4 x 4 blocks, raster across them
    and inside one)."""
    n, mx, my = macro(w, h)
    tx, ty = tiles(w, h)
    order = sorted(range(mx * my), key=lambda i: (i // mx // 4, i % mx // 4, i // mx % 4, i % mx % 4))
    rank, k = {}, 0
    for m in range(n * n):
        for i in order:
            c, r = (m // n) * mx + i % mx, (m % n) * my + i // mx
            if c < tx and r < ty:
                rank[(c, r)] = k
                k += 1
    return rank


def raster_rank(w, h):
    tx, ty = tiles(w, h)
    return {(c, r): r * tx + c for r in range(ty) for c in range(tx)}


def owners(w, h, g, model):
    """{slot base (512-dword unit): the tile that owns it} under a model."""
    late = model.startswith("H-LATE")
    rank = header_rank(w, h) if "/HDR" in model else raster_rank(w, h)
    best = {}
    for t, k in rank.items():
        s = t[1] * (g + 1) + t[0]
        if s not in best or (k > rank[best[s]] if late else k < rank[best[s]]):
            best[s] = t
    return best


def floor24(z):
    return min(int(z * 16777216), 0xFFFFFF)


def zov_predict(full, w, h, g, model, fmt=0):
    """{dword index: value} the overlapping store holds under a model, from the full-pitch
    control's dump `full` (dwords): the owner tile's 512 dwords at its slot (format 0: the floats;
    format 1: floor(z * 2^24), O10-2/E977, same in-tile index)."""
    tx, _ = tiles(w, h)
    out = {}
    for s, (c, r) in owners(w, h, g, model.split("/H-EXT")[0]).items():
        src = 512 * (r * tx + c)
        for k in range(512):
            v = full[src + k]
            out[512 * s + k] = v if fmt == 0 else floor24(f32(v))
    return out


# ---- zbits and isp0x -------------------------------------------------------------------------
C_ARGS = (f"{MAIN} {size(80, 40)} --tri-v 0,0,40960,0,0,20480 --tri-z 1,0,1 --depth --depth-ctl "
          "{ctl:#010x} --depth-fill 0xdeadbeef --depth-dump \"$W\" --poke blk:1={isp:#010x}{extra}")
L_ARGS = (f"{MAIN} {size(64, 32)} --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl {{ctl:#010x}} "
          "--depth-fill 0x3f400000 --depth-store --depth-dump \"$W\" --poke blk:1=0x00400200 --pixels")
C_CTL = 0x00171014              # E977 z242-c: STORE | G 2
L_CTL = 0x0017500E              # E977 z243-ctl


def c_args(ctlw, isp=LESS, extra=""):
    return C_ARGS.format(ctl=ctlw, isp=isp, extra=extra)


def with_bits(c, mask):
    """mask 'all', 'set' or 'clr' applied to control word c."""
    if mask == "set":
        return c | SET_BITS
    if mask == "clr":
        return c & ~CLR_BITS
    return (c & ~CLR_BITS) | SET_BITS


def zbits_rows():
    """[(name, set, args, kept job of E977 whose dumps it is compared with, models)]: models
    {model: (drawn, hash or None)}; hash None: not predicted."""
    inert = lambda kept: {"H-INERT": (2048 if kept == "z243-ctl" else 3200,
                                      HASH_L if kept == "z243-ctl" else HASH_C)}
    out = [("zb-ctl-f0", "control", c_args(C_CTL), "z242-c-f0", inert("z242-c-f0")),
           ("zb-ctl-f1", "control", c_args(C_CTL | 1 << 24), "z242-c-f1", inert("z242-c-f1"))]
    out += [("zb-all-f0", "heldout", c_args(with_bits(C_CTL, "all")), "z242-c-f0", inert("z242-c-f0")),
            ("zb-all-f1", "heldout", c_args(with_bits(C_CTL | 1 << 24, "all")), "z242-c-f1",
             inert("z242-c-f1")),
            ("zb-all-load", "heldout", L_ARGS.format(ctl=with_bits(L_CTL, "all")), "z243-ctl",
             inert("z243-ctl")),
            ("zb-set-f0", "heldout", c_args(with_bits(C_CTL, "set")), "z242-c-f0", inert("z242-c-f0")),
            ("zb-clr-f0", "heldout", c_args(with_bits(C_CTL, "clr")), "z242-c-f0", inert("z242-c-f0"))]
    e665 = lambda kept: {"H-E665": (0, None), "H-INERT": inert(kept)["H-INERT"]}
    for name, c, kept in (("zb-b0-f0", C_CTL, "z242-c-f0"), ("zb-b0-f1", C_CTL | 1 << 24, "z242-c-f1"),
                          ("zb-b0-f2", C_CTL | 2 << 24, "z242-c-f2")):
        out.append((name, "heldout", c_args(c | 1), kept, e665(kept)))
    out.append(("zb-b0-load", "heldout", L_ARGS.format(ctl=L_CTL | 1), "z243-ctl", e665("z243-ctl")))
    return out


def isp0x_rows():
    null = {"H-NULL": (3200, HASH_C)}
    out = [("x-ctl", "control", c_args(C_CTL), "z242-c-f0", null)]
    for b in (15, 16, 17):
        out.append((f"x-w0b{b}", "heldout", c_args(C_CTL, LESS | 1 << b), "z242-c-f0", null))
    for b in (3, 23):
        out.append((f"x-w1b{b}", "heldout", c_args(C_CTL, extra=f" --poke blk:2^={1 << b:#x}"),
                    "z242-c-f0", null))
    return out


KEPT = "render/closing-r9-x/out/20261113-081821/zls"


def bits_jobs(rows, kept_sha, kept_line):
    """[(name, set, knobs, args, {quantity: {model: value}})] of zbits or isp0x: kept_sha(job,
    dump name) the sha256 of E977's kept dump, kept_line(job, prefix) the line of its kept output
    that starts with prefix. A load row's stored depth (--depth-store) is frozen as E977's
    `depth store #1:` line (its count, distinct values and the commonest; the scorer reads one dump
    a row, depth.1.bin, the loaded buffer there)."""
    out = []
    for name, st, args, kept, models in rows:
        q = {}
        for m, (drawn, h) in models.items():
            q.setdefault("drawn", {})[m] = str(drawn)
            if h is not None:
                q.setdefault("hash", {})[m] = h
            q.setdefault("depth.1.bin", {})[m] = "sha256:" + kept_sha(kept, "depth.1.bin")
            if kept == "z243-ctl":
                q.setdefault("store_line", {})[m] = kept_line(kept, "depth store #1: ")
        out.append((name, st, "expectdiff" + (" reads:depth_changed" if st == "control" else ""),
                    args, q))
    return out
