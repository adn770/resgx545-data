# SPDX-License-Identifier: MIT
"""texmodel.py: r8-lgeo's texture models (Q283, Q178), standard library only.

The probe fill is 64 x 32 pixels; pixel (x, y) samples texel (X, Y) of a w x h texture, and the
scratch buffer's dword i is 0xD0000000 | i (E725's map fill; the tool's tag fill covers its whole
64 KiB, 16384 dwords, sgxfive-test.c SCRATCH_FILL, so a 128 x 128 type 4 texture of 16384 dwords
is tagged in every dword). Window (r7-geo gen/texbuild.py's map axis, which ORs an offset into
the pixel coordinate before the mask): X = (x | xo) & (w - 1), Y = (y | yo) & (h - 1), w and h
powers of two, xo a multiple of 64 and yo of 32; the linear axis of the non-power-of-two widths
(texcatalog.swin) puts X = x mod w, Y = y mod h.

Types 1 and 3 (Q283; E725, E910): a raster of rows `s` dwords apart, offset Y s + X:
  RASTERW   s = w                (E725, E910 held out from 4 to 128 wide for type 1)
  H-MIN8    s = max(8, w)        (E910's type 3 at 4 x 16: rows 8 dwords apart, post hoc)
  H-2W      s = 2 w              (the other reading of E910's one row: parts at 2 and 1 wide)
  RASTERP2  s = the power of two at or above w (the non-power-of-two widths only)
Type 4 (Q283; E910 post hoc): 32 x 32 blocks of 1024 dwords, (Y mod 32) 32 + (X mod 32) inside a
block, blocks numbered by
  H-BLKROW  (Y div 32) ceil(w / 32) + (X div 32)       (row by row)
  H-BLKCOL  (X div 32) ceil(h / 32) + (Y div 32)       (column by column)
  H-BLKZ    the bits of X div 32 and Y div 32 interleaved, X's in bit 0 (E910: columns 32 to 63
            at +1024 at 64 wide)
Type 5 (Q178; E911, the leftovers' P2 post hoc fit): the pixel is 0x0000ffff iff
  H-DW8     bit 0 of dword floor(t / 8) is set
  H-DW4B1   bit 1 of dword floor(t / 4) is set
else 0, t = Y w + X (the raster index); dword i is the stored value for i below the stored count,
else the tag fill 0xD0000000 | i. On the plain fill the two are one function (both read bit 3
of t's dword index), so only stored words part them."""
from __future__ import annotations

import hashlib

TAG = 0xD0000000
LIT = 0x0000FFFF
FW, FH = 64, 32
SCRATCH_DWORDS = 16384


def p2(n):
    k = 1
    while k < n:
        k <<= 1
    return k


def texel(x, y, w, h, xo=0, yo=0, linear=False):
    if linear:
        return x % w, y % h
    return (x | xo) & (w - 1), (y | yo) & (h - 1)


STRIDES = {"RASTERW": lambda w: w, "H-MIN8": lambda w: max(8, w), "H-2W": lambda w: 2 * w,
           "RASTERP2": p2}


def interleave(bx, by):
    out, k = 0, 0
    while bx or by:
        out |= (bx & 1) << (2 * k) | (by & 1) << (2 * k + 1)
        bx >>= 1
        by >>= 1
        k += 1
    return out


def block_index(hyp, bx, by, w, h):
    if hyp == "H-BLKROW":
        return by * -(-w // 32) + bx
    if hyp == "H-BLKCOL":
        return bx * -(-h // 32) + by
    if hyp == "H-BLKZ":
        return interleave(bx, by)
    raise ValueError(hyp)


def offset(hyp, X, Y, w, h):
    if hyp in STRIDES:
        return Y * STRIDES[hyp](w) + X
    return block_index(hyp, X // 32, Y // 32, w, h) * 1024 + (Y % 32) * 32 + (X % 32)


def tex_image(hyp, w, h, xo=0, yo=0, linear=False, dwords=SCRATCH_DWORDS):
    """The 64 x 32 fill (raster order) under a layout hypothesis of types 1, 3 and 4; None for a
    texel past the tag fill's `dwords`."""
    out = []
    for y in range(FH):
        for x in range(FW):
            X, Y = texel(x, y, w, h, xo, yo, linear)
            off = offset(hyp, X, Y, w, h)
            out.append(TAG | off if off < dwords else None)
    return out


def dword(i, stored):
    return stored.get(i, TAG | i) if stored else TAG | i


def type5_image(hyp, w, h, stored=None, xo=0, yo=0):
    """The 64 x 32 fill of type 5; stored: {dword: value} the program writes before its sample."""
    out = []
    for y in range(FH):
        for x in range(FW):
            X, Y = texel(x, y, w, h, xo, yo)
            t = Y * w + X
            if hyp == "H-DW8":
                bit = dword(t // 8, stored) & 1
            elif hyp == "H-DW4B1":
                bit = (dword(t // 4, stored) >> 1) & 1
            else:
                raise ValueError(hyp)
            out.append(LIT if bit else 0)
    return out


def sha_list(dwords):
    """r7-geo models.sha_list: sha256 of the dwords as comma-separated 8-digit hex."""
    return hashlib.sha256(",".join("%08x" % (int(d) & 0xFFFFFFFF) for d in dwords).encode()).hexdigest()


def probe_rows(text):
    """probe NAME: row N: hex... -> dwords in raster order (2048 for a fill); [] if none."""
    rows = {}
    for ln in text.splitlines():
        i = ln.find(": row ")
        if ln.startswith("probe ") and i > 0:
            n, _, rest = ln[i + 6:].partition(":")
            try:
                rows[int(n)] = [int(t, 16) for t in rest.split()]
            except ValueError:
                return []
    return [v for k in sorted(rows) for v in rows[k]]
