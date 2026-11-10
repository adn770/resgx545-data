"""Post hoc: per-vertex fate (lost / duplicated / unreadable of 126) of g-e5 jobs, with the
functions of resgx545-data vdm/verification-1141ta/recompute/q164_fate.py applied to the S1 dumps
(not run by the frozen scorer)."""
import collections, gzip, pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / "src/resgx545-data/vdm/verification-1141ta/recompute"))
import q164_fate as Q
d = pathlib.Path(sys.argv[1])
for name in sys.argv[2:]:
    pp = sorted(d.glob(f"{name}.*param.bin.gz")); tt = sorted(d.glob(f"{name}.*tadata.bin.gz"))
    if not pp:
        print(name, "no dump"); continue
    p, td = gzip.open(pp[0]).read(), gzip.open(tt[0]).read()
    per, ws, O = Q.objects(p, td)
    seen, unread = collections.Counter(), 0
    sizes = []
    for a, (nv, e) in sorted(O.items()):
        vs = Q.verts(ws, per, a, nv, e)
        sizes.append(nv)
        for v in vs:
            if v is None: unread += 1
            else: seen[v] += 1
    lost = [i for i in range(126) if seen[i] == 0]
    dup = [i for i, c in seen.items() if c > 1]
    print(name, "objects", len(O), "sizes", sizes, "lost", lost, "dup", len(dup), "unreadable", unread)
