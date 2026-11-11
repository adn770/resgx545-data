#!/usr/bin/env python3
"""pbmodel.py: the parameter-buffer page model and the TA-data layout of a 4x job (standard library only).

Two readings of ONE rule, counted differently (DECISIONS-R4.md, lead check):
  closing4/render4x/pb_pages.py (this file)   used = 1 + ceil(2 * tiles16 / 32)    scene pages, page 0 included
  closing4/rank/q292_pbfit.py                 ceil(tiles32 / 8) + 4                NON-ZERO pages of a dump (page 0 and 3 fixed)
with tiles16 = ceil(W/16) * ceil(H/16) and tiles32 = ceil(W/32) * ceil(H/16).  Of the non-zero pages of a dump taken at
render_pb_pages 0x422 (dump pages 0 to 0x463), three are no scene page (0x422, 0x423: the page table; 0x463: the state page), so
the rank's count is `pages_nonzero_all` = u4 + 3, and `pages_nonzero` (pages 0 to 0x421 only) = u4.  They agree exactly when the
width is a multiple of 32 and the height of 16 (every size of this session); tests/test_gen.py checks both against E824's ten
dumps and over the tables.
The layout is closing3/kernel/layout_f4.py's formula (sgx_render.c), as transcribed in closing4/render4x/u4_layout.py.
"""
import math

PB_PAGES = 0x422                 # the default of debugfs render_pb_pages
PB_FIXED_RESERVE = 0x22          # a scene overflows when P - 0x22 < its need (E625, E735, E773)
DUMP_FIXED = (0x422, 0x423, 0x463)   # non-zero pages of a dump that belong to no scene


def rup(a, m):
    return (a + m - 1) // m * m


def tiles16(w, h):
    return math.ceil(w / 16) * math.ceil(h / 16)


def u4(w, h):
    """Scene pages a four-array 4x full-triangle job uses, page 0 included."""
    return 1 + math.ceil(2 * tiles16(w, h) / 32)


def u1(w, h):
    """The same at one sample a pixel (MODEL: no 1x scene was measured at this form)."""
    return 1 + math.ceil(tiles16(w, h) / 32)


def u4_rank(w, h):  # = u4 + 3 where W % 32 == 0 and H % 16 == 0
    """The other count of the rule: ceil(tiles32 / 8) + 4 fixed pages (closing4/rank/q292_pbfit.py)."""
    return math.ceil(math.ceil(w / 32) * math.ceil(h / 16) / 8) + 4


def usable(p):
    return p - PB_FIXED_RESERVE


def overflows(need, p):
    return usable(p) < need


def layout(w, h, f=1):
    """(rgn_size, rgn, zls, size) of the TA data: f region-header arrays of the ext-Z area."""
    tx, ty = (w + 31) // 32, (h + 15) // 16
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = rup((tx + n - 1) // n, 4), rup((ty + n - 1) // n, 4)
    span = max(n * mx, n * my)
    side = 1
    while side < span:
        side <<= 1
    rgn_size = 0xc0 * (mx // 4) * (my // 4) * n * n
    rgn = rup(4 * side * side, 4096) + 3 * 4096
    zls = rgn + rup(f * rgn_size, 4096)
    return rgn_size, rgn, zls, zls + rup(rgn_size, 4096)


def tadata_4x(w, h):
    return layout(w, h, f=4)[3]


def pages_nonzero(dump):
    """Non-zero 4 KiB pages among pages 0 to 0x421 of a render_param dump taken at P = 0x422 (the scene's pages)."""
    return sum(1 for i in range(min(len(dump) // 4096, PB_PAGES)) if dump[i * 4096:(i + 1) * 4096].strip(b"\0"))


def pages_nonzero_all(dump):
    return sum(1 for i in range(len(dump) // 4096) if dump[i * 4096:(i + 1) * 4096].strip(b"\0"))
