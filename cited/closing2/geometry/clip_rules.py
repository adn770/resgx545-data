#!/usr/bin/env python3
"""Q230 offline: two readings of the clipped objects, checked on every polygon dumped in S1/S1b g-e3.

R1 (prim list): each 5-bit entry field = (bit 4: the edge from this vertex to the next of the triangle lies on the
    polygon's boundary, not an internal diagonal) | (bits 3:0: the stored vertex index).
R2 (vertex order): the stored vertices are the Sutherland-Hodgman polygon p0..p(n-1) (edges A->B, B->C, C->A, the
    end vertex output when inside, the intersection when the edge crosses) in triangle-STRIP zigzag order
    p1, p2, p0, p3, p(n-1), p4, p(n-2), ...; the strip's triangles are (s0,s1,s2), (s2,s1,s3), (s2,s3,s4), ...
Here R1 is checked against the geometry (which edges are internal) for every polygon, and R2 against the z cuts,
where the SH polygon is computable from the program (z = 2x +- 1, w = 1).  The w/guard-band cuts (e3c, e3g, e3w-1e3)
have polygons from several planes; R2 is checked there only as "a convex strip zigzag" (the vertex set's convex hull
order), not against SH's start vertex.
"""
import sys, pathlib, gzip, math
sys.dont_write_bytecode = True
HOME = pathlib.Path.home()
sys.path.insert(0, str(HOME / "src/resgx545/tools/usse-asm"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pbdump  # noqa: E402
from e3_decode import decode, gz  # noqa: E402


def strip_tris(n):
    out = []
    for i in range(n - 2):
        out.append((i, i + 1, i + 2) if i % 2 == 0 else (i + 1, i, i + 2))
    return out


def zigzag(n):
    """strip order of a convex polygon p0..p(n-1): p1, p2, p0, p3, p(n-1), p4, p(n-2) ..."""
    order = [1, 2, 0]
    lo, hi = 3, n - 1
    turn = 0
    while lo <= hi:
        if turn % 2 == 0:
            order.append(lo); lo += 1
        else:
            order.append(hi); hi -= 1
        turn += 1
    return order[:n]


def hull_order(pts):
    """the polygon boundary order of a convex point set (angular about the centroid), as indices."""
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    return sorted(range(len(pts)), key=lambda i: math.atan2(pts[i][1] - cy, pts[i][0] - cx))


def check(name, r):
    vs = [(x, y) for x, y, _, _ in r["vs"]]
    n = len(vs)
    prims = r["prims"]
    # R1: decode entries
    tris = [tuple(e & 0xf for e in p) for p in prims]
    flags = [tuple(e >> 4 for e in p) for p in prims]
    exp_tris = strip_tris(n)
    ok_tris = tris == exp_tris
    # boundary edges: consecutive in the convex hull order
    ho = hull_order(vs)
    bnd = {frozenset((ho[i], ho[(i + 1) % n])) for i in range(n)}
    ok_flags = all(f == tuple(int(frozenset((t[k], t[(k + 1) % 3])) in bnd) for k in range(3)) for t, f in zip(tris, flags))
    # R2: stored order is a zigzag of some rotation/direction of the hull order
    zz = zigzag(n)
    cands = []
    for s in range(n):
        for d in (1, -1):
            poly = [ho[(s + d * k) % n] for k in range(n)]
            cands.append([poly[z] for z in zz])
    ok_zz = list(range(n)) in cands
    print(f"{name:14} n={n} tris {tris} {'OK' if ok_tris else 'NOT strip'} | edge flags {flags} {'OK' if ok_flags else 'MISMATCH'} | zigzag of hull {'OK' if ok_zz else 'NO'}")
    return ok_tris, ok_flags, ok_zz


def sh_clip(poly, inside, cross):
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ia, ib = inside(a), inside(b)
        if ia and ib:
            out.append(b)
        elif ia and not ib:
            out.append(cross(a, b))
        elif not ia and ib:
            out.append(cross(a, b)); out.append(b)
    return out


def main():
    tot = [0, 0, 0, 0]
    for tag, d in (("S1", HOME / "src/resgx545-data/render/closing-s1/out/g-e3"),
                   ("S1b", HOME / "src/resgx545-data/render/closing-s1b/out/g-e3")):
        for n in sorted({p.name.split(".")[0] for p in d.glob("*.txt.gz")}):
            param = next((gz(p) for p in d.glob(f"{n}.*param.bin.gz")), None)
            tadata = next((gz(p) for p in d.glob(f"{n}.*tadata.bin.gz")), None)
            r = decode(param, tadata) if param and tadata else None
            if not r or r.get("unlisted") or r["nv"] < 3:
                continue
            # skip degenerate (repeated vertex) polygons for the hull check
            pts = [(x, y) for x, y, _, _ in r["vs"]]
            if len(set(pts)) < len(pts):
                print(f"{tag}/{n}: repeated vertex, prims {r['prims']} (hull check skipped)")
                continue
            a, b, c = check(f"{tag}/{n}", r)
            tot[0] += 1; tot[1] += a; tot[2] += b; tot[3] += c
    print(f"\nobjects {tot[0]}: strip triangles {tot[1]}, edge flags {tot[2]}, zigzag-of-hull order {tot[3]}")
    # R2 against SH for the z cuts, clip x in [-0.75, 0.75, -0.375] -> window 32 + 32 x
    A, B, C = (-0.75, -0.75), (0.75, -0.375), (-0.375, 0.75)
    win = lambda p: (32 + 32 * p[0], 32 + 32 * p[1])
    for name, inside in (("cut-p (z=2x+1 <= w: x <= 0)", lambda p: p[0] <= 0), ("cut-m (z=2x-1 >= -w: x >= 0)", lambda p: p[0] >= 0)):
        cross = lambda a, b: (0.0, a[1] + (0 - a[0]) / (b[0] - a[0]) * (b[1] - a[1]))
        poly = sh_clip([A, B, C], inside, cross)
        order = zigzag(len(poly))
        print(f"SH polygon {name}: {[win(p) for p in poly]} -> strip order {[win(poly[i]) for i in order]}")


if __name__ == "__main__":
    main()
