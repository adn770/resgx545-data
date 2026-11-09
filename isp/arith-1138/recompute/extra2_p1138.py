#!/usr/bin/env python3
"""extra2_p1138.py DIR: post-hoc analyses (after the freeze and after the fit data were read; flagged as such in the
records): where the depth and iteration errors are, by class, triangle area and gradient."""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1138lib as L  # noqa: E402
from recompute_p1138 import Data, load, log  # noqa: E402


def errors(cases, data, imgs, valfn, decode):
    rows = []
    for c in cases:
        if c.id not in imgs or data.cov(c.id) is None:
            continue
        px = L.Pixels([c], margin=0)
        cov = data.cov(c.id)
        m = cov[px.y, px.x]
        ref = L.plane_at(px, "none", (128, 128), np.array([valfn(c)]))
        obs = decode(imgs[c.id])[px.y, px.x]
        err = np.abs(obs - ref) / 2.0 ** -23
        v = c.v.astype(np.float64) / 256.0
        area = abs((v[1][0] - v[0][0]) * (v[2][1] - v[0][1]) - (v[1][1] - v[0][1]) * (v[2][0] - v[0][0])) / 2
        val = np.array(valfn(c))
        grad = (val.max() - val.min()) / max(np.sqrt(area), 1e-3)
        rows.append((c, int(m.sum()), err[m], area, grad))
    return rows


def report(title, rows):
    log("\n## %s" % title)
    by = collections.defaultdict(list)
    for c, n, e, area, grad in rows:
        by[(c.set, c.cls, c.w)].append((n, e, area, grad))
    for k in sorted(by):
        es = np.concatenate([e for _, e, _, _ in by[k]]) if by[k] else np.zeros(0)
        if es.size:
            log("   %-8s %-10s w=%-3d pixels %6d  >1ulp %.4f  >4ulp %.4f  max %.1f ulp  mean %.3f" % (
                k + (es.size, float(np.mean(es > 1)), float(np.mean(es > 4)), float(es.max()), float(es.mean()))))
    # error against the gradient (value range / sqrt(area)) and area, all classes
    allr = [(a, g, e) for _, _, e, a, g in rows if e.size]
    gs = np.array([g for _, g, _ in allr])
    for lo, hi in ((0, 0.05), (0.05, 0.2), (0.2, 1), (1, 5), (5, 1e9)):
        sel = [e for a, g, e in allr if lo <= g < hi]
        if sel:
            es = np.concatenate(sel)
            log("   gradient (value range per sqrt(area)) %7.2f..%-8.2f triangles %4d pixels %6d >1ulp %.4f max %.1f" % (
                lo, hi, len(sel), es.size, float(np.mean(es > 1)), float(es.max())))


def main():
    cases, jobs = load(sys.argv[1])
    data = Data(sys.argv[1], cases, jobs)
    sets = {"fit", "heldout"}
    cs = [c for c in cases if c.set in sets]
    report("depth error of the covered pixels, plane through the unsnapped vertices at the centre (ulps of 1.0)", errors(
        cs, data, data.dep, lambda c: np.array(c.z), lambda i: L.f32(i).astype(np.float64)))
    report("pa0 (clip z)", errors(cs, data, data.i0, lambda c: 2 * np.array(c.z) - 1, lambda i: L.f32(i).astype(np.float64)))
    report("pa1 (clip x)", errors(cs, data, data.i1, lambda c: c.v[:, 0] / (128.0 * c.w) - 1.0, lambda i: L.f32(i).astype(np.float64)))


if __name__ == "__main__":
    main()
