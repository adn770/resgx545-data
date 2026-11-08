"""Post hoc: region-level test (32 x 16 regions) for the one-line jobs: feasible expansion e of the
segment's bounding box or of the segment."""
import sys, math, re
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path("data/ta-line-point")
def gap(lo, hi, a, b): return max(lo - b, a - hi, 0.0)
def segdist(a, b, x0, y0, x1, y1):
    best = 1e9
    for i in range(4001):
        t = i / 4000; px, py = a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t
        dx = max(x0 - px, 0, px - x1); dy = max(y0 - py, 0, py - y1)
        best = min(best, math.hypot(dx, dy))
    return best
rows = []
for c in R.load_cases(d):
    if not c["name"].startswith("ln-"): continue
    t, p, td = R.load(d, c["name"])
    if R.outcome(t) == "fail" or not p: continue
    v = R.geometry(c["args"], c["w"], c["h"])
    m = re.search(r"--vdm 2=0x([0-9a-f]+)", c["args"]); nl = (int(m[1], 16) & 0x3fffff) // 2
    if nl != 1: continue
    a, b = v[0], v[1]
    rm, first = R.region_map(p, td)
    for ty in range(0, c["h"], 16):
        for tx in range(0, c["w"], 32):
            inn = (tx, ty) in rm
            gx = gap(tx, tx + 32, min(a[0], b[0]), max(a[0], b[0])); gy = gap(ty, ty + 16, min(a[1], b[1]), max(a[1], b[1]))
            rows.append((c["name"], tx, ty, inn, gx, gy, segdist(a, b, tx, ty, tx + 32, ty + 16)))
for metric, f in (("bbox-chebyshev", lambda r: max(r[4], r[5])), ("bbox-euclid", lambda r: math.hypot(r[4], r[5])), ("segment", lambda r: r[6])):
    lo = max((f(r) for r in rows if r[3]), default=0); hi = min((f(r) for r in rows if not r[3]), default=1e9)
    wl = max((r for r in rows if r[3]), key=f); wh = min((r for r in rows if not r[3]), key=f)
    print("%-15s e >= %.4f (%s %d,%d)   e < %.4f (%s %d,%d)   %s" % (metric, f(wl), wl[0], wl[1], wl[2], f(wh), wh[0], wh[1], wh[2], "CONSISTENT" if f(wl) < f(wh) else "inconsistent"))
