"""POST HOC: g-ctl (1024 x 32, S1) against E731's dp-bx-b0 (256 x 128): the same plane (A = 1/6400, z0 = 0.5, B = 0)
on two target widths.  Compares the stored words of the shared pixels (x < 256, y < 32)."""
import gzip, pathlib, sys
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score")); sys.path.insert(0, str(S1 / "gen"))
import score_pix as P
from s1lib import Kept
D = pathlib.Path.home() / "src/resgx545-data/texture/p1141/out-hw/p1141tex-dumps/isp-b-depth"
e = P.depth_image(gzip.open(D / "dp-bx-b0.depth.1.bin.gz").read(), 256, 128)
k = Kept(S1 / "out" / "p-b1")
g = P.depth_image(k.depth("g-ctl"), 1024, 32)
a, b = e[:32, :256].astype(np.int64), g[:32, :256].astype(np.int64)
m = (a != P.BG) & (a != 0x3F800000) & (b != P.BG) & (b != 0x3F800000)
d = (b - a)[m]
print("shared covered pixels", int(m.sum()), "word differences (g-ctl - dp-bx-b0):", dict(zip(*np.unique(d, return_counts=True))))
for x in range(0, 256, 32):
    print(f"  x {x:3d}: e731 {a[0, x]:#x} s1 {b[0, x]:#x} diff {b[0, x] - a[0, x]:+d}")
print("frozen row_range on dp-bx-b0 (256 x 128):", P.row_range(e))
print("frozen row_range on dp-bx-b0 rows 0..31:", P.row_range(e[:32]))
print("frozen row_range on g-ctl x < 256:", P.row_range(g[:, :256]))
dd = np.argwhere(m & (a != b))
print("differing pixels by tile column (x // 32):", dict(zip(*np.unique(dd[:, 1] // 32, return_counts=True))))
print("differing pixels by row:", dict(zip(*np.unique(dd[:, 0], return_counts=True))))
print("first differing pixels:", [(int(x), int(y), hex(int(a[y, x])), hex(int(b[y, x]))) for y, x in dd[:8]])
