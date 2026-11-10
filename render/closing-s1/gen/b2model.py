"""B2 frozen predictions from the E731 dump of dp-ax-b2 (the control d-ctl reproduces).

The deviation map is stored - trunc32(exact) in ulps per pixel; its region is fitted by a line
xmin(y) = c0 + c1 y over the rows that deviate; HT keeps the map in target coordinates, HV moves it
with the triangle.  numpy, scratch only.
"""
from __future__ import annotations

import gzip
import pathlib
import sys
from fractions import Fraction

import numpy as np

from s1common import DATA, PREDS

D = DATA / "texture/p1141/out-hw/p1141tex-dumps/isp-b-depth"
W, H, G = 256, 128, 7
BG = 0xDEADBEEF


def mort(x, y):
    r = 0
    for k, (v, b) in enumerate([(y, 0), (x, 0), (y, 1), (x, 1), (y, 2), (x, 2), (y, 3), (x, 3)]):
        r |= ((v >> b) & 1) << k
    return r | (((x >> 4) & 1) << 8)


def idx_map(w, h):
    tw = (w + 31) // 32
    return np.array([[512 * ((y // 16) * tw + x // 32) + mort(x % 32, y % 16) for x in range(w)] for y in range(h)])


def trunc32(v):
    w = v.astype(np.float32)
    up = w.astype(np.float64) > v
    w[up] = np.nextafter(w[up], np.float32(-np.inf))
    return w


def deviation(raw: bytes, w, h, V, Z):
    """stored - trunc32(exact) in float32 ulps per pixel; covered mask."""
    z = np.frombuffer(raw, dtype="<u4")[idx_map(w, h)]
    cov = (z != BG) & (z != 0)
    (x0, y0), (x1, y1), (x2, y2) = [(Fraction(a, 256), Fraction(b, 256)) for a, b in V]
    z0, z1, z2 = [Fraction(float(v)) for v in Z]
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    A = ((z1 - z0) * (y2 - y0) - (z2 - z0) * (y1 - y0)) / det
    B = ((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / det
    T = z0 - A * x0 - B * y0
    ys, xs = np.mgrid[0:h, 0:w]
    v = float(T) + float(A) * (xs + 0.5) + float(B) * (ys + 0.5)
    ex = trunc32(v).astype(np.float64)
    wv = z.view(np.float32).astype(np.float64)
    ulp = 2.0 ** (np.floor(np.log2(np.abs(ex))) - 23)
    return np.round((wv - ex) / ulp).astype(int), cov


def ctl_model(rows):
    raw = gzip.open(D / "dp-ax-b2.depth.1.bin.gz").read()
    d, cov = deviation(raw, W, H, ((0, 0), (131072, 0), (0, 131072)), (0.125, 0.1875, 0.125))
    dev = (d != 0) & cov
    vals, cnt = np.unique(d[cov], return_counts=True)
    xmin = {y: int(np.nonzero(dev[y])[0].min()) for y in range(H) if dev[y].any()}
    ys = np.array(sorted(xmin))
    c1, c0 = np.polyfit(ys, np.array([xmin[y] for y in ys]), 1)
    # covered pixels of the moved triangle (64, 32): x + 0.5 >= 64, y + 0.5 >= 32 on this target
    yy, xx = np.mgrid[0:H, 0:W]
    cov_shift = (xx + 0.5 >= 64) & (yy + 0.5 >= 32)
    ht = dev & cov_shift
    hv = np.zeros_like(dev)
    hv[32:, 64:] = dev[:H - 32, :W - 64]
    hv &= cov_shift
    PREDS.mkdir(exist_ok=True)
    for nm, a in (("ctl", dev), ("ht_shift", ht), ("hv_shift", hv)):      # deterministic bytes (an npz carries times)
        (PREDS / f"p-b2-set-{nm}.bits").write_bytes(np.packbits(a).tobytes())
    perrow = {t: int(dev[16 * t:16 * t + 16].sum()) for t in range(H // 16)}
    out = [("d-ctl", "dev_counts", ";".join(f"{int(v)}:{int(c)}" for v, c in zip(vals, cnt) if v), "E731", "control"),
           ("d-ctl", "dev_per_tile_row", ";".join(f"{t}:{c}" for t, c in perrow.items()), "E731", "control"),
           ("d-ctl", "xmin_line_c0_c1", f"{c0:.3f},{c1:.4f}", "fit on E731 dp-ax-b2 (FIT)", "control"),
           ("d-shift", "dev_pixels", str(int(ht.sum())), "HT (region fixed in target coordinates)", "heldout"),
           ("d-shift", "dev_pixels", str(int(hv.sum())), "HV (region moves (64, 32))", "heldout"),
           ("d-shift", "set_sha256", _sha(ht), "HT", "heldout"), ("d-shift", "set_sha256", _sha(hv), "HV", "heldout"),
           ("d-shift", "xmin_line_c0_c1", f"{c0:.3f},{c1:.4f}", "HT", "heldout"),
           ("d-shift", "xmin_line_c0_c1", f"{c0 + 64 - 32 * c1:.3f},{c1:.4f}", "HV", "heldout"),
           ("d-tall", "dev_per_tile_row", "t>=2: min(4096, 256+512*(t-2))", "HT: grows per tile row", "heldout"),
           ("d-tall", "dev_per_tile_row", "bounded by the triangle", "HV", "heldout"),
           ("d-tall", "dev_per_tile_row", "binade only", "HS", "heldout"),
           ("d-b3", "dev_pixels", f">= {int(dev.sum())} and max |ulps| >= 2", "HT/HS: more, larger", "heldout"),
           ("d-ygrad", "boundary", "x-growth stays (xmin falls with y)", "HT", "heldout"),
           ("d-ygrad", "boundary", "rotated with the gradient (y-growth)", "HV", "heldout")]
    return out


def _sha(a):
    import hashlib
    return hashlib.sha256(np.packbits(a).tobytes()).hexdigest()


if __name__ == "__main__":
    for r in ctl_model([]):
        print(r)
