"""Post hoc: for each line job, tile membership of each line (16 x 16 tiles) against variants of a
thickened segment test."""
import sys, math, collections
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path("data/ta-line-point")
cases = [c for c in R.load_cases(d) if c["name"].startswith("ln-")]

def obs_tiles(par, td, nprims):
    return R.observed_tiles(par, td, nprims)

def seg_dist_rect(a, b, x0, y0, x1, y1, half, shape):
    """does the segment ab, thickened by `half` (capsule: shape 'cap'; box-expanded bbox: 'bbox';
    square-ended rectangle: 'rect'), meet [x0, x1) x [y0, y1)? high sides open, low closed."""
    if shape == "bbox":
        bx0, bx1 = min(a[0], b[0]) - half, max(a[0], b[0]) + half
        by0, by1 = min(a[1], b[1]) - half, max(a[1], b[1]) + half
        return bx1 >= x0 and by1 >= y0 and bx0 < x1 and by0 < y1
    if shape == "ycol":   # thickened in y only (a segment's vertical extent +- half), x exact
        bx0, bx1 = min(a[0], b[0]), max(a[0], b[0])
        by0, by1 = min(a[1], b[1]) - half, max(a[1], b[1]) + half
        return bx1 >= x0 and by1 >= y0 and bx0 < x1 and by0 < y1
    # capsule: sample the distance from the tile rectangle to the segment: use fine sampling of the segment
    n = 400
    ex = x1 - 1e-9; ey = y1 - 1e-9
    for i in range(n + 1):
        t = i / n
        px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx = max(x0 - px, 0, px - ex); dy = max(y0 - py, 0, py - ey)
        if dx * dx + dy * dy <= half * half + 1e-12:
            return True
    return False

shapes = ["bbox", "ycol", "cap"]
halves = {"zero": lambda w: 0.0, "half": lambda w: w / 2, "full": lambda w: w}
tot = collections.Counter(); n = 0
for c in cases:
    t, p, td = R.load(d, c["name"])
    if R.outcome(t) == "fail" or not p:
        print(c["name"], "failed"); continue
    v = R.geometry(c["args"], c["w"], c["h"])
    m = [int(x, 16) for x in __import__("re").findall(r"--vdm 2=0x([0-9a-f]+)", c["args"])]
    nl = (m[0] & 0x3fffff) // 2
    lines = [(v[2 * i], v[2 * i + 1]) for i in range(nl)]
    wm = __import__("re").search(r"--blk 2=0x([0-9a-f]+)", c["args"])
    width = ((int(wm[1], 16) >> 8) & 0xff) / 16 if wm else 1.0
    obs = obs_tiles(p, td, nl)
    res = {}
    for sh in shapes:
        for hn, hf in halves.items():
            mis = 0
            for ty in range(0, c["h"], 16):
                for tx in range(0, c["w"], 16):
                    pred = {i for i, (a, b) in enumerate(lines) if seg_dist_rect(a, b, tx, ty, tx + 16, ty + 16, hf(width), sh)}
                    o = obs.get((tx, ty), set())
                    if "any" in o:
                        mis += 0 if pred else 1
                    elif pred != o:
                        mis += len(pred ^ o)
            res[(sh, hn)] = mis; tot[(sh, hn)] += mis
    n += 1
    print("%-16s w %.2f nl %d " % (c["name"], width, nl) + " ".join("%s/%s=%d" % (k[0], k[1][0], v_) for k, v_ in res.items()))
for k, v_ in sorted(tot.items(), key=lambda kv: kv[1]): print(k, v_)
