# SPDX-License-Identifier: MIT
"""fold/bilin_post.py KEPT_DIR: POST HOC (written after the run, on the kept images; no held-out
claim) decode of tw16's six bilinear rows. For each row and two footprint forms it prints the
pixels whose blend matches the kept read (each byte within 1, texmodel's blend, E561's tiles with a
tile row of W + 4096 texels, gen/tw16.py), split by edge (X = floor(W frac(u) - 1/2) = -1: left,
W - 1: right, else inside) and by whether u lies on the 1/4096 grid (m = floor(4096 frac(u))
exact) or between two of its steps (bl128right and bl128h16right step u by 1/8192 a pixel).
  F-FRAC  columns X mod W + m, X + 1 + m (E1049's post hoc form, frozen as tw16's hypothesis)
  UNWRAP  columns X + m, X + 1 + m: the left column not wrapped (a column -1 when m = 0 has no
          tile: counted as a miss)
E1049's two kept bilinear rows (render/closing-r15-tw) are decoded the same way for comparison."""
import gzip
import os
import re
import sys
from fractions import Fraction as F

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import tw16 as T  # noqa: E402

ROWS = ("bl64in", "bl64left", "bl128right", "bl128vedge", "bl16h16in", "bl128h16right")


def kept(d, n):
    t = gzip.decompress(open(os.path.join(d, n + ".txt.gz"), "rb").read()).decode()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()]
            for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", t, re.M)}
    return [v for y in sorted(rows) for v in rows[y]]


def taps(form, u, v, w, h):
    fx, fy = F(u) * w - F(1, 2), F(v) * h - F(1, 2)
    x0, y0 = T.fl(fx), T.fl(fy)
    kx, ky = int(64 * (fx - x0)), int(64 * (fy - y0))
    m, bx = T.mv(u), T.fl(w * (F(u) - T.fl(u)) - F(1, 2))
    cols = (bx % w + m, bx + 1 + m) if form == "F-FRAC" else (bx + m, bx + 1 + m)
    return [T.tile(c, r, w + 4096, min(h, 16)) for r in (y0 % h, (y0 + 1) % h) for c in cols], \
        kx, ky, bx


def match(t, kx, ky, got):
    if min(t) < 0:
        return False
    v = T.blend([T.name_of(i) for i in t], kx, ky)
    return all(abs((v >> 8 * k & 255) - (got >> 8 * k & 255)) <= 1 for k in range(4))


def decode(name, w, h, uv, px):
    print(name)
    for form in ("F-FRAC", "UNWRAP"):
        tally = {}
        for y in range(32):
            for x in range(64):
                u, v = uv(x, y)
                t, kx, ky, bx = taps(form, u, v, w, h)
                edge = "left" if bx == -1 else "right" if bx == w - 1 else "inside"
                grid = "on grid" if (4096 * (F(u) - T.fl(u))).denominator == 1 else "off grid"
                k = f"{edge}, {grid}"
                tally.setdefault(k, [0, 0])
                tally[k][0] += match(t, kx, ky, px[y * 64 + x])
                tally[k][1] += 1
        print("  %-7s" % form, "; ".join(f"{k} {a}/{b}" for k, (a, b) in sorted(tally.items())),
              "; total", sum(a for a, _ in tally.values()))


def main(d):
    for n in ROWS:
        _, _, w, h, *_ = T.row(n)
        decode(n, w, h, lambda x, y, n=n: T.uv(n, x, y), kept(d, n))
    t15 = T.tw15()
    for n in ("tw-bl32", "tw-bl16"):
        decode("E1049 " + n, t15.row(n)[2], 32, lambda x, y, n=n: t15.uv(n, x, y), T.kept15(n))


if __name__ == "__main__":
    main(sys.argv[1])
