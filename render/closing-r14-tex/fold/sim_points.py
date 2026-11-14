"""Fold helper (after the run): kept pixels of addr5's uv5 rows and srgb4's trilinear rows, one
per region or a sample of pixels, printed as the sgx-sim tests' expectations (tex.rs)."""
import gzip, os, re, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import addr as A, forms5 as F5
F5.install(A.UV5_FORM)
D = os.path.join(KP, "out/20261114-054258")


def px(stage, name):
    t = gzip.open(os.path.join(D, stage, name + ".txt.gz"), "rt").read()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()]
            for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", t, re.M)}
    return [v for y in sorted(rows) for v in rows[y]]


print("// addr5: (w, h, s, t, texels past the base)")
for (w, h) in F5.FORMS:
    k = px("addr5", f"addr5-{w}x{h}-uv5")
    seen = {}
    for p, v in enumerate(k):
        s, t = A.texel(w, h, "uv5", p % 64, p // 64)
        reg = ("L" if s < 0 else "R" if s >= w else "I") + ("A" if t < 0 else "B" if t >= h else "I")
        if reg not in seen:
            seen[reg] = (w, h, s, t, (v & 0x0FFFFFFF) - A.BASE)
    for r in sorted(seen):
        print("(%d, %d, %d, %d, %d)," % seen[r])
print("// srgb4: (row, x, y, kept)")
for n in ("srgb4-t1125", "srgb4-t12", "srgb4-tdark"):
    k = px("srgb4", n)
    for p in (0, 70, 333, 1000, 1500, 2047):
        print('("%s", %d, %d, 0x%08x),' % (n, p % 64, p // 64, k[p]))
print("// srgb4 pixels where TRI-G15 parts from TRI-RNTU or from TRI-G15-NF")
P = os.path.join(KP, "predictions/srgb4")
for n in ("srgb4-t1125", "srgb4-tdark"):
    k = px("srgb4", n)
    g = open(os.path.join(P, n + ".TRI-G15.txt")).read().split()
    for other in ("TRI-RNTU", "TRI-G15-NF"):
        o = open(os.path.join(P, f"{n}.{other}.txt")).read().split()
        ps = [p for p in range(2048) if g[p] != o[p]][:2]
        for p in ps:
            print('("%s", %d, %d, 0x%08x), // parts %s' % (n, p % 64, p // 64, k[p], other))
