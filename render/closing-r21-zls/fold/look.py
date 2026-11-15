# SPDX-License-Identifier: MIT
"""fold/look.py: post hoc reads of r21-zls's kept files at the fold (not frozen).

  python3 fold/look.py OUT_ATTEMPT_DIR
zl: per row, the four most frequent values of the window dwords of the load buffer (depth) and
the store buffer (depth-store) after render 1 and after the final, by region: tile rows 0-11 (lo)
and below (hi), T2 inside (in) and outside (out), edges left out; the final's target check.
zl, zw: the distinct 0x0480 values before, during and after the partial renders (0x0658 bit 0)."""
import collections
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


def hist(d, move):
    c = collections.defaultdict(collections.Counter)
    for i, e in SC.window(move):
        if e == -1 or i >= len(d):
            continue
        c[("lo" if i < PL.ROW12 else "hi") + ("-in" if e == 1 else "-out")][d[i]] += 1
    return "; ".join(f"{k}: " + ", ".join(f"0x{v:08x} x {n}" for v, n in c[k].most_common(4))
                     for k in sorted(c))


def regs(d, n):
    t = K.text(d, n + ".txt")
    col, rows = SC.timeline(t)
    a, p = col["0x0480"], col["0x0658"]
    first = next((i for i, x in enumerate(rows) if x[p] & 1), len(rows))
    last = max((i for i, x in enumerate(rows) if x[p] & 1), default=len(rows))
    out = []
    for k, rr in (("before", rows[:first]), ("pr", [x for x in rows if x[p] & 1]),
                  ("after", rows[last + 1:])):
        c = collections.Counter(x[a] for x in rr)
        out.append(f"  {k}: " + ", ".join(f"0x{v:08x} x {m}" for v, m in sorted(c.items())))
    return "\n".join(out)


def main(out):
    for st in ("zl", "zw"):
        d = os.path.join(out, st)
        for r in PL.tables()[st]:
            n = r["name"]
            print(f"== {n} (P 0x{r['p']:x}, control 0x{r['ctl']:08x}, raised {r['raised']})")
            if st == "zl":
                for sfx in ("depth.1", "depth-store.1", "depth.2", "depth-store.2"):
                    b = K._read(os.path.join(d, f"{n}.{sfx}.bin"))
                    print(f"  {sfx}: {hist(SC.dwords(b), PL.MOVE)}")
                print(f"  final check {SC.tri_line(K.text(d, n + '.txt'), 2)}")
            print(regs(d, n))


if __name__ == "__main__":
    main(sys.argv[1])
