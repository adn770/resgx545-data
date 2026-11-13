"""Post hoc (fold): addr3's offsets (the read less H-MASK-V's index) per row against 8 max(W, H) + 52
(H-MAX, formed after the run), and mode 5's reads past the texture against 5 M + 52 + t and
6 M + 52 + t with M = max(W, H)."""
import collections, gzip, os, sys
KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import addr as A, texprog as T
ATT = os.path.join(KP, "out/20261113-102730/addr3")
for name, st, w, h, um, vm, models in A.JOBS:
    px = T.pixels(gzip.open(os.path.join(ATT, name + ".txt.gz"), "rt").read())
    m = max(w, h)
    ok = 0
    for y in range(32):
        for x in range(64):
            s, t = A.texel(w, h, x, y)
            if um == 5 and not 0 <= s < w:
                want = (5 if s < 0 else 6) * m + 52 + t
            else:
                want = A.index(A.wrap(s, um, w), A.wrap(t, vm, h), w, h) + (8 * m + 52 if um else 0)
            ok += (px[(x, y)] & 0x0FFFFFFF) - A.BASE == want
    print(f"{name} ({w} x {h}, u mode {um}): H-MAX {ok}/2048")
