#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/posthoc.py: r35-o0's post hoc readings (not frozen; E1143's fold). Usage:
python3 fold/posthoc.py out/ATT/o. Prints, per A' row at 128, the pixels that are not A'(x, y)
and what they read; per P row the leftover pixels against its group's A' (same pixel, another
pixel and its offset, alien)."""
import collections
import gzip
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import score as SC  # noqa: E402


def fl(b):
    return struct.unpack("<f", struct.pack("<I", b))[0]


def dec(v):
    return fl(v & 0xFFFF0000), fl((v & 0xFFFF) << 16)


def img(d, r):
    t = gzip.open(os.path.join(d, r["name"] + ".txt.gz")).read().decode()
    return SC.image(t, SC.opt(r, "--width"))


def main(d):
    tab = SC.K.table(KP, "o")
    imgs = {r["name"]: img(d, r) for r in tab if SC.role(r) in ("a", "k", "p")}
    for i, r in enumerate(tab):
        n = r["name"]
        if SC.role(r) == "a":
            w = SC.opt(r, "--width")
            bad = {p: v for p, v in SC.nonbg(imgs[n]).items() if v != SC.f_a(p[0], p[1], w)}
            print(f"A {n} ({w}): {len(bad)} pixels not A'(x, y)")
            for (x, y), v in sorted(bad.items(), key=lambda kv: (kv[0][1], kv[0][0]))[:40]:
                e = SC.f_a(x, y, w)
                print(f"  ({x},{y}) read {v:08x} {dec(v)} want {e:08x} {dec(e)} xor {v ^ e:08x}")
        elif SC.role(r) == "p" and r["set"] != "control":
            a = SC.a_row_of(tab, i)
            A, Pm = imgs[a["name"]], imgs[n]
            pos = {v: p for p, v in SC.nonbg(A).items()}
            nb = SC.nonbg(Pm)
            off = collections.Counter()
            alien = collections.Counter()
            for p, v in nb.items():
                if v in pos:
                    q = pos[v]
                    off[(q[0] - p[0], q[1] - p[1])] += 1
                else:
                    alien[v] += 1
            print(f"P {n} after {a['name']}: {len(nb)} pixels; offsets (source - pixel) "
                  f"{dict(off.most_common(8))}; other values {dict((f'{k:08x}', c) for k, c in alien.most_common(4))}")
            if nb:
                ys = sorted({p[1] for p in nb})
                xs = sorted({p[0] for p in nb})
                print(f"  x {xs[0]}..{xs[-1]}, y {ys[0]}..{ys[-1]}")


if __name__ == "__main__" and len(sys.argv) == 2:
    main(sys.argv[1])


def sources(d):
    """Per A' row at 128: each wrong pixel's value decoded as the pixel whose A' it is."""
    tab = SC.K.table(KP, "o")
    for r in tab:
        if SC.role(r) != "a" or SC.opt(r, "--width") != 128:
            continue
        im = img(d, r)
        inv = {SC.f_a(x, y, 128): (x, y) for y in range(128) for x in range(128)}
        tri = set(SC.nonbg(im))
        bad = {p: v for p, v in SC.nonbg(im).items() if v != SC.f_a(p[0], p[1], 128)}
        src = {p: inv.get(v) for p, v in bad.items()}
        print(f"SOURCES {r['name']}: {len(bad)} wrong; A' of another pixel "
              f"{sum(1 for q in src.values() if q)} (inside the triangle "
              f"{sum(1 for q in src.values() if q in tri)}); blocks "
              f"{sorted({(p[0] // 4 * 4, p[1] // 4 * 4) for p in bad})}; "
              + ", ".join(f"{p}<-{q}" for p, q in sorted(src.items())[:6]))


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "sources":
    sources(sys.argv[1])
