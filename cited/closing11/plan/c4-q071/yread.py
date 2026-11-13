# post hoc: do the linear-layout dumps of E997 show any y dependence? rows of 96 dwords.
import gzip, struct, sys
D = "/Users/jtorra/src/resgx545-data/render/closing-r10-x/out/20261113-101116/zbits/"
for n in ("zb-clr-f0", "zb-all-f0", "zb-all-f1"):
    b = gzip.open(D + n + ".depth.1.bin.gz").read()
    w = struct.unpack("<%dI" % (len(b) // 4), b)
    rows = [w[96 * y:96 * y + 96] for y in range(48)]
    same = sum(1 for r in rows if r == rows[0])
    nd = len({r for r in rows})
    print(n, "dwords", len(w), "rows of 96:", len(rows), "rows equal to row 0:", same,
          "distinct rows:", nd, "next-row-diff index list:",
          [y for y in range(1, 48) if rows[y] != rows[y - 1]])
    if nd > 1:
        for y in range(48):
            d = [x for x in range(96) if rows[y][x] != rows[0][x]]
            if d: print("  row", y, "differs from row 0 at x", d[:12], "... n", len(d))
