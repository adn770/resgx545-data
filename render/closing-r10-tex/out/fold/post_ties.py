"""Post hoc (fold): cube3's tie rows, per row the face each tie pixel read (axis, sign), the columns of
the higher-axis reads, and the tied value there."""
import collections, gzip, os, sys
KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import cube as C, texprog as T
ATT = os.path.join(KP, "out/20261113-102730/cube3")
for name, st, spec, n, t0, kind in C.jobs3():
    if kind not in ("tie", "replay"): continue
    px = T.pixels(gzip.open(os.path.join(ATT, name + ".txt.gz"), "rt").read())
    faces = collections.Counter(); hicols = collections.Counter(); locols = collections.Counter()
    for (x, y), c in C.tie_cells(spec).items():
        ax = C.tied_axes(c)
        if len(ax) != 2: continue
        f = (px[(x, y)] & 0x0FFFFFFF) // 256
        faces["+-xyz"[0] + "xyz"[f // 2] + ("-" if f & 1 else "+")] += 1
        (hicols if f // 2 == max(ax) else locols)[x] += 1
    print(name, dict(faces), "high cols", sorted(hicols)[:8], "...", len(hicols), "cols")
    if hicols and locols:
        xs = sorted(hicols)
        print("   high at x", xs, "tied value there", [float(T.coord(spec[min(C.tied_axes(tuple(T.coord(s, x, 0) for s in spec)))], x, 0)) for x in xs[:4]])
