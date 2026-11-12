#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""For each region a render dump streams, which 16 x 16 tiles of the 32 x 16 region our
triangle covers (a bounding-box test, half-open on the line between the tiles, and a closed edge
test), against the control stream's PRIM_TILES field, the primitive word's bits 23:16 (E180).
Reads the ta-regions-sweep-* dumps of probes/ta/regions.toml, in the directory given or below it
(the ta-regions dataset keeps them in <probe>/dumps/): the triangle of sgxfive_tri_default on
128 x 128, shifted by NAME's x or y pixels. The last line counts the regions whose PRIM_TILES is
a form E180 gives their tile pair (0x80 the left tile only, 0x98 the right only, 0x90 both; the
wide-mask forms 0x8a the left and 0x8c the right, which the sweep's one triangle never shows).

    region_tiles.py DUMPS_DIR       a table of (left tile, right tile) against PRIM_TILES
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

import pbdump

V = [(-0.75, -0.75), (0.75, -0.375), (-0.375, 0.75)]

# The PRIM_TILES forms of each tile pair (left, right) a triangle meets (E180; the glossary's
# PRIM_TILES row): masks in the word, then masks too wide for it.
TILE_FORMS = {(True, False): (0x80, 0x8a), (False, True): (0x98, 0x8c), (True, True): (0x90,)}


def triangle(name: str, size: int = 128) -> list[tuple[float, float]]:
    """Our triangle's pixel vertices for a ta-regions-sweep-{x,y}NN dump."""
    m = re.search(r"sweep-([xy])(\d+)", name)
    dx = int(m[2]) if m and m[1] == "x" else 0
    dy = int(m[2]) if m and m[1] == "y" else 0
    return [((x + 1) * size / 2 + dx, (y + 1) * size / 2 + dy) for x, y in V]


def prim_tiles(word: int) -> int:
    """The primitive word's PRIM_TILES field (pbdump.prim_word: CSTREAM, bits 23:16)."""
    return pbdump.prim_word(word)["PRIM_TILES"]


def _overlaps(t, x0: float, y0: float, x1: float, y1: float, x1_open: bool = False) -> bool:
    """Whether the triangle meets the rectangle by two tests: its bounding box against the
    rectangle (closed, or half-open on the right with x1_open), then each edge's line against
    the rectangle's corners (closed: a corner on an edge counts)."""
    bx0, bx1 = min(p[0] for p in t), max(p[0] for p in t)
    by0, by1 = min(p[1] for p in t), max(p[1] for p in t)
    if bx1 < x0 or (bx0 >= x1 if x1_open else bx0 > x1) or by1 < y0 or by0 > y1:
        return False
    corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    for i in range(3):
        a, b, c = t[i], t[(i + 1) % 3], t[(i + 2) % 3]
        nx, ny = b[1] - a[1], a[0] - b[0]
        side = nx * (c[0] - a[0]) + ny * (c[1] - a[1])
        if all((nx * (x - a[0]) + ny * (y - a[1])) * side < 0 for x, y in corners):
            return False
    return True


def tiles(t, x0: float, y0: float) -> tuple[bool, bool]:
    """(left, right): whether the triangle meets the region's two 16 x 16 tiles. Both are
    closed for the edge test; the bounding-box test is half-open on the line between them,
    so a triangle whose leftmost point is on it is the right tile's only."""
    return (_overlaps(t, x0, y0, x0 + 16, y0 + 16, x1_open=True),
            _overlaps(t, x0 + 16, y0, x0 + 32, y0 + 16))


def table(d: pathlib.Path) -> dict:
    """{(left, right): Counter of PRIM_TILES} over the sweep dumps in d or below it."""
    out: dict = collections.defaultdict(collections.Counter)
    for f in sorted(d.rglob("ta-regions-sweep-*.param.bin")):
        name = f.name[:-len(".param.bin")]
        param, td = f.read_bytes(), (f.parent / f"{name}.tadata.bin").read_bytes()
        t = triangle(name)
        for r in pbdump.regions(td):
            if r.stream:
                key = tiles(t, r.col * 16, (r.row & 0xfff) * 8)
                out[key][prim_tiles(pbdump.stream(param, r.stream)[0])] += 1
    return out


def agreement(t: dict) -> tuple[int, int]:
    """(regions whose PRIM_TILES is a form of their tile pair, regions)."""
    agree = sum(c[f] for k, c in t.items() for f in TILE_FORMS.get(k, ()))
    return agree, sum(sum(c.values()) for c in t.values())


def main(argv: list[str] | None = None) -> int:
    a = sys.argv[1:] if argv is None else argv
    if len(a) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    t = table(pathlib.Path(a[0]))
    for (left, right), c in sorted(t.items()):
        forms = ", ".join(f"PRIM_TILES {form:#04x} {n}" for form, n in sorted(c.items()))
        print(f"left {'x' if left else '-'} right {'x' if right else '-'}: {forms}")
    agree, total = agreement(t)
    print(f"regions whose PRIM_TILES is their tile pair's form: {agree} of {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
