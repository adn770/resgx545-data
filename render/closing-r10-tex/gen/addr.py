# SPDX-License-Identifier: MIT
"""addr.py: stage addr3 (S10-tex, Q177, seeds plan closing10/seeds/exp-seeds-r10.md section 2):
r9-geo's gen/addr.py (resgx545-data render/closing-r9-geo/gen/addr.py) extended to textures whose
width and height differ. Standard library only.

Every texture sits at page 12 of a 32-page scratch buffer whose every dword is named (dword i =
0xD0000000 | i, the probe's own fill), so every read decodes to the dword it came from: T2
0x5CAFC000 (the scratch address + 0xC000) and `probe --scratch-pages 32` on every row (the
generator test checks both and that every rival's farthest read is inside the mapping). The index
read is the value less 0xD0000000 less 12288.

Textures: twiddled 32-bit, type 0, T1 = 0x0c000000 | (W - 1) << 12 | (H - 1) (E565's t1tw,
tools/texture/p1132/gen/catalog.py). The texel index is E561's tile law: tiles of up to 16 x 16
texels (the whole side when it is shorter), each interleaved with t in bit 0 and the longer side's
extra bits above (texmodel's morton), the tiles in raster order, s first (E561: 14 sizes, 8 to 128
a side, non-square ones included; E565's 32 x 8 reads it with + 308, seeds q177/ns_read.out).

The swept u takes 128 positions at one texel a step on every pair of rows, u = (p - 64 + 1/2) / W
for p = x | (y & 1) << 6 (r9-geo's form with W for N), so texels -64 to 63; v sits on texel H / 2's
centre (in the texture in every mode).

Frozen, nothing fitted (E957 named the rivals; the seeds' q177/rivals.out):
  H-W      H-MASK-V's index + 8 W + 52 dwords (E957's fit, the width; E565's 32 x 8 reads 308)
  H-H      + 8 H + 52 (the height)
  H-SQ     + 8 sqrt(W H) + 52 (the size as a square's side; only where it is an integer)
  H-WH     + 4 (W + H) + 52
  mode 5 (u mode 5, v mode 0):
  H-B5     inside the texture H-W's read; left of it (s < 0) dword 5 W + 52 + t, right of it
           (s >= W) 6 W + 52 + t, t = H / 2 the texel row (seeds finding 2: E565's 32 x 8 reads
           212 + t and 244 + t, E932's 16 x 16 140 and 156 at t = 8)
  H-B5H    the same with H for W everywhere [infer: the rival the non-square rows part]
  REPEAT   the control (u mode 0): H-MASK-V's index, no offset (E932's, E957's control)
H-MASK-V is E932's v reading on the swept axis: modes 0, 4, 5 repeat, 6, 7 clamp."""
import texprog as T

BASE_PAGE = 12
PAGES = 32
BASE = BASE_PAGE * 1024           # dwords
T0_BASE = 0x07fe0000
T2 = 0x5cafc000                   # SCRATCH_IMM | 0xC000: the scratch address + 12 pages
T3 = 0x00800800                   # E565's, every row
SMP = "smp2d r10, r24, r20, drc0"

# name, set, W, H, u mode, v mode, models (the scorer's order)
MODE4 = ("H-W", "H-H", "H-SQ", "H-WH")
MODE5 = ("H-B5", "H-B5H")
JOBS = [
    ("addr3-ctl-u0", "control", 16, 16, 0, 0, ("REPEAT",)),
    ("addr3-u4-rep", "replicate", 16, 16, 4, 0, MODE4),
    ("addr3-ns32x8-u4", "replicate", 32, 8, 4, 4, MODE4),
    ("addr3-8x32-u4", "heldout", 8, 32, 4, 0, MODE4),
    ("addr3-16x64-u4", "heldout", 16, 64, 4, 0, MODE4),
    ("addr3-64x16-u4", "heldout", 64, 16, 4, 0, MODE4),
    ("addr3-64x64-u4", "heldout", 64, 64, 4, 0, MODE4),
    ("addr3-64x64-u6", "heldout", 64, 64, 6, 0, MODE4),
    ("addr3-4x4-u4", "heldout", 4, 4, 4, 0, MODE4),
    ("addr3-16x32-u5", "heldout", 16, 32, 5, 0, MODE5),
    ("addr3-32x16-u5", "heldout", 32, 16, 5, 0, MODE5),
]
# the rows whose rivals part (the stage's question: what sets the offset)
NONSQUARE = ("addr3-8x32-u4", "addr3-16x64-u4", "addr3-64x16-u4")


def t1(w, h):
    return 0x0c000000 | (w - 1) << 12 | (h - 1)


def sweep(w):
    """("p7", K, C): u = K (1 + p / 128) + C = (p - 64 + 1/2) / w."""
    return ("p7", T.bits(128.0 / w), T.bits(-191.5 / w))


def centre(h):
    return ("bits", T.bits((h // 2 + 0.5) / h))


def coords(w, h):
    return (sweep(w), centre(h))


def twords(w, h, umode, vmode):
    return (T0_BASE | umode << 6 | vmode << 3, t1(w, h), T2, T3)


def morton(x, y, w, h):
    """texmodel's morton (resgx545 tools/texture/p1132/recompute/texmodel.py): y in bit 0, the
    longer side's extra bits above."""
    bw, bh = max(w, 1).bit_length() - 1, max(h, 1).bit_length() - 1
    common = min(bw, bh)
    i = 0
    for b in range(common):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    rest = (x if bw > bh else y) >> common
    return i | rest << (2 * common)


def index(s, t, w, h):
    """E561's tile law: tiles of min(w, 16) x min(h, 16), interleaved, in raster order s first."""
    tw, th = min(w, 16), min(h, 16)
    return morton(s % tw, t % th, tw, th) + tw * th * (s // tw + (w // tw) * (t // th))


def wrap(v, mode, n):
    if mode in (0, 4, 5):
        return v % n
    return min(max(v, 0), n - 1)


def texel(w, h, x, y):
    """(s, t) of the pixel, unwrapped."""
    cs = [T.coord(c, x, y) for c in coords(w, h)]
    return int((cs[0] * w).__floor__()), int((cs[1] * h).__floor__())


def offset(model, w, h):
    if model == "REPEAT":
        return 0
    if model in ("H-W", "H-B5"):
        return 8 * w + 52
    if model in ("H-H", "H-B5H"):
        return 8 * h + 52
    if model == "H-SQ":
        r = int(round((w * h) ** 0.5))
        return 8 * r + 52 if r * r == w * h else None
    if model == "H-WH":
        return 4 * (w + h) + 52
    raise ValueError(model)


def predict(w, h, umode, vmode, model, x, y):
    """The dword index read (less 12288), or None where the model has no prediction."""
    s, t = texel(w, h, x, y)
    off = offset(model, w, h)
    if off is None:
        return None
    if model in ("H-B5", "H-B5H") and not 0 <= s < w:
        side = w if model == "H-B5" else h
        tt = wrap(t, vmode, h)
        return (5 if s < 0 else 6) * side + 52 + tt
    return index(wrap(s, umode, w), wrap(t, vmode, h), w, h) + off


def image(w, h, umode, vmode, model):
    """[2048 indices] raster order, or None when the model has no prediction for the row."""
    out = [predict(w, h, umode, vmode, model, x, y) for y in range(T.H) for x in range(T.W)]
    return None if any(v is None for v in out) else out


def jobs():
    """[(name, set, w, h, umode, vmode, {model: [index]})] in run order: the control first."""
    out = []
    for name, st, w, h, um, vm, models in JOBS:
        ims = {m: image(w, h, um, vm, m) for m in models}
        out.append((name, st, w, h, um, vm, {m: v for m, v in ims.items() if v is not None}))
    return out
