"""Post hoc: for the multi-line jobs, which vertex pair (i, j) of the job's 6 vertices gives each TA object's
region list (distance from the segment to the 32 x 16 region <= 0.5)."""
import sys, math, re, itertools, collections
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path("data/ta-line-point")
def segdist(a, b, x0, y0, x1, y1):
    best = 1e9
    for i in range(801):
        t = i / 800; px, py = a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t
        dx = max(x0 - px, 0, px - x1); dy = max(y0 - py, 0, py - y1)
        best = min(best, math.hypot(dx, dy))
    return best
for name in ("ln-ctl64-two", "ln-two128", "ln-two128-shift", "ln-three64", "ln-three128", "ln-two128-w40"):
    c = next(c for c in R.load_cases(d) if c["name"] == name)
    t, p, td = R.load(d, name)
    v = R.geometry(c["args"], c["w"], c["h"])
    objs = collections.defaultdict(set)
    for (_i, x0, y0, _f, st) in R.regions(td):
        if st:
            for (pw, ow, _e, _m) in R.stream_objects(R.stream(p, st)):
                objs[ow & 0x3ffffff].add((x0, y0))
    print(name, "objects", {hex(k): len(s) for k, s in objs.items()})
    for addr, regs in sorted(objs.items()):
        best = []
        for i, j in itertools.combinations(range(6), 2):
            pred = {(x0, y0) for y0 in range(0, c["h"], 16) for x0 in range(0, c["w"], 32) if segdist(v[i], v[j], x0, y0, x0 + 32, y0 + 16) <= 0.5}
            best.append((len(pred ^ regs), (i, j), len(pred)))
        best.sort()
        print("   object", hex(addr), len(regs), "regions; best single pairs (mismatches, pair, size):", best[:3])
