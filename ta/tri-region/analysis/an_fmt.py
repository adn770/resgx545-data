import sys, gzip
sys.path.insert(0, "recompute")
import recompute_p1131 as R
d = R.pathlib.Path("data/ta-object-format")
for n in sys.argv[1:]:
    txt, par, td = R.load(d, n)
    o = R.first_object(par, td)
    print(n, "fmt %08x per %s masks %s" % (o["fmt"], o["per"], [hex(m) for m in o["masks"]]))
    for v in o["vertices"][:2]:
        print("   ", " ".join("%08x" % x for x in v))
