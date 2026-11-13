"""python -I score_q078.py > score_q078.out"""
import sys
sys.path.insert(0, "/Users/jtorra/src/scratch/resgx545/closing11/plan/c8-q078")
from common import *
import q078_rule as R
inv, lv = inverse()
J = {  # job: (T3, p1132 dump, r9-x replicate dump)
    "an-t3b11": (0x00800000, P32 + "an-t3b11.txt.gz", R9 + "an-t3b11.txt.gz"),
    "an-t3b12": (0x00801800, P32 + "an-t3b12.txt.gz", R9 + "an-t3b12.txt.gz"),
    "an-ctl": (0x00800800, P32 + "an-ctl.txt.gz", R9 + "an-ctl.txt.gz"),
}
def score(fn, px):
    n = 0
    for p in range(2048):
        if fn(p % 64, p // 64) == px[p]:
            n += 1
    return n
img = {k: (pixels(v[1]), pixels(v[2])) for k, v in J.items()}
print("replicate check (r9-x image == E564 image):", {k: a == b for k, (a, b) in img.items()})
print("distinct names: ", {k: len(set(a)) for k, (a, b) in img.items()})
# inverse map of the two decoded jobs
for k in ("an-t3b11", "an-t3b12"):
    a = img[k][0]
    from collections import Counter
    c = Counter(inv[v & 0xfffffff] if k == "an-t3b12" else inv[v & 0xfffffff][0] for v in a)
    print("inverse map", k, dict(c))
print("uniqueness: chain dwords", len(inv), "distinct inverse entries", len(set(inv.values())), "(counting fill: each dword names itself)")
# control's level from the value range (values are blends inside a level, so only the level is read)
cl = [inv[v & 0xfffffff][0] for v in img["an-ctl"][0]]
pred = [R.level(p % 64) for p in range(2048)]
print("control level (value range) vs round(lod):", sum(a == b for a, b in zip(cl, pred)), "of 2048")
print()
print("BIT 11 CLEARED, an-t3b11 (fit job; r9-x replicate is the same image):")
for nm, fn in (("B11-LEVEL0", R.b11_level0), ("B11-STRIDE", R.b11_stride), ("B11-CHAIN0", R.b11_chain0)):
    print(" ", nm, score(fn, img["an-t3b11"][0]), score(fn, img["an-t3b11"][1]), "of 2048 (E564, r9-x)")
ks = [k for k in range(0, 129) if score(lambda x, y, k=k: R.b11_bias(x, y, k), img["an-t3b11"][0]) == 2048]
print("  B11-BIAS-k exact for k (eighths):", (min(ks), max(ks)) if ks else None, "count", len(ks), "of 129")
print("  B11-MIPOFF equals B11-LEVEL0 pixel for pixel: True (by definition)")
print("BIT 12 SET, an-t3b12 (fit job):")
for nm, fn in (("B12-LAST", R.b12_last), ("B12-BIT10", R.b12_bit10)):
    print(" ", nm, score(fn, img["an-t3b12"][0]), score(fn, img["an-t3b12"][1]), "of 2048")
ks = [k for k in range(0, 129) if score(lambda x, y, k=k: R.b12_bias(x, y, k), img["an-t3b12"][0]) == 2048]
print("  B12-BIAS-k exact for k (eighths):", (min(ks), max(ks)) if ks else None, "count", len(ks), "of 129")
print("  B12-CTL (level round(lod), 3 or 4):", sum(inv[v & 0xfffffff][0] == R.level(p % 64) for p, v in enumerate(img["an-t3b12"][0])), "of 2048 pixels at the control's level")
print("  B12-ADDR equals B12-LAST pixel for pixel (a constant 5460 either way)")
print()
bits = img["an-t3b11"][0]
print("cross check: bit-11-clear image vs bit-12 image share no pixel:",
      sum(a == b for a, b in zip(bits, img["an-t3b12"][0])), "of 2048")
