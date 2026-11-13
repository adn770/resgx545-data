"""POST HOC (formed after reading bd-uv5 and bd-hb-ns-uv5; not frozen, both jobs are the fit).
Mode 5, v also mode 5, texel (s, t):
  s inside, t < 0:   7 M + 52 + s     s inside, t >= H: 4 M + 52 + s     (M = max(W, H))
  corners (s, t both outside): c + {0: t<0 s<0, 1: t<0 s>=W, 2: t>=H s<0, 3: t>=H s>=W}
with c = 16 at 16 x 16 and 20 at 32 x 8; candidate forms of c: (W+H)/2, 12 + M/4, 12 + W/4.
Run: python -I post_a.py > post_a.out"""
import collections
exec(open("score_a.py").read().split('print("job;')[0])
for name, w, h, um, vm, st in jobs:
    if um != 5 or vm != 5: continue
    m = max(w, h)
    ok = n = 0
    cs = collections.Counter()
    for s, t, got in st:
        if 0 <= s < w and t < 0: ok += got == 7 * m + 52 + s; n += 1
        elif 0 <= s < w and t >= h: ok += got == 4 * m + 52 + s; n += 1
        elif not 0 <= s < w and not 0 <= t < h:
            cs[got - ((0 if t < 0 else 2) + (0 if s < 0 else 1))] += 1
    print(f"{name} {w}x{h}: s-inside rows {ok}/{n}; corner base c values {dict(cs)}; (W+H)/2 = {(w+h)//2}, 12 + M/4 = {12 + m//4}")
