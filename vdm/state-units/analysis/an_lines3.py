"""Post hoc: the smallest constant expansion e (pixels) of a line's bounding box, or of the segment,
that reproduces the observed tile membership: lower and upper bound over all tiles of all line jobs."""
import sys, math, re, collections
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path("data/ta-line-point")
def gap(lo, hi, a, b):   # distance between interval [a,b] and [lo,hi)
    return max(lo - b, a - hi, 0.0)
def segdist(a, b, x0, y0, x1, y1):
    best = 1e9
    for i in range(2001):
        t = i / 2000; px, py = a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t
        dx = max(x0 - px, 0, px - x1); dy = max(y0 - py, 0, py - y1)
        best = min(best, math.hypot(dx, dy))
    return best
for metric in ("bbox-chebyshev", "bbox-euclid", "segment"):
    lo, hi = 0.0, 1e9; wl = wh = None
    for c in R.load_cases(d):
        if not c["name"].startswith("ln-"): continue
        t, p, td = R.load(d, c["name"])
        if R.outcome(t) == "fail" or not p: continue
        v = R.geometry(c["args"], c["w"], c["h"])
        m = re.search(r"--vdm 2=0x([0-9a-f]+)", c["args"]); nl = (int(m[1], 16) & 0x3fffff) // 2
        if nl != 1: continue
        lines = [(v[2*i], v[2*i+1]) for i in range(nl)]
        obs = R.observed_tiles(p, td, nl)
        for ty in range(0, c["h"], 16):
            for tx in range(0, c["w"], 16):
                o = obs.get((tx, ty), set())
                for i, (a, b) in enumerate(lines):
                    inn = (i in o) or ("any" in o)
                    gx = gap(tx, tx + 16, min(a[0], b[0]), max(a[0], b[0])); gy = gap(ty, ty + 16, min(a[1], b[1]), max(a[1], b[1]))
                    g = max(gx, gy) if metric == "bbox-chebyshev" else math.hypot(gx, gy) if metric == "bbox-euclid" else segdist(a, b, tx, ty, tx + 16, ty + 16)
                    if inn and g > lo: lo, wl = g, (c["name"], tx, ty, i)
                    if not inn and g < hi: hi, wh = g, (c["name"], tx, ty, i)
    print("%-15s required e >= %.4f (%s)  and e < %.4f (%s)" % (metric, lo, wl, hi, wh))
