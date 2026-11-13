# Design of held-out far vertices for a later hardware row [post hoc fit, needs a held-out row].
# Survivors of round 3: clip family, exact interpolation, half-up 1/256, hi guard G = 16..22 (x <= 64+G),
# lo guard in -8..-32 (untested to either side, every lo fits the 12 far-x25n rows).  For random far
# vertices (1/32 pixel grid, |coordinate| <= 2^24, within t4's reach) the predicted 64 x 64 image of each
# survivor is computed; a vertex is useful when the survivors give different images.
# python -I q261_heldout.py > q261_heldout.out
import sys, os, random, fractions, hashlib, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/Users/jtorra/src/resgx545-data/render/closing-r10-geo/gen")
import far as FA
import q261_rule2 as R
import math
F = fractions.Fraction
random.seed(261)


def image(V, cand):
    W = R.prep(V, cand)
    if W is None:
        return None
    # pixels within 0.5 px of any polygon edge line, plus the exact interior test elsewhere: just decide all,
    # cheap enough with python ints for few hundred candidates
    out = []
    for y in range(64):
        for x in range(64):
            out.append(R.decide(cand, W, x * 256 + 128, y * 256 + 128))
    return "".join("1" if v else "0" for v in out)


def cands(side):
    if side == "pos-x":
        return [("G=%d" % g, R.Cand("hi%d" % g, "clip", lo=-16, hi=64 + g, interp="exact-halfup")) for g in range(16, 23)]
    if side == "neg-x":
        return [("lo=-%d" % a, R.Cand("lo%d" % a, "clip", lo=-a, hi=80, interp="exact-halfup")) for a in (8, 12, 16, 20, 24, 32)]
    return [("Gy=%d" % g, R.Cand("y%d" % g, "clip", lo=-g, hi=64 + g, interp="exact-halfup")) for g in (8, 12, 16, 20, 24, 32)]


def grid32(p):
    return F(round(p * 32), 32)


N = {"pos-x": ((F(25, 4), F(37, 4)), (F(19, 2), F(215, 4))),
     "neg-x": ((F(225, 4), F(31, 4)), (F(113, 2), F(223, 4))),
     "far-y": ((F(27, 4), F(233, 4)), (F(229, 4), F(219, 4)))}
N["far-y"] = ((F(27, 4), F(233, 4)), (F(229, 4), F(219, 4)))
res = {}
for side in ("pos-x", "neg-x", "far-y"):
    cs = cands(side)
    ex = R.Cand("exact", "exact")
    pool = []
    for _ in range(400):
        if side == "pos-x":
            X = grid32(random.uniform(2 ** 22, 2 ** 24 - 1)); Y = grid32(random.uniform(-2 ** 22, 2 ** 23))
        elif side == "neg-x":
            X = grid32(random.uniform(-2 ** 25 + 1, -2 ** 22)); Y = grid32(random.uniform(-2 ** 23, 2 ** 23))
        else:
            Y = grid32(random.uniform(-2 ** 25 + 1, -2 ** 22)); X = grid32(random.uniform(-2 ** 23, 2 ** 23))
        vp = list(N[side]) + [(X, Y)]
        V = [(FA.grid(a), FA.grid(b)) for a, b in vp]
        ims = [image(V, c) for _, c in cs]
        e = image(V, ex)
        if any(i is None for i in ims) or e is None:
            continue
        pool.append((X, Y, ims, e))
    chosen, classes = [], [tuple()] * len(cs)
    for _ in range(5):
        def score(p):
            sig = [classes[k] + (p[2][k],) for k in range(len(cs))]
            return len(set(sig))
        p = max(pool, key=score)
        if score(p) == len(set(classes)):
            break
        chosen.append(p)
        classes = [classes[k] + (p[2][k],) for k in range(len(cs))]
    print("side", side, "survivors", [n for n, _ in cs], "-> %d vertices, %d distinct signatures of %d" % (len(chosen), len(set(classes)), len(cs)))
    for X, Y, ims, e in chosen:
        print("  far vertex (%s, %s) px = (%s, %s)" % (X, Y, float(X), float(Y)))
        for (n, _), im in zip(cs, ims):
            dif = [(i % 64, i // 64) for i in range(4096) if im[i] != e[i]]
            print("     %-8s pixels off the exact image: %d %s" % (n, len(dif), dif[:6]))
    res[side] = [(str(X), str(Y)) for X, Y, i, e in chosen]
json.dump(res, open(os.path.join(HERE, "q261_proposals.json"), "w"), indent=1)
