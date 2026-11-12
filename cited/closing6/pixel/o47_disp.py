# SPDX-License-Identifier: MIT
"""Round 6 planning, Q276, offline step O2 (post hoc reading of E858's kept images; exploration, nothing held out).
For every image word of a p5-o4 configuration whose x-job and y-job words at one pixel agree in tag and bits 5:4 and carry the
job's markers: source pixel (decoded from the coordinate halves, the frozen decode of score_o4.py), destination pixel,
displacement, parities, and whether the destination is a pixel the triangle covers (own tag-1 word in c-all4... approximated by:
the destination is the source of some own-pixel word in any job of the stage).
Reads only render/closing-r5-pixel of resgx545-data.  Standard library only."""
import collections, pathlib, sys
sys.dont_write_bytecode = True
R5 = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r5-pixel")
sys.path.insert(0, str(R5 / "score"))
import r4lib as L, score_o4 as S4
k = L.Kept(R5 / "out/20261112-091752/p5-o4")
mk = dict(ln.split("\t") for ln in (R5 / "bins/p5o4-markers.tsv").read_text().splitlines())
cfgs = sorted({n[:-2] for n in mk if n.endswith("-x")})
tri = set()
rec = []
for c in cfgs:
    gx, gy = S4.read_grid(k, c + "-x"), S4.read_grid(k, c + "-y")
    if gx is None or gy is None:
        continue
    mx = int(mk[c + "-x"])
    for y in range(64):
        for x in range(64):
            vx, vy = gx[y][x], gy[y][x]
            if L.BG in (vx, vy):
                continue
            if (vx & 0x3f) != (vy & 0x3f) or ((vx & 0xffff) >> 6) != mx or ((vy & 0xffff) >> 6) != mx + 1:
                rec.append((c, "unpaired", x, y, None)); continue
            s = S4.source_of(vx, vy)
            rec.append((c, vx & 15, x, y, s))
            if s == (x, y):
                tri.add(s)
print("configurations", len(cfgs), "triangle pixels seen as own", len(tri))
by = collections.defaultdict(list)
for c, t, x, y, s in rec:
    by[t].append((c, x, y, s))
for t in sorted(by, key=str):
    rows = by[t]
    if t == "unpaired":
        print(f"unpaired pixels (x and y jobs differ in low 6 bits or marker): {len(rows)}"); continue
    own = sum(1 for _, x, y, s in rows if s == (x, y))
    dis = [(x, y, s) for _, x, y, s in rows if s and s != (x, y)]
    nos = sum(1 for _, x, y, s in rows if s is None)
    print(f"\ntag {t}: {len(rows)} paired words; own pixel {own}; displaced {len(dis)}; source off target {nos}")
    if not dis:
        continue
    d = collections.Counter((x - s[0], y - s[1]) for x, y, s in dis)
    print("  displacement (dest - source) top:", d.most_common(8))
    print("  source parity (x&1,y&1):", dict(collections.Counter((s[0] & 1, s[1] & 1) for _, _, s in dis)))
    print("  dest parity:", dict(collections.Counter((x & 1, y & 1) for x, y, _ in dis)))
    print("  dest in triangle:", sum(1 for x, y, _ in dis if (x, y) in tri), "of", len(dis))
    print("  same place in 32x16 tile:", sum(1 for x, y, s in dis if (x % 32, y % 16) == (s[0] % 32, s[1] % 16)),
          "; same place in 2x2 quad origin:", sum(1 for x, y, s in dis if (x & ~1, y & ~1) == (s[0] & ~1, s[1] & ~1)))
    print("  tile step (dest tile - source tile, tiles 32x16):", collections.Counter(((x // 32) - (s[0] // 32), (y // 16) - (s[1] // 16)) for x, y, s in dis).most_common(8))
    print("  in-tile offset (dest - source mod tile):", collections.Counter(((x % 32) - (s[0] % 32), (y % 16) - (s[1] % 16)) for x, y, s in dis).most_common(6))
