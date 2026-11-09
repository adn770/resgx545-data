#!/usr/bin/env python3
"""recompute_p1138.py DIR: the analysis of the 11.38 arithmetic sweep, from cases.tsv and the kept raw dumps
only (run/run_p1138.py is not imported).  Python with numpy (e.g. ~/src/nhc/.venv/bin/python).

DIR holds cases.tsv, jobs.tsv, D/ID.txt.gz + ID.depth.gz, I0/, I1/, C/ (see run_p1138.py).
Sections: 0 accounting, 1 coverage (the whole grid of snap x sample point x tie rule fitted on the fit
set only, the winner and the frozen primary hypothesis on the held-out set), 2 shared-edge pairs,
3 depth, 4 iteration, 5 repeats and pixel-program independence, 6 the frozen criteria.
The thresholds of section 6 are the ones of predictions-1138.toml (frozen by hash with this file)."""
import argparse
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1138lib as L  # noqa: E402

PRIMARY = ("r16", (128, 128), "R1")     # the frozen primary coverage hypothesis (predictions-1138.toml P1)
PRIMARY_RULES = [("R%d" % k) for k in range(1, 9)]
SNAPS_PLANE = ["none", "r16", "f16", "r8", "r32"]
ULP1 = 2.0 ** -23


def log(*a):
    print(*a, flush=True)


def load(dirn):
    cases = L.load_cases(os.path.join(dirn, "cases.tsv"))
    jobs = {}
    jp = os.path.join(dirn, "jobs.tsv")
    if os.path.exists(jp):
        for line in open(jp):
            f = line.rstrip("\n").split("\t")
            jobs[(int(f[0]), f[1])] = dict(rc=int(f[2]), flags=f[6])      # the last record of a job wins
    return cases, jobs


def job_ok(jobs, i, kind):
    j = jobs.get((i, kind))
    return j is not None and j["flags"] == "-" and j["rc"] == 0


class Data:
    """per case: colour image of the D job, depth image, I0/I1 images, C image (None when missing)"""

    def __init__(self, dirn, cases, jobs):
        self.col, self.dep, self.i0, self.i1, self.cimg = {}, {}, {}, {}, {}
        for c in cases:
            if "D" in c.jobs and job_ok(jobs, c.id, "D"):
                p = os.path.join(dirn, "D", "%d.txt.gz" % c.id)
                img = L.parse_rows(L.read_gz(p).decode("utf-8", "replace"), c.w, c.h)
                self.col[c.id] = img
                dp = os.path.join(dirn, "D", "%d.depth.gz" % c.id)
                if os.path.exists(dp):
                    self.dep[c.id] = L.depth_image(L.read_gz(dp), c.w, c.h, max(1, (c.w + 31) // 32 - 1))
            if "I" in c.jobs:
                for k, store in (("I0", self.i0), ("I1", self.i1)):
                    if job_ok(jobs, c.id, k):
                        store[c.id] = L.parse_rows(L.read_gz(os.path.join(dirn, k, "%d.txt.gz" % c.id)).decode("utf-8", "replace"), c.w, c.h)
            if "C" in c.jobs and job_ok(jobs, c.id, "C"):
                self.cimg[c.id] = L.parse_rows(L.read_gz(os.path.join(dirn, "C", "%d.txt.gz" % c.id)).decode("utf-8", "replace"), c.w, c.h)

    def cov(self, i):
        img = self.col.get(i)
        return None if img is None else img != L.BG


def pct(a, b):
    return "%d of %d (%.4f%%)" % (a, b, 100.0 * a / b if b else 0.0)


def coverage_section(cases, data, out):
    log("\n## 1 coverage")
    fit = [c for c in cases if c.set == "fit" and data.cov(c.id) is not None]
    held = [c for c in cases if c.set == "heldout" and data.cov(c.id) is not None]
    log("fit cases %d, heldout cases %d" % (len(fit), len(held)))
    px = L.Pixels(fit)
    obs, ok = L.observed(px, [data.cov(c.id) for c in fit])
    res = L.fit_coverage(px, obs, ok)
    best = min(res.values())
    plateau = sorted([k for k, v in res.items() if v == best], key=lambda k: (list(L.SNAPS).index(k[0]), k[1], k[2]))
    log("fit pixels %d (bounding boxes + 2), covered %d; hypotheses %d" % (px.tri.size, int(obs.sum()), len(res)))
    log("best mismatch on fit: %d pixels; %d hypotheses at that count" % (best, len(plateau)))
    for k in plateau[:12]:
        log("   best  %-5s S=(%3d,%3d) %s" % (k[0], k[1][0], k[1][1], k[2]))
    top = sorted(res.items(), key=lambda kv: kv[1])
    log("next best distinct counts:", sorted(set(v for _, v in top))[:8])
    for k, name in ((("none", (128, 128), "R1"), "no snap, centre"), (PRIMARY, "PRIMARY r16 centre R1"),
                    (("r16", (96, 32), "R1"), "r16 at (0.375, 0.125)"), (("r16", (128, 128), "ALL"), "r16 centre ALL"),
                    (("r16", (128, 128), "NONE"), "r16 centre NONE")):
        log("   %-24s fit mismatch %s" % (name, pct(res[k], int(ok.sum()))))
    out["fit_best"] = best
    out["fit_plateau"] = plateau
    out["fit_primary"] = res[PRIMARY]
    out["fit_pixels"] = int(ok.sum())
    out["fit_none_centre"] = res[("none", (128, 128), "R1")]
    # the winner by a frozen preference: plateau order (snap order none, r32, r16, f16, r8, r4; S, rule)
    win = plateau[0]
    pref = sorted(plateau, key=lambda k: (abs(k[1][0] - 128) + abs(k[1][1] - 128), list(L.SNAPS).index(k[0]) != 2, k[2]))[0]
    log("fitted winner (nearest the centre, r16 first): %s S=%s %s" % (pref[0], pref[1], pref[2]))
    out["winner"] = pref
    # held out
    if not held:
        return
    pxh = L.Pixels(held)
    obsh, okh = L.observed(pxh, [data.cov(c.id) for c in held])
    for name, hyp in (("winner", pref), ("PRIMARY", PRIMARY)):
        pred = L.covered(pxh, *hyp)
        mm = (pred != obsh) & okh
        log("held out, %s: %s mismatching pixels (bounding boxes); triangles exact: %d of %d" % (
            name, pct(int(mm.sum()), int(okh.sum())), sum(1 for i in range(len(held)) if not mm[pxh.tri == i].any()), len(held)))
        by = collections.defaultdict(lambda: [0, 0, 0, 0])
        for i, c in enumerate(held):
            m = mm[pxh.tri == i]
            key = (c.cls, "%dx%d" % (c.w, c.h))
            by[key][0] += 1
            by[key][1] += int(m.any())
            by[key][2] += int(m.sum())
            by[key][3] += int(np.count_nonzero(pxh.tri == i))
        for key in sorted(by):
            n, bad, mp, npx = by[key]
            log("   %-10s %-8s triangles %3d inexact %3d mismatching pixels %5d of %d" % (key[0], key[1], n, bad, mp, npx))
        out["held_" + name] = int(mm.sum())
        out["held_px"] = int(okh.sum())
        out["held_inexact_" + name] = sum(1 for i in range(len(held)) if mm[pxh.tri == i].any())
        out["held_n"] = len(held)
        # the f32 evaluation of the same hypothesis
        pf = L.covered_f32(pxh, *hyp)
        log("   float32 edge functions, %s: %d mismatching pixels (vs %d exact), %d pixels differ from the exact model" % (
            name, int(((pf != obsh) & okh).sum()), int(mm.sum()), int((pf != pred).sum())))
    # refit informational: the held-out set alone (a refit, not a test)
    resh = L.fit_coverage(pxh, obsh, okh, snaps=["none", "r16", "f16", "r32", "r8"])
    bh = min(resh.values())
    log("informational refit on held-out: best %d mismatching pixels, at %s" % (bh, [k for k, v in resh.items() if v == bh][:4]))
    out["held_refit_best"] = bh


def degenerate_section(cases, data, out):
    log("\n## 1b degenerate and thin triangles (observed)")
    tot = collections.defaultdict(lambda: [0, 0, 0])
    for c in cases:
        cov = data.cov(c.id)
        if cov is None or c.cls not in ("degenerate", "sliver", "needle"):
            continue
        t = tot[(c.set, c.cls, "%dx%d" % (c.w, c.h))]
        t[0] += 1
        t[1] += int(cov.sum())
        t[2] += int(cov.any())
    for k in sorted(tot):
        log("   %-8s %-10s %-8s triangles %3d, pixels drawn %5d, triangles drawing any %3d" % (k + tuple(tot[k])))
    out["degenerate_pixels"] = sum(v[1] for k, v in tot.items() if k[1] == "degenerate")
    out["degenerate_n"] = sum(v[0] for k, v in tot.items() if k[1] == "degenerate")


def pair_section(cases, data, out):
    """A pair is the triangles (c0, c1, c2) and (c0, c2, c3): the shared edge is the diagonal c0-c2.  Near the
    diagonal (centre within one pixel of the line, 10% to 90% along it) every centre must be drawn by exactly
    one of the two; a centre exactly on the line is a tie."""
    log("\n## 2 shared-edge pairs (observed coverage only)")
    pairs = collections.defaultdict(list)
    for c in cases:
        if c.cls in ("pairA", "pairB"):
            pairs[(c.set, c.pair)].append(c)
    n = dbl = gaps = ties1 = ties0 = ties2 = near_total = 0
    per_set = collections.defaultdict(lambda: [0, 0, 0, 0])
    for (sn, pid), cs in sorted(pairs.items()):
        if len(cs) != 2 or any(data.cov(c.id) is None for c in cs):
            continue
        a, b = sorted(cs, key=lambda c: c.cls)               # pairA, pairB
        ca, cb = data.cov(a.id), data.cov(b.id)
        c0, c2 = a.v[0].astype(np.int64), a.v[2].astype(np.int64)
        ys, xs = np.mgrid[0:a.h, 0:a.w]
        px, py = xs * 256 + 128, ys * 256 + 128
        dx, dy = int(c2[0] - c0[0]), int(c2[1] - c0[1])
        cross = dx * (py - c0[1]) - dy * (px - c0[0])                  # exact, integers
        dot = dx * (px - c0[0]) + dy * (py - c0[1])
        len2 = dx * dx + dy * dy
        near = (cross.astype(np.float64) ** 2 <= 256.0 * 256.0 * len2) & (dot * 10 >= len2) & (dot * 10 <= 9 * len2)
        tie = near & (cross == 0)
        n += 1
        near_total += int(near.sum())
        both = ca & cb
        neither = ~ca & ~cb
        g = int(np.count_nonzero(near & neither & ~tie))
        dbl += int(both.sum())
        gaps += g
        t1 = int(np.count_nonzero(tie & (ca ^ cb)))
        t0 = int(np.count_nonzero(tie & neither))
        t2 = int(np.count_nonzero(tie & both))
        ties1 += t1
        ties0 += t0
        ties2 += t2
        row = per_set[sn]
        row[0] += 1
        row[1] += int(g > 0)
        row[2] += int(both.any())
        row[3] += int(t0 + t2 > 0)
    log("pairs %d (%d near-diagonal centres): drawn by both %d, off-diagonal gaps %d; centres exactly on the shared "
        "edge: drawn by one %d, by none %d, by both %d" % (n, near_total, dbl, gaps, ties1, ties0, ties2))
    for sn, (np_, g, d_, t) in sorted(per_set.items()):
        log("   %-8s pairs %3d with a gap %3d with a double hit %3d with a tie drawn 0 or 2 times %3d" % (sn, np_, g, d_, t))
    out.update(pairs=n, pair_double=dbl, pair_gaps=gaps + ties0, pair_tie1=ties1, pair_tie0=ties0, pair_tie2=ties2)


def plane_fit(px, obs_vals, vals, snaps, step=16, mask=None):
    """for every (snap, S) the errors of the plane against observed values over the pixels of px (mask: used
    pixels); returns {hyp: (fraction within 1 ulp, max abs error in ulps of 1.0, mean abs error)}"""
    res = {}
    for sn in snaps:
        for S in L.grid_samples(step):
            ref = L.plane_at(px, sn, S, vals)
            err = np.abs(obs_vals - ref)[mask] / ULP1
            err = err[np.isfinite(err)]
            res[(sn, S)] = (float(np.mean(err <= 1.0)) if err.size else 0.0, float(err.max()) if err.size else 0.0,
                            float(err.mean()) if err.size else 0.0)
    return res


def pick(res):
    return sorted(res.items(), key=lambda kv: (-kv[1][0], kv[1][2]))[:6]


def plane_section(title, cases, data, imgs, valfn, decode, out, key, snaps=SNAPS_PLANE):
    log("\n## %s" % title)
    for setn in ("fit", "heldout"):
        cs = [c for c in cases if c.set == setn and c.id in imgs and data.cov(c.id) is not None]
        if not cs:
            continue
        px = L.Pixels(cs, margin=0)
        vals = np.array([valfn(c) for c in cs])
        # the pixels the colour image says are covered
        obs_cov, ok = L.observed(px, [data.cov(c.id) for c in cs])
        vv = np.zeros(px.tri.size)
        for i, c in enumerate(cs):
            s = px.tri == i
            vv[s] = decode(imgs[c.id])[px.y[s], px.x[s]]
        res = plane_fit(px, vv, vals, snaps, mask=obs_cov & ok)
        log("%s cases %d, covered pixels %d" % (setn, len(cs), int((obs_cov & ok).sum())))
        for k, v in pick(res):
            log("   %-5s S=(%3d,%3d)  within 1 ulp %.4f  max %.2f ulp  mean %.3f ulp" % (k[0], k[1][0], k[1][1], v[0], v[1], v[2]))
        if setn == "fit":
            best = pick(res)[0]
            out[key + "_fit"] = best
        else:
            out[key + "_heldout_at_fit"] = res.get(out[key + "_fit"][0])
            log("   held out at the fitted hypothesis %s: within 1 ulp %.4f  max %.2f ulp  mean %.3f ulp" % ((out[key + "_fit"][0],) + out[key + "_heldout_at_fit"]))
            out[key + "_heldout_best"] = pick(res)[0]
            log("   (a refit on held-out, informational: %s)" % (pick(res)[0],))


def depth_section(cases, data, out):
    def valfn(c):
        return np.array(c.z, dtype=np.float64)

    def decode(img):
        return L.f32(img).astype(np.float64)
    plane_section("3 depth: the stored depth of the covered pixels against the plane through the vertices", cases, data,
                  data.dep, valfn, decode, out, "depth")
    both = mism = 0
    for c in cases:
        if c.id in data.dep and data.cov(c.id) is not None:
            d = L.f32(data.dep[c.id])
            dc = (data.dep[c.id] != L.FILL) & (d < 1.0)
            both += c.w * c.h
            mism += int(np.count_nonzero(dc != data.cov(c.id)))
    log("coverage by the depth buffer (stored < 1.0) against the colour image: %d mismatching pixels of %d" % (mism, both))
    out["depth_vs_colour"] = mism


def iteration_section(cases, data, out):
    def zvals(c):
        return 2 * np.array(c.z, dtype=np.float64) - 1.0

    def xvals(c):
        return c.v[:, 0].astype(np.float64) / (128.0 * c.w) - 1.0

    def decode(img):
        return L.f32(img).astype(np.float64)
    plane_section("4a iteration: pa0 (clip z) against the plane through the vertices", cases, data, data.i0, zvals, decode, out, "it0")
    plane_section("4b iteration: pa1 (clip x) against the plane through the vertices", cases, data, data.i1, xvals, decode, out, "it1")


def other_section(cases, data, jobs, out):
    log("\n## 5 repeats and pixel-program independence")
    byv = {}
    for c in cases:
        if c.set != "repeat":
            byv.setdefault((c.w, c.h, tuple(c.v.ravel()), tuple(c.z)), c)
    same = tot = 0
    for c in cases:
        if c.set != "repeat" or c.id not in data.col:
            continue
        o = byv.get((c.w, c.h, tuple(c.v.ravel()), tuple(c.z)))
        if o is None or o.id not in data.col:
            continue
        tot += 1
        eq = (data.col[c.id] == data.col[o.id]).all() and (c.id not in data.dep or o.id not in data.dep or
                                                            (data.dep[c.id] == data.dep[o.id]).all())
        same += int(eq)
    log("repeat runs identical to their first run (colour and depth): %d of %d" % (same, tot))
    out["repeat"] = (same, tot)
    cd = ct = 0
    pd_ = pt = 0
    for c in cases:
        a = data.cov(c.id)
        if a is None:
            continue
        if c.id in data.cimg:
            ct += 1
            cd += int(((data.cimg[c.id] != L.BG) == a).all())
        for img in (data.i0.get(c.id), data.i1.get(c.id)):
            if img is not None:
                pt += 1
                pd_ += int(((img != L.BG) == a).all())
    log("coverage of the plain green probe equals the depth job's colour image: %d of %d cases" % (cd, ct))
    log("coverage of the two iteration probes equals it: %d of %d images" % (pd_, pt))
    out["indep_green"] = (cd, ct)
    out["indep_iter"] = (pd_, pt)
    nj = collections.Counter()
    for (i, k), j in jobs.items():
        nj[(k, "ok" if j["flags"] == "-" else "flagged")] += 1
    log("jobs:", dict(nj))
    out["jobs"] = dict(nj)


def criteria(out):
    log("\n## 6 the frozen criteria (predictions-1138.toml)")
    res = []

    def row(name, cond, text):
        res.append(cond)
        log("%-6s %-5s %s" % (name, "PASS" if cond else "FAIL", text))
    if "fit_best" in out:
        row("P1", out["fit_primary"] <= 0.0005 * out["fit_pixels"] and out["fit_best"] <= out["fit_primary"],
            "the primary hypothesis (r16, centre, R1) misses at most 0.05%% of the fit pixels: %d of %d (best of the grid %d)" % (
                out["fit_primary"], out["fit_pixels"], out["fit_best"]))
        row("P2", out["fit_none_centre"] >= 50, "without snapping the fit set misses at least 50 pixels: %d" % out["fit_none_centre"])
        if "held_PRIMARY" in out:
            row("P3", out["held_PRIMARY"] <= 0.001 * out["held_px"],
                "the primary hypothesis misses at most 0.1%% of the held-out pixels: %d of %d" % (out["held_PRIMARY"], out["held_px"]))
            row("P3b", out["held_inexact_PRIMARY"] <= 0.02 * out["held_n"],
                "and at most 2%% of the held-out triangles are inexact: %d of %d" % (out["held_inexact_PRIMARY"], out["held_n"]))
    if "degenerate_n" in out and out["degenerate_n"]:
        row("P10", out["degenerate_pixels"] == 0, "collinear (zero-area) triangles draw nothing: %d pixels from %d triangles" % (
            out["degenerate_pixels"], out["degenerate_n"]))
    if "pairs" in out:
        row("P5", out["pair_gaps"] == 0 and out["pair_double"] == 0,
            "shared-edge pairs: no gap and no pixel drawn twice (gaps %d, doubles %d of %d pairs)" % (out["pair_gaps"], out["pair_double"], out["pairs"]))
    if "depth_fit" in out:
        d = out["depth_fit"]
        row("P6", d[1][0] >= 0.99 and d[1][1] <= 4.0, "depth: the fitted plane is within 1 ulp at 99%% of the pixels, max 4 ulp: %.4f, %.2f" % (d[1][0], d[1][1]))
        if out.get("depth_heldout_at_fit"):
            h = out["depth_heldout_at_fit"]
            row("P6b", h[0] >= 0.99 and h[1] <= 4.0, "and the same hypothesis on held-out: %.4f, %.2f" % (h[0], h[1]))
    if "it0_fit" in out:
        k = out["it0_fit"]
        row("P7", k[0][1] == (96, 32) and k[1][0] >= 0.99, "iteration: the best sample point of pa0 is (0.375, 0.125) as E502: %s %.4f" % (k[0], k[1][0]))
    if "it0_fit" in out:
        k = out["it0_fit"]
        row("P7c", k[0] == ("none", (128, 128)) and k[1][0] >= 0.99,
            "(declared after the 3-case pilot) iteration at the pixel centre through the unsnapped vertices: best %s %.4f" % (k[0], k[1][0]))
    if "depth_fit" in out:
        k = out["depth_fit"]
        row("P7d", k[0] == ("none", (128, 128)) and k[1][0] >= 0.99,
            "(declared after the pilot) depth likewise at the centre through the unsnapped vertices: best %s %.4f" % (k[0], k[1][0]))
    if "it1_fit" in out:
        k = out["it1_fit"]
        row("P7b", k[0][1][0] == 96 and k[1][0] >= 0.99, "and the x of pa1 is the pixel's x + 0.375: best %s %.4f" % (k[0], k[1][0]))
    if "jobs" in out:
        okj = sum(v for (kd, st), v in out["jobs"].items() if st == "ok")
        allj = sum(out["jobs"].values())
        row("P11", okj >= 0.99 * allj and allj > 0, "at least 99%% of the jobs complete unflagged: %d of %d" % (okj, allj))
    if "repeat" in out:
        row("P8", out["repeat"][0] == out["repeat"][1], "repeats identical: %d of %d" % out["repeat"])
    if "indep_green" in out:
        row("P9", out["indep_green"][0] == out["indep_green"][1] and out["indep_iter"][0] == out["indep_iter"][1],
            "coverage independent of the pixel program: green %d of %d, iteration %d of %d" % (out["indep_green"] + out["indep_iter"]))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    cases, jobs = load(a.dir)
    data = Data(a.dir, cases, jobs)
    out = {}
    log("# recompute_p1138 on %s: %d cases" % (a.dir, len(cases)))
    only = a.only.split(",") if a.only else ["cov", "pair", "depth", "iter", "other"]
    if "cov" in only:
        coverage_section(cases, data, out)
        degenerate_section(cases, data, out)
    if "pair" in only:
        pair_section(cases, data, out)
    if "depth" in only:
        depth_section(cases, data, out)
    if "iter" in only:
        iteration_section(cases, data, out)
    if "other" in only:
        other_section(cases, data, jobs, out)
    criteria(out)


if __name__ == "__main__":
    main()
