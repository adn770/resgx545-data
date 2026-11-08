import sys
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path("data/ta-line-point")
cs = {c["name"]: c for c in R.load_cases(d)}
for n in sys.argv[1:]:
    c = cs[n]
    t, p, td = R.load(d, n)
    v = R.geometry(c["args"], c["w"], c["h"])
    print(n, c["args"][c["args"].index("--blk 1"):][:150])
    print(" verts", [(round(x, 4), round(y, 4)) for x, y in v])
    o = R.first_object(p, td)
    if o and "error" not in o:
        print(" nv", o["nv"], "prims", o["prims"], "plist", ["%08x" % x for x in o["plist"]], "isp", ["%08x" % x for x in o["isp"]], "lw %08x fmt %08x" % (o["lw"], o["fmt"]))
    for r in sorted(R.regions(td), key=lambda r: (r[2], r[1])):
        if r[4]:
            print("  region", r[1], r[2], " ".join("%08x" % w for w in R.stream(p, r[4])))
