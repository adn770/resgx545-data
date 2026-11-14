# SPDX-License-Identifier: MIT
"""z16.py: r16-zls's rows and frozen rivals (round 16 plan closing16/plan/rank-round16.md sections
2, 3 and 5, decisions R16-1 (a), R16-3 (a), R16-6 (a), R16-8 (a); tool t10, resgx545 a581c06
sgxfive-test.c). Round 15's r15-zls (render/closing-r15-zls gen/z15.py, E1050, E1051, E1053) is
the direct predecessor: its helpers are copied here, not imported, so this file alone is frozen.
The stages group the rows by the dump their scorer reads (STAGE_ROWS at the end); a row's name
prefix names its record: zp2- E1059 (Q297), zb4- E1063 (Q071), zo- E1064 (Q299), zw2- E1066
(Q069). Kept records are read at the frozen data commit (gen/pins.py, KEPT below).

Part zpass2 (Q297, E1059; rows zp2-). E1050's zpass form (64 x 32, --tri-full, the depth buffer
filled bit:9: 0.25f in tile column 0, 0.75f in column 1 at G 1; the load and store enables
0x0017500e, `--depth-store`, 20 pages, depth test less) at seven flat depths, each pass row with
its no-load twin right after it (0x0017100c: the same triangle stored from the clear 1.0):
  H-PASS-TWIN   the pass stores, at each dword, the twin's value where the twin's float is below
                the loaded float (strict, E995), else the loaded dword (sign cleared, E467); the
                drawn count is the number of such dwords: the pass adds nothing to the plane's own
                error (Q200) [infer]
  H-PASS-OWN    the pass stores the exact float of the depth where it is below the load (E1050's
                frozen H-PASS-Z store; zp-z125 refuted it at 0.125, so it is the negative)
  H-PASS-EXACT  at the one-float depths (0.375, 0.625, 0.5 + 2^-20: E1054's FL-REC0 rows and
                twin), the store is the depth's own float where drawn (scored there only)
Depths 0.125 (the replicate), 0.0625, 0.1, 0.3, 0.375, 0.625, 0.5 + 2^-20; drawn 2048 below 0.25,
1024 from 0.3 up (the 0.75 column only). E1050's H-PASS-LE does not part on these rows (no depth
equals a loaded one) and is not scored (README deviation). Controls (can fail): zp2-c-z125, E1050's
zp-z125 rerun (its kept store byte for byte, 2048 drawn: the determinism premise of H-PASS-TWIN;
the pair's verdict is printed on its twin zp2-t-z125, held out: no twin ran) and zp2-c-467 (E1050's
zp-c-467: 256 x 128 G 7, its kept store byte for byte, 16384 drawn).

Part zbits4 (Q071, E1063; rows zb4-). Bit 0 under controls not run (E997 ran formats 0 to 2 at G 2
and a depth load): E988's stencil row st1-b0 (0x0017300f), E1031's flat format-6 row zf-flat-f6
(0x0617300f), E1031's F7K row zf-7k-3f (0x0717300f) and E1030's zbs-c16 (bit 16 cleared,
0x0016300f):
  H-B0          the depth dump and the stencil store equal the kept twin's (the row without bit
                0) byte for byte and no pixel takes the triangle's colour (E997) [infer]
  H-B0-NOSTORE  nothing is stored: the depth dump keeps its fill, the stencil store its fill
Bit 20 cleared on routes not run (E1030 cleared it with the st1 and ramp rows only): zf-flat-f6
(0x0607300e), zf-7k-3f (0x0707300e), E1042's zb2-d12 (bit 12 cleared with a depth load,
0x0007400e: in stage zovp, the depth-store stage) and E1041's zo-640-f0 (640 x 480, four
macrotiles, 0x0007109c: in stage zoff, the depth-only stage):
  H-INERT20     each dump the row's scorer reads and the drawn count equal the kept twin's
Bit 23's bytes (0x3f, 0x80, 0 by x mod 16, E1053) on E1042's zb2-b23 form (0x0097300e) with the
reference (ISP word 0 bits 7:0, E284) at 0x80 (`--poke blk:1^=0x80`), the compare mask (ISP word
2 bits 15:8) at 0xff (`--isp2 0x0405ffff`) and the background stencil CR_ISP_BGOBJVALS.STENCIL
(render details dword 17, 3d.md section 11.3; t10's 0x300 with bit 8 set, so 0x35a) at 0x5a:
  H23-FIXED     on every row the byte the test reads (the stored byte, XOR 0xff where the pixel
                drew) is COL23[x mod 16]
  H23-REF, H23-MASK, H23-BG  the bytes follow that value: on its own row the read bytes are not
                COL23 at some pixel, on the other two rows they are (the source named)
Controls (can fail): zb4-c-base (E988's st1-b0: E1042's kept stencil store and depth dump, 1024
drawn), zb4-c-b23 (E1042's zb2-b23 rerun, kept, 1536 drawn) and zb4-c-f6 (E1031's zf-flat-f6 rerun,
kept, 176 depth dwords changed).

Part zovp (Q299, E1064; rows zo-). The load pass over overlapping tiles (E996: G below the tiles
across minus one): E996's plane (z 0, ZX, 1 at (0,0), (2W,0), (0,2H)), whose every pixel has its
own float, loaded and stored (0x0017500e with G) at 64 x 32 G 0 and 160 x 48 G 2, depth less, the
depth buffer filled with the constant 0.2 (0x3e4ccccd, a value fill: below and above the plane in
every overlapped tile row, so the three forms part; the plan's flat 0.375 stores the same in every
form, README deviation). Each tile reads its slot of the load buffer by E465 (slot ty (G + 1) + tx:
shared slots read the same dwords) and the plane is the kept full-pitch reference's float (E996's
zov-64x32-ctl and zov-160x48-ctl, H-PASS-TWIN [infer]):
  H-OVL-PASS    every tile passes as E1050 against its slot's load and a shared store slot holds
                the tile visited last in region header order (E996, E1051's H-LATE/HDR)
  H-OVL-FIRST   the slot holds the tile visited first
  H-OVL-SKIP    a tile whose slot is shared takes no load (starts from the clear 1.0), the slot the
                last tile's
The same pass with E988's stencil load (st1 form at G 0 and G 2; rows zo-s-64, zo-s-160, in
stage zbits4, the stencil-store stage): H-OVL-PASS (each tile reads its slot's bytes) against
H-OVL-SKIP (shared slots start from stencil 0); first and last store the same bytes there.
A kept NaN into an integer store (E1050's zpass form, depth test never, the load buffer filled
0x7fc00000, 0xffc00000 (format 1 only) and 0x7f800001, formats 1 and 2):
  H-NAN-SAT     the stored dword is the conversion's clamp: 0x00ffffff (format 1), 0xffffffff
                (format 2): NaN above every depth (E995's H-ABS), then E1051's clamp above 1
  H-NAN-ZERO    0
  H-NAN-LOW     the word's low 24 bits after the sign is cleared (format 2: their top 16 twice)
Controls (can fail): zo-c-64 (the pass row's no-load twin, 0x00171004 at G 0: E996's owner rule
from the kept reference, decided by E996 and E1051: the overlap form's own control) and zo-c-f1
(E1050's zp-f1 rerun, its kept store byte for byte, 1024 drawn: the integer pass form's).

Part zoff (Q069, E1066; rows zw2-). E987's zw form (256 x 128, the triangle (0,0) (512,0) (0,256) at
depths 0, 1, 0, so t = x / 512; format 0 at G 7, 0x0017103c; depth less) with the viewport z offset
w (state-block word 10, `--poke blk:10`) and, on two rows, its z scale s (word 11, 0.5 in t10's
block). The offline gate OQ069 (gen/oq069.py, gen/oq069.out) replayed E987's zw-0125 and E981's
z2-a-f0 (w 0.125 and 0.25): H-POLYCLIP's cut covers 8192 and 16384 pixels where the kept rows
drew all 32768 (refuted on coverage), and H-LIN holds at 31856 of 32768 dwords in each, the
other 912 the same pixels in both rows (the bend BEND past x/512 + y/256 = 0.817, E987's 912). So
only H-LIN passes the gate, on the pixels outside BEND, and is frozen [fitted]; zoff runs:
  H-LIN         (1.6 w + 0.2) t at every pixel outside BEND (within 1e-5 relative, E987's rule), all
                32768 drawn [fitted: E987's two points]; BEND's dwords are a reading
  H-LIN-S       (1.6 w + 0.4 s) t: the far vertex at f + 0.6 n (f = w + s, n = w - s), the same
                two points written with s [infer]; equal to H-LIN at s = 0.5
  H-POLYCLIP    the polygon cut at z = 0 (E1056) of z = s (2 t - 1) + w: drawn iff t > (s - w) /
                (2 s), there z = s (2 t - 1) + w (1e-4 absolute, E1056's clipped planes)
Rows: w = 0, 1/16, 3/16, 5/16, 3/8, 7/16 at s = 0.5 (H-LIN against H-POLYCLIP), and w = 0.25 at
s = 0.25 (H-LIN 0.6 t against H-LIN-S and H-POLYCLIP, both 0.5 t: no negative vertex) and 0.75
(0.6 t, 0.7 t, the cut at t = 1/3). Order: nearest the kept range first, w = 0 and s = 0.75 (a
vertex depth of -0.5, below every one run) last. Control (can fail): zw2-c-0125 (E987's zw-0125
rerun on t10, its kept dump byte for byte, 32768 drawn). zb4-20-640 runs here (depth only)."""
import math
import struct

MAIN = "tri --keep-going --wait-ms 20000"
TILE_DW = 512
FILL_DEAD = 0xDEADBEEF
CLEAR = 0x3F800000
NEVER, LESS, ALWAYS = 0x00000200, 0x00400200, 0x01C00200
TRI_COLOUR = 0xFF00FF00

R9Z = "render/closing-r9-z2/out/20261113-082522/z2/"
R10X = "render/closing-r10-x/out/20261113-101116/zov/"
R10Z = "render/closing-r10-zls/out/20261113-102039/zw/"
R13Z = "render/closing-r13-zls/out/20261113-213117/"
R14Z = "render/closing-r14-zls/out/20261114-054846/"
R15Z = "render/closing-r15-zls/out/20261114-073826/"
# key: the kept record (data:PATH, a .gz the pins unpack)
KEPT = {
    "zp-z125.dst": R15Z + "zpass/zp-z125.depth-store.1.bin.gz",          # E1050
    "zp-c-467.dst": R15Z + "zpass/zp-c-467.depth-store.1.bin.gz",        # E1050
    "zp-f1.dst": R15Z + "zpass/zp-f1.depth-store.1.bin.gz",              # E1050
    "zb2-c-base.sst": R14Z + "zbits2/zb2-c-base.stencil-store.1.bin.gz",   # E1042
    "zb2-c-base.dep": R14Z + "zbits2/zb2-c-base.depth.1.bin.gz",
    "zb2-c-base.txt": R14Z + "zbits2/zb2-c-base.txt.gz",
    "zb2-b23.sst": R14Z + "zbits2/zb2-b23.stencil-store.1.bin.gz",         # E1042
    "zb2-b23.dep": R14Z + "zbits2/zb2-b23.depth.1.bin.gz",
    "zf-flat-f6.sst": R13Z + "zfmt/zf-flat-f6.stencil-store.1.bin.gz",     # E1031
    "zf-flat-f6.dep": R13Z + "zfmt/zf-flat-f6.depth.1.bin.gz",
    "zf-flat-f6.txt": R13Z + "zfmt/zf-flat-f6.txt.gz",
    "zf-7k-3f.sst": R13Z + "zfmt/zf-7k-3f.stencil-store.1.bin.gz",         # E1031
    "zf-7k-3f.dep": R13Z + "zfmt/zf-7k-3f.depth.1.bin.gz",
    "zf-7k-3f.txt": R13Z + "zfmt/zf-7k-3f.txt.gz",
    "zbs-c16.sst": R13Z + "zbits/zbs-c16.stencil-store.1.bin.gz",          # E1030
    "zbs-c16.dep": R13Z + "zbits/zbs-c16.depth.1.bin.gz",
    "zbs-c16.txt": R13Z + "zbits/zbs-c16.txt.gz",
    "zb2-d12.dst": R14Z + "zgran/zb2-d12.depth-store.1.bin.gz",            # E1042
    "zb2-d12.txt": R14Z + "zgran/zb2-d12.txt.gz",
    "zo-640-f0.dep": R14Z + "zodd/zo-640-f0.depth.1.bin.gz",               # E1041
    "zo-640-f0.txt": R14Z + "zodd/zo-640-f0.txt.gz",
    "zov-64x32-ctl.dep": R10X + "zov-64x32-ctl.depth.1.bin.gz",            # E996
    "zov-160x48-ctl.dep": R10X + "zov-160x48-ctl.depth.1.bin.gz",          # E996
    "zov-64x32-g0.dep": R10X + "zov-64x32-g0.depth.1.bin.gz",              # E996 (zo-c-64's rule)
    "zw-0125.dep": R10Z + "zw-0125.depth.1.bin.gz",                        # E987
    "z2-a-f0.dep": R9Z + "z2-a-f0.depth.1.bin.gz",                         # E981
}
# the kept tables whose rows the replicated rows are (tests/test_gen.py)
TABLES = ("render/closing-r15-zls/tables/zpass.txt", "render/closing-r14-zls/tables/zbits2.txt",
          "render/closing-r14-zls/tables/zgran.txt", "render/closing-r14-zls/tables/zodd.txt",
          "render/closing-r13-zls/tables/zfmt.txt", "render/closing-r13-zls/tables/zbits.txt",
          "render/closing-r10-zls/tables/zw.txt", "render/closing-r9-z2/tables/z2.txt",
          "render/closing-r10-x/tables/zov.txt")


def kept(key):
    import pins
    return pins.blob("data:" + KEPT[key])


# ---- shared (z15's helpers) ------------------------------------------------------------------


def size(w, h):
    return f"--width {w} --height {h} --max-width {w} --max-height {h}"


def tiles(w, h):
    return -(-w // 32), -(-h // 16)


def f32(u):
    """the float of the word u with its sign cleared"""
    return struct.unpack("<f", struct.pack("<I", u & 0x7FFFFFFF))[0]


def f32s(u):
    """the signed float of the word u"""
    return struct.unpack("<f", struct.pack("<I", u))[0]


def f32_bits(s):
    """the float32 the tool's strtof gives a --tri-z word (round to nearest)"""
    return struct.unpack("<I", struct.pack("<f", float(s)))[0]


def in_tile_index(x, y):
    """E465: the dword of pixel (x, y) in its 32 x 16 tile, y0 x0 y1 x1 y2 x2 y3 x3 x4"""
    x, y = x & 31, y & 15
    i = 0
    for b in range(4):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    return i | (x >> 4 & 1) << 8


def slot(x, y, g):
    """E465: the slot of pixel (x, y)'s tile at pitch G"""
    return (y >> 4) * (g + 1) + (x >> 5)


def store_dword(x, y, g):
    return TILE_DW * slot(x, y, g) + in_tile_index(x, y)


def dwords(b):
    return None if b is None else list(struct.unpack("<%dI" % (len(b) // 4), b[:len(b) // 4 * 4]))


def fill_at(f, i):
    """t10's fill_at (sgxfive-test.c): a value, index, bit:K, bytes[:S]"""
    if f == "index":
        return i & 0xFFFFFFFF
    if f.startswith("bit:"):
        return 0x3F400000 if i >> int(f[4:]) & 1 else 0x3E800000
    if f.startswith("bytes"):
        s = int(f.split(":")[1]) if ":" in f else 0
        b = 4 * i + s
        return (b & 0xFF) | ((b + 1) & 0xFF) << 8 | ((b + 2) & 0xFF) << 16 | ((b + 3) & 0xFF) << 24
    return int(f, 0)


def fill_byte(f, b):
    return fill_at(f, b // 4) >> (8 * (b % 4)) & 0xFF


def ctl_g(ctl):
    return ctl >> 3 & 0x1FF


def with_g(ctl, g):
    return (ctl & ~0xFF8) | g << 3


def less(a, b):
    """E995: the depth test less on two words, each compared with its sign cleared (NaN above)"""
    fa, fb = f32(a), f32(b)
    if math.isnan(fb):
        return not math.isnan(fa)
    return fa < fb


# ---- zpass2 ----------------------------------------------------------------------------------
ZP_CTL = 0x0017500E                         # depth loaded (1, 14) and stored, G 1 (E1029, E1050)
ZP_TWIN_CTL = 0x0017100C                    # the same without the load (E1050's zp-c-band)
ZP_FILL = "bit:9"
DEPTHS = {"z125": "0.125", "z0625": "0.0625", "z1": "0.1", "z3": "0.3", "z375": "0.375",
          "z625": "0.625", "z5e20": "0.50000095367431640625"}
ONE_FLOAT = ("z375", "z625", "z5e20")       # E1054: FL-REC0 at 0.375 and 0.625, twin 0x3f000010
PASS_MODELS = ("H-PASS-TWIN", "H-PASS-OWN")


def zp_args(w, h, ctl, dfill, z, test, pages=20):
    return (f"{MAIN} {size(w, h)} --tri-full --tri-z {z},{z},{z} --depth --depth-ctl {ctl:#010x} "
            f"--depth-fill {dfill} --depth-store --depth-store-fill {FILL_DEAD:#010x} "
            f'--depth-pages {pages} --depth-dump "$W" --poke blk:1={test:#010x} --pixels')


ZP_ARGS = {"zp2-c-467": zp_args(256, 128, 0x0017503E, "bit:9", "0.5", LESS, 40)}
for _k, _z in DEPTHS.items():
    ZP_ARGS[("zp2-c-" if _k == "z125" else "zp2-p-") + _k] = zp_args(64, 32, ZP_CTL, ZP_FILL, _z, LESS)
    ZP_ARGS[f"zp2-t-{_k}"] = zp_args(64, 32, ZP_TWIN_CTL, ZP_FILL, _z, LESS)
ZP_CONTROL = {"zp2-c-z125": ("zp-z125.dst", 2048), "zp2-c-467": ("zp-c-467.dst", 16384)}


def pass_name(k):
    return ("zp2-c-" if k == "z125" else "zp2-p-") + k


def zp_loaded(i):
    return fill_at(ZP_FILL, i) & 0x7FFFFFFF


def pass_predict(k, model, twin=None):
    """({store dword: value}, drawn) of the pass at depth key k under model: the 2048 dwords of
    the target's four tiles (64 x 32 at G 1: dword i is slot i // 512); twin the twin's store
    dwords (H-PASS-TWIN), else the depth's own float"""
    zb = f32_bits(DEPTHS[k])
    out, drawn = {}, 0
    for i in range(2048):
        p = twin[i] if model == "H-PASS-TWIN" else zb
        lo = zp_loaded(i)
        if less(p, lo):
            out[i], drawn = p, drawn + 1
        else:
            out[i] = lo
    return out, drawn


def pass_drawn(k):
    """the frozen drawn count: the depth's float against the loaded 0.25 / 0.75 (the twin's
    floats lie on the same side of both: every twin E1050 and E1054 kept did)"""
    return pass_predict(k, "H-PASS-OWN")[1]


# ---- zbits4 ----------------------------------------------------------------------------------
ST_CTL = 0x0017300E                        # E988's st1: stencil loaded (1, 13) and stored, G 1
ISP2_B0 = 0x040501FF                       # EQUAL, invert on pass, compare mask 0x01 (E988)
ISP2_MASKFF = 0x0405FFFF                   # the same with the compare mask 0xff
COL23 = (0x3F, 0x80, 0x00, 0x00, 0x80, 0x00, 0x00, 0x3F, 0x00, 0x00, 0x3F, 0x80, 0x00, 0x3F,
         0x80, 0x00)                       # E1042's zb2-b23, E1053's H23-MOD16
BG_RD17 = 0x35A                            # t10's isp_bgobj 0x300 with STENCIL 0x5a
B0_MODELS = ("H-B0", "H-B0-NOSTORE")
B23_MODELS = ("H23-FIXED", "H23-REF", "H23-MASK", "H23-BG")


def st_args(ctl, w=64, h=32, sfill="bytes", isp2=ISP2_B0, extra=""):
    """E988's st1 form (zb2-c-base's argv)"""
    return (f"{MAIN} --tri-full {size(w, h)} --depth --depth-ctl {ctl:#010x} --depth-fill "
            f"0x3f800000 --stencil --stencil-fill {sfill} --stencil-store --isp2 {isp2:#010x} "
            f'--depth-dump "$W" --pixels{extra}')


def zf_args(ctl, z, sfill="index"):
    """E1031's zfmt form (zf-flat-f6, zf-7k-3f)"""
    return (f"{MAIN} {size(64, 32)} --tri-full --tri-z {z} --depth --depth-ctl {ctl:#010x} "
            f"--depth-fill 0xdeadbeef --stencil --stencil-fill {sfill} --stencil-store --depth-dump "
            f'"$W" --poke blk:1={LESS:#010x}')


def zbs_args(ctl):
    """E1030's zbits form (zbs-c16): st1 with --depth-fill 0x3f800000"""
    return st_args(ctl)


F6_CTL, F7_CTL = 0x0617300E, 0x0717300E
ZB4_ARGS = {
    "zb4-c-base": st_args(ST_CTL),
    "zb4-c-b23": st_args(ST_CTL | 1 << 23),
    "zb4-c-f6": zf_args(F6_CTL, "0.5,0.5,0.5"),
    "zb4-b0-st": st_args(ST_CTL | 1),
    "zb4-b0-f6": zf_args(F6_CTL | 1, "0.5,0.5,0.5"),
    "zb4-b0-f7": zf_args(F7_CTL | 1, "0.25,0.75,0.25", "0x3f3f3f3f"),
    "zb4-b0-c16": st_args((ST_CTL & ~(1 << 16)) | 1),
    "zb4-20-f6": zf_args(F6_CTL & ~(1 << 20), "0.5,0.5,0.5"),
    "zb4-20-f7": zf_args(F7_CTL & ~(1 << 20), "0.25,0.75,0.25", "0x3f3f3f3f"),
    "zb4-23-ref": st_args(ST_CTL | 1 << 23, extra=" --poke blk:1^=0x80"),
    "zb4-23-msk": st_args(ST_CTL | 1 << 23, isp2=ISP2_MASKFF),
    "zb4-23-bg": st_args(ST_CTL | 1 << 23, extra=f" --kpoke-render 1:rd:17={BG_RD17:#x}"),
}
# the kept twin of each zbits4 row (its depth dump, stencil store, text) and the depth fill
ZB4_TWIN = {"zb4-c-base": "zb2-c-base", "zb4-c-b23": "zb2-b23", "zb4-c-f6": "zf-flat-f6",
            "zb4-b0-st": "zb2-c-base", "zb4-b0-f6": "zf-flat-f6", "zb4-b0-f7": "zf-7k-3f",
            "zb4-b0-c16": "zbs-c16", "zb4-20-f6": "zf-flat-f6", "zb4-20-f7": "zf-7k-3f"}
ZB4_CONTROL = {"zb4-c-base": ("drawn", 1024), "zb4-c-b23": ("drawn", 1536),
               "zb4-c-f6": ("depth_changed", 176)}
ZB4_READS = {"zb4-c-base": "drawn,sst_changed", "zb4-c-b23": "drawn,sst_changed",
             "zb4-c-f6": "depth_changed,sst_changed"}
# bit 23's rows: (reference, compare mask, the rival whose source the row moves)
B23_ROWS = {"zb4-23-ref": (0x80, 0x01, "H23-REF"), "zb4-23-msk": (0x00, 0xFF, "H23-MASK"),
            "zb4-23-bg": (0x00, 0x01, "H23-BG")}


def depth_fill_of(args):
    a = args.split()
    return int(a[a.index("--depth-fill") + 1], 0)


def st_pos(x, y, g=1):
    """E988: the stencil byte of pixel (x, y): 512 bytes a tile at the slot, the in-tile index"""
    return TILE_DW * slot(x, y, g) + in_tile_index(x, y)


def b23_predict(name, model):
    """({stencil-store byte: value}, drawn) of a bit-23 row under model (64 x 32, G 1); None
    where the model names no bytes (a rival on its own row: the bytes are not COL23)"""
    ref, mask, own = B23_ROWS[name]
    if model == own:
        return None
    out, drawn = {}, 0
    for y in range(32):
        for x in range(64):
            r = COL23[x % 16]
            p = st_pos(x, y)
            if (r & mask) == (ref & mask):
                out[p], drawn = r ^ 0xFF, drawn + 1
            else:
                out[p] = r
    return out, drawn


# ---- zovp ------------------------------------------------------------------------------------
OVL_MODELS = ("H-OVL-PASS", "H-OVL-FIRST", "H-OVL-SKIP")
OVS_MODELS = ("H-OVL-PASS", "H-OVL-SKIP")
OVL_FILL = "0x3e4ccccd"                     # 0.2f
# name: (w, h, g, the kept full-pitch reference, its pitch)
OVP_ROWS = {"zo-p-64": (64, 32, 0, "zov-64x32-ctl.dep", 1),
            "zo-p-160": (160, 48, 2, "zov-160x48-ctl.dep", 4)}
OVS_ROWS = {"zo-s-64": (64, 32, 0), "zo-s-160": (160, 48, 2)}


def zx(h):
    """The largest power of two at most 1/(2H) (r10-x gen/z.py)."""
    v = 1.0
    while v > 1 / (2 * h):
        v /= 2
    return v


def ovp_args(w, h, ctl, fill=OVL_FILL):
    return (f"{MAIN} {size(w, h)} --tri-v 0,0,{512 * w},0,0,{512 * h} --tri-z 0,{zx(h)!r},1 "
            f"--depth --depth-ctl {ctl:#010x} --depth-fill {fill} --depth-store --depth-store-fill "
            f'{FILL_DEAD:#010x} --depth-pages 20 --depth-dump "$W" --poke blk:1={LESS:#010x} --pixels')


def macro(w, h):
    """libsgxfive render.c sgxfive_tiling (r10-x gen/z.py): n macrotiles a side, mx x my regions"""
    tx, ty = tiles(w, h)
    n = 4 if w * h >= 640 * 480 else 2
    return n, ((tx + n - 1) // n + 3) & ~3, ((ty + n - 1) // n + 3) & ~3


def header_rank(w, h):
    """{(tx, ty): its place in the region header order} (r10-x gen/z.py, sgx-pipe ta.rs)"""
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


def owners(w, h, g, late=True):
    """{slot: the tile that owns it}: visited last (late) or first in header order"""
    rank = header_rank(w, h)
    best = {}
    for t, k in rank.items():
        s = t[1] * (g + 1) + t[0]
        if s not in best or (k > rank[best[s]] if late else k < rank[best[s]]):
            best[s] = t
    return best


def shared_slots(w, h, g):
    seen = {}
    for t in header_rank(w, h):
        seen.setdefault(t[1] * (g + 1) + t[0], []).append(t)
    return {s for s, ts in seen.items() if len(ts) > 1}


def ovp_predict(full, w, h, g, gref, model, fill=OVL_FILL, load=True):
    """({store dword: value}, drawn) of the depth pass at an overlapping pitch under model: the
    plane's float of pixel (x, y) is the reference's dword at pitch gref; the start the load's
    dword at the tile's slot (sign cleared) or the clear 1.0"""
    tw, th = tiles(w, h)
    shared = shared_slots(w, h, g)
    own = owners(w, h, g, late=model != "H-OVL-FIRST")
    out, drawn = {}, 0
    for r in range(th):
        for c in range(tw):
            s = r * (g + 1) + c
            skip = not load or (model == "H-OVL-SKIP" and s in shared)
            for yy in range(16):
                for xx in range(32):
                    x, y = 32 * c + xx, 16 * r + yy
                    d = TILE_DW * s + in_tile_index(x, y)
                    p = full[store_dword(x, y, gref)]
                    start = CLEAR if skip else fill_at(fill, d) & 0x7FFFFFFF
                    passed = less(p, start)
                    drawn += passed and x < w and y < h
                    if own[s] == (c, r):
                        out[d] = p if passed else start
    return out, drawn


def ovs_predict(w, h, g, model):
    """({stencil-store byte: value}, drawn) of the stencil pass at an overlapping pitch: each tile
    reads its slot's loaded byte (E988), or 0 where H-OVL-SKIP has it skip the load; the test
    passes where the byte's bit 0 is 0 and stores it inverted, else the byte"""
    tw, th = tiles(w, h)
    shared = shared_slots(w, h, g)
    own = owners(w, h, g)
    out, drawn = {}, 0
    for r in range(th):
        for c in range(tw):
            s = r * (g + 1) + c
            for yy in range(16):
                for xx in range(32):
                    x, y = 32 * c + xx, 16 * r + yy
                    p = st_pos(x, y, g)
                    rd = 0 if model == "H-OVL-SKIP" and s in shared else fill_byte("bytes", p)
                    passed = rd & 1 == 0
                    drawn += passed and x < w and y < h
                    if own[s] == (c, r):
                        out[p] = rd ^ 0xFF if passed else rd
    return out, drawn


NAN_MODELS = ("H-NAN-SAT", "H-NAN-ZERO", "H-NAN-LOW")
# name: (format, the load buffer's value)
NAN_ROWS = {"zo-n1-7fc": (1, 0x7FC00000), "zo-n2-7fc": (2, 0x7FC00000),
            "zo-n1-ffc": (1, 0xFFC00000), "zo-n1-7f8": (1, 0x7F800001),
            "zo-n2-7f8": (2, 0x7F800001)}


def nan_word(fmt, v, model):
    u = v & 0x7FFFFFFF
    if model == "H-NAN-SAT":
        d = 0xFFFFFF
    elif model == "H-NAN-ZERO":
        d = 0
    else:
        d = u & 0xFFFFFF
    return d if fmt == 1 else (d >> 8) | (d >> 8) << 16


def nan_predict(name, model):
    fmt, v = NAN_ROWS[name]
    return {i: nan_word(fmt, v, model) for i in range(2048 if fmt == 1 else 1024)}


ZO_ARGS = {"zo-c-64": ovp_args(64, 32, 0x00171004), "zo-c-f1": zp_args(64, 32, ZP_CTL | 1 << 24,
                                                                       ZP_FILL, "0.375", LESS)}
for _n, (_w, _h, _g, _r, _gr) in OVP_ROWS.items():
    ZO_ARGS[_n] = ovp_args(_w, _h, with_g(ZP_CTL, _g))
for _n, (_w, _h, _g) in OVS_ROWS.items():
    ZO_ARGS[_n] = st_args(with_g(ST_CTL, _g), _w, _h)
for _n, (_f, _v) in NAN_ROWS.items():
    ZO_ARGS[_n] = zp_args(64, 32, ZP_CTL | _f << 24, f"{_v:#010x}", "0.5", NEVER)
ZB4_ARGS["zb4-20-d12"] = (f"{MAIN} {size(64, 32)} --tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl "
                          f"0x0007400e --depth-fill index --depth-store --depth-store-fill 0x3e800000 "
                          f'--depth-pages 20 --depth-dump "$W" --poke blk:1=0x00000200 --pixels '
                          f"--kpoke-render 1:rd:12=0x1000")
ZB4_ARGS["zb4-20-640"] = (f"{MAIN} {size(640, 480)} --tri-v 0,0,327680,0,0,245760 --tri-z "
                          f"0,0.0009765625,1 --depth --depth-ctl 0x0007109c --depth-fill 0xdeadbeef "
                          f'--depth-dump "$W" --poke blk:1={LESS:#010x}')
ZB4_TWIN.update({"zb4-20-d12": "zb2-d12", "zb4-20-640": "zo-640-f0"})
ZO_CONTROL = {"zo-c-64": ("dst_changed", 1536), "zo-c-f1": ("dst_changed", 2048)}
ZO_READS = {"zo-c-64": "drawn,dst_changed", "zo-c-f1": "drawn,dst_changed"}
ZO_C_F1_DRAWN = 1024


# ---- zoff ------------------------------------------------------------------------------------
ZW_CTL = 0x0017103C                        # format 0, G 7 (E977, E987)
OFF_MODELS = ("H-LIN", "H-POLYCLIP")
SCALE_MODELS = ("H-LIN", "H-LIN-S", "H-POLYCLIP")
# name: (w, s)
ZOFF_ROWS = {"zw2-w7": (0.4375, 0.5), "zw2-w6": (0.375, 0.5), "zw2-w5": (0.3125, 0.5),
             "zw2-w3": (0.1875, 0.5), "zw2-s25": (0.25, 0.25), "zw2-w1": (0.0625, 0.5),
             "zw2-s75": (0.25, 0.75), "zw2-w0": (0.0, 0.5)}
LIN_TOL, CLIP_TOL = 1e-5, 1e-4


def zw_args(w, s=None):
    return (f"{MAIN} {size(256, 128)} --tri-v 0,0,131072,0,0,65536 --tri-z 0,1,0 --depth "
            f'--depth-ctl {ZW_CTL:#010x} --depth-fill {FILL_DEAD:#010x} --depth-dump "$W" '
            f"--poke blk:1={LESS:#010x} --poke blk:10={f32_bits(w):#010x}"
            + (f" --poke blk:11={f32_bits(s):#010x}" if s is not None else ""))


ZW_ARGS = {"zw2-c-0125": zw_args(0.125)}
for _n, (_w, _s) in ZOFF_ROWS.items():
    ZW_ARGS[_n] = zw_args(_w, None if _s == 0.5 else _s)


def t_of(x):
    return (x + 0.5) / 512


def lin_k(model, w, s):
    return 1.6 * w + 0.2 if model == "H-LIN" else 1.6 * w + 0.4 * s


def zoff_pixel(model, w, s, x):
    """(drawn, depth) of pixel column x (every row alike: t = x / 512) under model"""
    t = t_of(x)
    if model == "H-POLYCLIP":
        z = s * (2 * t - 1) + w
        return (z > 0), z
    return True, lin_k(model, w, s) * t


def zoff_drawn(model, w, s):
    return 128 * sum(1 for x in range(256) if zoff_pixel(model, w, s, x)[0])


def bend(dep, w=0.125):
    """E987's bend: the pixels of a kept zw row whose depth is off H-LIN (1e-5 relative)"""
    k = 1.6 * w + 0.2
    out = set()
    for y in range(128):
        for x in range(256):
            v = f32s(dep[store_dword(x, y, 7)])
            if abs(v - k * t_of(x)) > LIN_TOL * k * t_of(x):
                out.add((x, y))
    return out


_BEND = []


def BEND():
    """the frozen bend set (from E987's kept zw-0125; gen/oq069.py shows E981's z2-a-f0 alike)"""
    if not _BEND:
        _BEND.append(frozenset(bend(dwords(kept("zw-0125.dep")))))
    return _BEND[0]


def zoff_fit(dep, model, w, s, skip=frozenset()):
    """(held, text) of a zw dump under model: every pixel outside skip as the model's (drawn ones
    within the tolerance, undrawn ones the fill)"""
    hit = miss = 0
    for y in range(128):
        for x in range(256):
            if (x, y) in skip:
                continue
            dr, z = zoff_pixel(model, w, s, x)
            u = dep[store_dword(x, y, 7)]
            if not dr:
                ok = u == FILL_DEAD
            elif model == "H-POLYCLIP":
                ok = u != FILL_DEAD and abs(f32s(u) - z) <= CLIP_TOL
            else:
                ok = u != FILL_DEAD and abs(f32s(u) - z) <= LIN_TOL * abs(z)
            hit, miss = hit + ok, miss + (not ok)
    return miss == 0, f"{hit}/{hit + miss}"


# ---- the rows --------------------------------------------------------------------------------
# A stage's rows all write the dump its scorer reads (REQUIRED is per row): the stencil overlap
# rows run in zbits4 (stencil store), bit 20's d12 row in zovp (depth store) and its 640 row in
# zoff (depth only). Each pass row's twin follows it. Rows reaching a range never run are last in
# their stage (bit 23's background poke, the vertex depth -0.5); zoff ends the session on a stop.
STAGE_ROWS = {
    "zpass2": ["zp2-c-467", "zp2-c-z125", "zp2-t-z125", "zp2-p-z0625", "zp2-t-z0625", "zp2-p-z1",
               "zp2-t-z1", "zp2-p-z3", "zp2-t-z3", "zp2-p-z375", "zp2-t-z375", "zp2-p-z625",
               "zp2-t-z625", "zp2-p-z5e20", "zp2-t-z5e20"],
    "zbits4": ["zb4-c-base", "zb4-c-b23", "zb4-c-f6", "zb4-b0-st", "zb4-b0-f6", "zb4-b0-f7",
               "zb4-b0-c16", "zb4-20-f6", "zb4-20-f7", "zo-s-64", "zo-s-160", "zb4-23-ref",
               "zb4-23-msk", "zb4-23-bg"],
    "zovp": ["zo-c-64", "zo-c-f1", "zo-p-64", "zo-p-160", *NAN_ROWS, "zb4-20-d12"],
    "zoff": ["zw2-c-0125", "zb4-20-640", *ZOFF_ROWS],
}
ARGS = {**ZP_ARGS, **ZB4_ARGS, **ZO_ARGS, **ZW_ARGS}
STAGE_OF = {n: s for s, ns in STAGE_ROWS.items() for n in ns}


def kept_drawn(twin):
    import re
    m = re.search(r"^tri \d+x\d+ #1: (\d+) triangle", kept(twin + ".txt").decode(), re.M)
    return int(m.group(1))


def row(n):
    """(set, knobs, {quantity: {model: value}}) of row n"""
    if n in ZP_CONTROL:
        return "control", "expectdiff reads:drawn,dst_changed", {
            "store": {"H-KEPT": "kept:" + ZP_CONTROL[n][0]}, "drawn": {"H-KEPT": str(ZP_CONTROL[n][1])}}
    if n.startswith("zp2-t-"):
        k = n[6:]
        if k == "z125":
            return "heldout", "expectdiff", {
                "store": {"H-PASS-TWIN": "rule:twin", "H-PASS-OWN": "rule:own"},
                "drawn": {m: str(pass_drawn(k)) for m in PASS_MODELS}}
        return "reading", "expectdiff", {}
    if n.startswith("zp2-p-"):
        k = n[6:]
        ms = PASS_MODELS + (("H-PASS-EXACT",) if k in ONE_FLOAT else ())
        return "heldout", "expectdiff", {
            "store": {m: ("rule:twin" if m == "H-PASS-TWIN" else
                          f"v={f32_bits(DEPTHS[k]):#010x} where drawn") for m in ms},
            "drawn": {m: str(pass_drawn(k)) for m in ms}}
    if n in ZB4_CONTROL:
        k, v = ZB4_CONTROL[n]
        return "control", f"expectdiff reads:{ZB4_READS[n]}", {
            k: {"H-KEPT": str(v)}, "dumps": {"H-KEPT": "kept:" + ZB4_TWIN[n]}}
    if n.startswith("zb4-b0-"):
        return "heldout", "expectdiff", {
            "dumps": {"H-B0": "kept:" + ZB4_TWIN[n], "H-B0-NOSTORE": "fill"},
            "drawn": {"H-B0": "0", "H-B0-NOSTORE": "0"}}
    if n.startswith("zb4-20-"):
        return "heldout", "expectdiff", {"dumps": {"H-INERT20": "kept:" + ZB4_TWIN[n]},
                                         "drawn": {"H-INERT20": str(kept_drawn(ZB4_TWIN[n]))}}
    if n in B23_ROWS:
        q = {"read": {}, "drawn": {}}
        for m in B23_MODELS:
            p = b23_predict(n, m)
            q["read"][m] = "COL23" if p else "not COL23"
            q["drawn"][m] = str(p[1]) if p else "rule"
        return "heldout", "expectdiff", q
    if n in OVS_ROWS:
        return "heldout", "expectdiff", {
            "stencil": {m: "rule" for m in OVS_MODELS},
            "drawn": {m: str(ovs_predict(*OVS_ROWS[n], m)[1]) for m in OVS_MODELS}}
    if n in ZO_CONTROL:
        k, v = ZO_CONTROL[n]
        q = {"store": {"H-KEPT": "kept:zp-f1.dst" if n == "zo-c-f1" else "rule:E996 owner"},
             k: {"H-KEPT": str(v)}}
        return "control", f"expectdiff reads:{ZO_READS[n]}", q
    if n in OVP_ROWS:
        w, h, g, ref, gref = OVP_ROWS[n]
        full = dwords(kept(ref))
        return "heldout", "expectdiff", {
            "store": {m: "rule" for m in OVL_MODELS},
            "drawn": {m: str(ovp_predict(full, w, h, g, gref, m)[1]) for m in OVL_MODELS}}
    if n in NAN_ROWS:
        return "heldout", "expectdiff", {
            "store": {m: f"all {nan_predict(n, m)[0]:#010x}" for m in NAN_MODELS},
            "drawn": {m: "0" for m in NAN_MODELS}}
    if n == "zw2-c-0125":
        return "control", "expectdiff reads:drawn,depth_changed", {
            "dump": {"H-KEPT": "kept:zw-0125.dep"}, "drawn": {"H-KEPT": "32768"}}
    w, s = ZOFF_ROWS[n]
    ms = OFF_MODELS if s == 0.5 else SCALE_MODELS
    return "heldout", "expectdiff", {
        "depth": {m: (f"{lin_k(m, w, s):.6g} t outside BEND" if m != "H-POLYCLIP" else
                      f"cut at t {(s - w) / (2 * s):.6g}") for m in ms},
        "drawn": {m: str(zoff_drawn(m, w, s)) for m in ms}}


def jobs():
    """[(stage, name, set, knobs, args, {quantity: {model: value}})] in run order"""
    return [(st, n, *row(n)[:2], ARGS[n], row(n)[2]) for st, ns in STAGE_ROWS.items() for n in ns]
