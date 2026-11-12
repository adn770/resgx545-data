"""models_q287.py: r7-rp's Q287 model (odd WIDTHS at H 18; round 6 did odd heights at W 34).  Pure functions, no I/O; the
generator, scorer, world and tests import this one file.  r3_geo.py (byte copy of round 3's published model, via round 6's copy)
gives the band rules A, FLOOR, ROUND, CEIL, RSTRICT and the Morton order inside a tile.

The depth store is TILE-MAJOR at the ZLS control word's pitch field G (bits 11:3): tile row r, tile column c is at tile slot
r * (G + 1) + c, 512 dwords a tile (sgx-pipe zls.rs store_dword).  At 0x17100c, G = 1: two tiles a row whatever the width
(<= 64), so the dump's extent is tile_rows * 2 * 512 dwords, NOT the tool's own minimum depth_min_pages (W * H dwords) and NOT
ceil(W / 32) tiles a row.  The rows therefore pass an explicit --depth-pages: the store's whole extent plus round 6's 16 pages.
"""
from __future__ import annotations

import math
import sys
sys.dont_write_bytecode = True

import os  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r3_geo as G  # noqa: E402

ODD_H = 18
CTL = 0x17100C                      # E831's control word: pitch field G = 1
MARGIN_PAGES = 16                   # round 6's margin (the tool's own DEPTH_MARGIN_PAGES)
PAGE_DWORDS = 1024
RULES = tuple(G.RULES)


def pitch_tiles(ctl=CTL):
    """Tiles a row of the store: G + 1, G = the control word's bits 11:3."""
    return ((ctl >> 3) & 0x1FF) + 1


def tile_rows(h):
    return -(-h // G.TILE_H)


def store_dwords(h, ctl=CTL):
    """The store's whole extent in dwords: tile rows x tiles a row x 512."""
    return tile_rows(h) * pitch_tiles(ctl) * 512


def store_pages(h, ctl=CTL):
    return -(-store_dwords(h, ctl) // PAGE_DWORDS)


def pages(w, h, ctl=CTL):
    """--depth-pages N: the store's extent plus the margin (never less than the tool's own minimum plus the margin)."""
    return max(store_pages(h, ctl), tool_min_pages(w, h)) + MARGIN_PAGES


def tool_min_pages(w, h):
    """sgxfive-test.c depth_min_pages: W * H dwords."""
    return (w * h * 4 + 4095) // 4096


def band_fits(w):
    """The band (1.25 W) stays inside the two-tile pitch (64 pixels)."""
    return 1.25 * w <= pitch_tiles() * G.TILE_W


def depth_args(w, h, ramp, extra=""):
    """E730 / E831 / E885's row, token for token, at another size (E831's pages 18 at H 18)."""
    z = G.RAMP_X if ramp == "x" else G.RAMP_Y
    return ("tri --keep-overflow --wait-ms 20000 --width %d --height %d --tri-full --tri-z %s --depth --depth-ctl 0x%x "
            "--depth-fill 0xdeadbeef --depth-dump \"$W/depth\" --depth-pages %d --poke blk:1=0x00400200%s"
            % (w, h, z, CTL, pages(w, h), extra))


def band(rule, w, h):
    return G.band_set(rule, w, h)


def set_sha(pts):
    return G.set_sha(pts)


def dword_index(x, y, ptiles):
    return 512 * ((y // G.TILE_H) * ptiles + x // G.TILE_W) + G.mort(x % G.TILE_W, y % G.TILE_H)


def stored_set(words, w, h, ptiles):
    """(stored pixels = tile-area dwords not 1.0f, tile-area dwords still holding the pre-fill) from a depth dump, at the
    store's own pitch (ptiles tiles a row)."""
    aw, ah = G.area(w, h)
    st, dead = set(), 0
    for y in range(ah):
        for x in range(aw):
            v = words[dword_index(x, y, ptiles)]
            if v == G.FILL:
                dead += 1
            elif v != G.BG:
                st.add((x, y))
    return st, dead


def need_dwords(w, h, ptiles):
    """Dwords of the dump the tile area needs."""
    tw, th = G.tiles(w, h)
    return 512 * ((th - 1) * ptiles + tw)


def width_of(rule, w):
    return G.extent(rule, w, 1)[0]
