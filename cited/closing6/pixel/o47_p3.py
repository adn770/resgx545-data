# SPDX-License-Identifier: MIT
"""Round 6 planning, Q276, offline step O4 (post hoc reading of E858's kept P3 jobs; exploration, nothing held out).
P3 writes o3 = tag 4 under p1 and tag 4 + bit 4 under !p1, p1 = (g25 == k).  At k = 0 the x jobs read 5:0 and the y jobs 5:1.
Here the tag-5 words of the x and the y job are paired by pixel and tag ONLY (bits 5:4 may differ), and the source pixel decoded.
Reads only render/closing-r5-pixel of resgx545-data.  Standard library only."""
import collections, pathlib, sys
sys.dont_write_bytecode = True
R5 = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r5-pixel")
sys.path.insert(0, str(R5 / "score"))
import r4lib as L, score_o4 as S4
k = L.Kept(R5 / "out/20261112-091752/p5-o4")
mk = dict(ln.split("\t") for ln in (R5 / "bins/p5o4-markers.tsv").read_text().splitlines())
for c in [f"p3-{o}-k{kk}" for o in ("pa", "ps") for kk in (0, 3, 7)] + ["w-3", "c-all4"]:
    gx, gy = S4.read_grid(k, c + "-x"), S4.read_grid(k, c + "-y")
    mx = int(mk[c + "-x"])
    px = {(x, y) for y in range(64) for x in range(64) if gx[y][x] != L.BG and gx[y][x] & 15 == 5}
    py = {(x, y) for y in range(64) for x in range(64) if gy[y][x] != L.BG and gy[y][x] & 15 == 5}
    both = px & py
    bits = collections.Counter(); par = collections.Counter(); dpar_x = collections.Counter(); dpar_y = collections.Counter()
    for (x, y) in sorted(both):
        vx, vy = gx[y][x], gy[y][x]
        s = S4.source_of(vx, vy)
        bits[(vx >> 4 & 3, vy >> 4 & 3)] += 1
        par[None if s is None else (s[0] & 1, s[1] & 1)] += 1
    for (x, y) in px: dpar_x[(gx[y][x] >> 4 & 3, x & 1, y & 1)] += 1
    for (x, y) in py: dpar_y[(gy[y][x] >> 4 & 3, x & 1, y & 1)] += 1
    print(f"{c}: tag-5 pixels x {len(px)} y {len(py)} same pixel {len(both)}; (bits x, bits y) {dict(bits)}; source parity {dict(par)}")
    print(f"    x job (bits, dest x&1, dest y&1): {dict(sorted(dpar_x.items()))}")
    print(f"    y job (bits, dest x&1, dest y&1): {dict(sorted(dpar_y.items()))}")
