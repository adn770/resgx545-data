"""Offline models of R2-pixel (Q281 D2 and Q286 A2).  Scratch (no numpy needed here); frozen with the generators.

Q281 layout model HL (closing2/exp-pixel.md section 0.1, closing2/pixel/q281_layout.py):

  The probe allocates its scratch (P pages) and then the read-only coords surface (3 pages) in the GENERAL heap,
  adjacent.  The coords surface is filled with 0xdeadbeef and its first 2048 dwords overwritten with
  coord_texel(i) = (i // 64) << 16 | (i % 64).  The L2e2 program reads dwords 20480..21244 of the scratch base (A4:
  the dword index of every pixel, d-L2e2-21 at 21 pages, where every read lands in the scratch as 0xD0000000 | dword).
  With P pages the read of dword w is at offset w - 1024 * P of the coords surface:
      off < 0              scratch word            0xD0000000 | w
      0     <= off < 2048  coords texel            (off // 64) << 16 | (off % 64)       (pages 0 and 1)
      2048  <= off < 3072  coords page 2           0xdeadbeef
      off >= 3072          past the coords surface unmapped: BIF fault 0x90002 at scratch base + 4 * w + 1
The knob is the probe's own `scratch at 0x3e003000 (N KiB)` line.
"""
from __future__ import annotations

import hashlib
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SENTINEL = 0xDEADBEEF
BASE = 0x3E003000


def load_dwords() -> list[int]:
    """The dword index of every pixel of the L2e2 program, in the probe's row order (2048 values)."""
    rows = [r.split("\t") for r in (HERE / "data" / "s1b_p-d-A4.tsv").read_text().splitlines()[1:]]
    ln = next(r for r in rows if r[0] == "d-L2e2-21")          # S1b's frozen A4 image at 21 pages (measured 2048/2048)
    px = [int(v, 16) for v in ln[3].split(",")]
    assert len(px) == 2048 and all(v >> 28 == 0xD for v in px)
    return [v & 0x0FFFFFFF for v in px]


def layout_word(w: int, pages: int):
    """The word the read of scratch dword w returns with `pages` scratch pages, or ('fault', address)."""
    off = w - 1024 * pages
    if off < 0:
        return 0xD0000000 | w
    if off < 2048:
        return ((off // 64) << 16) | (off % 64)
    if off < 3072:
        return SENTINEL
    return ("fault", BASE + 4 * w + 1)


def image(pages: int, xor: int = 0):
    """The L2e2 image at `pages` scratch pages (words ^ xor), or None if the first read faults."""
    out = []
    for w in load_dwords():
        v = layout_word(w, pages)
        if isinstance(v, tuple):
            return None
        out.append(v ^ xor)
    return out


def first_fault(pages: int):
    """(the faulting address of the first read past the coords surface) or None."""
    for w in load_dwords():
        v = layout_word(w, pages)
        if isinstance(v, tuple):
            return v[1]
    return None


def pix_hash(px) -> str:
    """The sha256 over the comma-joined 8-digit hex words (S1b's pix_hash and the scorers' pixel_sha)."""
    return hashlib.sha256(",".join(f"{v:08x}" for v in px).encode()).hexdigest()


# ---- Q286 (TA data layout of the kernel, transcribed in score/r2lib.py) -------------------------------------------
