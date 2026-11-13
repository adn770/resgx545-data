"""Q202 clause 1: E606 coverage vs perspective jobs (g6-rwa, g6-rw, g5-rwa, g5-rw). Rivals: rule.json."""
import gzip, struct, sys, pathlib, re, hashlib
from fractions import Fraction as F
import numpy as np  # float32 only
SC = "/Users/jtorra/src/resgx545-data/render/closing-r6-pixel/score"
sys.dont_write_bytecode = True
sys.path.insert(0, SC)
import rwdesign6 as D6, rwdesign5 as D5
assert hashlib.sha256(open("rule.json", "rb").read()).hexdigest() == open("rule.sha256").read().split()[0]
R6 = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r6-pixel/out/20261112-142113")
R5 = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r5-pixel/out/20261112-091752")
f32 = np.float32
GRID = 256

def snap(fr):  # exact Fraction, round half up
    return (fr * GRID + F(1, 2)).__floor__()

def covers(v, x, y):
    (a, b, c) = v
    area = (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])
    if area == 0: return False
    if area < 0: b, c = c, b
    v = [a, b, c]
    px, py = GRID*x + 128, GRID*y + 128
    for i in range(3):
        A, B = v[i], v[(i+1) % 3]
        dx, dy = B[0]-A[0], B[1]-A[1]
        e = dx*(py-A[1]) - dy*(px-A[0])
        if not (e > 0 or (e == 0 and (dy < 0 or (dy == 0 and dx > 0)))): return False
    return True

def image(v):
    # bounding box limited for speed
    xs = [p[0] for p in v]; ys = [p[1] for p in v]
    x0, x1 = max(0, min(xs)//GRID - 1), min(63, max(xs)//GRID + 1)
    y0, y1 = max(0, min(ys)//GRID - 1), min(63, max(ys)//GRID + 1)
    m = np.zeros((64, 64), bool)
    for y in range(y0, y1+1):
        for x in range(x0, x1+1):
            m[y, x] = covers(v, x, y)
    return m

def verts_exact(p):
    S = p["S"]; ws = p["w"]
    return [(snap(32 + 32*S*D5.VX[i]/ws[i]), snap(32 + 32*S*D5.VY[i]/ws[i])) for i in range(3)]

def fr32(x): return F(float(x))
def verts_f32(p, recip=False):
    S = p["S"]; out = []
    for i in range(3):
        w = f32(float(p["w"][i])); assert fr32(w) == p["w"][i]
        c = []
        for vv in (D5.VX[i], D5.VY[i]):
            xs = f32(float(S*vv)); assert fr32(xs) == S*vv
            q = f32(xs * f32(f32(1)/w)) if recip else f32(xs / w)
            win = f32(f32(f32(32)*q) + f32(32))
            c.append(snap(fr32(win)))
        out.append(tuple(c))
    return out

def packed(path):
    d = gzip.open(path).read()
    dw = struct.unpack("<%dI" % (len(d)//4), d)
    pk = dw[21:29]
    bits = 0
    for i, w in enumerate(pk): bits |= w << (32*i)
    vs = []
    for k in range(3):
        o = 80*k
        Y = bits >> o & 0xffffff; X = bits >> (o+24) & 0xffffff
        vs.append((X - 4096*256, Y - 4096*256))
    return vs, dw

def observed(path, name):
    m = np.zeros((64, 64), bool); n = 0
    for ln in gzip.open(path, "rt"):
        r = re.match(r"probe %s: row (\d+): (.*)" % re.escape(name[1:] if name.startswith("rl-") else name), ln)
        if r:
            px = r[2].split(); assert len(px) == 64, (name, len(px))
            y = int(r[1]); m[y] = [p == "ff00ff00" for p in px]
            assert all(p in ("ff00ff00", "ff203040") for p in px), (name, y)
            n += 1
    assert n == 64, (name, n)
    return m

def margin(v):
    """min distance (pixels) from any pixel centre in the bbox to an edge line, and the exact-vs-f32 window shift bound"""
    best = None
    a0 = v
    for i in range(3):
        A, B = v[i], v[(i+1) % 3]
        dx, dy = B[0]-A[0], B[1]-A[1]
        L = (dx*dx+dy*dy) ** 0.5
        if L == 0: continue
        for y in range(64):
            for x in range(64):
                e = abs(dx*(GRID*y+128-A[1]) - dy*(GRID*x+128-A[0]))
                d = e / L / GRID
                if best is None or d < best: best = d
    return best

def jobs():
    L = []
    for p in D6.controls(): L.append((p, R6/"g6-rwa"))
    for p in D6.g6_rows(): L.append((p, R6/"g6-rw"))
    return L

def main():
    RIV = ["H-EXACT", "H-F32", "H-F32R", "H-STORED"]
    tot = {r: 0 for r in RIV}; exact_jobs = {r: 0 for r in RIV}; rows_ex = {r: 0 for r in RIV}
    disc_total = 0; disc_win = {r: 0 for r in RIV}; njobs = 0; rows_total = 0
    mg = []; sw = {}   # stored-vs-exact snapped vertex deltas
    print("job\tcovered\t" + "\t".join(RIV) + "\tdisc_px\tvert_exact\tvert_stored")
    for p, d in jobs():
        name = p["name"]
        if p["kind"].startswith("control") and p.get("template") == "r5": pass
        f = d/(name+".txt.gz"); pb = d/(name+"."+(name[1:] if name.startswith("rl-") else name)+".param.bin.gz")
        if not f.exists() or not pb.exists():
            print(name, "MISSING"); continue
        obs = observed(f, name)
        stv, dw = packed(pb)
        vs = {"H-EXACT": verts_exact(p), "H-F32": verts_f32(p), "H-F32R": verts_f32(p, True), "H-STORED": stv}
        pred = {r: image(v) for r, v in vs.items()}
        allp = np.stack([pred[r] for r in RIV]); disc = allp.any(0) & ~allp.all(0)
        ndisc = int(disc.sum()); disc_total += ndisc; njobs += 1
        cells = []
        for r in RIV:
            bad = pred[r] != obs; nb = int(bad.sum()); tot[r] += nb; cells.append(nb)
            exact_jobs[r] += nb == 0; rows_ex[r] += int((~bad.any(1)).sum())
            disc_win[r] += int((disc & ~bad).sum())
        rows_total += 64
        mg.append(margin(vs["H-EXACT"]))
        dv = max(max(abs(a-b) for a, b in zip(x, y)) for x, y in zip(vs["H-EXACT"], stv))
        dv2 = max(max(abs(a-b) for a, b in zip(x, y)) for x, y in zip(vs["H-F32"], stv))
        sw[name] = (dv, dv2)
        print(f"{name}\t{int(obs.sum())}\t" + "\t".join(map(str, cells)) + f"\t{ndisc}\t{dv}\t{dv2}")
    print("\nSUMMARY jobs scored:", njobs, "rows:", rows_total)
    for r in RIV:
        print(f"{r}: jobs exact {exact_jobs[r]}/{njobs}, pixels off {tot[r]}, rows exact {rows_ex[r]}/{rows_total}, discriminating pixels it gets right {disc_win[r]}/{disc_total}")
    print("discriminating pixels (rivals disagree), summed over jobs:", disc_total)
    print("min distance of a pixel centre to an edge line over all jobs (pixels): %.6g; jobs with a centre within 1e-4 px: %d" % (min(mg), sum(1 for m in mg if m < 1e-4)))
    mx = max(v[0] for v in sw.values()); mx2 = max(v[1] for v in sw.values())
    print("max |snapped exact - stored| over vertices (1/256 units):", mx, "; max |snapped f32 - stored|:", mx2)
    print("jobs where exact snapped vertices != stored:", sum(1 for v in sw.values() if v[0]), "; f32 != stored:", sum(1 for v in sw.values() if v[1]))

main()
