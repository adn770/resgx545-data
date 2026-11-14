# SPDX-License-Identifier: MIT
"""fold/bilin_forms.py KEPT_DIR: post hoc (after the run) candidate footprints for tw14's two
bilinear rows: each form names the left and right tap columns (taps on texel rows y and y + 1, E561's
tiles with a tile row of W + 4096 texels, kx = x, ky = 16, texmodel's blend, each byte within 1);
prints each form's pixels by region (u below or past the integer, t below or from 16)."""
import gzip
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import tw  # noqa: E402


def kept(d, n):
    t = gzip.decompress(open(os.path.join(d, n + ".txt.gz"), "rb").read()).decode()
    rows = {int(m.group(1)): [int(v, 16) for v in m.group(2).split()]
            for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", t, re.M)}
    return [v for y in sorted(rows) for v in rows[y]]


def m_of(q):
    """floor(4096 frac(q))."""
    return tw.fl(4096 * (q - tw.fl(q)))


def forms(u, w):
    fx = u * w - tw.F(1, 2)
    x0 = tw.fl(fx)
    a, b = x0 % w, (x0 + 1) % w
    m = m_of(u)
    mL, mR = m_of(tw.F(2 * a + 1, 2 * w)), m_of(tw.F(2 * (x0 + 1) + 1, 2 * w))
    ul = tw.F(2 * x0 + 1, 2 * w)            # the left tap's centre, unwrapped
    ur = tw.F(2 * x0 + 3, 2 * w)
    return {
        "TW (wrap, sample m)": (a + m, b + m),
        "SHIFT (a+1, sample m)": (a + m, a + 1 + m),
        "TAP (own wrapped centre)": (a + mL, b + m_of(tw.F(2 * b + 1, 2 * w))),
        "TAPU (own unwrapped centre, a and b)": (a + m_of(ul), b + m_of(ur)),
        "TAPU-SHIFT": (a + m_of(ul), a + 1 + m_of(ur)),
        "WIDE (x0, x0 + 1 in W + 4096)": None,
        "H-FOOT-FR (X = floor(W frac(u) - 1/2): X mod W, X + 1)": (
            tw.fl(w * (u - tw.fl(u)) - tw.F(1, 2)) % w + m,
            tw.fl(w * (u - tw.fl(u)) - tw.F(1, 2)) + 1 + m),
        "LEFT m from left centre, right SHIFT": (a + m_of(ul), a + 1 + m_of(ul)),
        "m from floor(4096 frac(u)) of x0's texel, both": (a + m_of(ul), b + m_of(ul)),
    }


def idx(c, t, w):
    return tw.tl(c, t, w + 4096)


def main(d):
    for n in ("tw-bl32", "tw-bl16"):
        w = tw.row(n)[2]
        px = kept(d, n)
        tally = {}
        for y in range(32):
            for x in range(64):
                u, _ = tw.uv(n, x, y)
                reg = ("u past" if u >= tw.fl(tw.uv(n, 63, 0)[0]) else "u below") + (
                    ", t>=16" if y >= 16 else ", t<16")
                for name, cols in forms(u, w).items():
                    if cols is None:
                        continue
                    cl, cr = cols
                    t = [idx(cl, y, w), idx(cr, y, w), idx(cl, (y + 1) % 32, w),
                         idx(cr, (y + 1) % 32, w)]
                    v = tw.blend([tw.name_of(i) for i in t], x, 16)
                    ok = all(abs((v >> 8 * k & 255) - (px[y * 64 + x] >> 8 * k & 255)) <= 1
                             for k in range(4))
                    tally.setdefault(name, {}).setdefault(reg, [0, 0])
                    tally[name][reg][0] += ok
                    tally[name][reg][1] += 1
        print(n)
        for name, regs in tally.items():
            print("  %-48s" % name, "; ".join(f"{r} {a}/{b}" for r, (a, b) in sorted(regs.items())))


if __name__ == "__main__":
    main(sys.argv[1])
