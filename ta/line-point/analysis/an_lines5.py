"""Post hoc: region presence of every line job (any number of lines) against 'some line's segment is
within e of the region rectangle', e swept."""
import sys, math, re
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/ta-line-point")
def segdist(a, b, x0, y0, x1, y1):
    best = 1e9
    for i in range(2001):
        t = i / 2000; px, py = a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t
        dx = max(x0 - px, 0, px - x1); dy = max(y0 - py, 0, py - y1)
        best = min(best, math.hypot(dx, dy))
    return best
data = []
for c in R.load_cases(d):
    if not c["name"].startswith(("ln-", "lb-")): continue
    t, p, td = R.load(d, c["name"])
    if R.outcome(t) == "fail" or not p: continue
    v = R.geometry(c["args"], c["w"], c["h"])
    m = re.search(r"--vdm 2=0x([0-9a-f]+)", c["args"]); nl = (int(m[1], 16) & 0x3fffff) // 2
    lines = [(v[2*i], v[2*i+1]) for i in range(nl)]
    rm, _ = R.region_map(p, td)
    for ty in range(0, c["h"], 16):
        for tx in range(0, c["w"], 32):
            dist = min(segdist(a, b, tx, ty, tx + 32, ty + 16) for a, b in lines)
            data.append((c["name"], tx, ty, (tx, ty) in rm, dist))
print("regions compared", len(data))
for e in (0.0, 0.25, 0.4375, 0.5, 0.5625, 0.75, 1.0, 1.5, 1.94):
    mis = [r for r in data if (r[4] <= e) != r[3]]
    print("e = %.4f: %d mismatches" % (e, len(mis)), [(r[0], r[1], r[2], round(r[4], 3)) for r in mis[:3]])
lo = max(r[4] for r in data if r[3]); hi = min(r[4] for r in data if not r[3])
print("feasible: e >= %.4f and e < %.4f" % (lo, hi), [r for r in data if r[3] and r[4] == lo][:1], [r for r in data if not r[3] and r[4] == hi][:1])
