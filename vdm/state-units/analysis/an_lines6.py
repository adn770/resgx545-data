"""Post hoc: tile classes (left/right/both) of the one-line jobs against 'segment within e of the
16 x 16 tile'."""
import sys, math, re
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path("data/ta-line-point")
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
            cl = rm.get((tx, ty), "-")
            dl, dr = segdist(a, b, tx, ty, tx + 16, ty + 16), segdist(a, b, tx + 16, ty, tx + 32, ty + 16)
            rows.append((c["name"], tx, ty, cl, dl, dr))
for e in (0.4, 0.5, 0.6, 1.0, 1.5):
    mis = []
    for r in rows:
        pl, pr = r[4] <= e, r[5] <= e
        pc = "-" if not (pl or pr) else "B" if pl and pr else "L" if pl else "R"
        if pc != r[3]: mis.append((r[0], r[1], r[2], "obs", r[3], "pred", pc, round(r[4], 2), round(r[5], 2)))
    print("tile rule e=%.2f: %d of %d regions differ" % (e, len(mis), len(rows)), mis[:4])
# region rule: both tiles whenever the region is touched ('0x90') except where a form says one tile
import collections
cnt = collections.Counter(r[3] for r in rows)
print(cnt)
