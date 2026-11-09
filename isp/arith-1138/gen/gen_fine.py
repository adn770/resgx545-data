#!/usr/bin/env python3
"""gen_fine.py: the follow-up set of the 11.38 sweep ("fine"): vertices finer than 1/256 pixel.  Declared after the main
fit set was analysed (the main fit says: no snapping down to 1/256, centre sample, a top-left tie rule) and before any fine job.
Columns as cases.tsv plus a last column, the unit: v is in 1/2^unit pixel.
FA: unit 12 (1/4096), 64 x 64: edge sweeps of 65 steps of one unit across the tie (V+/-, H+/-, D+/-).
FB: unit 12, 64 x 64: 100 small, 60 medium random triangles and 60 'nearcentre' (half-integer vertices jittered by 0 to 3 units).
FC: unit 16 (1/65536), 256 x 128: V+/-, H+/- sweeps of 33 steps across the tie near the origin and far from it (x or y about 215 / 100).
"""
import random
import sys

SEED = 11380


def zs(r):
    return [r.randrange(51, 972) / 1024.0 for _ in range(3)]


def main():
    r = random.Random(SEED)
    rows = []

    def add(setn, cls, w, h, v, unit):
        rows.append([setn, cls, w, h] + [c for p in v for c in p] + ["%.10f" % z for z in zs(r)] + ["-", "D", unit])

    # FA
    u = 4096
    xb = yb = 20 * u
    for g in range(-32, 33):
        t = 2048 + g
        add("fine", "fsweepV+", 64, 64, [(xb + t, yb), (xb + t, yb + 24 * u), (xb + t + 20 * u, yb + 12 * u)], 12)
        add("fine", "fsweepV-", 64, 64, [(xb + t, yb + 24 * u), (xb + t, yb), (xb + t - 20 * u, yb + 12 * u)], 12)
        add("fine", "fsweepH+", 64, 64, [(xb, yb + t), (xb + 24 * u, yb + t), (xb + 12 * u, yb + t + 20 * u)], 12)
        add("fine", "fsweepH-", 64, 64, [(xb + 24 * u, yb + t), (xb, yb + t), (xb + 12 * u, yb + t - 20 * u)], 12)
        add("fine", "fsweepD+", 64, 64, [(xb + g, yb), (xb + g + 20 * u, yb + 20 * u), (xb + g + 30 * u, yb - 6 * u)], 12)
        add("fine", "fsweepD-", 64, 64, [(xb + g + 20 * u, yb + 20 * u), (xb + g, yb), (xb + g - 12 * u, yb + 30 * u)], 12)
    # FB
    for k in range(160):
        span = r.choice([1.0, 2.0, 3.0, 4.0]) if k < 100 else r.uniform(8, 40)
        bx, by = r.uniform(2, 64 - span - 2), r.uniform(2, 64 - span - 2)
        add("fine", "fsmall" if k < 100 else "fmedium", 64, 64,
            [(int((bx + r.uniform(0, span)) * u), int((by + r.uniform(0, span)) * u)) for _ in range(3)], 12)
    for k in range(60):
        v = [(r.randrange(2, 62) * u + u // 2 + r.randrange(0, 4), r.randrange(2, 62) * u + u // 2 + r.randrange(0, 4)) for _ in range(3)]
        add("fine", "nearcentre", 64, 64, v, 12)
    # FC
    u = 65536
    for place, (xo, yo) in (("near", (8, 8)), ("far", (215, 100))):
        for g in range(-16, 17):
            t = 32768 + g
            add("fine", "csweepV+" + place, 256, 128, [(xo * u + t, 20 * u), (xo * u + t, 44 * u), (xo * u + t + 20 * u, 32 * u)], 16)
            add("fine", "csweepV-" + place, 256, 128, [(xo * u + t, 44 * u), (xo * u + t, 20 * u), (xo * u + t - 8 * u, 32 * u)], 16)
            add("fine", "csweepH+" + place, 256, 128, [(100 * u, yo * u + t), (124 * u, yo * u + t), (112 * u, yo * u + t + 12 * u)], 16)
            add("fine", "csweepH-" + place, 256, 128, [(124 * u, yo * u + t), (100 * u, yo * u + t), (112 * u, yo * u + t - 6 * u)], 16)
    for i, row in enumerate(rows):
        sys.stdout.write("\t".join([str(100000 + i)] + [str(c) for c in row]) + "\n")


if __name__ == "__main__":
    main()
