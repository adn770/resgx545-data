#!/usr/bin/env python3
"""Goal 1e: opus/isp.md A1 on the stored 11.38 depth dumps: is the depth plane evaluated from a
float32 value at the 32 x 16 tile's corner? For every tile with >= 60 covered pixels the stored
float32 words bound T (the plane value at the tile corner) to an interval; the statistic is the
fraction of tiles whose interval centre lies within 0.05 ulp of the float32 grid, at the tile
corner and at control corners. main = the set the idea came from, fine2 = held out. numpy."""
import gzip, sys, math
import numpy as np
sys.dont_write_bytecode = True
from lib import DATA
R = DATA / "isp/arith-1138"
sys.path.insert(0, str(R / "recompute"))
import p1138lib as L


def load(setname):
    f = "cases.tsv" if setname == "main" else "cases-fine2.tsv"
    out = []
    for ln in (R / f).read_text().splitlines():
        t = ln.split("\t")
        if len(t) < 16:
            continue
        unit = int(t[16]) if len(t) > 16 else 8
        out.append(dict(id=int(t[0]), set=t[1], cls=t[2], w=int(t[3]), h=int(t[4]),
                        v=np.array([int(x) for x in t[5:11]], dtype=np.int64).reshape(3, 2),
                        z=[float(x) for x in t[11:14]], unit=unit, jobs=t[15]))
    return out


def snap(v, unit):
    """to 1/256 half-up, then pixels (float64 exact)"""
    if unit > 8:
        g = 1 << (unit - 8)
        v = (v + g // 2) // g
    return v / 256.0


def plane(c):
    P = snap(c["v"], c["unit"])
    (x0, y0), (x1, y1), (x2, y2) = P
    z0, z1, z2 = c["z"]
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if det == 0:
        return None
    A = ((z1 - z0) * (y2 - y0) - (z2 - z0) * (y1 - y0)) / det
    B = ((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / det
    return z0, A, B, x0, y0


def ulp32(a):
    e = np.floor(np.log2(np.abs(a)))
    return 2.0 ** (e - 23)


def run(setname, root, offsets):
    res = {o: [0, 0, 0] for o in offsets}   # tiles used, within 0.05, interval empty
    for c in load(setname):
        d = root / ("D" if setname != "main" else "main/D") / f"{c['id']}.depth.gz"
        t = root / ("D" if setname != "main" else "main/D") / f"{c['id']}.txt.gz"
        if not d.exists() or not t.exists():
            continue
        pl = plane(c)
        if pl is None:
            continue
        w, h = c["w"], c["h"]
        img = L.parse_rows(L.read_gz(str(t)).decode("utf-8", "replace"), w, h)
        if img is None:
            continue
        cov = img != L.BG
        G = max(1, (w + 31) // 32 - 1)
        dep = L.depth_image(L.read_gz(str(d)), w, h, G)
        if dep is None:
            continue
        z = np.asarray(dep, dtype=np.uint32).view(np.float32).astype(np.float64)
        z0, A, B, ox, oy = pl
        ys, xs = np.mgrid[0:h, 0:w]
        for ty in range((h + 15) // 16):
            for tx in range((w + 31) // 32):
                m = cov[ty * 16:ty * 16 + 16, tx * 32:tx * 32 + 32]
                if m.sum() < 60:
                    continue
                zz = z[ty * 16:ty * 16 + 16, tx * 32:tx * 32 + 32][m]
                if not np.all(zz > 0):
                    continue
                X = xs[ty * 16:ty * 16 + 16, tx * 32:tx * 32 + 32][m] + 0.5
                Y = ys[ty * 16:ty * 16 + 16, tx * 32:tx * 32 + 32][m] + 0.5
                for o in offsets:
                    cx, cy = tx * 32 + o[0], ty * 16 + o[1]
                    g = A * (X - cx) + B * (Y - cy)
                    lo = np.max(zz - g)
                    hi = np.min(zz + ulp32(zz) - g)
                    r = res[o]
                    if hi < lo:
                        r[2] += 1
                        continue
                    cen = 0.5 * (lo + hi)
                    u = ulp32(cen) if cen > 0 else None
                    if u is None or (hi - lo) > 0.08 * u:
                        continue
                    r[0] += 1
                    q = cen / u
                    r[1] += abs(q - round(q)) < 0.05
    return res


if __name__ == "__main__":
    offs = [(0, 0), (16, 8), (8, 4), (16, 0), (0, 8), (32, 16)]
    for s in ("main", "fine2"):
        r = run(s, R / s if s != "main" else R, offs)
        print(f"== {s}: corner offset -> tiles with a narrow interval, within 0.05 ulp of the float32 grid, "
              f"(intervals empty)")
        for o, (n, k, e) in r.items():
            print(f"   offset {o}: {n:5d} tiles, {k:5d} on the grid = {100 * k / max(n, 1):5.1f} %  (empty {e})")
