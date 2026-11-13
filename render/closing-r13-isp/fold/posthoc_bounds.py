# SPDX-License-Identifier: MIT
"""fold/posthoc_bounds.py [post hoc, written after the run's scores were read]: the interval of
each guard bound (in 1/16 pixel steps) that draws every kept held-out row of its side, the other
bounds at gen/clip.py's DEFAULT, through the frozen engine (gen/clip.py, gen/q261_rule2.py).
  python3 -B fold/posthoc_bounds.py > fold/posthoc_bounds.out"""
import os
import sys
from fractions import Fraction as F

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import clip as C  # noqa: E402
import kitscore as K  # noqa: E402
import score as SC  # noqa: E402

A = os.path.join(KP, "out/20261113-215416")


def rows():
    for st in ("q261", "far"):
        for r in K.table(KP, st):
            if r["set"] == "control":
                continue
            a = r["args"].split()
            w = int(a[a.index("--width") + 1])
            unit = int(a[a.index("--tri-unit") + 1])
            v = [int(t) for t in a[a.index("--tri-v") + 1].split(",")]
            px = SC.pixels(K.text(os.path.join(A, st), r["name"] + ".txt"), w * w)
            V = C.variants([(v[0], v[1]), (v[2], v[3]), (v[4], v[5])], unit, w)[0]
            vp = [(F(x, 256), F(y, 256)) for x, y in V]
            yield st, r["name"], w, V, C.side_of(vp), [p == SC.GREEN for p in px]


def fits(V, w, b, got):
    return C.image(V, b, w) == got


def scan(V, w, side, got, lo, hi):
    out = []
    for k in range(lo * 16, hi * 16 + 1):
        t = F(k, 16)
        b = list(C.bounds(side, C.DEFAULT[C.FAMILY[side][0]], w))
        if side == "pos-x":
            b[1] = t
        elif side == "neg-x":
            b[0] = -t
        elif side == "neg-y":
            b[2] = -t
        else:
            b[3] = t
        if fits(V, w, tuple(b), got):
            out.append(t)
    return out


def ivals(pts):
    if not pts:
        return "none"
    out, s, p = [], pts[0], pts[0]
    for t in pts[1:]:
        if t - p != F(1, 16):
            out.append((s, p))
            s = t
        p = t
    out.append((s, p))
    return " u ".join("[%s, %s]" % (float(a), float(b)) for a, b in out)


acc = {}
for st, n, w, V, side, got in rows():
    if side in ("pos-x", "pos-y"):
        rng = (w, w + 64)
    else:
        rng = (0, 64)
    pts = scan(V, w, side, got, *rng)
    key = (side, w)
    acc[key] = set(pts) if key not in acc else acc[key] & set(pts)
    print("%s %s %dx%d %s bound (pixels, 1/16 steps): %s" % (st, n, w, w, side, ivals(pts)))
for (side, w), s in sorted(acc.items()):
    print("ALL %s %dx%d: %s" % (side, w, w, ivals(sorted(s))))

# the one rule the integer survivors share [post hoc]: a guard at a quarter of the target past
# each edge (clip x and y within +-1.5 w), every row of both stages, controls and replicate too
n = ok = 0
for st in ("q261", "far"):
    for r in K.table(KP, st):
        a = r["args"].split()
        w = int(a[a.index("--width") + 1])
        unit = int(a[a.index("--tri-unit") + 1])
        v = [int(t) for t in a[a.index("--tri-v") + 1].split(",")]
        px = SC.pixels(K.text(os.path.join(A, st), r["name"] + ".txt"), w * w)
        got = [p == SC.GREEN for p in px]
        b = (-F(w, 4), F(5 * w, 4), -F(w, 4), F(5 * w, 4))
        res = [C.image(V, b, w) == got for V in C.variants([(v[0], v[1]), (v[2], v[3]), (v[4], v[5])], unit, w)]
        n += 1
        ok += all(res)
        print("QUARTER %s %s %dx%d: %s" % (st, r["name"], w, w, "draws the kept image" if all(res) else "MISSES"))
print("QUARTER: %d of %d rows" % (ok, n))
