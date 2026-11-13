"""q078_rule.py: the rules scored by score_q078.py. POST HOC: written after both E564 images
(an-t3b11, an-t3b12) and the control had been decoded in the inventory step, so nothing here is
a held-out prediction; see NOTE.md. Texture: 64x64 32-bit twiddled chain, 7 levels (64..1), levels
at dword offsets 0, 4096, 5120, 5376, 5440, 5456, 5460, each in the E561 tile law; the scratch
buffer is the counting fill (dword i reads 0xD0000000 | i). T0 0x07fc1400 (top 0x3f, max level
field 14, nearest level, linear filters), pixel (x, y) of the 64x32 fill, u = (2x+1)/128 and
v = (2y+1)/128 modulo 1 (texel centres of level 0), gradient LOD = log2 max(8 (1 + x/64), 2)
(3.0 at x = 0 to 3.98 at x = 63), the level the nearest-level rule picks being round(lod).

Pass criterion for a rule: every one of the 2048 pixels reads exactly the dword the rule names.

BIT 11 CLEARED (T3 0x00800000), the job an-t3b11:
  B11-LEVEL0  the read is level 0, texel (x, y): dword = tile-law index of (x, y) in 64x64.
  rivals (all scored):
  B11-MIPOFF  same image by another mechanism (mips off); the two are one image here
  B11-BIAS-k  the LOD biased by -k eighths, k = 0..128 (level = max(0, round(lod - k/8)))
  B11-STRIDE  the twiddle replaced by a stride: dword = y * 64 + x
  B11-CHAIN0  the level the control picks (round(lod), 3 or 4) with the offset chain of the
              level sizes replaced by 0: dword = tile-law index of (x >> l, y >> l) at 64 >> l
BIT 12 SET (T3 0x00801800, bit 11 set), the job an-t3b12:
  B12-LAST    every pixel reads the last level (1 x 1) at dword 5460
  rivals (all scored):
  B12-BIAS-k  the LOD biased by +k eighths, k = 0..128 (level = min(6, round(lod + k/8)))
  B12-ADDR    a constant dword 5460 regardless of the chain (the same image: one image here)
  B12-BIT10   the bit-10 read (the base dword 0)
  B12-CTL     the control's level (3 or 4) unchanged (bit 12 changes nothing)
"""
import math, sys
sys.path.insert(0, "/Users/jtorra/src/scratch/resgx545/closing11/plan/c8-q078")
from common import morton, inverse

OFFS = [0, 4096, 5120, 5376, 5440, 5456, 5460]
SIDES = [64, 32, 16, 8, 4, 2, 1]
NAME = 0xD0000000

def lod(x):
    return math.log2(max(8 * (1 + x / 64), 2.0))

def level(x, bias_eighths=0, cap=6):
    return min(max(math.floor(lod(x) + bias_eighths / 8 + 0.5), 0), cap)

def dword(l, tx, ty):
    return NAME | (OFFS[l] + morton(tx, ty, SIDES[l]))

def b11_level0(x, y):
    return dword(0, x, y)

def b11_bias(x, y, k):
    l = level(x, -k)
    s = SIDES[l]
    return None if l else dword(0, x, y)     # None: a blended (non-name) value, never exact

def b11_stride(x, y):
    return NAME | (y * 64 + x)

def b11_chain0(x, y):
    l = level(x)
    return NAME | morton(x >> l, y >> l, SIDES[l])

def b12_last(x, y):
    return dword(6, 0, 0)

def b12_bias(x, y, k):
    l = level(x, k)
    return dword(6, 0, 0) if l == 6 else None

def b12_bit10(x, y):
    return NAME

def b12_ctl(x, y):
    l = level(x)
    return None
