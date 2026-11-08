"""Per primitive, per 16x16 tile: observed membership (from the control streams) against rule
variants of tile/triangle overlap. Post hoc analysis over the 27 ta-tri-boundary cases."""
import sys, itertools, collections
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/ta-tri-boundary")
cases = R.load_cases(d)

def observed(par, td, nprims):
    """{(tx,ty): (set of prims in tile)} per 16x16 tile, from the first stream object of each region."""
    obs = collections.defaultdict(set)
    bad = 0
    for (_i, x0, y0, _f, st) in R.regions(td):
        if not st:
            continue
        sw = R.stream(par, st)
        w0 = sw[0]; t = (w0 >> 16) & 0xff; vm = w0 & 0xffff
        ANY = {"any"}
        if t in (0x80, 0x90, 0x98):
            L = ANY if t in (0x80, 0x90) else set()
            Rr = ANY if t in (0x98, 0x90) else set()
        elif t == 0x88:
            L = {p for p in range(nprims) if sw[2] & (1 << p)}
            Rr = {p for p in range(nprims) if (sw[2] >> 16) & (1 << p)}
        elif t in (0x8a, 0x8c):
            m = {p for p in range(nprims) if sw[2] & (1 << p)}
            L, Rr = (m, set()) if t == 0x8a else (set(), m)
        else:
            bad += 1; continue
        for p in L: obs[(x0, y0)].add(p)
        for p in Rr: obs[(x0 + 16, y0)].add(p)
    return obs, bad

def ov(t, x0, y0, x1, y1, lo_open, hi_open, edge_open):
    bx0, bx1 = min(p[0] for p in t), max(p[0] for p in t)
    by0, by1 = min(p[1] for p in t), max(p[1] for p in t)
    if (bx1 <= x0 if lo_open else bx1 < x0) or (by1 <= y0 if lo_open else by1 < y0):
        return False
    if (bx0 >= x1 if hi_open else bx0 > x1) or (by0 >= y1 if hi_open else by0 > y1):
        return False
    for i in range(3):
        a, b, c = t[i], t[(i + 1) % 3], t[(i + 2) % 3]
        nx, ny = b[1] - a[1], a[0] - b[0]
        side = nx * (c[0] - a[0]) + ny * (c[1] - a[1])
        vals = [(nx * (x - a[0]) + ny * (y - a[1])) * side for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        if all((v <= 0) if edge_open else (v < 0) for v in vals):
            return False
    return True

variants = list(itertools.product((False, True), repeat=3))
tot = collections.Counter(); nprim_pairs = 0
for c in cases:
    t, par, td = R.load(d, c["name"])
    if R.outcome(t) == "fail" or not par:
        print(c["name"], "failed"); continue
    v = R.geometry(c["args"], c["w"], c["h"])
    tris = [v[i:i + 3] for i in range(0, len(v) - 2, 3)]
    obs, bad = observed(par, td, len(tris))
    res = []
    for var in variants:
        mism = 0
        for ty in range(0, c["h"], 16):
            for tx in range(0, c["w"], 16):
                pred = {p for p, tr in enumerate(tris) if ov(tr, tx, ty, tx + 16, ty + 16, *var)}
                o = obs.get((tx, ty), set())
                if o == {"any"}:
                    mism += 0 if pred else 1
                elif pred != o:
                    mism += len(pred ^ o)
        tot[var] += mism
        res.append(mism)
    nprim_pairs += (c["w"] // 16) * (c["h"] // 16) * len(tris)
    print("%-20s %-7s bad %d mismatching (prim,tile) per variant (lo_open,hi_open,edge_open): %s" % (c["name"], c["set"], bad, res))
print("pairs", nprim_pairs)
for var in variants:
    print("variant lo_open=%d hi_open=%d edge_open=%d: %d mismatches" % (*map(int, var), tot[var]))

if len(sys.argv) > 2:
    name = sys.argv[2]
    c = next(c for c in cases if c["name"] == name)
    t, par, td = R.load(d, name)
    v = R.geometry(c["args"], c["w"], c["h"])
    tris = [v[i:i + 3] for i in range(0, len(v) - 2, 3)]
    print([(tuple(round(x, 4) for x in p)) for p in tris[0]], len(tris))
    obs, bad = observed(par, td, len(tris))
    for (_i, x0, y0, _f, st) in R.regions(td):
        if st: print(" region", x0, y0, " ".join("%08x" % w for w in R.stream(par, st)))
    for ty in range(0, c["h"], 16):
        for tx in range(0, c["w"], 16):
            pred = {p for p, tr in enumerate(tris) if ov(tr, tx, ty, tx + 16, ty + 16, False, True, False)}
            o = obs.get((tx, ty), set())
            if (o == {"any"} and not pred) or (o != {"any"} and pred != o):
                print(" tile", tx, ty, "pred", sorted(pred), "obs", sorted(obs.get((tx, ty), set())))
