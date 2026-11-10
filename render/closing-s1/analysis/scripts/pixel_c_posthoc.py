"""POST HOC re-reading of p-c (same decode as score_pix.score_c): where are the tag-2' pixels of c-u; per-config
tag maps by source parity and by lane (sx&1, sy&1); the replicate c-k7-x-rep against c-k7-x; and the frozen
hypotheses applied with c-u's 1.0 relaxed.  Not frozen."""
import collections, pathlib, sys
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score")); sys.path.insert(0, str(S1 / "gen"))
import score_pix as P
from s1lib import Kept, rows_of
k = Kept(S1 / "out" / "p-c")

def decode(cfg):
    gx, gy = P.read_pairs(k, f"{cfg}-x", f"{cfg}-y")
    H, W = gx.shape
    tags = collections.defaultdict(set)
    for y in range(H):
        for x in range(W):
            vx, vy = int(gx[y, x]), int(gy[y, x])
            if 0xff203040 in (vx, vy) or (vx & 15) != (vy & 15) or (vx & 15) not in (2, 12, 5):
                continue
            sx = round(P.f32_hi(vx) * W / 2 + W / 2 - .5); sy = round(P.f32_hi(vy) * H / 2 + H / 2 - .5)
            tags[(vx & 15, sx, sy)].add((x, y))
    return gx, gy, tags

for cfg in ("c-e709", "c-u", "c-k7", "c-k0", "c-k3", "c-g23"):
    gx, gy, tags = decode(cfg)
    src2 = {(sx, sy) for t, sx, sy in tags if t == 2}
    src12 = {(sx, sy) for t, sx, sy in tags if t == 12}
    both = src2 & src12
    print(f"{cfg}: sources tag2 {len(src2)} tag2' {len(src12)} both {len(both)}; tag-5 pairs "
          f"{sum(1 for t in tags if t[0] == 5)}; bg dwords x {int((gx == 0xff203040).sum())}")
    if cfg == "c-u":
        for t, sx, sy in sorted(tags):
            if t == 12:
                print(f"   c-u tag2' source ({sx},{sy}) at destinations {sorted(tags[(t, sx, sy)])}; same source has tag 2: {(sx, sy) in src2}")
    if cfg in ("c-g23", "c-k0", "c-k3"):
        par12 = collections.Counter((sx & 1, sy & 1) for sx, sy in src12)
        print(f"   tag2' by parity {dict(par12)}")
        if cfg == "c-g23":
            xs = collections.Counter(sx % 8 for sx, sy in src2); ys = collections.Counter(sy % 8 for sx, sy in src2)
            print(f"   g23 tag2 sources by sx%8 {dict(sorted(xs.items()))} by sy%8 {dict(sorted(ys.items()))}")
            q = collections.Counter(((sx // 2) & 1, (sy // 2) & 1) for sx, sy in src2)
            print(f"   g23 tag2 by (sx>>1&1, sy>>1&1) {dict(q)}")
# replicate
a, b = rows_of(k.out("c-k7-x")), rows_of(k.out("c-k7-x-rep"))
print("c-k7-x-rep identical pixels to c-k7-x:", a == b)
