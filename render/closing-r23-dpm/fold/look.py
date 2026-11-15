#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/look.py: r23-dpm's post hoc reads of the kept files (not frozen; the fold's).

  python3 fold/look.py out/20261115-202532

rl: per row render 1's line, render 2's keep colours, red + green against |T1 u T2| (the library's
reference, inside or within a pixel of an edge, T2 = T1 moved 96 px) and green against |T1 \\ T2|.
og: the kept copies' sizes and their non-zero dwords of pages 1 to 3. zn: the final's check."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402
import plan as PL  # noqa: E402
import kitscore as K  # noqa: E402


def main(att):
    a, b = SC.tri_default(PL.W, PL.H), SC.tri_default(PL.W, PL.H, PL.MOVE)
    t1 = t2 = u = d = 0
    for y in range(PL.H):
        for x in range(PL.W):
            e1, e2 = SC.tri_expect(a, x, y) != 0, SC.tri_expect(b, x, y) != 0
            t1 += e1
            t2 += e2
            u += e1 or e2
            d += e1 and not e2
    print(f"reference: |T1| {t1}, |T2| {t2}, |T1 u T2| {u}, |T1 \\ T2| {d} (inside or edge)")
    for st in ("rl", "og", "zn"):
        r = SC.Run(st, os.path.join(att, st))
        for n in r.meta:
            txt = r.text(n)
            if st == "rl":
                kl = SC.keep_line(txt)
                r1 = SC.tri_line(txt, 1)
                if kl:
                    c = kl[1]
                    print(f"rl {n}: raised {r.raised(n)}; render 1 {r1}; changed {kl[0]}, red "
                          f"{c.get(PL.RED, 0)}, green {c.get(PL.GREEN, 0)}, sentinel "
                          f"{c.get(PL.SENT, 0)}; red + green {c.get(PL.RED, 0) + c.get(PL.GREEN, 0)}")
                else:
                    print(f"rl {n}: render 1 {r1}; render 2 {SC.tri_line(txt, 2)}")
            elif st == "og":
                for k in ("closed.", "geo.", ""):
                    bb = r.dump(n, f".kept.{k}1.bin")
                    w = SC.dwords(bb) or ()
                    nz = [(i // 1024, i % 1024, hex(v)) for i, v in enumerate(w) if v and 1024 <= i < 4096]
                    print(f"og {n} kept.{k}1: {len(bb or b'')} bytes, pages 1-3 non-zero {nz}")
            else:
                print(f"zn {n}: raised {r.raised(n)}; final {SC.tri_line(txt, 2)}")


if __name__ == "__main__":
    main(sys.argv[1])
