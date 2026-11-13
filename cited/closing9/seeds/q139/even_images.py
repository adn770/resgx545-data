#!/usr/bin/env python3
"""Q139 round 9 offline step 2: H-EVEN (a block row of the first macrotile takes 8 floor(fx / 2)
slots, not R7-BLK's 16 floor(fx / 4); fitted on E944's three readable residue dumps by
residue_fit.py) against R7-BLK's slots, both in block order (blkrow, E944), on every kept image of
resgx545-data ta/mtile-fields and ta/mtile-fields-risky (E505, E506, E509) whose whole image was
kept, through E877's loader (its published copy). The jobs E944 replicated with a dump (m1-B2-10,
m1-B2-11, m1-B1-23 at 640 x 480: the fit) are reported apart. Read only.
    python3 -I -B even_images.py [DATA_REPO]"""
import os, re, sys
data = sys.argv[1] if len(sys.argv) > 1 else "/Users/jtorra/src/resgx545-data"
import importlib.util


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


F = load("q139_fit_r7", os.path.join(data, "render/closing-r7-rp/fold/q139_fit.py"))
sys.path.insert(0, os.path.join(data, "cited/closing6/fold-misc/q139"))
M = load("q139_model", os.path.join(data, "cited/closing6/fold-misc/q139/q139_model.py"))
FIT = {"q100-256x256-m1-B2-10", "q100-256x256-m1-B2-11", "q100-640x480-m1-B1-23"}


def predict(w, h, args, rowslots):
    tx, ty = F.cdiv(w, 32), F.cdiv(h, 16)
    m1, m2, s = F.words(w, h, args)
    n, bx, by = F.bounds(m1, m2)
    fx = bx[1]
    ws = []
    for r in range(max(ty, by[-1] + by[1])):
        for c in range(max(tx, bx[-1] + fx)):
            mcol, lx = F.place(c, bx)
            mrow, ly = F.place(r, by)
            sl = (mcol * n + mrow) * s + (ly >> 2) * rowslots(fx) + (lx >> 2) * 16 + (r & 3) * 4 + (c & 3)
            ws.append(((r >> 2, c >> 2, r, c), sl, (c, r)))
    ws.sort(key=lambda t: t[0])
    own = {}
    for _, sl, t in ws:
        own[sl] = t
    drawn = {t for t in own.values() if t[0] < tx and t[1] < ty}
    return sorted("%d.%d" % (c, r) for r in range(ty) for c in range(tx) if (c, r) not in drawn), (n, bx, by, s)


MODELS = {"R7-BLK": lambda f: 16 * (f >> 2), "H-EVEN": lambda f: 8 * (f >> 1), "H-4FX": lambda f: 4 * f}
tot = {k: [0, 0, 0, 0] for k in MODELS}   # all ok, all n, parting ok, parting n
for ds in ("ta/mtile-fields", "ta/mtile-fields-risky"):
    for line in list(open(os.path.join(data, ds, "cases.tsv")))[1:]:
        p = line.rstrip("\n").split("\t")
        name, w, h = p[0], int(p[2]), int(p[3])
        args = p[4] if len(p) > 4 else ""
        if any(i not in ("143", "144", "146") for i in re.findall(r"ta:(\d+)=", args)):
            continue
        try:
            m1, m2, s = F.words(w, h, args)
            n, bx, by = F.bounds(m1, m2)
        except Exception:
            continue
        if bx[1] <= 0 or by[1] <= 0 or max(bx[-1] + bx[1], by[-1] + by[1]) > 1024:
            continue
        W, H, job, bad = M.load(os.path.join(data, ds, "dumps", name + ".txt.gz"))
        if bad is None:
            continue
        obs = sorted("%d.%d" % t for t in bad)
        pr = {k: predict(w, h, args, f) for k, f in MODELS.items()}
        part = len({tuple(v[0]) for v in pr.values()}) > 1
        fit = name in FIT
        for k in MODELS:
            if fit:
                continue
            ok = pr[k][0] == obs
            tot[k][0] += ok; tot[k][1] += 1
            if part:
                tot[k][2] += ok; tot[k][3] += 1
        if part or fit or not all(pr[k][0] == obs for k in MODELS):
            g = pr["H-EVEN"][1]
            print("%-6s %-44s obs %3d  %s  fx=%d bx=%s by=%s s=%d%s" % (ds.split("/")[1][-5:], name, len(obs), " ".join(
                "%s:%s(%d)" % (k, "ok" if pr[k][0] == obs else "NO", len(pr[k][0])) for k in MODELS), g[1][1], g[1], g[2], g[3],
                "  [FIT]" if fit else "  [parts]" if part else ""))
print()
for k, v in tot.items():
    print("%-7s outside the fit: %d of %d whole images; where the models part: %d of %d" % (k, *v))
