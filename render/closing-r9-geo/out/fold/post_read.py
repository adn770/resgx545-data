#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""out/fold/post_read.py ATT: the fold's post hoc readings of r9-geo (2026-11-13), none frozen.
Reads only the kept outputs of ATT and the session's frozen generator (gen/).

  seam   seam4's stored image against seam1's, job by job (one array against four)
  cube   the face read at every face-tie pixel of this stage's jobs and of r8-geo's kept cube jobs
         (RESGX545_DATA, default /Users/jtorra/src/resgx545-data), the tied axes' higher or lower,
         by job (a direction run at several face sizes counted once); the outer tap of each edge job's out pixels, solved from
         the blend (the in-face tap known), against H-SEAM-ADJ's and H-SEAM-WRAP's texel
  addr   per job the index read less H-MASK-V's, and the line offset = 8 N + 52 dwords through the
         three sizes (fitted here on these rows and E932's 16 x 16)"""
import collections
import gzip
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "gen"))
import addr as A  # noqa: E402
import cube as C  # noqa: E402
import texprog as T  # noqa: E402


def text(att, stage, name):
    return gzip.open(os.path.join(att, stage, name + ".txt.gz"), "rt").read()


def tri_pixels(t):
    out = {}
    for m in re.finditer(r"^row (\d+): ([0-9a-fx ]+)$", t, re.M):
        for x, v in enumerate(m.group(2).split()):
            out[(x, int(m.group(1)))] = int(v, 16)
    return out


def seam(att):
    print("== seam: seam4 (four arrays) against seam1 (one array), job by job")
    same = 0
    names = [ln.split("\t")[0] for ln in open(os.path.join(att, "seam1", "cases.tsv")).read().splitlines()[1:]]
    for n in names:
        a = tri_pixels(text(att, "seam1", n))
        b = tri_pixels(text(att, "seam4", "f4-" + n))
        eq = a == b
        same += eq
        if not eq:
            print(f"  {n}: {sum(a[p] != b.get(p) for p in a)} pixels differ")
    print(f"  {same} of {len(names)} jobs store the same image with one array and with four")


def cube(att):
    R = C.rule()
    print("== cube: edge jobs, the outer tap solved from each out pixel's blend")
    for k, spec in C.EDGE.items():
        n = "cube-edge-" + k
        px = T.pixels(text(att, "cube2", n))
        seen = collections.Counter()
        for p, (f, kind) in sorted(C.edge_cells(R, spec).items()):
            if kind != "out":
                continue
            c = tuple(T.coord(s, *p) for s in spec)
            face, vs, vt, ma, order = C.st(R, c, 16)
            for i, v in enumerate((vs, vt)):
                for tx, w in C.taps(v, 16):
                    if w and not 0 <= tx < 16:
                        ax, otx, ow = i, tx, w
            loc = [C.flo(vs), C.flo(vt)]
            loc[ax] = 15 if otx == 16 else 0
            a = 0xD0000000 | (face * 256 + C.local(loc[0], loc[1], order, 16, "MORTON"))
            b = [(((px[p] >> (8 * i)) & 255) - (1 - ow) * ((a >> (8 * i)) & 255)) / ow for i in range(2)]
            adj = C.outer_texel(R, c, 16, ax, otx, "H-SEAM-ADJ")
            wrp = C.outer_texel(R, c, 16, ax, otx, "H-SEAM-WRAP")
            seen[(p[0], "%.1f" % float(b[1]), "%.1f" % float(b[0]), float(round(ow, 3)),
                  "%03x" % (adj & 0xfff), "%03x" % (wrp & 0xfff))] += 1
        print(f"  {n}: (x, solved G, solved low byte, outer weight, ADJ index, WRAP index): count")
        for key, v in sorted(seen.items()):
            print("   ", key, v)


def ties(att):
    print("== cube: face ties, the face read (the higher or the lower tied axis), every kept job")
    R = C.rule()
    data = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
    r8 = os.path.join(data, "render/closing-r8-geo/out/20261113-015842/cube")
    r9 = os.path.join(att, "cube2")
    r8f = {"fu": (C.const(0.75), C.lin("y", 0.25, -0.5), C.lin("x", 0.0625, 0.65625)),
           "fn": (C.const(-0.75), C.lin("y", 0.25, -0.5), C.lin("x", 0.0625, 0.65625))}
    # (file, spec, face size); r8-geo's n8/n32 b1..b3 and r9-geo's n64/n4 repeat a1, a2, a4 at
    # other sizes: counted once (their 16 x 16 runs), the faces read are the same
    jobs = [(r8, "cube-off-" + k, v, 16) for k, v in C.OFF.items()]
    jobs += [(r8, "cube-ftie-" + k, v, 16) for k, v in r8f.items()]
    jobs += [(r9, "cube-n32-" + k, v, 32) for k, v in C.NEW32.items()]
    jobs += [(r9, "cube-ftie-" + k, v, 16) for k, v in C.FTIE.items()]
    tot = collections.Counter()
    for d, name, spec, n in jobs:
        px = T.pixels(gzip.open(os.path.join(d, name + ".txt.gz"), "rt").read())
        tab, low = collections.Counter(), []
        for p, c in C.tie_cells(spec).items():
            ax = C.tied_axes(c)
            rd = (px[p] & 0x0fffffff) // (n * n) // 2
            if len(ax) == 3:
                tab["three-way"] += 1
                continue
            k = "higher" if rd == max(ax) else "lower" if rd == min(ax) else "other"
            tab[k] += 1
            if k != "higher":
                third = [i for i in range(3) if i not in ax][0]
                low.append("%s=%s %s (|3rd|/|ma| %.3f)" % ("xyz"[ax[0]] + "xyz"[ax[1]], "".join(
                    "+" if c[i] > 0 else "-" for i in ax), k, float(abs(c[third]) / abs(c[ax[0]]))))
        tot.update(tab)
        print(f"  {name}: {dict(sorted(tab.items()))}" + (f"; {', '.join(low)}" if low else ""))
    print(f"  all: {dict(sorted(tot.items()))}")


def addr(att):
    print("== addr: index read less H-MASK-V's, per job")
    offs = {}
    for name, st, n, um, vm, t3, kind in A.jobs():
        if um == 0 or um == 5:
            continue
        px = T.pixels(text(att, "addr2", name))
        mask = A.image(n, um, vm, kind, "H-MASK-V")
        d = collections.Counter((v & 0x0fffffff) - 12288 - mask[p] for p, v in px.items())
        print(f"  {name} (N {n}, T3 0x{t3:08x}): {dict(d)}")
        if len(d) == 1 and "-t3-" not in name and kind == "u":
            offs.setdefault(n, set()).add(next(iter(d)))
    print("  offsets by size:", {k: sorted(v) for k, v in sorted(offs.items())},
          "; 8 N + 52:", {k: 8 * k + 52 for k in sorted(offs)}, "[fitted]")


if __name__ == "__main__":
    att = sys.argv[1]
    seam(att)
    cube(att)
    ties(att)
    addr(att)
