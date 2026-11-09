#!/usr/bin/env python3
"""recompute_p1140.py DATADIR [--groups S1,S2,...] [--sets fit,heldout,...]: the analysis of the p1140 sweep.  numpy (scratch
analysis).  Reads only cases-1140.tsv, jobs.tsv and raw/ID.txt.gz of DATADIR and model1140.py; it shares no code with
run/run_p1140.py.  The coverage of the hardware image is every pixel that is not the background 0xff203040; the model is
model1140.coverage (vertices to the 1/256 grid by a rounding variant, exact integer edge test, left and top edges own ties).

Sections: 1 S1 size, 2 S2 sweeps, 3 S3 negative, 5 S5 tinyedge, 4 S4 far, 6 repeats and tool counts, 7 criteria P1..P14."""
import gzip
import os
import re
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model1140 as M  # noqa: E402

BG = 0xFF203040
COLS = ("id", "set", "group", "cls", "w", "h", "unit", "v0x", "v0y", "v1x", "v1y", "v2x", "v2y", "pair", "jobs")
RLE = re.compile(r"^rle (\d+):(.*)$", re.M)
RUN = re.compile(r"0x([0-9a-f]{8})x(\d+)")
COUNT = re.compile(r"^tri (\d+)x(\d+) #1: (\d+) triangle, (\d+) background, (\d+) other", re.M)


class Case:
    def __init__(self, f):
        self.id, self.set, self.group, self.cls = int(f[0]), f[1], f[2], f[3]
        self.w, self.h, self.unit = int(f[4]), int(f[5]), int(f[6])
        self.v = np.array([int(x) for x in f[7:13]], dtype=np.int64).reshape(3, 2)
        self.pair, self.jobs = f[13], f[14]


def log(s=""):
    print(s, flush=True)


def load(d):
    cases = [Case(l.rstrip("\n").split("\t")) for l in open(os.path.join(d, "cases-1140.tsv")) if l.strip()]
    jobs = {}
    for line in open(os.path.join(d, "jobs.tsv")):
        f = line.rstrip("\n").split("\t")
        jobs[int(f[0])] = (f[1], f[5])           # rc, flags (the last record of a case counts)
    return cases, jobs


def raw_text(d, c):
    p = os.path.join(d, "raw", "%d.txt.gz" % c.id)
    return gzip.open(p).read().decode("utf-8", "replace") if os.path.exists(p) else None


def image(text, w, h):
    """(h, w) bool covered image, and the set of colours seen, from the 'rle Y:' lines; None when a row is missing"""
    if text is None:
        return None, set()
    img = np.zeros((h, w), dtype=bool)
    seen, colours = set(), set()
    for m in RLE.finditer(text):
        y = int(m.group(1))
        runs = RUN.findall(m.group(2))
        x = 0
        for v, n in runs:
            n = int(n)
            colours.add(int(v, 16))
            if int(v, 16) != BG:
                img[y, x:x + n] = True
            x += n
        if x != w:
            return None, colours
        seen.add(y)
    return (img if len(seen) == h else None), colours


class Result:
    """one case: hardware image, mismatches per model variant"""
    pass


def mism(img, V, c, variant="HU", limit=None, f32=False):
    k = c.unit
    m = M.coverage(V, k, c.w, c.h, variant, limit, f32)
    return int((m != img).sum())


def collect(d, cases, jobs, groups, sets):
    out = []
    for c in cases:
        if c.group not in groups or c.set not in sets:
            continue
        txt = raw_text(d, c)
        img, cols = image(txt, c.w, c.h)
        rc, fl = jobs.get(c.id, ("?", "missing"))
        out.append((c, txt, img, cols, rc == "0" and fl == "-"))
    return out


def by(lst, keyf):
    g = defaultdict(list)
    for x in lst:
        g[keyf(x)].append(x)
    return g


def sec_size(rows, R):
    log("\n## 1 S1 size: random 1/256 triangles; H0 = round half up to 1/256 + exact centre test + left/top ties")
    tot = defaultdict(lambda: [0, 0, 0, 0])      # set -> [cases, inexact cases, mismatching pixels, pixels]
    for c, txt, img, cols, ok in rows:
        if c.group != "S1" or c.set == "repeat":
            continue
        if img is None:
            R["s1_missing"] = R.get("s1_missing", 0) + 1
            continue
        n = mism(img, c.v, c)
        t = tot[(c.set, c.w, c.h)]
        t[0] += 1
        t[1] += n > 0
        t[2] += n
        t[3] += c.w * c.h
        R.setdefault("s1", {})[c.id] = n
    for k in sorted(tot):
        t = tot[k]
        log("  %-8s %4dx%-4d cases %3d inexact %3d mismatching pixels %d of %d" % (k[0], k[1], k[2], t[0], t[1], t[2], t[3]))
    R["s1_tot"] = tot
    # classes
    cl = defaultdict(lambda: [0, 0])
    for c, txt, img, cols, ok in rows:
        if c.group == "S1" and c.set != "repeat" and c.id in R.get("s1", {}):
            cl[(c.set, c.cls)][0] += 1
            cl[(c.set, c.cls)][1] += R["s1"][c.id]
    for k in sorted(cl):
        log("  class %-8s %-8s cases %3d mismatching pixels %d" % (k[0], k[1], cl[k][0], cl[k][1]))
    # shared edges
    pairs = defaultdict(list)
    for c, txt, img, cols, ok in rows:
        if c.group == "S1" and c.pair != "-" and img is not None and c.set != "repeat":
            pairs[(c.set, c.w, c.h, c.pair)].append((c, img))
    both = none_in = 0
    npair = 0
    for k, v in pairs.items():
        if len(v) != 2:
            continue
        npair += 1
        both += int((v[0][1] & v[1][1]).sum())
        # a pixel the model puts inside the quad's two triangles exactly once and the hardware covers by neither
        mm = [M.coverage(c.v, c.unit, c.w, c.h) for c, _ in v]
        none_in += int((((mm[0] ^ mm[1])) & ~(v[0][1] | v[1][1])).sum())
    log("  shared edges: %d pairs, pixels drawn by both triangles %d, pixels the model gives to one and the hardware to none %d" %
        (npair, both, none_in))
    R["pairs"] = (npair, both, none_in)


def sec_sweep(rows, R):
    log("\n## 2 S2 sweeps of an edge across the half-grid tie (steps of 1/4096 pixel; 1/1024 from 2048 wide)")
    per = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for c, txt, img, cols, ok in rows:
        if c.group != "S2":
            continue
        if img is None:
            R["s2_missing"] = R.get("s2_missing", 0) + 1
            continue
        hu = mism(img, c.v, c, "HU")
        alts = [mism(img, c.v, c, v) for v in ("HD", "FL", "NONE")]
        t = per[(c.set, c.w, c.h)]
        t[0] += 1
        t[1] += hu
        for i, a in enumerate(alts):
            t[2 + i] += a > 0
        R.setdefault("s2", {})[c.id] = hu
    for k in sorted(per):
        t = per[k]
        log("  %-8s %4dx%-4d cases %3d H0 mismatching pixels %d; cases the alternatives would mispredict: HD %d FL %d NONE %d" %
            (k[0], k[1], k[2], t[0], t[1], t[2], t[3], t[4]))
    R["s2_tot"] = per
    # the observed flip step per sweep class
    log("  observed flips (the first t of the sweep at which the covered pixel set changes; t in the case's unit):")
    for (st, w, h), grp in sorted(by([r for r in rows if r[0].group == "S2"], lambda r: (r[0].set, r[0].w, r[0].h)).items()):
        cl = by(grp, lambda r: r[0].cls)
        parts = []
        for cn, cs in sorted(cl.items()):
            cs.sort(key=lambda r: r[0].id)
            keys = [r[2].tobytes() if r[2] is not None else None for r in cs]
            fl = [i for i in range(1, len(keys)) if keys[i] != keys[i - 1]]
            parts.append("%s %s" % (cn[5:], fl))
        log("    %-8s %4dx%-4d %s" % (st, w, h, "; ".join(parts)))


def sec_neg(rows, R):
    log("\n## 3 S3 negative coordinates with sub-grid fractions: mismatching pixels per rounding variant")
    tot = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for c, txt, img, cols, ok in rows:
        if c.group != "S3":
            continue
        if img is None:
            R["s3_missing"] = R.get("s3_missing", 0) + 1
            continue
        for var in M.ROUNDS:
            n = mism(img, c.v, c, var)
            tot[(c.set)][var][0] += 1
            tot[(c.set)][var][1] += n
            R.setdefault("s3", {}).setdefault((c.set, var), []).append(n)
    for st in sorted(tot):
        log("  %-8s %s" % (st, "  ".join("%s %d (%d cases inexact)" % (v, tot[st][v][1], sum(1 for n in R["s3"][(st, v)] if n))
                                         for v in M.ROUNDS)))


def sec_tiny(rows, R):
    log("\n## 5 S5 tinyedge: a long edge passing the pixel centre (W/2, H/2) at a cross product of +1 / -1 (1/65536 pixel^2)")
    tot = defaultdict(lambda: [0, 0, 0, 0, 0])
    for c, txt, img, cols, ok in rows:
        if c.group != "S5":
            continue
        if img is None:
            R["s5_missing"] = R.get("s5_missing", 0) + 1
            continue
        hu = mism(img, c.v, c, "HU")
        f = mism(img, c.v, c, "HU", None, True)
        px = bool(img[c.h // 2, c.w // 2])
        want = c.cls.endswith("+1")
        t = tot[(c.set, c.w)]
        t[0] += 1
        t[1] += hu > 0
        t[2] += hu
        t[3] += f > 0
        t[4] += px != want
        R.setdefault("s5", {})[c.id] = (hu, f, px == want)
    for k in sorted(tot):
        t = tot[k]
        log("  %-8s %4d^2 cases %3d H0 inexact cases %d (pixels %d); float32 edge function inexact cases %d; sample pixel not as the sign says: %d" %
            (k[0], k[1], t[0], t[1], t[2], t[3], t[4]))
    R["s5_tot"] = tot


def sec_far(rows, R):
    log("\n## 4 S4 far vertices (one vertex at +-2^k pixels): mismatching pixels against H0 and the best limit variant")
    alts = [("exact", None)] + [("clamp", p) for p in range(14, 24)] + [("wrap", p) for p in range(14, 24)]
    first = {}
    for c, txt, img, cols, ok in sorted((r for r in rows if r[0].group == "S4"), key=lambda r: r[0].id):
        if txt is None:
            continue
        k = int(c.cls[3:c.cls.index("d")])
        d = int(c.cls[c.cls.index("d") + 1:])
        if img is None:
            log("  %s %-8s k=%2d d=%d: no image (%s)" % (c.set, c.cls, k, d, "flagged" if not ok else "incomplete"))
            R.setdefault("s4", {})[c.id] = (k, d, None)
            continue
        n = int(img.sum())
        e = mism(img, c.v, c, "HU")
        best = []
        for nm, p in alts:
            lim = None if nm == "exact" else (nm, p)
            if mism(img, c.v, c, "HU", lim) == 0:
                best.append(nm if p is None else "%s%d" % (nm, p))
        if n == 0:
            best.append("empty")
        R.setdefault("s4", {})[c.id] = (k, d, e)
        if e and (c.set, c.w) not in first:
            first[(c.set, c.w)] = k
        log("  %-8s %dx%d k=%2d d=%d covered %7d H0 mismatching %7d matches: %s" % (c.set, c.w, c.h, k, d, n, e, ",".join(best) or "none"))
    R["s4_first"] = first
    log("  first k with a mismatch against H0: %s" % first)


def sec_repeat(rows, d, R):
    log("\n## 6 repeats, tool counts, colours, flags")
    orig = {}
    for c, txt, img, cols, ok in rows:
        if c.set != "repeat":
            orig[(c.group, c.cls, c.w, c.h, tuple(c.v.ravel()), c.unit)] = img
    same = tot = 0
    for c, txt, img, cols, ok in rows:
        if c.set == "repeat":
            tot += 1
            o = orig.get((c.group, c.cls, c.w, c.h, tuple(c.v.ravel()), c.unit))
            same += int(o is not None and img is not None and np.array_equal(o, img))
    log("  repeats identical to the first run: %d of %d" % (same, tot))
    R["rep"] = (same, tot)
    bad_cnt = bad_col = flagged = 0
    for c, txt, img, cols, ok in rows:
        if not ok:
            flagged += 1
        if img is None:
            continue
        m = COUNT.search(txt)
        if m and int(m.group(3)) != int(img.sum()):
            bad_cnt += 1
        if not cols <= {BG, 0xFF00FF00}:
            bad_col += 1
    log("  jobs flagged or without an exact record: %d; images whose count differs from the tool's line: %d; images with a "
        "colour other than the two: %d" % (flagged, bad_cnt, bad_col))
    R["flag"] = (flagged, bad_cnt, bad_col)


def criteria(R, rows):
    log("\n## 7 criteria (predictions-1140.toml)")
    res = []

    def crit(name, ok, text):
        res.append((name, ok))
        log("  %-4s %-4s %s" % (name, "PASS" if ok else "FAIL", text))

    s1 = R.get("s1_tot", {})
    f = sum(t[2] for k, t in s1.items() if k[0] == "fit")
    nf = sum(t[0] for k, t in s1.items() if k[0] == "fit")
    crit("P1", nf > 0 and f == 0, "S1 fit (%d cases, 512x256, 96x64, 640x480): %d mismatching pixels, want 0" % (nf, f))
    h = sum(t[2] for k, t in s1.items() if k[0] == "heldout" and k[1] != 4096)
    nh = sum(t[0] for k, t in s1.items() if k[0] == "heldout" and k[1] != 4096)
    crit("P2", nh > 0 and h == 0, "S1 held-out below 4096 (%d cases): %d mismatching pixels, want 0" % (nh, h))
    h4 = [t for k, t in s1.items() if k[0] == "heldout" and k[1] == 4096]
    crit("P2b", bool(h4) and sum(t[2] for t in h4) == 0, "S1 4096x4096 (%d cases): %s mismatching pixels, want 0" %
         (sum(t[0] for t in h4), sum(t[2] for t in h4) if h4 else "n/a"))
    s2 = R.get("s2_tot", {})
    for nm, st in (("P3", "fit"), ("P4", "heldout")):
        n = sum(t[1] for k, t in s2.items() if k[0] == st)
        c_ = sum(t[0] for k, t in s2.items() if k[0] == st)
        crit(nm, c_ > 0 and n == 0, "S2 %s sweeps (%d cases): %d mismatching pixels against H0, want 0" % (st, c_, n))
    hd = sum(t[2] for t in s2.values())
    crit("P4b", hd >= 20, "S2 power: half-down would mispredict %d sweep cases (>= 20 needed for the set to separate it)" % hd)
    for nm, st in (("P5", "fit"), ("P6", "heldout")):
        a = R.get("s3", {}).get((st, "HU"), [])
        crit(nm, bool(a) and sum(a) == 0, "S3 %s negative (%d cases): H0 mismatching pixels %d, want 0" % (st, len(a), sum(a)))
    alt_fail = all(sum(R.get("s3", {}).get(("fit", v), [0])) > 0 for v in ("HD", "FL", "CE", "TR", "HA", "HE"))
    crit("P5b", alt_fail, "S3 fit power: every alternative rounding mispredicts at least one pixel: " +
         ", ".join("%s %d" % (v, sum(R.get("s3", {}).get(("fit", v), [0]))) for v in ("HD", "FL", "CE", "TR", "HA", "HE")))
    s5 = R.get("s5_tot", {})
    fit_in = sum(t[1] for k, t in s5.items() if k[0] == "fit")
    crit("P7", bool(s5) and fit_in == 0, "S5 fit (512^2, 1024^2): H0 inexact cases %d of %d, want 0" %
         (fit_in, sum(t[0] for k, t in s5.items() if k[0] == "fit")))
    f32 = sum(t[3] for t in s5.values())
    crit("P7b", f32 >= 10, "S5 power: a float32 edge function mispredicts %d cases (>= 10 needed)" % f32)
    k2 = sum(t[1] for k, t in s5.items() if k == ("heldout", 2048))
    crit("P8a", ("heldout", 2048) in s5 and k2 == 0, "S5 2048^2: H0 inexact cases %d of %d, want 0" %
         (k2, s5.get(("heldout", 2048), [0])[0]))
    k4 = sum(t[1] for k, t in s5.items() if k == ("heldout", 4096))
    crit("P8b", ("heldout", 4096) in s5 and k4 >= 1, "S5 4096^2: H0 inexact cases %d of %d, want >= 1 (the edge function is not exact "
         "to 42 bits)" % (k4, s5.get(("heldout", 4096), [0])[0]))
    s4 = R.get("s4", {})
    lowbad = [(k, d, e) for k, d, e in s4.values() if e and k <= 15]
    crit("P9", bool(s4) and not lowbad, "S4 far vertices with |v| <= 2^15 pixels: %d cases mismatching (fit and held-out), want 0" % len(lowbad))
    first = R.get("s4_first", {})
    crit("P10", bool(first) and all(v == 16 for v in first.values()),
         "S4 first k with a mismatch: %s, want 16 on every target" % first)
    crit("P11", R.get("rep", (0, 0))[1] > 0 and R["rep"][0] == R["rep"][1], "repeats identical: %s of %s" % R.get("rep", (0, 0)))
    fl = R.get("flag", (1, 1, 1))
    crit("P12", fl == (0, 0, 0), "no flagged job, tool counts equal image counts, two colours only: %s" % (fl,))
    return res


def main():
    dirs = [a for a in sys.argv[1:] if not a.startswith("--")]
    groups = {"S1", "S2", "S3", "S4", "S5"}
    sets = {"fit", "heldout", "repeat", "pilot"}
    for a in sys.argv[2:]:
        if a.startswith("--groups="):
            groups = set(a.split("=")[1].split(","))
        if a.startswith("--sets="):
            sets = set(a.split("=")[1].split(","))
    rows = []
    for d in dirs:                       # one directory per run (main, far, pilot): each has cases-1140.tsv, jobs.tsv, raw/
        cases, jobs = load(d)
        done = {c.id for c, *_ in rows}
        rows += [r for r in collect(d, cases, jobs, groups | {"P"}, sets) if r[0].id not in done and r[1] is not None]
    R = {}
    d = dirs[0]
    log("p1140 recompute: %d cases read from %s" % (len(rows), " ".join(dirs)))
    if "S1" in groups:
        sec_size(rows, R)
    if "S2" in groups:
        sec_sweep(rows, R)
    if "S3" in groups:
        sec_neg(rows, R)
    if "S5" in groups:
        sec_tiny(rows, R)
    if "S4" in groups:
        sec_far(rows, R)
    sec_repeat(rows, d, R)
    criteria(R, rows)


if __name__ == "__main__":
    main()
