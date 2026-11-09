"""model1140.py: the coverage rule of E606/E607 as a function, and the alternatives of the p1140 sweep.  numpy, scratch
analysis; it shares no code with run/run_p1140.py.

    coverage(V, k, w, h, round_variant="HU", limit=None) -> bool (h, w) array

V: three (x, y) integer vertices in 1/2^k pixel.  The vertices are put on the 1/256 grid by `round_variant` (HU: round half
up = E607's rule; the others are the alternatives of predictions-1140.toml), then optionally limited (`limit`), then every
pixel centre is tested exactly in integers: inside iff the edge functions are > 0, or == 0 on a left or top edge (rule R4 of
E606: after the vertices are ordered to one winding, an edge owns a sample on it iff dy < 0, or dy == 0 and dx > 0)."""
import numpy as np

ROUNDS = ["HU", "HD", "FL", "CE", "TR", "HA", "HE", "NONE"]


def to_grid(n, k, variant):
    """integers n in 1/2^k -> integers in 1/256 (k >= 8), or (NONE) left in 1/2^k"""
    n = np.asarray(n, dtype=np.int64)
    if variant == "NONE" or k == 8:
        return n
    g = 1 << (k - 8)
    h = g // 2
    if variant == "HU":
        return (n + h) // g
    if variant == "HD":
        return -((-n + h) // g)
    if variant == "FL":
        return n // g
    if variant == "CE":
        return -((-n) // g)
    if variant == "TR":
        return np.where(n >= 0, n // g, -((-n) // g))
    if variant == "HA":
        return np.where(n >= 0, (n + h) // g, -((-n + h) // g))
    if variant == "HE":
        q, r = n // g, n % g
        return q + ((r > h) | ((r == h) & (q % 2 == 1)))
    raise ValueError(variant)


def apply_limit(v256, limit):
    """limit = ("clamp", P) or ("wrap", P): coordinates in 1/256 pixel limited to +-2^P pixels (clamp) or wrapped into
    the signed P+1 bit pixel range (wrap)"""
    if limit is None:
        return v256
    kind, p = limit
    lim = (1 << p) * 256
    if kind == "clamp":
        return np.clip(v256, -lim, lim - 1)
    if kind == "wrap":
        return ((v256 + lim) % (2 * lim)) - lim
    raise ValueError(kind)


def coverage(V, k, w, h, round_variant="HU", limit=None, f32=False):
    V = np.asarray(V, dtype=np.int64).reshape(3, 2)
    if round_variant == "NONE":
        kk = k
        v = V
    else:
        kk = 8
        v = to_grid(V, k, round_variant)
        v = apply_limit(v, limit)
    out = np.zeros((h, w), dtype=bool)
    a, b, c = v[0], v[1], v[2]
    area = int((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    if area == 0:
        return out
    if area < 0:
        b, c = c, b
    one = 1 << kk
    x0 = max(int(v[:, 0].min() // one) - 1, 0)
    x1 = min(int(v[:, 0].max() // one) + 2, w)
    y0 = max(int(v[:, 1].min() // one) - 1, 0)
    y1 = min(int(v[:, 1].max() // one) + 2, h)
    if x1 <= x0 or y1 <= y0:
        return out
    xs = np.arange(x0, x1, dtype=np.int64) * one + one // 2
    edges = []
    for p, q in ((a, b), (b, c), (c, a)):
        dx, dy = int(q[0] - p[0]), int(q[1] - p[1])
        own = dy < 0 or (dy == 0 and dx > 0)
        edges.append((int(p[0]), int(p[1]), dx, dy, own))
    step = max(1, 4_000_000 // max(x1 - x0, 1))
    for ya in range(y0, y1, step):
        yb = min(ya + step, y1)
        sy = (np.arange(ya, yb, dtype=np.int64) * one + one // 2)[:, None]
        inside = np.ones((yb - ya, x1 - x0), dtype=bool)
        for px, py, dx, dy, own in edges:
            if f32:
                s = np.float32(1.0 / one)
                e = (np.float32(dx * s) * (sy.astype(np.float32) * s - np.float32(py * s))).astype(np.float32) - \
                    (np.float32(dy * s) * (xs.astype(np.float32)[None, :] * s - np.float32(px * s))).astype(np.float32)
            else:
                e = dx * (sy - py) - dy * (xs[None, :] - px)
            inside &= (e > 0) | ((e == 0) & own)
        out[ya:yb, x0:x1] = inside
    return out
