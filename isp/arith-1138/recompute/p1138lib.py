"""p1138lib.py: parsing and the hypotheses of the 11.38 arithmetic sweep.  Shares no code with the run
scripts (run/run_p1138.py): it reads cases.tsv and the kept raw dumps.  numpy is required.

Units: vertices are integers in 1/256 pixel (window coordinates, y down); a pixel (x, y) has its top-left
corner at (256 x, 256 y); a sample point S = (sx, sy) in 1/256 pixel from that corner (centre (128, 128)).
"""
import gzip
import itertools
import os
import struct

import numpy as np

BG = 0xff203040
FILL = 0xdeadbeef

# ---------------------------------------------------------------------------------------------- cases


class Case:
    def __init__(self, f):
        self.id = int(f[0])
        self.set, self.cls = f[1], f[2]
        self.w, self.h = int(f[3]), int(f[4])
        self.v = np.array([int(x) for x in f[5:11]], dtype=np.int64).reshape(3, 2)
        self.z = [float(x) for x in f[11:14]]
        self.pair, self.jobs = f[14], f[15]


def load_cases(path):
    return [Case(l.rstrip("\n").split("\t")) for l in open(path) if l.strip()]


# ---------------------------------------------------------------------------------------------- dumps


def read_gz(path):
    with gzip.open(path, "rb") as fh:
        return fh.read()


def parse_rows(text, w, h):
    """The pixel rows of a tool output ('row N: 0x...' of tri, 'probe NAME: row N: ...' of probe):
    an (h, w) uint32 array, or None when a row is missing."""
    img = np.zeros((h, w), dtype=np.uint32)
    seen = set()
    for line in text.splitlines():
        i = line.find("row ")
        if i < 0 or (i and "probe " not in line[:i]):
            continue
        head, _, rest = line[i + 4:].partition(":")
        if not head.strip().isdigit():
            continue
        y = int(head)
        vals = [int(t, 16) for t in rest.split()]
        if y < h and len(vals) == w:
            img[y] = vals
            seen.add(y)
    return img if len(seen) == h else None


def mort(x, y):
    """in-tile dword index of the pixel (x, y) of a 32 x 16 tile: y0 x0 y1 x1 y2 x2 y3 x3 x4 (E465)"""
    r = 0
    for k, (v, b) in enumerate([(y, 0), (x, 0), (y, 1), (x, 1), (y, 2), (x, 2), (y, 3), (x, 3)]):
        r |= ((v >> b) & 1) << k
    return r | (((x >> 4) & 1) << 8)


def depth_index(w, h, g=1):
    """(h, w) array: the dword of the depth buffer that holds each pixel (E465, pitch G + 1 tiles)"""
    ys, xs = np.mgrid[0:h, 0:w]
    low = np.zeros((h, w), dtype=np.int64)
    for k, (arr, b) in enumerate([(ys, 0), (xs, 0), (ys, 1), (xs, 1), (ys, 2), (xs, 2), (ys, 3), (xs, 3)]):
        low |= ((arr >> b) & 1) << k
    low |= ((xs >> 4) & 1) << 8
    return 512 * ((ys // 16) * (g + 1) + xs // 32) + low


def depth_image(raw, w, h, g=1):
    buf = np.frombuffer(raw, dtype="<u4")
    idx = depth_index(w, h, g)
    return buf[idx] if idx.max() < buf.size else None


def f32(u):
    return np.asarray(u, dtype=np.uint32).view(np.float32)


# ---------------------------------------------------------------------------------------------- coverage

SNAPS = {"none": (1, "r"), "r32": (8, "r"), "r16": (16, "r"), "f16": (16, "f"), "r8": (32, "r"), "r4": (64, "r")}


def snap(v, name):
    g, mode = SNAPS[name]
    v = np.asarray(v, dtype=np.int64)
    if g == 1:
        return v
    return ((v + g // 2) // g) * g if mode == "r" else (v // g) * g


# owner predicates of a winding-normalised edge direction (dx, dy): who owns a sample on the edge
RULES = {
    "R1": lambda dx, dy: (dy > 0) | ((dy == 0) & (dx > 0)),
    "R2": lambda dx, dy: (dy < 0) | ((dy == 0) & (dx < 0)),
    "R3": lambda dx, dy: (dy > 0) | ((dy == 0) & (dx < 0)),
    "R4": lambda dx, dy: (dy < 0) | ((dy == 0) & (dx > 0)),
    "R5": lambda dx, dy: (dx > 0) | ((dx == 0) & (dy > 0)),
    "R6": lambda dx, dy: (dx < 0) | ((dx == 0) & (dy < 0)),
    "R7": lambda dx, dy: (dx > 0) | ((dx == 0) & (dy < 0)),
    "R8": lambda dx, dy: (dx < 0) | ((dx == 0) & (dy > 0)),
    "ALL": lambda dx, dy: np.ones_like(dx, dtype=bool),
    "NONE": lambda dx, dy: np.zeros_like(dx, dtype=bool),
}
RULE_ORDER = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "ALL", "NONE"]


class Pixels:
    """the pixels of the bounding boxes (grown by a margin) of a list of cases, with their vertices"""

    def __init__(self, cases, margin=2):
        cols = {k: [] for k in ("tri", "x", "y", "w", "h")}
        for i, c in enumerate(cases):
            lo = c.v.min(axis=0) // 256 - margin
            hi = c.v.max(axis=0) // 256 + margin + 1
            x0, y0 = max(int(lo[0]), 0), max(int(lo[1]), 0)
            x1, y1 = min(int(hi[0]), c.w), min(int(hi[1]), c.h)
            if x1 <= x0 or y1 <= y0:
                continue
            ys, xs = np.mgrid[y0:y1, x0:x1]
            n = xs.size
            cols["tri"].append(np.full(n, i, dtype=np.int64))
            cols["x"].append(xs.ravel())
            cols["y"].append(ys.ravel())
        self.tri = np.concatenate(cols["tri"]) if cols["tri"] else np.zeros(0, dtype=np.int64)
        self.x = np.concatenate(cols["x"]) if cols["x"] else np.zeros(0, dtype=np.int64)
        self.y = np.concatenate(cols["y"]) if cols["y"] else np.zeros(0, dtype=np.int64)
        self.V = np.array([c.v for c in cases], dtype=np.int64)          # (n, 3, 2)
        self.cases = cases


def covered(px, snapname, S, rule):
    """bool array: pixel centre-sample S of each pixel of px inside the triangle snapped as snapname, the
    edge function exact (integers), the owner rule RULES[rule] for samples on an edge"""
    V = snap(px.V, snapname)[px.tri]                                  # (m, 3, 2)
    a, b, c = V[:, 0], V[:, 1], V[:, 2]
    area = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    neg = area < 0
    b2 = np.where(neg[:, None], c, b)
    c2 = np.where(neg[:, None], b, c)
    sx = px.x * 256 + S[0]
    sy = px.y * 256 + S[1]
    inside = area != 0
    own = RULES[rule]
    for p, q in ((a, b2), (b2, c2), (c2, a)):
        dx, dy = q[:, 0] - p[:, 0], q[:, 1] - p[:, 1]
        e = dx * (sy - p[:, 1]) - dy * (sx - p[:, 0])
        inside &= (e > 0) | ((e == 0) & own(dx, dy))
    return inside


def covered_f32(px, snapname, S, rule):
    """the same with the edge functions evaluated in float32 from pixel-unit float32 coordinates"""
    V = snap(px.V, snapname)[px.tri].astype(np.float64) / 256.0
    f = np.float32
    a, b, c = V[:, 0].astype(f), V[:, 1].astype(f), V[:, 2].astype(f)
    area = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    neg = area < 0
    b2 = np.where(neg[:, None], c, b)
    c2 = np.where(neg[:, None], b, c)
    sx = (px.x + f(S[0] / 256.0)).astype(f)
    sy = (px.y + f(S[1] / 256.0)).astype(f)
    inside = area != 0
    own = RULES[rule]
    for p, q in ((a, b2), (b2, c2), (c2, a)):
        dx, dy = q[:, 0] - p[:, 0], q[:, 1] - p[:, 1]
        e = (dx * (sy - p[:, 1])).astype(f) - (dy * (sx - p[:, 0])).astype(f)
        inside &= (e > 0) | ((e == 0) & own(dx, dy))
    return inside


def observed(px, imgs):
    """imgs: list over cases of a bool (h, w) coverage image (or None): the observation at the pixels of px"""
    out = np.zeros(px.tri.size, dtype=bool)
    ok = np.ones(px.tri.size, dtype=bool)
    starts = np.searchsorted(px.tri, np.arange(len(px.cases)))
    ends = np.searchsorted(px.tri, np.arange(len(px.cases)), side="right")
    for i, img in enumerate(imgs):
        s, e = starts[i], ends[i]
        if img is None:
            ok[s:e] = False
        else:
            out[s:e] = img[px.y[s:e], px.x[s:e]]
    return out, ok


def grid_samples(step=16):
    return [(sx, sy) for sy in range(0, 256, step) for sx in range(0, 256, step)]


def fit_coverage(px, obs, ok=None, snaps=None, samples=None, rules=None):
    """every (snap, S, rule) of the grid against the observation obs (bool per pixel of px): a dict
    hypothesis -> number of mismatching pixels (only pixels where ok).  Same arithmetic as covered(),
    with the per-snap and per-rule parts computed once."""
    res = {}
    ok = np.ones(obs.size, dtype=bool) if ok is None else ok
    sxb, syb = px.x * 256, px.y * 256
    for sn in (snaps or list(SNAPS)):
        V = snap(px.V, sn)[px.tri]
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        area = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
        neg = area < 0
        b2 = np.where(neg[:, None], c, b)
        c2 = np.where(neg[:, None], b, c)
        nz = area != 0
        edges = []
        for p, q in ((a, b2), (b2, c2), (c2, a)):
            dx, dy = q[:, 0] - p[:, 0], q[:, 1] - p[:, 1]
            A = dx * (syb - p[:, 1]) - dy * (sxb - p[:, 0])
            edges.append((dx, dy, A, {r: RULES[r](dx, dy) for r in (rules or RULE_ORDER)}))
        for S in (samples or grid_samples()):
            es = [A + dx * S[1] - dy * S[0] for dx, dy, A, _ in edges]
            gt = [e > 0 for e in es]
            eq = [e == 0 for e in es]
            for r in (rules or RULE_ORDER):
                pred = nz.copy()
                for i in range(3):
                    pred &= gt[i] | (eq[i] & edges[i][3][r])
                res[(sn, S, r)] = int(np.count_nonzero((pred != obs) & ok))
    return res


# ---------------------------------------------------------------------------------------------- planes


def plane_at(px, snapname, S, vals):
    """the value at each pixel's sample point S of the plane through the (snapped) vertices carrying
    vals (n, 3) float64; exact in float64"""
    V = snap(px.V, snapname)[px.tri].astype(np.float64)
    a, b, c = V[:, 0], V[:, 1], V[:, 2]
    z = vals[px.tri]
    area = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    sx = px.x * 256.0 + S[0]
    sy = px.y * 256.0 + S[1]
    with np.errstate(divide="ignore", invalid="ignore"):
        l1 = ((sx - a[:, 0]) * (c[:, 1] - a[:, 1]) - (sy - a[:, 1]) * (c[:, 0] - a[:, 0])) / area
        l2 = ((b[:, 0] - a[:, 0]) * (sy - a[:, 1]) - (b[:, 1] - a[:, 1]) * (sx - a[:, 0])) / area
    return z[:, 0] + l1 * (z[:, 1] - z[:, 0]) + l2 * (z[:, 2] - z[:, 0])


def ulp_error(obs, ref):
    """|obs - ref| in ulps of float32 at ref (ulp of 1.0 .. 2.0 = 2^-23 for |ref| in [1, 2)), float64 inputs"""
    r = np.abs(ref)
    with np.errstate(divide="ignore"):
        u = np.where(r > 0, 2.0 ** (np.floor(np.log2(np.where(r > 0, r, 1.0))) - 23), 2.0 ** -149)
    return np.abs(obs - ref) / u
