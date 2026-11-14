#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""derive.py: the builder's re-derivation of H-WIDE (decision R17-2 a) from the kept files alone,
before the freeze: E1049's two bilinear bit-14 rows (r15-tw tw14: tw-bl32, tw-bl16) and E1058's six
(r16-tw tw16), each read at the data commit session.toml pins, their coordinates from the
published generators (r16-tw gen/tw16.py, r15-tw gen/tw.py through it). POST HOC: these rows are
the fit set; tw17's rows are held out (no kept job ran their inputs).

For each kept bilinear pixel and each frozen bilinear form of gen/tw17.py it counts the pixels
whose blend matches the kept read within 1 a byte and exactly; at the pixels where H-WIDE's left
column wraps (x0 = -1) it counts how many are exact under H-WIDE (W' - 1) and under H-WIDE-G
(W - 1): the kept side of the LEFT-WRAP rule. On every kept bit-14 point row of both rounds it
counts where H-WIDE-PT and H-TWP name different dwords and how many pixels H-WIDE-PT gives.

  derive.py            print the tallies (debug/derive.out keeps a copy for the fold)
tests/test_gen.py asserts the numbers (16384 of 16384 for H-WIDE within 1)."""
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tw17 as T  # noqa: E402

KEPT15 = "data:render/closing-r15-tw/out/20261114-074356/tw14/"
BIL16 = ("bl64in", "bl64left", "bl128right", "bl128vedge", "bl16h16in", "bl128h16right")
BIL15 = ("tw-bl32", "tw-bl16")
PT16 = ("pt32h8", "pt128h8", "pt32h16", "pt128h16", "pt16h64u0", "pt16h64u1", "pt64h64u0",
        "pt64h64u1")
PT15 = ("tw16-u0", "tw16-u1", "tw64-u0", "tw64-u2", "tw128-u0", "tw128-u2")


def kept15(name):
    return T.pins.kept_pixels(KEPT15 + name + ".txt.gz")


def bil_rows():
    """[(label, W, H, uv(x, y), kept pixels)] of the eight kept bilinear bit-14 rows."""
    t16 = T.tw16()
    t15 = t16.tw15()
    out = [("E1058:" + n, t16.row(n)[2], t16.row(n)[3], lambda x, y, n=n: t16.uv(n, x, y),
            T.kept16(n)) for n in BIL16]
    out += [("E1049:" + n, t15.row(n)[2], 32, lambda x, y, n=n: t15.uv(n, x, y), kept15(n))
            for n in BIL15]
    return out


def pt_rows():
    t16 = T.tw16()
    t15 = t16.tw15()
    out = [("E1058:" + n, t16.row(n)[2], t16.row(n)[3], lambda x, y, n=n: t16.uv(n, x, y),
            T.kept16(n)) for n in PT16]
    out += [("E1049:" + n, t15.row(n)[2], 32, lambda x, y, n=n: t15.uv(n, x, y), kept15(n))
            for n in PT15]
    return out


def within(a, b, tol):
    return all(abs((a >> 8 * c & 255) - (b >> 8 * c & 255)) <= tol for c in range(4))


def bilinear():
    """{label: {form: [within-1 pixels, exact pixels]}, plus 'leftwrap': [n, WIDE exact, G
    exact]}."""
    res = {}
    for label, w, h, uvf, px in bil_rows():
        r = {m: [0, 0] for m in T.BIL}
        lw = [0, 0, 0]
        for i, (x, y) in enumerate(T.pixels()):
            u, v = uvf(x, y)
            got = px[i]
            vals = {m: T.bil_value(m, u, v, w, h) for m in T.BIL}
            for m, val in vals.items():
                r[m][0] += within(val, got, 1)
                r[m][1] += val == got
            if T.columns("H-WIDE", u, w)[3] < 0:
                lw[0] += 1
                lw[1] += vals["H-WIDE"] == got
                lw[2] += vals["H-WIDE-G"] == got
        r["leftwrap"] = lw
        res[label] = r
    return res


def point():
    """{label: (pixels where H-WIDE-PT and H-TWP part, H-WIDE-PT's exact pixels)}."""
    res = {}
    for label, w, h, uvf, px in pt_rows():
        d = hit = 0
        for i, (x, y) in enumerate(T.pixels()):
            u, v = uvf(x, y)
            a = T.point_index("H-WIDE-PT", u, v, w, h)
            d += a != T.point_index("H-TWP", u, v, w, h)
            hit += T.name_of(a) == px[i]
        res[label] = (d, hit)
    return res


def main():
    b = bilinear()
    tot = {m: [0, 0] for m in T.BIL}
    lw = [0, 0, 0]
    for label, r in b.items():
        print(label, "; ".join(f"{m} {r[m][0]}/2048 ({r[m][1]} exact)" for m in T.BIL),
              "; left wrap %d: H-WIDE exact %d, H-WIDE-G exact %d" % tuple(r["leftwrap"]))
        for m in T.BIL:
            tot[m][0] += r[m][0]
            tot[m][1] += r[m][1]
        lw = [a + c for a, c in zip(lw, r["leftwrap"])]
    print("TOTAL", "; ".join(f"{m} {a}/16384 ({e} exact)" for m, (a, e) in tot.items()))
    print("LEFT WRAP %d pixels: H-WIDE exact %d, H-WIDE-G exact %d" % tuple(lw))
    for label, (d, hit) in point().items():
        print(f"{label}: H-WIDE-PT vs H-TWP part on {d}; H-WIDE-PT {hit}/2048")


if __name__ == "__main__":
    main()
