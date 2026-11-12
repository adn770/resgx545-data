#!/usr/bin/env python3
"""layout_b.py (set B, the r6-kernel module): the TA-data layout of a render context with the tail room of linux fork branch
r6-kernel, commit 56f8b932 "give 4x render contexts four times the tail room" (tip 3f0b3e74, read only), transcribed from
sgx_render.c sgx_render_tail_room() and sgx_render_tadata_layout_in():

  room   = setting                  if debugfs render_tail_room is non-zero and a whole number of pages (for EITHER kind)
         = 4 x tail_size            for a context made for 4x targets (DRM_SGXFIVE_CTX_RENDER_AA_4X), tail_size = 4 side^2
         = tail_size                for a 1x context (as on the rgn4 kernel, byte for byte)
  control = round_up(room, 4 KiB); otpm, state, rgn one page each after it; zls = rgn + round_up(arrays x rgn_size, 4 KiB);
  size = zls + round_up(rgn_size, 4 KiB); -E2BIG past 4 MiB.  arrays: 4 for a 4x context, 1 for 1x (render_rgn_arrays 0).
The RT data's tail-size word stays the single-sampled tail_size (unchanged).  The region headers start at td.rgn, so the readers of
rlib (whose base is the rgn4 layout's) are given the base here.  Standard library only; set A's files are not touched.
"""
import struct

import rules as R

SLOT = 4 << 20


def rup(a, m):
    return (a + m - 1) // m * m


def tail_size(mw, mh):
    t = R.lay(mw, mh)
    return 4 * t["side"] * t["side"]


def room(mw, mh, aa4, setting=0):
    if setting and setting % 4096 == 0:
        return setting
    return 4 * tail_size(mw, mh) if aa4 else tail_size(mw, mh)


def layout(mw, mh, aa4, setting=0):
    """{'room', 'control', 'rgn', 'zls', 'size'} of a context for a mw x mh maximum on the r6-kernel module, or None for -E2BIG."""
    t = R.lay(mw, mh)
    rm = room(mw, mh, aa4, setting)
    if rm > SLOT:
        return None
    ctl = rup(rm, 4096)
    rgn = ctl + 0x3000
    arrays = 4 if aa4 else 1
    zls = rgn + rup(arrays * t["rgn_size"], 4096)
    size = zls + rup(t["rgn_size"], 4096)
    if size > SLOT:
        return None
    return {"room": rm, "control": ctl, "rgn": rgn, "zls": zls, "size": size}


def fault(w, h, mw, mh, setting=0):
    """H-TPM on the r6-kernel layout: a four-array 4x job faults iff the end of its target's entries passes td.rgn."""
    return R.entries_end(w, h) > layout(mw, mh, True, setting)["rgn"]


def lost(w, h, mw, mh, setting=0):
    return R.lost(w, h, mw, mh, rgn=layout(mw, mh, True, setting)["rgn"])


def positions(w, h, base):
    """[(byte offset, x, y, macrotile, inside)] of the region headers of a w x h target from `base` (rlib.header_positions' order)."""
    t = R.lay(w, h)
    tx, ty, n, mx, my = t["tx"], t["ty"], t["n"], t["mx"], t["my"]
    out, i = [], 0
    for col in range(n):
        for row in range(n):
            mt = col * n + row
            for by in range(2 * my // 4):
                for bx in range(2 * mx // 4):
                    for yy in range(4):
                        for xx in range(4):
                            x, y = col * 2 * mx + bx * 4 + xx, row * 2 * my + by * 4 + yy
                            out.append((base + 12 * i, x, y, mt, x < 2 * tx and y < 2 * ty))
                            i += 1
    return out


def headers_off(tadata, w, h, base):
    """The doubled-grid rule (rlib.headers) from `base`: the offsets of the headers off the rule, or None if the dump is short."""
    pos = positions(w, h, base)
    if tadata is None or len(tadata) < pos[-1][0] + 12:
        return None
    off = []
    for o, x, y, mt, inside in pos:
        w0, w1, w2 = struct.unpack_from("<3I", tadata, o)
        ok = (((w0 >> 16) & 0xff) == x and (w0 & 0xfff) == y and ((w0 >> 12) & 0xf) == mt
              and bool(w0 & (1 << 25)) == (not inside) and bool(w1) == inside and w2 == 0)
        if not ok:
            off.append(o)
    return off


def lost_offsets(tadata, w, h, base):
    """In-target headers (by position) whose word 1 is zero, from `base`; None if the dump is short."""
    pos = positions(w, h, base)
    if tadata is None or len(tadata) < pos[-1][0] + 12:
        return None
    return [o for o, x, y, mt, inside in pos if inside and struct.unpack_from("<I", tadata, o + 4)[0] == 0]
