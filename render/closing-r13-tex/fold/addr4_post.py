"""POST HOC (after the run, not frozen): what the uv5 rows' corner pixels read (every frozen
corner form, CO-WH2, CO-12M4, CO-12W4, read 0 of the corner pixels on both rows)."""
import collections, gzip, os, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import addr as A, pins
D = os.path.join(KP, "out/20261113-214825/addr4")
for job in A.JOBS:
    if job[6] != "uv5":
        continue
    name, _, w, h = job[:4]
    px = pins.pixels(gzip.open(os.path.join(D, name + ".txt.gz"), "rt").read())
    c = collections.defaultdict(collections.Counter)
    for p, v in enumerate(px):
        s, t = A.texel(w, h, "uv5", p % 64, p // 64)
        if not 0 <= s < w and not 0 <= t < h:
            k = ("above" if t < 0 else "below") + "-" + ("left" if s < 0 else "right")
            c[k][(v & 0x0FFFFFFF) - A.BASE] += 1
    print(name, f"W {w} H {h} M {max(w, h)}:",
          {k: dict(v.most_common(3)) for k, v in sorted(c.items())})
# the corner base c (above-left) over every kept shape: E565's bd-uv5 16 x 16 (16), bd-hb-ns-uv5
# 32 x 8 (20; closing11 c2's post_a.out) and these two (24): candidate forms, fitted after reading
import math
seen = {(16, 16): 16, (32, 8): 20, (64, 16): 24, (16, 64): 24}
forms = {"(W + H) / 2": lambda w, h: (w + h) // 2, "12 + M / 4": lambda w, h: 12 + max(w, h) // 4,
         "12 + W / 4": lambda w, h: 12 + w // 4,
         "4 log2 M": lambda w, h: 4 * int(math.log2(max(w, h)))}
for k, f in forms.items():
    print(f"corner base {k}: {sum(f(w, h) == c for (w, h), c in seen.items())} of {len(seen)} shapes")
