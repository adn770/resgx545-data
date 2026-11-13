# SPDX-License-Identifier: MIT
"""addr.py: stage addr2 (S9-geo, Q177): r8-geo's gen/addr.py (resgx545-data
render/closing-r8-geo/gen/addr.py) extended to other sizes, T3 values, both axes in mode 4 and a
mode 5 reading. Standard library only.

Every texture sits at page 12 of a 32-page scratch buffer whose every dword is named (dword i =
0xD0000000 | i, the probe's own fill), so every read decodes to the dword it came from: the
program's T2 word 0x5CAFC000 (the scratch address + 0xC000, SCRATCH_IMM) and `probe
--scratch-pages 32` on every row (tests/test_r9geo.py checks both). The index read is the value
less 0xD0000000 less 12288.

Textures: twiddled 32-bit (T1 0x0c00N0N, type 0), N = 8, 16 or 32. The texel index (E561, E565's
bd-u0 and bd-v0): Morton(s, t) with t in bit 0 for N <= 16; at 32 the 16 x 16 tiles in raster
order with s fast, + 256 (s >> 4) + 512 (t >> 4).

The swept coordinate takes 128 positions at one texel a step on every pair of rows, u = (p - 64 +
1/2) / N for p = x | (y & 1) << 6 (r8-geo's form at N = 16), so texels -64 to 63; the other sits
on texel N / 2's centre. The uv job sweeps u along x (texels -24 to 39) and v down the rows
(texels -8 to 23).

Frozen, nothing fitted (every row held out but the control and the replicate):
  H-MASK-V     E932's v reading on the swept axis: modes 4 and 5 repeat, 6 and 7 clamp
  H-OFF180     H-MASK-V's index + 180 dwords at every size (E932's u reading, post hoc there)
  H-OFFSCALE   + 180 N^2 / 256 dwords: 45 at 8 x 8, 180 at 16, 720 at 32 x 32
  H-OFFNONE    no offset at sizes other than 16 (+ 180 at 16)
  H-T3-INERT   + 180 at 16 x 16 whatever T3 (the T3 rows' null; their reading table otherwise)
  H-OFF360     uv job: + 180 for each axis in modes 4 to 7 [infer], against H-OFF180's one
  H-U5-E932    mode 5 on u: the index E932's addr-u5 read at each position, replicated
The control is mode 0 on u (repeat) at 16 x 16, E932's control."""
import texprog as T

BASE_PAGE = 12
PAGES = 32
BASE = BASE_PAGE * 1024           # dwords
T0_BASE = 0x07fe0000
T1 = {8: 0x0c007007, 16: 0x0c00f00f, 32: 0x0c01f01f}
T2 = 0x5cafc000                   # SCRATCH_IMM | 0xC000: the scratch address + 12 pages
T3 = 0x00800800                   # E565's, every row but the T3 rows
SMP = "smp2d r10, r24, r20, drc0"
# E932's addr-u5 per position (render-closing-r8-geo out/20261113-015842 score-addr.txt READ line):
# the index read less 12288 at p = 0 .. 127
E932_U5 = [140] * 64 + [244, 246, 252, 254, 276, 278, 284, 286, 372, 374, 380, 382, 404, 406, 412,
                        414] + [156] * 48


def sweep(n):
    """("p7", K, C): u = K (1 + p / 128) + C = (p - 64 + 1/2) / n."""
    return ("p7", T.bits(128.0 / n), T.bits(-191.5 / n))


def centre(n):
    return ("bits", T.bits((n // 2 + 0.5) / n))


UV_U = ("lin", "x", T.bits(4.0), T.bits(-5.46875))     # (x - 24 + 1/2) / 16
UV_V = ("lin", "y", T.bits(2.0), T.bits(-2.46875))     # (y - 8 + 1/2) / 16


def jobs():
    """[(name, set, n, umode, vmode, t3, kind)] in run order: the control first."""
    out = [("addr-ctl-u0", "control", 16, 0, 0, T3, "u"),
           ("addr-u4-rep", "replicate", 16, 4, 0, T3, "u")]
    out += [("addr-u%d-n%d" % (m, n), "heldout", n, m, 0, T3, "u") for n in (8, 32) for m in (4, 6)]
    out += [("addr-u4-t3-%08x" % t3, "heldout", 16, 4, 0, t3, "u")
            for t3 in (0x00000000, 0x00000800, 0x00800000)]
    out += [("addr-uv4", "heldout", 16, 4, 4, T3, "uv"),
            ("addr-u5-rep", "replicate", 16, 5, 0, T3, "u")]
    return out


def coords(n, kind):
    return (UV_U, UV_V) if kind == "uv" else (sweep(n), centre(n))


def twords(n, umode, vmode, t3):
    return (T0_BASE | umode << 6 | vmode << 3, T1[n], T2, t3)


def index(s, t, n):
    """The twiddled texel index (E561's law above 16)."""
    nb = min(n, 16).bit_length() - 1
    i = 0
    for b in range(nb):
        i |= (((t & 15) >> b) & 1) << (2 * b) | (((s & 15) >> b) & 1) << (2 * b + 1)
    if n > 16:
        i += 256 * (s >> 4) + 256 * (n // 16) * (t >> 4)
    return i


def wrap(v, mode, n):
    if mode in (0, 4, 5):
        return v % n
    return min(max(v, 0), n - 1)


def texel(n, kind, x, y):
    """(s, t) of the pixel, unwrapped."""
    cs = [T.coord(c, x, y) for c in coords(n, kind)]
    return tuple(int((c * n).__floor__()) for c in cs)


def offset(model, n, umode, vmode):
    if umode == 0:
        return 0
    if model in ("H-OFF180", "H-T3-INERT"):
        return 180
    if model == "H-OFFSCALE":
        return 180 * n * n // 256
    if model == "H-OFFNONE":
        return 180 if n == 16 else 0
    if model == "H-OFF360":
        return 180 * ((umode >= 4) + (vmode >= 4))
    if model == "H-MASK-V":
        return 0
    raise ValueError(model)


def predict(n, umode, vmode, kind, model, x, y):
    """The dword index read (less 12288)."""
    s, t = texel(n, kind, x, y)
    if model == "H-U5-E932":
        return E932_U5[x | (y & 1) << 6]
    return index(wrap(s, umode, n), wrap(t, vmode, n), n) + offset(model, n, umode, vmode)


def models(name, umode, n, kind):
    """The frozen models of a row, in the scorer's order."""
    if umode == 0:
        return ("REPEAT",)
    if kind == "uv":
        return ("H-OFF180", "H-OFF360", "H-MASK-V")
    if "-t3-" in name:
        return ("H-T3-INERT",)
    if umode == 5:
        return ("H-U5-E932",)
    if n == 16:
        return ("H-OFF180",)
    return ("H-OFF180", "H-OFFSCALE", "H-OFFNONE")


def image(n, umode, vmode, kind, model):
    m = "H-MASK-V" if model == "REPEAT" else model
    return {(x, y): predict(n, umode, vmode, kind, m, x, y) for y in range(T.H) for x in range(T.W)}
