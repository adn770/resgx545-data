#!/usr/bin/env python3
"""gen_p1140.py: the cases of the p1140 sweep (seed 1140), written to stdout as cases-1140.tsv:
id, set, group, cls, w, h, unit, x0 y0 x1 y1 x2 y2 (integers in 1/2^unit pixel), pair, jobs.

Groups (sets are fit / heldout; a fit set is the only one a rule may be chosen on):
 S1 size       random triangles at 1/256 on targets E606 did not run (small, medium, large, centre, pairs)
 S2 sweep      an edge moved in steps of 1/4096 (1/1024 from 2048 wide) across the half-grid tie
 S3 negative   vertices at negative coordinates with sub-grid fractions, edges aimed at pixel centres, kept only when the
               rounding variants disagree on the image
 S5 tinyedge   a long edge passing a pixel centre at cross product +1 / -1 (1/65536 pixel^2) on 512^2 .. 4096^2
 S4 far        one vertex at +-2^k pixels (the limits), run last
 P  pilot      outside every set, to test the pipeline
"""
import math
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "recompute"))
import model1140 as M  # noqa: E402

SEED = 1140
FIT_SIZES = [(512, 256), (96, 64), (640, 480)]
HELD_SIZES = [(512, 512), (1024, 768), (2048, 1024), (4096, 4096), (200, 120), (1000, 600), (130, 66)]
SWEEP_FIT = [(512, 256), (96, 64), (640, 480)]
SWEEP_HELD = [(1024, 768), (2048, 1024), (4096, 4096), (200, 120)]
NEG_FIT = [(64, 64), (512, 256)]
NEG_HELD = [(96, 64), (640, 480), (1024, 768), (130, 66)]
TINY_FIT = [512, 1024]
TINY_HELD = [2048, 4096]
FAR_FIT = [(64, 64)]
FAR_HELD = [(512, 512)]
rows = []


def add(r, st, grp, cls, w, h, unit, v, pair="-", jobs="C"):
    rows.append([st, grp, cls, w, h, unit] + [c for p in v for c in p] + [pair, jobs])


def small(r, w, h, span_lo, span_hi):
    span = r.uniform(span_lo, span_hi)
    bx, by = r.uniform(2, w - span - 2), r.uniform(2, h - span - 2)
    return [(int((bx + r.uniform(0, span)) * 256), int((by + r.uniform(0, span)) * 256)) for _ in range(3)]


def s1(r, st, w, h):
    for _ in range(12):
        add(r, st, "S1", "small", w, h, 8, small(r, w, h, 1, 4))
    for _ in range(12):
        add(r, st, "S1", "medium", w, h, 8, small(r, w, h, 8, min(40, min(w, h) / 3)))
    for _ in range(12):
        add(r, st, "S1", "large", w, h, 8, [(int(r.uniform(-0.09, 1.24) * w * 256), int(r.uniform(-0.09, 1.24) * h * 256))
                                              for _ in range(3)])
    for _ in range(8):
        add(r, st, "S1", "centre", w, h, 8, [(r.randrange(0, w) * 256 + 128, r.randrange(0, h) * 256 + 128) for _ in range(3)])
    for i in range(8):                                     # a quad cut along a diagonal: the shared edge
        bx, by = r.uniform(4, w - 60), r.uniform(4, h - 60)
        sx, sy = r.uniform(10, 50), r.uniform(10, 50)
        q = [(bx, by), (bx + sx, by + r.uniform(-4, 4)), (bx + sx + r.uniform(-4, 4), by + sy), (bx + r.uniform(-4, 4), by + sy)]
        if i % 2:
            q = [(int(x) * 256 + 128, int(y) * 256 + 128) for x, y in q]
        else:
            q = [(int(x * 256), int(y * 256)) for x, y in q]
        pid = "q%d" % len(rows)
        add(r, st, "S1", "pairA", w, h, 8, [q[0], q[1], q[2]], pid)
        add(r, st, "S1", "pairB", w, h, 8, [q[0], q[2], q[3]], pid)


def s2(r, st, w, h):
    unit = 12 if w < 2048 else 10
    u = 1 << unit
    ts = range(-12, 13) if unit == 12 else range(-5, 6)
    xc, yc = r.randrange(w // 4, w // 2), r.randrange(h // 4, h // 2)
    xo, yo = xc * u + u // 2, yc * u + u // 2
    L = min(20, w // 8, h // 8) * u
    for t in ts:
        add(r, st, "S2", "sweepV+", w, h, unit, [(xo + t, yo - L), (xo + t, yo + L), (xo + t + 2 * L, yo)])
        add(r, st, "S2", "sweepV-", w, h, unit, [(xo + t, yo + L), (xo + t, yo - L), (xo + t - 2 * L, yo)])
        add(r, st, "S2", "sweepH+", w, h, unit, [(xo - L, yo + t), (xo + L, yo + t), (xo, yo + t + 2 * L)])
        add(r, st, "S2", "sweepH-", w, h, unit, [(xo + L, yo + t), (xo - L, yo + t), (xo, yo + t - 2 * L)])


def s3(r, st, w, h, n):
    """negative coordinates with sub-grid fractions at 1/4096 pixel; an edge aimed at a pixel centre; kept when the
    rounding variants (HU HD FL CE TR HA HE) give at least 3 distinct images"""
    u = 4096
    made = tries = 0
    while made < n and tries < 20000:
        tries += 1
        cx, cy = r.randrange(2, w - 2), r.randrange(2, h - 2)
        C = (cx * u + u // 2, cy * u + u // 2)
        kind = r.choice(["x", "y", "xy", "xy"])
        A = []
        for axis in range(2):
            neg = (kind == "xy") or (kind == "x" and axis == 0) or (kind == "y" and axis == 1)
            if neg:
                n256 = r.randrange(1, 400)          # about -1/256 .. -1.6 pixel .. a few hundred pixels
                frac = r.choice([7, 8, 9, 8, 8, r.randrange(0, 16)])
                A.append(-(n256 * 16) + frac - 16 * 0 if r.random() < 0.5 else -(n256 * 16 * r.choice([1, 4, 16])) + frac)
            else:
                A.append(r.randrange(0, w if axis == 0 else h) * u + u // 2 + r.randrange(-3, 4))
        s = r.uniform(1.3, 3.0)
        B = (int(A[0] + s * (C[0] - A[0])), int(A[1] + s * (C[1] - A[1])))
        D = (r.randrange(-1, w + 2) * u + r.randrange(u), r.randrange(-1, h + 2) * u + r.randrange(u))
        V = [tuple(A), B, D]
        if r.random() < 0.5:
            V = [B, tuple(A), D]
        imgs = {}
        for var in M.ROUNDS[:-1]:
            imgs[var] = M.coverage(V, 12, w, h, var)
        distinct = {x.tobytes() for x in imgs.values()}
        hu = imgs["HU"].tobytes()
        if len(distinct) >= 3 and sum(1 for x in imgs.values() if x.tobytes() != hu) >= 2:
            add(r, st, "S3", "neg" + kind, w, h, 12, V)
            made += 1


def tinyedge(r, st, size, count):
    w = h = size
    sx = sy = (size // 2) * 256 + 128
    made = 0
    lo, hi = size * 256 // 8, size * 256 * 3 // 8

    def egcd(a, b):
        if b == 0:
            return (a, 1, 0)
        g, x, y = egcd(b, a % b)
        return (g, y, x - (a // b) * y)

    while made < count:
        dx, dy = r.randrange(lo, hi), r.randrange(lo, hi)
        if r.random() < 0.5:
            dy = -dy
        if math.gcd(abs(dx), abs(dy)) != 1:
            continue
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
        for sgn in (1, -1):
            AA, BB = (A, B) if sgn == 1 else (-A, -B)
            x0, y0 = sx - BB, sy - AA
            v0, v1 = (x0, y0), (x0 + dx, y0 + dy)
            v2 = (x0 + dx // 2 - dy // 2, y0 + dy // 2 + dx // 2)
            if not all(256 <= c < (size - 2) * 256 for c in (v0[0], v0[1], v1[0], v1[1], v2[0], v2[1])):
                cases = []
                break
            cases.append(("tinyedge%+d" % sgn, [v0, v1, v2]))
        for cls, v in cases:
            add(r, st, "S5", cls, w, h, 8, v)
        made += len(cases) // 2


def s4(r, st, w, h):
    """a far vertex at +-2^k pixels (exact in float32), the other two inside the target; directions: +x, -x, +y -y diagonal"""
    for k in range(9, 22):
        for d, (fx, fy) in enumerate([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]):
            a = (r.randrange(w // 8, w - w // 8) * 256 + r.randrange(256), r.randrange(h // 8, h - h // 8) * 256 + r.randrange(256))
            b = (r.randrange(w // 8, w - w // 8) * 256 + r.randrange(256), r.randrange(h // 8, h - h // 8) * 256 + r.randrange(256))
            far = ((fx << k) * 256 + (0 if fx else r.randrange(0, w) * 256), (fy << k) * 256 + (0 if fy else r.randrange(0, h) * 256))
            if abs(far[0]) >= 1 << 30 or abs(far[1]) >= 1 << 30:
                continue
            add(r, st, "S4", "far%d%s" % (k, "pmxy"[0] if False else "d%d" % d), w, h, 8, [a, b, far])


def pilot(r):
    add(r, "pilot", "P", "pilot", 64, 64, 8, [(8 * 256, 8 * 256), (56 * 256, 20 * 256), (20 * 256, 56 * 256)])
    add(r, "pilot", "P", "pilot", 512, 256, 8, small(r, 512, 256, 8, 40))
    add(r, "pilot", "P", "pilot", 96, 64, 8, small(r, 96, 64, 8, 20))
    add(r, "pilot", "P", "pilot", 4096, 4096, 8, small(r, 4096, 4096, 8, 40))
    add(r, "pilot", "P", "pilot", 640, 480, 8, [(-3 * 256 - 100, 10 * 256), (300 * 256 + 17, 100 * 256 + 5), (50 * 256, 400 * 256)])
    add(r, "pilot", "P", "pilot", 128, 128, 12, [(-5000, 20000), (400000, 100003), (10000, 480000)])


def main():
    r = random.Random(SEED)
    pilot(r)
    for w, h in FIT_SIZES:
        s1(r, "fit", w, h)
    for w, h in HELD_SIZES:
        s1(r, "heldout", w, h)
    for w, h in SWEEP_FIT:
        s2(r, "fit", w, h)
    for w, h in SWEEP_HELD:
        s2(r, "heldout", w, h)
    for w, h in NEG_FIT:
        s3(r, "fit", w, h, 40)
    for w, h in NEG_HELD:
        s3(r, "heldout", w, h, 40)
    for sz in TINY_FIT:
        tinyedge(r, "fit", sz, 20)
    for sz in TINY_HELD:
        tinyedge(r, "heldout", sz, 20)
    n_main = len(rows)
    # repeats: 30 fit cases of S1 run a second time (ids point at the originals)
    fit_s1 = [i for i, x in enumerate(rows) if x[0] == "fit" and x[1] == "S1"]
    for i in r.sample(fit_s1, 30):
        rows.append(["repeat"] + rows[i][1:])
    for w, h in FAR_FIT:
        s4(r, "fit", w, h)
    for w, h in FAR_HELD:
        s4(r, "heldout", w, h)
    for i, row in enumerate(rows):
        sys.stdout.write("\t".join([str(1400000 + i)] + [str(c) for c in row]) + "\n")


if __name__ == "__main__":
    main()
