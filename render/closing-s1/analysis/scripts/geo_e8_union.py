"""Post hoc: g-e8 images against the frozen numpy ISP model with the depth starting at 1.0 (no load,
E664: bits 1 and 14 both needed; the frozen ctl 0x0017100e lacks bit 14), colour ignored or not."""
import sys, pathlib, re, collections, numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "score"))
from s1lib import Kept, rows_of
import score_geo as G
k = Kept(sys.argv[1])

def model(nobj, cmp_, mv, start):
    zs = [float(np.float32(z)) for z in (0.2, 0.5, 0.8)]
    base = [(16, 16), (112, 40), (40, 112)]
    depth = np.full((128, 128), start); cover = np.zeros((128, 128), int); ne = np.zeros((128, 128), bool)
    ys, xs = np.mgrid[0:128, 0:128]; px, py = xs + 0.5, ys + 0.5
    for oi in range(nobj):
        dx, dy = mv if oi == 1 else (0, 0)
        (x0, y0), (x1, y1), (x2, y2) = [(a + dx, b + dy) for a, b in base]
        det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        l1 = ((px - x0) * (y2 - y0) - (x2 - x0) * (py - y0)) / det
        l2 = ((x1 - x0) * (py - y0) - (px - x0) * (y1 - y0)) / det
        l0 = 1 - l1 - l2
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        z = l0 * zs[0] + l1 * zs[1] + l2 * zs[2]
        ne |= (inside & (np.minimum(np.minimum(l0, l1), l2) < 2e-4)) | (inside & (np.abs(z - depth) < 1e-4))
        if cmp_ == "less":
            draw = inside & (z < depth); depth = np.where(draw, z, depth); cover = np.where(draw, oi + 1, cover)
    return cover, ~ne

for n in k.names():
    m = re.match(r"o(\d)-(less|never)-?(m[AB]|ctl)?", n)
    img = np.array(rows_of(k.out(n) or ""), dtype=np.int64)
    mv = {"mA": (32, 16), "mB": (-16, 24), "ctl": (0, 0), None: (0, 0)}[m[3]]
    cov, valid = model(int(m[1]), m[2], mv, 1.0)
    obs_any = (img == 0xff00ff00) | (img == 0xffff0000)
    d_any = int(((obs_any != (cov > 0)) & valid).sum())
    obs = np.where(img == 0xff00ff00, 1, np.where(img == 0xffff0000, 2, 0))
    d_col = int(((obs != cov) & valid).sum())
    print(n, "colours", dict(collections.Counter(hex(v) for v in img.ravel().tolist()).most_common(4)),
          "| start 1.0: drawn-vs-model differ", d_any, "; colour-by-object differ", d_col)
