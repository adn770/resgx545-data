"""POST HOC: row 0 of a p-b1 depth image against the exact plane z = 0.5 + A (x + 0.5) (ulps of the stored value)."""
import pathlib, sys
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score")); sys.path.insert(0, str(S1 / "gen"))
import score_pix as P
from s1lib import Kept
k = Kept(S1 / "out" / "p-b1")
n = sys.argv[1]
A = float(sys.argv[2])
z = P.depth_image(k.depth(n), 1024, 32)
for r in [int(a) for a in sys.argv[3:]] or [0]:
    row = z[r]
    m = (row != P.BG) & (row != 0x3F800000)
    xs = np.nonzero(m)[0]
    zf = row.view(np.float32).astype(np.float64)
    ex = 0.5 + A * (xs + 0.5) + A * 0  # plane along x, B = 0
    d = (zf[xs] - ex) / P.ulp32(zf[xs])
    print(n, "row", r, "covered", len(xs), "x", xs.min(), xs.max())
    for t in range(0, xs.max() // 32 + 1):
        sel = (xs // 32) == t
        if sel.any():
            print(f"  tile {t:2d}: dev ulps min {d[sel].min():+.2f} max {d[sel].max():+.2f}  first word {row[xs[sel][0]]:#010x}")
