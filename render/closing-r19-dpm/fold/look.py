# SPDX-License-Identifier: MIT
"""fold/look.py: post hoc reads of r19-dpm's kept files at the fold (not frozen).

  python3 fold/look.py OUT_ATTEMPT_DIR
Per geometry row: the raise (ta3d.1.bin dword 38 == 0x20, E625), the partial renders and peaks
(rt); dza/dzo/zs stores with the sign bit masked; ld's walk proxies."""
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import plan as PL  # noqa: E402
import score as SC  # noqa: E402


def rd(d, n, s):
    return K._read(os.path.join(d, n + s))


def main(out):
    T = PL.tables()
    for st in PL.STAGES:
        d = os.path.join(out, st)
        for r in T[st]:
            n = r["name"]
            t = K.text(d, n + ".txt")
            col, rows = SC.timeline(t)
            prs, peaks = SC.runs(rows, col) if col else ([], [])
            w = SC.dwords(rd(d, n, ".ta3d.1.bin"))
            raised = None if not w or len(w) < 39 else w[38] == 0x20
            line = f"{st} {n}: raised {raised}, partial renders {len(prs)}, starts {prs}, peaks {peaks}"
            d1, d2 = SC.dwords(rd(d, n, ".depth.1.bin")), SC.dwords(rd(d, n, ".depth.2.bin"))
            if r.get("form") == "ov" and d1 and d2:
                idx = [i for i in range(PL.ROW12, min(len(d1), len(d2)))
                       if d1[i] not in (r["fill"], SC.CLEAR, 0)]
                km = sum(1 for i in idx if d2[i] & 0x7FFFFFFF == d1[i] & 0x7FFFFFFF)
                s1 = sum(1 for i in idx if d1[i] >> 31)
                s2 = sum(1 for v in d2 if v >> 31)
                line += f"; ov: t1 {len(idx)}, signed in t1 {s1}, kept1 masked {km}, depth.2 signed {s2}"
            if r.get("form") == "dl" and r.get("geo"):
                st2 = SC.dwords(rd(d, n, ".depth-store.2.bin"))
                st1 = SC.dwords(rd(d, n, ".depth-store.1.bin"))
                if st2:
                    hi = sum(1 for i in range(PL.ROW12, len(st2)) if st2[i] == i)
                    hm = sum(1 for i in range(PL.ROW12, len(st2)) if st2[i] & 0x7FFFFFFF == i)
                    sg = sum(1 for v in st2 if v >> 31)
                    z = sum(1 for v in st2[:PL.ROW12] if v == 0)
                    line += f"; dl store.2: idx_hi {hi}, masked {hm}, signed {sg}, zero below row 12 {z}"
                if st1:
                    line += f"; store.1 idx_hi {sum(1 for i in range(PL.ROW12, len(st1)) if st1[i] == i)}"
            if st in ("zs", "rd") and d1 and d2:
                line += (f"; depth.1 signed {sum(1 for v in d1 if v >> 31)}, zero {sum(1 for v in d1 if v == 0)}"
                         f"; depth.2 signed {sum(1 for v in d2 if v >> 31)}, zero {sum(1 for v in d2 if v == 0)}"
                         f", equal to depth.1 {sum(1 for a, b in zip(d1, d2) if a == b)}")
            print(line)


if __name__ == "__main__":
    main(sys.argv[1])
