# SPDX-License-Identifier: MIT
"""Round 6 planning, Q230: how often 18 words of a window are 'separable' (delta = [frac >= theta] for some theta) by chance, if the
excess e of each mantissa were independent of its neighbours (e uniform on [0, 0.5), delta = [frac + e >= 1], frac uniform).
Also with the FIT set's own empirical shares by frac decile (rw6_look.out).  Seeded; standard library only."""
import random
random.seed(20261112)
SHARE = [0, 0, 0, 0, 0, 1 / 13, 2 / 11, 2 / 8, 3 / 9, 7 / 8]
def sep(pts):
    ones = [f for f, d in pts if d]; zeros = [f for f, d in pts if not d]
    return not ones or not zeros or min(ones) > max(zeros)
for label, draw in (("e uniform on [0, 0.5)", lambda f: f + random.random() / 2 >= 1),
                    ("FIT shares by decile", lambda f: random.random() < SHARE[int(f * 10)])):
    for n in (18, 36):
        T = 200000; k = triv = 0
        for _ in range(T):
            pts = [(f, draw(f)) for f in (random.random() for _ in range(n))]
            s = sep(pts); k += s; triv += s and not any(d for _, d in pts)
        print(f"{label}, n = {n}: separable {k / T:.4f} (of which no RZ + 1 word at all {triv / T:.4f})")
