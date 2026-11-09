#!/usr/bin/env python3
"""gen_p1138.py: the case table of the 11.38 arithmetic sweep (coverage, depth, iteration of random
sub-pixel triangles).  Everything is seeded; `cases.tsv` is the result and its sha256 is frozen with
the predictions (predictions-1138.toml) before any run.  Vertices are integers in 1/256 pixel
(window coordinates, y down), depths are multiples of 1/1024 (exact in float32).

Columns: id, set (fit | heldout), cls, w, h, v0x v0y v1x v1y v2x v2y, z0 z1 z2, pair (id of the
other triangle of a shared-edge pair, or -), jobs (D = tri with depth store, I = the two
iteration probes, C = the plain green probe, repeated as R2 = a second D run).
Sets: fit = every 64 x 64 case of seed batch 1; heldout = every 128 x 128 and 256 x 128 case and the
64 x 64 cases of seed batch 2 (H64); nothing is adjusted on heldout.
"""
import random
import sys

SEED = 1138
PIX = 256


def zs(r):
    return [r.randrange(51, 972) / 1024.0 for _ in range(3)]


def rv(r, w, h, lo=0.0, hi=1.0):
    return (int(r.uniform(lo * w, hi * w) * PIX), int(r.uniform(lo * h, hi * h) * PIX))


def tri_box(r, w, h, span):
    """three vertices inside a span x span pixel box at a random place"""
    bx = r.uniform(2, w - span - 2)
    by = r.uniform(2, h - span - 2)
    return [(int((bx + r.uniform(0, span)) * PIX), int((by + r.uniform(0, span)) * PIX)) for _ in range(3)]


def half(r, w, h, lo=2, hi_margin=2):
    """a vertex at a pixel centre (x + 0.5, y + 0.5)"""
    return (int(r.randrange(lo, w - hi_margin) * PIX + 128), int(r.randrange(lo, h - hi_margin) * PIX + 128))


def build():
    rows = []
    r = random.Random(SEED)

    def add(setn, cls, w, h, v, z, pair="-", jobs="D"):
        rows.append(dict(set=setn, cls=cls, w=w, h=h, v=v, z=z, pair=pair, jobs=jobs))

    def sweeps(setn, w, h, step_p, step_m, step_d):
        # vertical edge x = X0 + f / 256, the third vertex to the right (+) or left (-)
        xb, yb = (w // 2 - 12) * PIX, (h // 2 - 12) * PIX
        for f in range(0, 257, step_p):
            add(setn, "sweepV+", w, h, [(xb + f, yb), (xb + f, yb + 24 * PIX), (xb + f + 20 * PIX, yb + 12 * PIX)], zs(r))
        for f in range(0, 257, step_m):
            add(setn, "sweepV-", w, h, [(xb + f, yb + 24 * PIX), (xb + f, yb), (xb + f - 20 * PIX, yb + 12 * PIX)], zs(r))
        for f in range(0, 257, step_p):   # horizontal edge y = Y0 + f / 256, third vertex below (+) or above (-)
            add(setn, "sweepH+", w, h, [(xb, yb + f), (xb + 24 * PIX, yb + f), (xb + 12 * PIX, yb + f + 20 * PIX)], zs(r))
        for f in range(0, 257, step_m):
            add(setn, "sweepH-", w, h, [(xb + 24 * PIX, yb + f), (xb, yb + f), (xb + 12 * PIX, yb + f - 20 * PIX)], zs(r))
        for f in range(0, 257, step_d):   # a 45 degree edge through (X0 + f/256, Y0), third vertex right / left
            add(setn, "sweepD+", w, h, [(xb + f, yb), (xb + f + 20 * PIX, yb + 20 * PIX), (xb + f + 30 * PIX, yb - 6 * PIX)], zs(r))
            add(setn, "sweepD-", w, h, [(xb + f + 20 * PIX, yb + 20 * PIX), (xb + f, yb), (xb + f - 12 * PIX, yb + 30 * PIX)], zs(r))

    def quad_pairs(setn, w, h, n, half_frac):
        pid = 0
        for k in range(n):
            if k < n * half_frac:     # corners at pixel centres: the shared diagonal can pass through centres
                bx, by = r.randrange(4, w - 30), r.randrange(4, h - 30)
                c = [(bx * PIX + 128, by * PIX + 128), ((bx + r.randrange(6, 24)) * PIX + 128, (by + r.randrange(-2, 3)) * PIX + 128),
                     ((bx + r.randrange(6, 24)) * PIX + 128, (by + r.randrange(6, 24)) * PIX + 128), ((bx + r.randrange(-2, 3)) * PIX + 128, (by + r.randrange(6, 24)) * PIX + 128)]
            else:
                bx, by = r.uniform(4, w - 34), r.uniform(4, h - 34)
                c = [(int((bx + r.uniform(0, 4)) * PIX), int((by + r.uniform(0, 4)) * PIX)),
                     (int((bx + r.uniform(12, 28)) * PIX), int((by + r.uniform(0, 4)) * PIX)),
                     (int((bx + r.uniform(12, 28)) * PIX), int((by + r.uniform(12, 28)) * PIX)),
                     (int((bx + r.uniform(0, 4)) * PIX), int((by + r.uniform(12, 28)) * PIX))]
            z = zs(r)
            t1, t2 = [c[0], c[1], c[2]], [c[0], c[2], c[3]]       # shared edge c0-c2, one winding
            pa = "p%s-%d" % (setn, pid)
            add(setn, "pairA", w, h, t1, z, pair=pa)
            add(setn, "pairB", w, h, t2, [z[0], z[2], zs(r)[0]], pair=pa)
            pid += 1

    def groups(setn, w, h, n_small, n_med, n_large, n_cent, n_pair, n_deg, sw):
        sweeps(setn, w, h, *sw) if sw else None
        for _ in range(n_small):
            add(setn, "small", w, h, tri_box(r, w, h, r.choice([1.0, 2.0, 3.0, 4.0])), zs(r), jobs="DIC" if _ % 4 == 0 else "DI")
        for _ in range(n_med):
            add(setn, "medium", w, h, tri_box(r, w, h, r.uniform(8, 40)), zs(r), jobs="DIC" if _ % 4 == 0 else "DI")
        for _ in range(n_large):
            lo, hi = (-0.1, 1.1) if r.random() < 0.3 else (0.0, 1.0)
            add(setn, "large", w, h, [rv(r, w, h, lo, hi) for _ in range(3)], zs(r), jobs="D")
        for _ in range(n_cent):
            add(setn, "centre", w, h, [half(r, w, h) for _ in range(3)], zs(r), jobs="DIC" if _ % 4 == 0 else "DI")
        quad_pairs(setn, w, h, n_pair, 0.5)
        for k in range(n_deg):
            x0, y0 = r.uniform(4, w - 20), r.uniform(4, h - 20)
            a = (int(x0 * PIX), int(y0 * PIX))
            d = (int(r.uniform(6, 16) * PIX), int(r.uniform(-8, 16) * PIX))
            if k % 3 == 0:     # collinear: the middle vertex exactly on the line
                d2 = (d[0] // 2, d[1] // 2)
                v = [a, (a[0] + d2[0], a[1] + d2[1]), (a[0] + 2 * d2[0], a[1] + 2 * d2[1])]
                cls = "degenerate"
            elif k % 3 == 1:   # a sliver: the third vertex 1 or 2 units (1/256 px) off the line
                b = (a[0] + d[0], a[1] + d[1])
                m = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2 + r.choice([1, 2, -1, -2]))
                v, cls = [a, m, b], "sliver"
            else:              # a needle: a long thin triangle, width below 1/16 px
                b = (a[0] + int(r.uniform(20, 40) * PIX), a[1] + int(r.uniform(-3, 3) * PIX))
                v, cls = [a, (b[0], b[1] + r.choice([6, 12, 15])), b], "needle"
            add(setn, cls, w, h, v, zs(r), jobs="D")

    # batch 1: 64 x 64, the fit set
    groups("fit", 64, 64, 150, 80, 30, 60, 40, 30, (4, 8, 8))
    # heldout: 128 x 128 and 256 x 128, then 64 x 64 with new seeds (batch 2)
    groups("heldout", 128, 128, 100, 60, 30, 60, 40, 30, (8, 16, 16))
    groups("heldout", 256, 128, 0, 0, 20, 20, 10, 10, None)
    groups("heldout", 64, 64, 100, 40, 20, 30, 20, 20, None)
    # repeats: the first 30 fit cases once more (a second run of the same job)
    first = [x for x in rows if x["set"] == "fit" and x["cls"] in ("small", "medium", "centre", "large", "pairA")][::9][:30]
    for x in first:
        rows.append(dict(x, set="repeat", cls=x["cls"] + "-rpt", jobs="D"))
    out = []
    for i, x in enumerate(rows):
        out.append("\t".join([str(i), x["set"], x["cls"], str(x["w"]), str(x["h"])] + [str(c) for p in x["v"] for c in p] +
                             ["%.10f" % z for z in x["z"]] + [x["pair"], x["jobs"]]))
    return out


def main():
    out = build()
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
