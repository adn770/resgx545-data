#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""OZ (round 9, Q260, decision S-2 / R9-8 a): the shared part of the fixed-point edge variants.

Loaders (read only over resgx545-data):
  fit_jobs()   E914's zs rows (render/closing-r7-geo, attempt 20261112-211113) and E943's zs2 rows
               (render/closing-r8-lgeo, attempt 20261113-024441): every completed job whose
               --pixels output is whole, controls included (E681's and E683's first 512 x 256
               cases appear there as controls; they are E681/E683 cases, see below).
  e683_cases() E683's 240 S3 cases (isp/coverage-envelope, the dataset's own loader).
  env_cases(groups) the other groups of that dataset (S1, S2, S4, S5), used as a control after the
               freeze only.

Engine: coverage(V, k, w, h, var) gives the covered (h, w) image of a triangle whose vertices V are
integers in 1/2^k pixel. The vertices go to the 1/256 grid by HA (half away from zero, model1140's
to_grid), are put in one winding, and each edge P -> Q (dx, dy in 1/256 pixel) is evaluated at
every pixel centre S. var None is the exact test (model1140 HA). A variant quantises the edge's
coefficients: with n the normalisation (major: max(|dx|, |dy|); pow2: the power of two at or above
it; pixel: 256), A = q(dx 2^b / n), B = q(dy 2^b / n) (q one of RN half away, TZ toward zero, FL
floor), the constant at the origin O exact (cq "x") or quantised the same way (cq "q"), and
    n 2^b E = 2^b e(S) + eps_C0 + epsA (Sy - Oy) - epsB (Sx - Ox),
with e(S) the exact edge function, epsA = n A - 2^b dx and epsB = n B - 2^b dy, all integers:
the sign is taken exactly in int64 (no float). Origins: target (0, 0), tile (the 32 x 16 tile, the
TA's region, holding S), P or Q (the edge's start or end vertex in the winding) or top (the edge's
vertex with the smaller y, then the smaller x). The tie rule (E606's R4) is unchanged.
Numpy, scratch only."""
import gzip
import os
import re
import sys

import numpy as np

DATA = "/Users/jtorra/src/resgx545-data"
ENV = DATA + "/isp/coverage-envelope"
sys.path.insert(0, ENV + "/recompute")
import model1140 as M  # noqa: E402
import recompute_p1140 as R  # noqa: E402

FIT_DIRS = (("E914", DATA + "/render/closing-r7-geo/out/20261112-211113/zs"),
            ("E943", DATA + "/render/closing-r8-lgeo/out/20261113-024441/zs2"))


class Job:
    def __init__(self, src, name, sset, w, h, k, v, img):
        self.src, self.name, self.set, self.w, self.h, self.k = src, name, sset, w, h, k
        self.v = np.asarray(v, dtype=np.int64).reshape(3, 2)
        self.img = img


def _pixels(text, w, h):
    rows = {}
    for m in re.finditer(r"^row (\d+): (.*)$", text, re.M):
        toks = m.group(2).split()
        if len(toks) != w:
            return None
        rows[int(m.group(1))] = np.array([t == "0xff00ff00" for t in toks], dtype=bool)
    if sorted(rows) != list(range(h)):
        return None
    return np.stack([rows[y] for y in range(h)])


def fit_jobs():
    out = []
    for src, d in FIT_DIRS:
        for line in open(os.path.join(d, "cases.tsv")):
            f = line.rstrip("\n").split("\t")
            if f[0] == "name" or f[8] != "ok":
                continue
            toks = f[6].split()
            w, h = int(toks[toks.index("--width") + 1]), int(toks[toks.index("--height") + 1])
            k = int(toks[toks.index("--tri-unit") + 1])
            v = [int(x) for x in toks[toks.index("--tri-v") + 1].split(",")]
            p = os.path.join(d, f[0] + ".txt.gz")
            img = _pixels(gzip.open(p).read().decode(), w, h) if os.path.exists(p) else None
            if img is not None:
                out.append(Job(src, f[0], f[2], w, h, k, v, img))
    return out


def env_cases(groups):
    d = ENV + "/main"
    cases, jobs = R.load(d)
    out = []
    for c, txt, img, cols, ok in R.collect(d, cases, jobs, set(groups), {c.set for c in cases}):
        if img is not None:
            out.append(Job(c.group, str(c.id), c.set, c.w, c.h, c.unit, c.v, img))
    return out


def e683_cases():
    return env_cases({"S3"})


def _q(num, den, mode):
    """q(num / den) for int64 arrays/ints, den > 0: RN half away, TZ, FL."""
    num = np.asarray(num, dtype=np.int64)
    if mode == "FL":
        return num // den
    if mode == "TZ":
        return np.where(num >= 0, num // den, -((-num) // den))
    if mode == "RN":
        return np.where(num >= 0, (2 * num + den) // (2 * den), -((-2 * num + den) // (2 * den)))
    raise ValueError(mode)


def _norm(dx, dy, kind):
    m = max(abs(dx), abs(dy))
    if kind == "major":
        return m
    if kind == "pow2":
        return 1 << (m - 1).bit_length()
    if kind == "pixel":
        return 256
    raise ValueError(kind)


def coverage(V, k, w, h, var=None):
    V = np.asarray(V, dtype=np.int64).reshape(3, 2)
    v = M.to_grid(V, k, "HA")
    out = np.zeros((h, w), dtype=bool)
    a, b, c = v[0], v[1], v[2]
    area = int((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    if area == 0:
        return out
    if area < 0:
        b, c = c, b
    x0 = max(int(v[:, 0].min() // 256) - 1, 0)
    x1 = min(int(v[:, 0].max() // 256) + 2, w)
    y0 = max(int(v[:, 1].min() // 256) - 1, 0)
    y1 = min(int(v[:, 1].max() // 256) + 2, h)
    if x1 <= x0 or y1 <= y0:
        return out
    px = np.arange(x0, x1, dtype=np.int64)
    py = np.arange(y0, y1, dtype=np.int64)
    sx = (px * 256 + 128)[None, :]
    sy = (py * 256 + 128)[:, None]
    inside = np.ones((y1 - y0, x1 - x0), dtype=bool)
    for p, qv in ((a, b), (b, c), (c, a)):
        Px, Py, Qx, Qy = int(p[0]), int(p[1]), int(qv[0]), int(qv[1])
        dx, dy = Qx - Px, Qy - Py
        own = dy < 0 or (dy == 0 and dx > 0)
        e = dx * (sy - Py) - dy * (sx - Px)
        if var is not None and var.get("fam") == "prod":
            e = _product_sign(var, Px, Py, Qx, Qy, dx, dy, px, py, sx, sy, e.shape)
        elif var is not None:
            e = _quantised_sign(e, var, Px, Py, Qx, Qy, dx, dy, px, py, sx, sy)
        inside &= (e > 0) | ((e == 0) & own)
    out[y0:y1, x0:x1] = inside
    return out


def origin(kind, Px, Py, Qx, Qy, px, py):
    if kind == "target":
        return np.int64(0), np.int64(0)
    if kind == "tile":
        return ((px // 32) * 32 * 256)[None, :], ((py // 16) * 16 * 256)[:, None]
    if kind == "P":
        return np.int64(Px), np.int64(Py)
    if kind == "Q":
        return np.int64(Qx), np.int64(Qy)
    if kind == "top":
        return (np.int64(Px), np.int64(Py)) if (Py, Px) <= (Qy, Qx) else (np.int64(Qx), np.int64(Qy))
    raise ValueError(kind)


def _quantised_sign(e, var, Px, Py, Qx, Qy, dx, dy, px, py, sx, sy):
    """an int64 array with the sign of n 2^b E (exact)."""
    b, mode, kind, ok, cq = var["b"], var["q"], var["norm"], var["origin"], var["cq"]
    n = _norm(dx, dy, kind)
    one = 1 << b
    A = int(_q(dx * one, n, mode))
    B = int(_q(dy * one, n, mode))
    epsA, epsB = n * A - one * dx, n * B - one * dy
    Ox, Oy = origin(ok, Px, Py, Qx, Qy, px, py)
    T = epsA * (sy - Oy) - epsB * (sx - Ox)
    if cq == "q":
        eO = dx * (Oy - Py) - dy * (Ox - Px)
        C = _q(eO * one, n, mode)
        T = T + (n * C - one * eO)
    T = np.broadcast_to(T, e.shape)
    kq = T >> b
    r = T - (kq << b)
    s = e + kq
    return np.where(s != 0, s, (r > 0).astype(np.int64))


def _fl(x, m, mode):
    """x (exact integers held in float64, |x| < 2^53) rounded to m significant bits: RE (to nearest,
    ties to even) or TZ (toward zero). Exact in float64."""
    x = np.asarray(x, dtype=np.float64)
    _, ex = np.frexp(x)
    sh = np.maximum(ex - m, 0)
    y = np.ldexp(x, -sh)
    y = np.round(y) if mode == "RE" else np.trunc(y)
    return np.ldexp(y, sh)


def _product_sign(var, Px, Py, Qx, Qy, dx, dy, px, py, sx, sy, shape):
    """family "prod": E = fl(C_O) + fl(dx (Sy - Oy)) - fl(dy (Sx - Ox)), each term rounded to m
    significant bits (C_O = e(O), exact before its rounding; 0 at a vertex origin), the sum exact."""
    m, mode = var["m"], var["q"]
    Ox, Oy = origin(var["origin"], Px, Py, Qx, Qy, px, py)
    t1 = _fl(np.float64(dx) * (sy - Oy).astype(np.float64), m, mode)
    t2 = _fl(np.float64(dy) * (sx - Ox).astype(np.float64), m, mode)
    eO = (dx * (Oy - Py) - dy * (Ox - Px))
    t0 = _fl(np.asarray(eO, dtype=np.float64), m, mode)
    s = np.broadcast_to(t0 + t1 - t2, shape)
    return np.sign(s).astype(np.int64)


def variants_prod():
    out = []
    for m in range(12, 41):
        for q in ("RE", "TZ"):
            for o in ("target", "tile", "P", "Q", "top"):
                out.append({"fam": "prod", "m": m, "q": q, "origin": o})
    return out


def variants():
    out = []
    for norm in ("major", "pow2", "pixel"):
        for b in range(4, 25):
            for q in ("RN", "TZ", "FL"):
                for o in ("target", "tile", "P", "Q", "top"):
                    for cq in ("x", "q"):
                        if cq == "q" and o in ("P", "Q", "top"):
                            continue          # the constant at a vertex is 0: the same variant as "x"
                        out.append({"norm": norm, "b": b, "q": q, "origin": o, "cq": cq})
    return out


def vname(var):
    if var is not None and var.get("fam") == "prod":
        return "prod-m%d-%s-%s" % (var["m"], var["q"], var["origin"])
    return "exact" if var is None else "%s-b%d-%s-%s-c%s" % (var["norm"], var["b"], var["q"], var["origin"], var["cq"])
