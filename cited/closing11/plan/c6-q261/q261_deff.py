# For chosen candidates: the effective y displacement D_eff of the far vertex (the s at which the exact
# edge through N and F+(0,s) has the candidate's value at the pixel centre) over the tell pixels of each
# pivot row, plus the interval each triangle needs (E1005).  [post hoc] diagnostic, no new candidate.
import sys, os, fractions
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/Users/jtorra/src/resgx545-data/render/closing-r10-geo/gen")
import far as FA, pivot as PV, q261_rule as R
F = fractions.Fraction
want = {"abs-cX/m14/RN", "abs-cX/m13/RN", "abs-cX/m12/RN", "abs-cX/m15/RN", "abs-cF/m13/RN", "tile32/m14/RN",
        "near/m11/RZ", "near/m10/RZ", "slope-near/m14/RN", "slope-near/m15/RN", "abs-cX/m16/RN", "abs-cF/m16/RZ"}
cands = [c for c in R.candidates() if c.id in want]
NEED = {"x23p": "> 586.6", "x24p": "(339.4, 467.4)", "x25n": "> 585.6"}


def exact_e(W, k, px, py):
    p, q = W[k], W[(k + 1) % 3]
    return (q[0] - p[0]) * (py - p[1]) - (q[1] - p[1]) * (px - p[0])


for cand in cands:
    print(cand.id)
    for tri in PV.TRIS:
        line = []
        for d in PV.DLIST:
            vp = PV.moved(PV.verts_px(tri), d)
            V = [(FA.grid(x), FA.grid(y)) for x, y in vp]
            fi = R.far_index(V)
            V1 = list(V); V1[fi] = (V[fi][0], V[fi][1] + 256)   # +1 pixel in y
            W = R.prep(V, R.Cand("exact", "exact"))
            W1 = R.prep(V1, R.Cand("exact", "exact"))
            Wc = R.prep(V, cand)
            vals = []
            for y in range(64):
                for x in range(64):
                    px, py = x * 256 + 128, y * 256 + 128
                    for k in range(3):
                        p, q = W[k], W[(k + 1) % 3]
                        if fi_edge := (V[fi] in (p, q)):
                            e0 = exact_e(W, k, px, py)
                            e1 = exact_e(W1, k, px, py)
                            L = ((q[0]-p[0])**2 + (q[1]-p[1])**2) ** .5
                            if abs(e0) / L < 256 * 0.001 and e1 != e0:
                                ec = R.edge_e(cand, p, q, px, py)
                                # only pixels on the segment N..F side: restrict by the exact rule used in E984 (in-span):
                                n = p if q == V[fi] else q
                                if (px - n[0]) * (V[fi][0] - n[0]) > 0 or (py - n[1]) * (V[fi][1] - n[1]) > 0:
                                    vals.append(float((ec - e0) / (e1 - e0)))
            line.append("%d:%s" % (d, ("%.0f..%.0f" % (min(vals), max(vals))) if vals else "-"))
        print("  far-%s need D %s ; D_eff by d: %s" % (tri[4:], NEED[tri[4:]], " ".join(line[:3] + line[8:])))
