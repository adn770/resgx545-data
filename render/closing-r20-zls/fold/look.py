# SPDX-License-Identifier: MIT
"""fold/look.py: post hoc reads of r20-zls's kept files at the fold (not frozen).

  python3 fold/look.py OUT_ATTEMPT_DIR
zr: per row, the window dwords of the load buffer (depth) and the store buffer (depth-store)
after render 1 and after the final, the four most frequent values per region: tile rows 0-11
(lo) and below (hi), T2 inside (in) and outside (out), edges left out. zm: the final's check
and the triangle's pixel count. zq: depth.2's zero dwords by region. Registers: the distinct
(0x0480, 0x0484, 0x0488) triples of zc's -n 1 rows and of zr's rows during and after the partial
renders, with the words' rd:1, rd:11, rd:12, rd:13."""
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


def main(out):
    d = os.path.join(out, "zr")
    for r in PL.tables()["zr"]:
        n, mv = r["name"], r["move"]
        g = 1 if r["ctl"] == PL.E336 else 33
        print(f"== {n} (P 0x{r['p']:x}, control 0x{r['ctl']:08x}, move {mv}, raised "
              f"{SC.dwords(K._read(os.path.join(d, n + '.ta3d.1.bin')))[38] != 0})")
        for s in ("depth.1", "depth-store.1", "depth.2", "depth-store.2"):
            b = SC.dwords(K._read(os.path.join(d, f"{n}.{s}.bin")))
            if g == 33:
                print(f"  {s}: {hist(b, mv)}")
            else:
                print(f"  {s}: " + ", ".join(f"0x{v:08x} x {k}" for v, k in
                                              collections.Counter(b).most_common(4)))
    d = os.path.join(out, "zm")
    for r in PL.tables()["zm"]:
        t = K.text(d, r["name"] + ".txt")
        print(f"== {r['name']}: render 1 {SC.tri_line(t, 1)}; final {SC.tri_line(t, 2)}")
    v1, v2 = SC.tri_default(PL.W, PL.H), SC.tri_default(PL.W, PL.H, PL.MOVE)
    print("T1 inside", sum(1 for y in range(PL.H) for x in range(PL.W) if SC.tri_expect(v1, x, y) == 1),
          "T2 inside", sum(1 for y in range(PL.H) for x in range(PL.W) if SC.tri_expect(v2, x, y) == 1))
    d = os.path.join(out, "zq")
    for r in PL.tables()["zq"]:
        if r["g"] != 33:
            continue
        for s in ("depth.1", "depth.2"):
            b = SC.dwords(K._read(os.path.join(d, f"{r['name']}.{s}.bin")))
            print(f"== {r['name']} {s}: zero lo {sum(1 for i, _ in SC.window(0) if i < len(b) and i < PL.ROW12 and b[i] == 0)}, "
                  f"zero hi {sum(1 for i, _ in SC.window(0) if i < len(b) and i >= PL.ROW12 and b[i] == 0)}, "
                  f"signed {sum(1 for i, _ in SC.window(0) if i < len(b) and b[i] >> 31)}")


def remainder(out):
    """zr-30-nl: the 0.5 dwords of the store after the final outside T2, by T1 state and the
    store after render 1 there."""
    d = os.path.join(out, "zr")
    s1 = SC.dwords(K._read(os.path.join(d, "zr-30-nl.depth-store.1.bin")))
    s2 = SC.dwords(K._read(os.path.join(d, "zr-30-nl.depth-store.2.bin")))
    v1, w2 = SC.tri_default(PL.W, PL.H), dict(SC.window(PL.MOVE))
    c = collections.Counter()
    for y in range(PL.H):
        for x in range(PL.W):
            i = SC.store_dword(x, y, 33)
            if w2[i] == 0 and s2[i] == PL.HALF:
                c[(SC.tri_expect(v1, x, y), s1[i])] += 1
    print("== zr-30-nl 0.5 outside T2 after the final, by (T1 state, store.1): "
          + ", ".join(f"({k[0]}, 0x{k[1]:08x}) x {n}" for k, n in sorted(c.items())))


def regs(out):
    for st, names in (("zc", ("zc-nl", "zc-ld", "zc-geo")), ("zr", [r["name"] for r in PL.tables()["zr"]])):
        d = os.path.join(out, st)
        for n in names:
            col, rows = SC.timeline(K.text(d, n + ".txt"))
            rd = SC.rd_words(K.text(d, n + ".words.1.txt"))
            a, b, c, p = (col[k] for k in ("0x0480", "0x0484", "0x0488", "0x0658"))
            pr = [i for i, x in enumerate(rows) if x[p] & 1]
            seg = {"before": rows[:pr[0]] if pr else rows, "pr": [rows[i] for i in pr],
                   "after": rows[pr[-1] + 1:] if pr else []}
            print(f"== regs {n}: rd:1 0x{rd.get(1, 0):08x} rd:11 0x{rd.get(11, 0):08x} "
                  f"rd:12 0x{rd.get(12, 0):08x} rd:13 0x{rd.get(13, 0):08x}")
            for k, rr in seg.items():
                cnt = collections.Counter((x[a], x[b], x[c]) for x in rr)
                print(f"  {k}: " + ", ".join("0x%08x 0x%08x 0x%08x x %d" % (t + (m,))
                                              for t, m in sorted(cnt.items())))


if __name__ == "__main__":
    remainder(sys.argv[1])
    regs(sys.argv[1])
    main(sys.argv[1])
