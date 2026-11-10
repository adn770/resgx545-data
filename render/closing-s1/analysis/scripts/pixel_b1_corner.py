"""POST HOC: tile-corner words of row 0 of p-b1 jobs against RZ32 of the exact plane at the corner and at the first
pixel centre; and the in-tile step (word difference between neighbours)."""
import pathlib, sys, struct
from fractions import Fraction as F
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score")); sys.path.insert(0, str(S1 / "gen"))
import score_pix as P
from s1lib import Kept
def rz32(q):  # q Fraction in [0.5, 1)
    return 0x3f000000 + int((q - F(1, 2)) * 2 ** 24)
k = Kept(S1 / "out" / "p-b1")
for n, a in [(x.split(":")[0], F(x.split(":")[1])) for x in sys.argv[1:]]:
    z = P.depth_image(k.depth(n), 1024, 32)
    row = z[0]
    m = (row != P.BG) & (row != 0x3F800000)
    xs = np.nonzero(m)[0]
    print(n, "A =", a, float(a))
    for t in range(xs.max() // 32 + 1):
        w = int(row[32 * t])
        c0 = rz32(F(1, 2) + a * 32 * t)
        c5 = rz32(F(1, 2) + a * (32 * t + F(1, 2)))
        steps = np.diff(row[32 * t:32 * t + 32][m[32 * t:32 * t + 32]].astype(np.int64))
        print(f"  t{t:2d} word {w:#x} corner-RZ {w - c0:+d} centre-RZ {w - c5:+d} steps {sorted(set(steps.tolist()))}")
