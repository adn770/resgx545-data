#!/usr/bin/env python3
"""fine_p1138.py DIR: analysis of the follow-up set (cases-fine.tsv, D jobs at vertex units of 1/4096 and 1/65536 pixel).
Reads only cases-fine.tsv and the kept dumps.  Sections: the flip of the first covered pixel of the edge sweeps against the
tie (exact model: V+, H+ own the tie, V-, H- do not, D+ owns it, D- does not); random triangles against the exact model and
against vertices snapped to 1/256 .. 1/2048 pixel and against float32 edge functions; depth of the fine triangles."""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1138lib as L  # noqa: E402
from recompute_p1138 import log  # noqa: E402

f32 = np.float32


class FCase:
    def __init__(self, f):
        self.id, self.set, self.cls = int(f[0]), f[1], f[2]
        self.w, self.h = int(f[3]), int(f[4])
        self.v = np.array([int(x) for x in f[5:11]], dtype=np.int64).reshape(3, 2)
        self.z = [float(x) for x in f[11:14]]
        self.unit = int(f[16])


def load(dirn):
    cases = [FCase(l.rstrip("\n").split("\t")) for l in open(os.path.join(dirn, "cases-fine.tsv")) if l.strip()]
    jobs = {}
    for line in open(os.path.join(dirn, "jobs.tsv")):
        f = line.rstrip("\n").split("\t")
        jobs[(int(f[0]), f[1])] = f[6] == "-" and f[2] == "0"
    return cases, jobs


def cov_image(dirn, c):
    img = L.parse_rows(L.read_gz(os.path.join(dirn, "D", "%d.txt.gz" % c.id)).decode("utf-8", "replace"), c.w, c.h)
    return None if img is None else img != L.BG


def covered(c, bbox_margin=2, snap_bits=None, rule="R4", f32edge=False):
    """exact (or float32) coverage of the pixel centres of c's bounding box, vertices snapped to 1/2^snap_bits pixel first"""
    k = c.unit
    v = c.v.copy()
    if snap_bits is not None and snap_bits < k:
        g = 1 << (k - snap_bits)
        v = ((v + g // 2) // g) * g
    lo = v.min(axis=0) // (1 << k) - bbox_margin
    hi = v.max(axis=0) // (1 << k) + bbox_margin + 1
    x0, y0, x1, y1 = max(int(lo[0]), 0), max(int(lo[1]), 0), min(int(hi[0]), c.w), min(int(hi[1]), c.h)
    ys, xs = np.mgrid[y0:y1, x0:x1]
    half = 1 << (k - 1)
    a, b, cc = v[0], v[1], v[2]
    area = (b[0] - a[0]) * (cc[1] - a[1]) - (b[1] - a[1]) * (cc[0] - a[0])
    out = np.zeros((c.h, c.w), dtype=bool)
    if area == 0:
        return out
    if area < 0:
        b, cc = cc, b
    own = L.RULES[rule]
    if not f32edge:
        sx, sy = xs.astype(np.int64) * (1 << k) + half, ys.astype(np.int64) * (1 << k) + half
        inside = np.ones(xs.shape, dtype=bool)
        for p, q in ((a, b), (b, cc), (cc, a)):
            dx, dy = int(q[0] - p[0]), int(q[1] - p[1])
            e = dx * (sy - int(p[1])) - dy * (sx - int(p[0]))
            inside &= (e > 0) | ((e == 0) & bool(own(np.array(dx), np.array(dy))))
    else:
        scale = 1.0 / (1 << k)
        sx, sy = xs.astype(f32) + f32(0.5), ys.astype(f32) + f32(0.5)
        inside = np.ones(xs.shape, dtype=bool)
        for p, q in ((a, b), (b, cc), (cc, a)):
            px, py = f32(p[0] * scale), f32(p[1] * scale)
            dx, dy = f32(q[0] * scale) - px, f32(q[1] * scale) - py
            e = (dx * (sy - py)).astype(f32) - (dy * (sx - px)).astype(f32)
            inside &= (e > 0) | ((e == 0) & bool(own(np.array(dx), np.array(dy))))
    out[ys, xs] = inside
    return out


def sweep_flip(c, cov):
    """the first (+) or last (-) covered pixel of the middle row (V, D) or column (H) of an edge sweep"""
    k = c.unit
    if "V" in c.cls:
        idx = np.flatnonzero(cov[int(c.v[:, 1].mean() // (1 << k))])
    elif "H" in c.cls:
        idx = np.flatnonzero(cov[:, int(c.v[:, 0].mean() // (1 << k))])
    else:
        idx = np.flatnonzero(cov[int(c.v[:, 1].min() // (1 << k)) + 10])
    if not idx.size:
        return -1
    return int(idx.min() if "+" in c.cls else idx.max())


def main():
    d = sys.argv[1]
    cases, jobs = load(d)
    ok = [c for c in cases if jobs.get((c.id, "D"))]
    log("# fine_p1138 on %s: %d cases, %d jobs ok" % (d, len(cases), len(ok)))
    imgs = {c.id: cov_image(d, c) for c in ok}
    log("\n## 1 sweeps: the change of the first (or last) covered pixel against the exact model")
    groups = collections.defaultdict(list)
    for c in ok:
        if "sweep" in c.cls and imgs[c.id] is not None:
            groups[c.cls].append(c)
    nmatch = ntot = 0
    for cls in sorted(groups):
        cs = groups[cls]
        obs = [sweep_flip(c, imgs[c.id]) for c in cs]
        mod = [sweep_flip(c, covered(c)) for c in cs]
        flips = [i for i in range(1, len(cs)) if obs[i] != obs[i - 1]]
        mflips = [i for i in range(1, len(cs)) if mod[i] != mod[i - 1]]
        agree = sum(1 for a, b in zip(obs, mod) if a == b)
        nmatch += agree
        ntot += len(cs)
        log("   %-14s cases %2d: observed changes after case index %s, exact model %s, per-case agreement %d of %d" % (
            cls, len(cs), [i - 1 for i in flips], [i - 1 for i in mflips], agree, len(cs)))
    log("   sweeps in total: observed flip equals the exact model's in %d of %d cases" % (nmatch, ntot))
    log("\n## 2 random fine triangles: coverage against models (mismatching pixels of the bounding boxes)")
    rnd = [c for c in ok if c.cls in ("fsmall", "fmedium", "nearcentre") and imgs[c.id] is not None]
    res = {}
    models = [("exact", dict()), ("float32 edge", dict(f32edge=True))] + [("snap 1/%d" % (1 << b), dict(snap_bits=b)) for b in (8, 9, 10, 11)]
    for cls in ("fsmall", "fmedium", "nearcentre"):
        cs = [c for c in rnd if c.cls == cls]
        for name, kw in models:
            mm = np_ = ntri = 0
            for c in cs:
                p = covered(c, **kw)
                bad = int(np.count_nonzero(p != imgs[c.id]))
                mm += bad
                ntri += int(bad > 0)
                np_ += c.w * c.h
            res[(cls, name)] = (mm, ntri, len(cs))
            log("   %-10s %-14s mismatching pixels %5d, inexact triangles %3d of %d" % (cls, name, mm, ntri, len(cs)))
    log("\n## 3 depth of the covered pixels of the fine triangles (plane through the unsnapped vertices at the centre)")
    errs = []
    for c in ok:
        dp = os.path.join(d, "D", "%d.depth.gz" % c.id)
        if not os.path.exists(dp) or imgs[c.id] is None or c.cls in ("fsmall",):
            continue
        g = max(1, (c.w + 31) // 32 - 1)
        img = L.depth_image(L.read_gz(dp), c.w, c.h, g)
        ys, xs = np.nonzero(imgs[c.id])
        if not xs.size:
            continue
        s = 1.0 / (1 << c.unit)
        v = c.v.astype(np.float64) * s
        z = np.array(c.z)
        area = (v[1][0] - v[0][0]) * (v[2][1] - v[0][1]) - (v[1][1] - v[0][1]) * (v[2][0] - v[0][0])
        sx, sy = xs + 0.5, ys + 0.5
        l1 = ((sx - v[0][0]) * (v[2][1] - v[0][1]) - (sy - v[0][1]) * (v[2][0] - v[0][0])) / area
        l2 = ((v[1][0] - v[0][0]) * (sy - v[0][1]) - (v[1][1] - v[0][1]) * (sx - v[0][0])) / area
        ref = z[0] + l1 * (z[1] - z[0]) + l2 * (z[2] - z[0])
        obs = L.f32(img[ys, xs]).astype(np.float64)
        errs.append((c.cls, np.abs(obs - ref) / 2.0 ** -23))
    allc = collections.defaultdict(list)
    for cls, e in errs:
        allc[cls].append(e)
    for cls in sorted(allc):
        e = np.concatenate(allc[cls])
        log("   %-12s pixels %6d  within 1 ulp %.4f  max %.2f ulp" % (cls, e.size, float(np.mean(e <= 1)), float(e.max())))
    log("\n## 4 the frozen criteria of predictions-fine-1138.toml")
    row = lambda n, c, t: log("%-5s %-5s %s" % (n, "PASS" if c else "FAIL", t))  # noqa: E731
    row("PF1", ntot > 0 and nmatch >= 0.995 * ntot, "the 65-step edge sweeps at 1/4096 (and the 33-step at 1/65536 near the origin) flip exactly at the tie, as the exact model: %d of %d cases" % (nmatch, ntot))
    m = res.get(("fsmall", "exact"), (0, 0, 1)), res.get(("fmedium", "exact"), (0, 0, 1)), res.get(("nearcentre", "exact"), (0, 0, 1))
    tot = sum(x[0] for x in m)
    row("PF2", tot <= 0.0005 * (100 + 60 + 60) * 4096 and res.get(("nearcentre", "snap 1/256"), (0,))[0] > 50,
        "random fine triangles: the exact model misses %d pixels (<= 0.05%% of the pixels) and the 1/256 snapped one misses %d (> 50)" % (
            tot, res.get(("nearcentre", "snap 1/256"), (0,))[0]))
    far = [c for c in groups if c.endswith("far")]
    fa = sum(1 for c in far for cc in groups[c] if sweep_flip(cc, imgs[cc.id]) == sweep_flip(cc, covered(cc)))
    fn = sum(len(groups[c]) for c in far)
    row("PF3", fn > 0 and fa >= 0.95 * fn, "far from the origin (x or y about 215/100 at 1/65536): the flips equal the exact model's in %d of %d cases" % (fa, fn))


if __name__ == "__main__":
    main()
