# SPDX-License-Identifier: MIT
"""tx6model.py: r9-lgeo's texture models for stage tx6 (Q283), standard library only, on top of
gen/texmodel.py (a byte copy of r8-lgeo's: the 64 x 32 probe fill, the tag fill 0xD0000000 | i
of every scratch dword, the map axis and the linear axis without offsets).

The linear axis with offsets (the program's u = (x + xo + 1/2) / w, v = (y + yo + 1/2) / h, the
repeat mode wrapping both): texel X = (x + xo) mod w, Y = (y + yo) mod h. It reads a texture of
any width, so type 4 at widths that are not powers of two, and windows past the fill's 64 x 32.

Type 4 past a multiple of 32 (Q283; E941's 32 x 32 blocks of 1024 dwords row by row, inside a
block (Y mod 32) 32 + (X mod 32)); the block row of a width w that is not a multiple of 32:
  H-CEIL  ceil(w / 32) whole blocks a block row (E941's rule as sgx-sim's tex.rs writes it)
  H-P2    the blocks of the width rounded up to a power of two (p2(w) / 32 a block row)
  H-PACK  floor(w / 32) whole blocks, then a partial block (w mod 32) columns wide: inside it
          (Y mod 32) (w mod 32) + (X mod 32); a block row is 32 w dwords
Type 1 at widths that are not powers of two (Q283; type 3 read the width at 24 and 40, E940):
  RASTERW  rows w dwords apart        RASTERP2  rows p2(w) dwords apart  (texmodel's)
Type 3's padding with a 16-bit format, two texels a dword (Q283; E940: rows max(8, w) dwords
apart at format 12), the texel k = Y s + X in 16-bit units, dword k div 2, the low half first
(sgx-sim tex.rs fetch: a texel's own bytes at byte 2 k), s in texels:
  H-DW8    max(16, w)   (8 dwords: the pad counts dwords)
  H-TX8    max(8, w)    (8 texels: the pad counts texels)
  RASTERW  w
Format 5 (sgx-sim tex.rs colour_texel: B5 G6 R5 from bit 0, each field widened by repeating its
bits, alpha 0xff) gives the pixel; the 16-bit word is read back from the pixel's top bits
(word_of), so a row decides on the words whatever the widening."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import texmodel as T  # noqa: E402

FW, FH, TAG = T.FW, T.FH, T.TAG
TYPE4 = ("H-CEIL", "H-P2", "H-PACK")
TYPE1 = ("RASTERW", "RASTERP2")
PAD16 = ("H-DW8", "H-TX8", "RASTERW")
p2 = T.p2


def texel_lin(x, y, w, h, xo=0, yo=0):
    return (x + xo) % w, (y + yo) % h


def type4_offset(hyp, X, Y, w, h):
    bx, by, inner = X // 32, Y // 32, (Y % 32) * 32 + X % 32
    if hyp == "H-CEIL":
        return (by * -(-w // 32) + bx) * 1024 + inner
    if hyp == "H-P2":
        return (by * max(1, p2(w) // 32) + bx) * 1024 + inner
    if hyp == "H-PACK":
        full, pw = w // 32, w % 32
        if bx < full:
            return by * 32 * w + bx * 1024 + inner
        return by * 32 * w + full * 1024 + (Y % 32) * pw + X % 32
    raise ValueError(hyp)


def type4_image(hyp, w, h, xo=0, yo=0, dwords=T.SCRATCH_DWORDS):
    """The 64 x 32 fill of a type 4 texture through the linear axis with offsets; None for a texel
    past the tag fill's `dwords`."""
    out = []
    for y in range(FH):
        for x in range(FW):
            X, Y = texel_lin(x, y, w, h, xo, yo)
            off = type4_offset(hyp, X, Y, w, h)
            out.append(TAG | off if off < dwords else None)
    return out


def pad_stride(hyp, w):
    return {"H-DW8": max(16, w), "H-TX8": max(8, w), "RASTERW": w}[hyp]


def widen565(v):
    b, g, r = v & 31, v >> 5 & 63, v >> 11 & 31
    return (b << 3 | b >> 2) | (g << 2 | g >> 4) << 8 | (r << 3 | r >> 2) << 16 | 0xFF << 24


def word_of(pixel):
    """The 16-bit B5G6R5 word a format 5 pixel came from: each channel's top bits."""
    return (pixel & 0xFF) >> 3 | ((pixel >> 8 & 0xFF) >> 2) << 5 | ((pixel >> 16 & 0xFF) >> 3) << 11


def pad16_words(hyp, w, h, hi_first=False):
    """The 16-bit words of the 64 x 32 fill (the map axis: X = x mod w, Y = y mod h, w and h powers
    of two) of a type 3 texture of a 16-bit format under a row rule; hi_first: the high half of a
    dword first (a reading only)."""
    s = pad_stride(hyp, w)
    out = []
    for y in range(FH):
        for x in range(FW):
            X, Y = T.texel(x, y, w, h)
            k = Y * s + X
            d = TAG | (k // 2)
            half = (k & 1) ^ int(hi_first)
            out.append(d >> (16 * half) & 0xFFFF)
    return out


def pad16_image(hyp, w, h):
    return [widen565(v) for v in pad16_words(hyp, w, h)]


def words_sha(words):
    return T.sha_list(words)


def parts(images):
    """{hyp: image} -> the pairs of hypotheses whose images differ."""
    ks = sorted(images)
    return [(a, b) for i, a in enumerate(ks) for b in ks[i + 1:] if images[a] != images[b]]
