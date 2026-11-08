import sys
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path("data/ta-tri-boundary")
cs = {c["name"]: c for c in R.load_cases(d)}
for n in sys.argv[1:]:
    c = cs[n]
    t, p, td = R.load(d, n)
    v = R.geometry(c["args"], c["w"], c["h"])
    print(n, "verts", [(round(x, 4), round(y, 4)) for x, y in v[:3]], "...")
    rm, first = R.region_map(p, td)
    for k in sorted(first, key=lambda k: (k[1], k[0])):
        sw = first[k]
        print("  region", k, " ".join("%08x" % w for w in sw))
