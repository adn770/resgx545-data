# pre-freeze engine check: candidate "exact" equals r10-geo far.py's coverage (vertices only, no hardware data)
import sys, fractions
sys.path.insert(0, "/Users/jtorra/src/resgx545-data/render/closing-r10-geo/gen")
sys.path.insert(0, ".")
import far as FA, q261_rule as R
F = fractions.Fraction
bad = 0
for name, verts in FA.FAR[:4]:
    V = [(FA.grid(x), FA.grid(y)) for x, y in verts]
    cov = FA.coverage(V)
    W = R.prep(V, R.Cand("exact", "exact"))
    for y in range(0, 64, 3):
        for x in range(0, 64, 3):
            if R.decide(R.Cand("exact", "exact"), W, x * 256 + 128, y * 256 + 128) != cov[(x, y)][0]:
                bad += 1
print("mismatch", bad)
# rnd sanity
print(R.rnd(F(1, 3), 24, "RN"), float(R.rnd(F(1, 3), 24, "RN")) == float(__import__("numpy").float32(1 / 3)))
print(R.rnd(5, 2, "RZ"), R.rnd(7, 2, "RN"), R.rnd(F(-5), 2, "RZ"))
