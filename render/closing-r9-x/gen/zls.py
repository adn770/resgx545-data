# SPDX-License-Identifier: MIT
"""zls.py: stages zls (R9-C: Q242, Q243) and zst (R9-D: Q120; Q121 dropped, below), `tri --depth`
rows in the form of E466/E467/E490/E831 (CR_ISP_ZLSCTL through --depth-ctl, the depth test
through ISP word 0 --poke blk:1, the buffers dumped with --depth-dump).

The control word: E466/E467's store control 0x0017110c with the pitch G (bits 11:3) set to the
target's tiles across minus one (no overlap), the format in bits 26:24, the loads (bit 1 with 14
depth, with 13 stencil) where a row loads. ISP word 0: 0x00400200 depth less and depth written
(E466's), 0x01000200 greater (DCMP 4, E282); the tool's default 0x01d00200 writes no depth.

Q242 (zls): a ramp over [0, 0.5] (rising, 256 x 128, G 7) or [0.5, 1) (falling, 320 x 240 G 9 and
80 x 40 G 2, edge tiles) drawn by one triangle over (0,0) (2W,0) (0,2H), stored in format 0, 1 and 2.
Format 0 (a control: every dword of the target's tiles leaves the 0xdeadbeef fill, E831's band or
the background 1.0) gives each dword's float z; frozen per dword from it (score.py applies them):
  format 1  H-ROUND round(z * 0xffffff) (E466/E663)  vs  H-FLOOR min(floor(z * 2^24), 0xffffff)
            (they differ for every z in [0.5, 1) and for some below 0.25)
  format 2  value H-ROUND >> 8 vs H-FLOOR16 min(floor(z * 2^16), 0xffff), layout H-E490 (256 dwords
            a tile at 256 (ty (G + 1) + tx) + in_tile_index16, y even in the low half) vs H-SLOT512
            (the float format's slot spacing, 512 (ty (G + 1) + tx) + in_tile_index16)
Q243 (zls): one render loads a depth buffer filled with a constant and stores into a second
(--depth-store), 64 x 32, one triangle over the target at one depth; the reading is the number of
pixels drawn (the tool's `N triangle`):
  f1-less   format 1, fill 0x00400000 (0.25 as an integer), triangle 0.125, less: H-INT (the load
            converts back) all 2048, H-RAW (read as a float, a denormal) none
  f2-less   format 2, fill 0x3fff3fff (0.25 per half), triangle 0.5, less: H-INT none, H-RAW (the
            dword as a float, 1.99998) all
  nan-less, nan-gt   format 0, fill 0x7fc00000, triangle 0.5: IEEE none in both, NAN-PASS all
  inf-less, inf-gt   format 0, fill 0x7f800000: IEEE all (less) and none (greater), INF-ZERO (a
            flush to 0) none and all
  ctl       format 0, fill 0.75 (0x3f400000), triangle 0.5, less: all (E467's load and test)
Q120 (zst): the x ramp of E466 (--tri-full --tri-z 0.25,0.75,0.25) with a stencil buffer filled
with each dword's index, loaded (bits 1 and 13, E467) and stored (bit 17) into --stencil-store,
formats 3 to 7 at 64 x 32 (G 1) and 96 x 48 (G 2); controls the same in format 0 (depth: every
dword of the tiles; stencil store: E467's copy, 128 dwords a tile). Frozen counts (E466 at 1024 x
768 scaled per tile, [infer] that the per-tile count holds at another size and with a loaded
stencil): format 4 160 depth dwords a tile (H-SCALE) vs none (H-NONE), format 7 12 a tile vs none;
formats 3, 5 and 6 are a reading table (no frozen count: data-dependent or a lower bound in E466).
Q121 is not run: its rows need ISP word 2 (a stencil operation) with the ZLS stencil buffers, and
tool t4 sets ISP word 2 only in `probe --tri` (--isp2), which has no --stencil buffers, while `tri`
has the buffers but no --isp2 (sgxfive-test.c at 4623753: parse_opts, the probe's option loop)."""
STORE = 0x00171004       # E466/E467's 0x0017110c without its G = 33 (bits 11:3)
LESS, GREATER = 0x00400200, 0x01000200
FILL = 0xDEADBEEF
MAIN = "tri --keep-going --wait-ms 20000"


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def ctl(w, h, fmt, load=0):
    tx, _ = tiles(w, h)
    return STORE | (tx - 1) << 3 | fmt << 24 | load


def size(w, h):
    return f"--width {w} --height {h} --max-width {w} --max-height {h}"


# Q242: name stem, W, H, z at (0,0) (2W,0) (0,2H)
Q242 = [("z242-a", 256, 128, "0,1,0"), ("z242-b", 320, 240, "1,0,1"), ("z242-c", 80, 40, "1,0,1")]
# Q243: name, format, depth fill, triangle z, test, {model: drawn of 2048}
Q243 = [
    ("z243-ctl", 0, 0x3F400000, "0.5", LESS, {"H-E467": 2048}),
    ("z243-f1-less", 1, 0x00400000, "0.125", LESS, {"H-INT": 2048, "H-RAW": 0}),
    ("z243-f2-less", 2, 0x3FFF3FFF, "0.5", LESS, {"H-INT": 0, "H-RAW": 2048}),
    ("z243-nan-less", 0, 0x7FC00000, "0.5", LESS, {"H-IEEE": 0, "H-NANPASS": 2048}),
    ("z243-nan-gt", 0, 0x7FC00000, "0.5", GREATER, {"H-IEEE": 0, "H-NANPASS": 2048}),
    ("z243-inf-less", 0, 0x7F800000, "0.5", LESS, {"H-IEEE": 2048, "H-INFZERO": 0}),
    ("z243-inf-gt", 0, 0x7F800000, "0.5", GREATER, {"H-IEEE": 0, "H-INFZERO": 2048}),
]
Q120_FMT = (3, 4, 5, 6, 7)
Q120_SIZES = [("s", 64, 32), ("m", 96, 48)]
PER_TILE = {4: 160, 7: 12}           # E466: 245760 and 18432 depth dwords over 1536 tiles


def zls_jobs():
    """[(name, set, knobs, args, {quantity: {model: value}})]"""
    out = []
    for stem, w, h, z in Q242:
        tx, ty = tiles(w, h)
        for f in (0, 1, 2):
            args = (f"{MAIN} {size(w, h)} --tri-v 0,0,{512 * w},0,0,{512 * h} --tri-z {z} --depth "
                    f"--depth-ctl {ctl(w, h, f):#010x} --depth-fill {FILL:#010x} --depth-dump "
                    f'"$W" --poke blk:1={LESS:#010x}')
            if f == 0:
                out.append((f"{stem}-f0", "control", "expectdiff reads:depth_changed", args,
                            {"depth_changed": {"H-E831": str(512 * tx * ty)}}))
            else:
                models = ("H-ROUND", "H-FLOOR") if f == 1 else (
                    "H-E490/H-ROUND", "H-E490/H-FLOOR", "H-SLOT512/H-ROUND", "H-SLOT512/H-FLOOR")
                out.append((f"{stem}-f{f}", "heldout", "expectdiff", args,
                            {"dwords": {m: f"rule:{stem}-f0" for m in models}}))
    for name, f, fill, z, test, models in Q243:
        args = (f"{MAIN} {size(64, 32)} --tri-full --tri-z {z},{z},{z} --depth --depth-ctl "
                f"{ctl(64, 32, f, 0x4002):#010x} --depth-fill {fill:#010x} --depth-store "
                f'--depth-dump "$W" --poke blk:1={test:#010x} --pixels')
        st = "control" if name.endswith("ctl") else "heldout"
        out.append((name, st, "expectdiff" + (" reads:drawn" if st == "control" else ""), args,
                    {"drawn": {m: str(v) for m, v in models.items()}}))
    return out


def zst_jobs():
    out = []
    for sz, w, h in Q120_SIZES:
        tx, ty = tiles(w, h)
        for f in (0,) + Q120_FMT:
            args = (f"{MAIN} {size(w, h)} --tri-full --tri-z 0.25,0.75,0.25 --depth --depth-ctl "
                    f"{ctl(w, h, f, 0x2002):#010x} --depth-fill {FILL:#010x} --stencil "
                    f'--stencil-fill index --stencil-store --depth-dump "$W" '
                    f"--poke blk:1={LESS:#010x}")
            if f == 0:
                out.append((f"z120-ctl-{sz}", "control", "expectdiff reads:depth_changed,sst_changed",
                            args, {"depth_changed": {"H-E831": str(512 * tx * ty)},
                                   "sst_changed": {"H-E467": str(128 * tx * ty)}}))
            elif f in PER_TILE:
                out.append((f"z120-f{f}-{sz}", "heldout", "expectdiff", args,
                            {"depth_changed": {"H-SCALE": str(PER_TILE[f] * tx * ty),
                                               "H-NONE": "0"}}))
            else:
                out.append((f"z120-f{f}-{sz}", "reading", "expectdiff", args, {}))
    return out


# ---- the ZLS layouts (sgx-pipe zls.rs, E465/E490), for the scorer ------------------------------
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
