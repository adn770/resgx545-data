"""Post hoc (fold): cube3's edges, per out column the kept bytes against H-SEAM-FLOAT and H-SEAM-ADJ
(row 0; every row has the same coordinates), and the outer tap's bytes solved from the kept value."""
import gzip, os, sys
KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import cube as C, texprog as T
ATT = os.path.join(KP, "out/20261113-102730/cube3")
R = C.rule()
for name, st, spec, n, t0, kind in C.jobs3():
    if kind != "edge": continue
    px = T.pixels(gzip.open(os.path.join(ATT, name + ".txt.gz"), "rt").read())
    fl = C.edge_tokens(R, spec, "H-SEAM-FLOAT"); ad = C.edge_tokens(R, spec, "H-SEAM-ADJ")
    rowsame = all(px[(x, y)] == px[(x, 0)] for x in range(64) for y in range(32))
    print(name, "rows identical:", rowsame)
    for x in range(64):
        t = fl[x]
        if not t.startswith("o:"): continue
        obs = [px[(x, 0)] >> 8 * i & 255 for i in range(4)]
        print("  x %2d kept %s FLOAT %s ADJ %s" % (x, obs, t[2:], ad[x][2:]))
