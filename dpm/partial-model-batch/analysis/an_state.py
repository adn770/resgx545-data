#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""11.39 P3: the macrotile lists in the state page of the st-* / fr-* / dp-z05 jobs against the macrotiles the
triangle (or two) covers on the 4 x 4 grid (index = column * 4 + row, down then across), with the pages the lists
span and TA3DCtl dwords 35, 37, 38 and 39. A macrotile is covered when a point of its 8 x 8 sample grid is inside."""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "recompute-b"))
import recompute_p1139b as r


def covered(c, w, h, tris):
    out = set()
    for ix in range(4):
        for iy in range(4):
            x0, y0, x1, y1 = ix * w / 4, iy * h / 4, (ix + 1) * w / 4, (iy + 1) * h / 4
            for a in range(8):
                for b in range(8):
                    x, y = x0 + (a + .5) * (x1 - x0) / 8, y0 + (b + .5) * (y1 - y0) / 8
                    if any(r.inside(t, x, y) for t in tris):
                        out.add(ix * 4 + iy)
    return out


def main(run):
    cs = r.load_cases(run)
    for n, c in cs.items():
        if not (n.startswith("st-") and "4096" not in n) and not n.startswith(("fr-1024-0x", "dp-z05-g1-0x2c-r1")):
            continue
        w, h = int(r.arg(c, "--width", 1024)), int(r.arg(c, "--height", 768))
        base = [(8 * w / 64, 8 * h / 64, 0), (56 * w / 64, 20 * h / 64, 0), (20 * w / 64, 56 * h / 64, 0)]
        mv = re.search(r"--move (\d):(-?\d+),(-?\d+)", c["args"])
        tris = [base]
        dx, dy = (int(mv.group(2)), int(mv.group(3))) if mv else (0, 0)
        if mv and "--geometry" in c["args"]:       # two triangles: render 1 the default, render 2 moved
            tris = [base, [(x + dx, y + dy, 0) for x, y, _ in base]]
        elif mv:
            tris = [[(x + dx, y + dy, 0) for x, y, _ in base]]
        k = r.Case(n, c)
        d = k.dump("tadata", 1) or k.dump("tadata", 2)
        ls = r.state_lists(d, r.state_off(c))
        have = {l[0] for l in ls[:16] if l}
        want = covered(c, w, h, tris)
        w1 = k.ta3d(1) or []
        wl = None
        for i in range(4, 0, -1):
            wl = k.ta3d(i)
            if wl and any(wl[35:41]):
                break
        wl = wl or w1
        pages = sorted(p for l in ls if l for p in (l[2], l[3]))
        print(f"{n}\tP {c['P']}\tlists {len(have)} covered {len(want)} equal {have == want} extra {sorted(have - want)} missing {sorted(want - have)}"
              f"\tsum {sum(l[1] for l in ls[:16] if l)}\tpages {pages[0] if pages else '-'}-{pages[-1] if pages else '-'}\tdw35-40 {' '.join('%x' % x for x in wl[35:41])}")


main(sys.argv[1])
