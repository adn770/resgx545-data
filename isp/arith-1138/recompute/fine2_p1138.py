#!/usr/bin/env python3
"""fine2_p1138.py DIR: analysis of the held-out confirmation set (cases-fine2.tsv, D jobs).  Reads only cases-fine2.tsv and the kept dumps.
Model M*: the vertices rounded half-up to 1/256 pixel, then the exact centre-sample test with the left/top tie rule (R4).
Compared with: half-down, floor, round to 1/512, and (tiny edges) float32 edge functions on the rounded vertices."""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1138lib as L  # noqa: E402
import fine_p1138 as F  # noqa: E402
import fine_extra_p1138 as X  # noqa: E402
from recompute_p1138 import log  # noqa: E402


def load(dirn):
    cases = [F.FCase(l.rstrip("\n").split("\t")) for l in open(os.path.join(dirn, "cases-fine2.tsv")) if l.strip()]
    jobs = {}
    for line in open(os.path.join(dirn, "jobs.tsv")):
        f = line.rstrip("\n").split("\t")
        jobs[(int(f[0]), f[1])] = f[6] == "-" and f[2] == "0"
    return cases, jobs


def covf32(c):
    """float32 edge functions on the vertices rounded half-up to 1/256"""
    c2 = F.FCase(["0", "x", "x", str(c.w), str(c.h)] + [str(x) for x in X.snapped(c, "half-up").ravel()] + ["0", "0", "0", "-", "D", str(c.unit)])
    return F.covered(c2, f32edge=True)


def main():
    d = sys.argv[1]
    cases, jobs = load(d)
    ok = [c for c in cases if jobs.get((c.id, "D"))]
    log("# fine2_p1138 on %s: %d cases, %d jobs ok" % (d, len(cases), len(ok)))
    imgs = {c.id: F.cov_image(d, c) for c in ok}
    main_cls = [c for c in ok if not c.cls.startswith("tinyedge")]
    log("\n## 1 coverage of the held-out set against models (mismatching pixels of the bounding boxes)")
    res = {}
    for name, fn in (("M* (half-up to 1/256)", lambda c: X.cov(c, "half-up", 8)), ("half-down to 1/256", lambda c: X.cov(c, "half-down", 8)),
                     ("floor to 1/256", lambda c: X.cov(c, "floor", 8)), ("half-up to 1/512", lambda c: X.cov(c, "half-up", 9)),
                     ("no rounding", lambda c: X.cov(c, "none", 8))):
        by = collections.defaultdict(lambda: [0, 0, 0])
        for c in main_cls:
            m = int(np.count_nonzero(fn(c) != imgs[c.id]))
            k = c.cls if not c.cls.startswith("gsweep") else "gsweep"
            by[k][0] += 1
            by[k][1] += int(m > 0)
            by[k][2] += m
        tot = sum(v[2] for v in by.values())
        res[name] = tot
        log("   %-22s mismatching pixels %5d  %s" % (name, tot, {k: tuple(v) for k, v in sorted(by.items())}))
    px = sum(c.w * c.h for c in main_cls)
    log("\n## 2 sweeps: observed flip against M*")
    groups = collections.defaultdict(list)
    for c in ok:
        if c.cls.startswith("gsweep"):
            groups[c.cls].append(c)
    agree = tot_s = 0
    for cls in sorted(groups):
        cs = groups[cls]
        obs = [F.sweep_flip(c, imgs[c.id]) for c in cs]
        mod = [F.sweep_flip(c, X.cov(c, "half-up", 8)) for c in cs]
        fl = [i - 1 for i in range(1, len(cs)) if obs[i] != obs[i - 1]]
        mf = [i - 1 for i in range(1, len(cs)) if mod[i] != mod[i - 1]]
        a = sum(1 for x, y in zip(obs, mod) if x == y)
        agree += a
        tot_s += len(cs)
        log("   %-9s cases %d: observed change after case index %s, M* %s, agreement %d of %d" % (cls, len(cs), fl, mf, a, len(cs)))
    log("\n## 3 tiny edges: the sample pixel (128, 128) on an edge at a cross product of +1 or -1 (units of 1/256 pixel squared)")
    tcount = collections.defaultdict(lambda: [0, 0, 0])
    for c in ok:
        if not c.cls.startswith("tinyedge"):
            continue
        want = c.cls.endswith("+1")
        o = bool(imgs[c.id][128, 128])
        mm = bool(X.cov(c, "half-up", 8)[128, 128])
        ff = bool(covf32(c)[128, 128])
        t = tcount[c.cls]
        t[0] += 1
        t[1] += int(o == mm)
        t[2] += int(o == ff)
    for k in sorted(tcount):
        n, e, f = tcount[k]
        log("   %-11s cases %d: observed pixel equals the exact model's %d, the float32 model's %d" % (k, n, e, f))
    te = sum(v[1] for v in tcount.values())
    tn = sum(v[0] for v in tcount.values())
    tf = sum(v[2] for v in tcount.values())
    log("   whole images of the tiny-edge cases equal to the exact model's: %d of %d" % (
        sum(1 for c in ok if c.cls.startswith("tinyedge") and not (X.cov(c, "half-up", 8) != imgs[c.id]).any()), tn))
    log("\n## 4 depth through the rounded vertices at the centre (the sweeps and the 1/65536 near-centre triangles)")
    errs = collections.defaultdict(list)
    for c in ok:
        dp = os.path.join(d, "D", "%d.depth.gz" % c.id)
        if not os.path.exists(dp) or c.cls.startswith("tinyedge"):
            continue
        g = max(1, (c.w + 31) // 32 - 1)
        img = L.depth_image(L.read_gz(dp), c.w, c.h, g)
        ys, xs = np.nonzero(imgs[c.id])
        if not xs.size:
            continue
        v = X.snapped(c, "half-up").astype(np.float64) / (1 << c.unit)
        z = np.array(c.z)
        area = (v[1][0] - v[0][0]) * (v[2][1] - v[0][1]) - (v[1][1] - v[0][1]) * (v[2][0] - v[0][0])
        sx, sy = xs + 0.5, ys + 0.5
        l1 = ((sx - v[0][0]) * (v[2][1] - v[0][1]) - (sy - v[0][1]) * (v[2][0] - v[0][0])) / area
        l2 = ((v[1][0] - v[0][0]) * (sy - v[0][1]) - (v[1][1] - v[0][1]) * (sx - v[0][0])) / area
        ref = z[0] + l1 * (z[1] - z[0]) + l2 * (z[2] - z[0])
        obs = L.f32(img[ys, xs]).astype(np.float64)
        errs["gsweep" if c.cls.startswith("gsweep") else c.cls].append(np.abs(obs - ref) / 2.0 ** -23)
    sw = np.concatenate(errs["gsweep"]) if errs.get("gsweep") else np.full(1, 1e9)
    for k in sorted(errs):
        if not errs[k]:
            continue
        e = np.concatenate(errs[k])
        log("   %-12s pixels %6d  within 1 ulp %.4f  above 4 ulp %.4f  max %.2f ulp" % (k, e.size, float(np.mean(e <= 1)), float(np.mean(e > 4)), float(e.max())))
    log("\n## 5 the frozen criteria of predictions-fine2-1138.toml")
    row = lambda n, c, t: log("%-5s %-5s %s" % (n, "PASS" if c else "FAIL", t))  # noqa: E731
    row("PH1", res["M* (half-up to 1/256)"] <= 0.0005 * px and agree >= 0.995 * tot_s,
        "M* misses %d pixels of %d (<= 0.05%%) and its sweep flips equal the observed in %d of %d" % (res["M* (half-up to 1/256)"], px, agree, tot_s))
    alts = [res[k] for k in ("half-down to 1/256", "floor to 1/256", "half-up to 1/512")]
    row("PH2", min(alts) >= 50, "the alternatives (half-down, floor, 1/512) miss %s pixels (each >= 50)" % alts)
    row("PH3", tn > 0 and te >= 0.95 * tn, "tiny edges: the observed pixel equals the exact integer model's in %d of %d cases (the float32 model's in %d)" % (te, tn, tf))
    row("PH4", float(np.mean(sw <= 1)) >= 0.98 and float(sw.max()) <= 4.0,
        "depth through the rounded vertices on the sweeps: within 1 ulp %.4f, max %.2f ulp" % (float(np.mean(sw <= 1)), float(sw.max())))


if __name__ == "__main__":
    main()
