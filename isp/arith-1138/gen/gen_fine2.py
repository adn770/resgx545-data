#!/usr/bin/env python3
"""gen_fine2.py: the held-out confirmation of the follow-up (set "fine2"), declared after the fine set (874 cases) was analysed: the
vertices are rounded half-up to 1/256 pixel before an exact centre-sample test (post hoc on the fine set: 0 mismatches over 874
cases against 144 for half-down, 1152 floor, 577 for 1/512).  New seed 11381.  Columns as cases-fine.tsv.
PA: 150 random small / medium / nearcentre at unit 12, 128 x 128.  PB: 60 nearcentre at unit 16, 256 x 128.
PC: 33-step sweeps (V+, V-, H+, H-) across the tie at unit 12 on 128 x 128 near x or y = 100.5.
PD: 'tinyedge': a long edge (50 to 120 pixels) passing within one unit (1/65536 pixel^2 of the cross product) of a pixel centre, on
a 256 x 256 target at unit 8: the exact integer test decides, a float32 edge function would not (80 cases, 40 directions, e = +1 and -1)."""
import math
import random
import sys

SEED = 11381


def zs(r):
    return [r.randrange(51, 972) / 1024.0 for _ in range(3)]


def egcd(a, b):
    if b == 0:
        return (a, 1, 0)
    g, x, y = egcd(b, a % b)
    return (g, y, x - (a // b) * y)


def main():
    r = random.Random(SEED)
    rows = []

    def add(cls, w, h, v, unit):
        rows.append(["fine2", cls, w, h] + [c for p in v for c in p] + ["%.10f" % z for z in zs(r)] + ["-", "D", unit])

    u = 4096
    for k in range(150):
        kind = k % 3
        if kind == 0:
            span = r.choice([1.0, 2.0, 3.0, 4.0])
            bx, by = r.uniform(2, 128 - span - 2), r.uniform(2, 128 - span - 2)
            add("gsmall", 128, 128, [(int((bx + r.uniform(0, span)) * u), int((by + r.uniform(0, span)) * u)) for _ in range(3)], 12)
        elif kind == 1:
            span = r.uniform(8, 40)
            bx, by = r.uniform(2, 128 - span - 2), r.uniform(2, 128 - span - 2)
            add("gmedium", 128, 128, [(int((bx + r.uniform(0, span)) * u), int((by + r.uniform(0, span)) * u)) for _ in range(3)], 12)
        else:
            add("gnearcentre", 128, 128, [(r.randrange(2, 126) * u + u // 2 + r.randrange(0, 9), r.randrange(2, 126) * u + u // 2 + r.randrange(0, 9)) for _ in range(3)], 12)
    u = 65536
    for k in range(60):
        add("hnearcentre", 256, 128, [(r.randrange(2, 254) * u + u // 2 + r.randrange(0, 129), r.randrange(2, 126) * u + u // 2 + r.randrange(0, 129)) for _ in range(3)], 16)
    u = 4096
    xb = yb = 0
    for g in range(-16, 17):
        t = 2048 + g
        xo, yo = 100 * u, 100 * u
        add("gsweepV+", 128, 128, [(xo + t, 40 * u), (xo + t, 60 * u), (xo + t + 20 * u, 50 * u)], 12)
        add("gsweepV-", 128, 128, [(xo + t, 60 * u), (xo + t, 40 * u), (xo + t - 20 * u, 50 * u)], 12)
        add("gsweepH+", 128, 128, [(40 * u, yo + t), (60 * u, yo + t), (50 * u, yo + t + 20 * u)], 12)
        add("gsweepH-", 128, 128, [(60 * u, yo + t), (40 * u, yo + t), (50 * u, yo + t - 20 * u)], 12)
    # tinyedge: unit 8 (1/256), 256 x 256, the sample pixel (128, 128): centre (128.5, 128.5) = 32896 units
    sx = sy = 128 * 256 + 128
    made = 0
    while made < 40:
        dx, dy = r.randrange(12800, 30720), r.randrange(12800, 30720)
        if r.random() < 0.5:
            dy = -dy
        if math.gcd(abs(dx), abs(dy)) != 1:
            continue
        # A = sy - y0, B = sx - x0 with dx * A - dy * B = 1 (extended Euclid), moved along (dy, dx) so that the sample is
        # between the edge's ends
        g, p, q = egcd(abs(dx), abs(dy))
        A = p * (1 if dx > 0 else -1)
        B = -q * (1 if dy > 0 else -1)
        assert dx * A - dy * B == 1
        k0 = round(A / dy - 0.5)
        A -= k0 * dy
        B -= k0 * dx
        assert dx * A - dy * B == 1
        t = (B * dx + A * dy) / (dx * dx + dy * dy)
        if not 0.2 <= t <= 0.8:
            continue
        cases = []
        for s in (1, -1):
            AA, BB = (A, B) if s == 1 else (-A, -B)      # e = +1 (inside by a hair) and e = -1 (outside by a hair)
            x0, y0 = sx - BB, sy - AA
            v0, v1 = (x0, y0), (x0 + dx, y0 + dy)
            v2 = (x0 + dx // 2 - dy // 2, y0 + dy // 2 + dx // 2)    # e(v2) = (dx^2 + dy^2) / 2 > 0: the interior side
            if not all(0 <= c < 255 * 256 for c in (v0[0], v0[1], v1[0], v1[1], v2[0], v2[1])):
                cases = []
                break
            cases.append(("tinyedge%+d" % s, [v0, v1, v2]))
        for cls, v in cases:
            add(cls, 256, 256, v, 8)
        made += len(cases) // 2
    for i, row in enumerate(rows):
        sys.stdout.write("\t".join([str(200000 + i)] + [str(c) for c in row]) + "\n")


if __name__ == "__main__":
    main()
