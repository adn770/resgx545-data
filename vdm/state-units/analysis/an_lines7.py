"""Post hoc: thick-line model. A line a-b is a rectangle of half-width hw (flat ends at a and b, sides
parallel to the segment) [model R], or a rectangle whose ends are extended by hw (model E); region listed iff
that polygon meets the closed region rectangle. For each (line, region) the least hw that makes them meet;
the feasible hw range over all the one-line jobs (ln-*, lb-*)."""
import sys, math, re
sys.path.insert(0, "recompute")
import recompute_p1131 as R
def sat_meet(poly, rect):
    # poly: 4 points convex; rect: x0,y0,x1,y1. Separating axis theorem: axes of the rect and of the poly.
    x0, y0, x1, y1 = rect
    rp = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    axes = [(1, 0), (0, 1)]
    for i in range(4):
        a, b = poly[i], poly[(i + 1) % 4]
        axes.append((-(b[1] - a[1]), b[0] - a[0]))
    for ax in axes:
        pp = [p[0] * ax[0] + p[1] * ax[1] for p in poly]; rr = [p[0] * ax[0] + p[1] * ax[1] for p in rp]
        if max(pp) < min(rr) - 1e-12 or max(rr) < min(pp) - 1e-12: return False
    return True
def poly(a, b, hw, ext):
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L; nx, ny = -uy, ux
    if ext:
        a = (a[0] - ux * hw, a[1] - uy * hw); b = (b[0] + ux * hw, b[1] + uy * hw)
    return [(a[0] + nx * hw, a[1] + ny * hw), (b[0] + nx * hw, b[1] + ny * hw), (b[0] - nx * hw, b[1] - ny * hw), (a[0] - nx * hw, a[1] - ny * hw)]
def hwmin(a, b, rect, ext):
    lo, hi = 0.0, 4.0
    if not sat_meet(poly(a, b, hi, ext), rect): return 99.0
    if sat_meet(poly(a, b, 1e-9, ext), rect): return 0.0
    for _ in range(40):
        m = (lo + hi) / 2
        if sat_meet(poly(a, b, m, ext), rect): hi = m
        else: lo = m
    return hi
rows = []
for sc in ("ta-line-point", "ta-line-bisect"):
    d = R.pathlib.Path("data/" + sc)
    if not d.exists(): continue
    for c in R.load_cases(d):
        if not c["name"].startswith(("ln-", "lb-")): continue
        t, p, td = R.load(d, c["name"])
        if R.outcome(t) == "fail" or not p: continue
        v = R.geometry(c["args"], c["w"], c["h"])
        m = re.search(r"--vdm 2=0x([0-9a-f]+)", c["args"]); nl = (int(m[1], 16) & 0x3fffff) // 2
        if nl != 1 or c["name"].endswith("-w80") or c["name"].endswith("-w40"): continue
        rm, _ = R.region_map(p, td)
        for ty in range(0, c["h"], 16):
            for tx in range(0, c["w"], 32):
                rows.append((c["name"], tx, ty, (tx, ty) in rm, v[0], v[1]))
for ext in (False, True):
    h = [(hwmin(r[4], r[5], (r[1], r[2], r[1] + 32, r[2] + 16), ext), r) for r in rows]
    lo = max((x for x, r in h if r[3]), default=0); hi = min((x for x, r in h if not r[3]), default=99)
    wl = max((x, r[0], r[1], r[2]) for x, r in h if r[3]); wh = min((x, r[0], r[1], r[2]) for x, r in h if not r[3])
    print("ends %s: listed needs hw >= %.4f (%s), not listed needs hw < %.4f (%s)  %s" % ("extended" if ext else "flat", lo, wl[1:], hi, wh[1:], "CONSISTENT" if lo < hi else "inconsistent"))
