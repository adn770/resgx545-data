# SPDX-License-Identifier: MIT
"""law.py: E561's tile law for twiddled textures, copied from r10-tex's gen/addr.py (resgx545-data
render/closing-r10-tex, pinned) with texmodel's coordinate rule: tiles of min(W, 16) x min(H, 16)
texels, each interleaved with t in bit 0 (texmodel's morton), the tiles in raster order, s first.
texmodel.py's own address (plain Morton over the whole texture) is not E561's above 16 a side: it
misses E566's kept tw32-ctl on 1024 of 2048 pixels, the tile law on none (tests/test_gen.py)."""
import pins
import tex


def morton(x, y, w, h):
    bw, bh = max(w, 1).bit_length() - 1, max(h, 1).bit_length() - 1
    common = min(bw, bh)
    i = 0
    for b in range(common):
        i |= (y >> b & 1) << (2 * b) | (x >> b & 1) << (2 * b + 1)
    rest = (x if bw > bh else y) >> common
    return i | rest << (2 * common)


def index(s, t, w, h):
    """E561's tile law; s may pass the width (H-TWX's unwrapped column): its tile then lies
    further on in raster order, as the law's arithmetic gives it."""
    tw, th = min(w, 16), min(h, 16)
    return morton(s % tw, t % th, tw, th) + tw * th * (s // tw + (w // tw) * (t // th))


def ev(spec, x, y):
    """A p1141 coordinate spec's value at pixel (x, y) (texmodel's ev, pinned)."""
    return pins.module(tex.TEXMODEL).ev(spec, x, y)
