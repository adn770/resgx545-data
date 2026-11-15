#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/look.py: r23-pk's post hoc reads (not frozen; labelled post hoc in E1096 to E1098).

  python3 fold/look.py > fold/look.out

1. q181 and pk-e568: each fill's 2048 pixels against E037's conversion (E037's coefficients in
   128ths) of the 16 texels of the 16 x 1 YUV texture (gen_p1132's catalog.py yuv_words: pattern
   0 the ramp, pattern 1 random.Random(2800 + 1)), for the four byte orders of a texel pair, with
   pixel (x, y) read as texel x mod 16 (T0_REP's repeat); and the texel E568's declared model
   reads (its yuv() clamps x to 0..15: texel 15 at every pixel).
2. q181's copies: the hash of c-copy-none against c-copy-csc's, in run order.
3. q123 (offline fit over landed records): every step u, a multiple of 8 up to 16 MiB, against
   the ten links of E476 and E492 with link = (X mod u) / 8 + 2.
4. q019: how many changed scratch dwords each kept row counts beyond the 32 printed."""
import gzip
import os
import random
import re

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(KP, "out", "20261115-202948")


def text(stage, name):
    return gzip.open(os.path.join(A, stage, name + ".txt.gz")).read().decode()


def words(pat):
    if pat == 0:
        return [(0x20 + 0x18 * j) | (0x70 + 0x0B * j) << 8 | (0x40 + 0x1C * j) << 16 |
                (0x90 + 0x07 * j) << 24 for j in range(8)]
    rnd = random.Random(2800 + pat)
    return [rnd.getrandbits(32) for _ in range(8)]


def conv(yy, u, v):
    sat = lambda t: min(max(t, 0), 255)  # noqa: E731
    r = sat((149 * (yy - 16) + 204 * (v - 128)) >> 7)
    g = sat((149 * (yy - 16) - 50 * (u - 128) - 104 * (v - 128)) >> 7)
    b = sat((149 * (yy - 16) + 258 * (u - 128)) >> 7)
    return 0xFF000000 | r << 16 | g << 8 | b


ORDERS = {"Y0 U Y1 V (fmt 28)": (0, 2, 1, 3), "U Y0 V Y1 (fmt 29)": (1, 3, 0, 2),
          "Y0 V Y1 U": (0, 2, 3, 1), "V Y0 U Y1": (1, 3, 2, 0)}


def texels(pat, order):
    w, out = words(pat), []
    for x in range(16):
        b = [w[x // 2] >> (8 * k) & 255 for k in range(4)]
        out.append(conv(b[order[0] if x % 2 == 0 else order[1]], b[order[2]], b[order[3]]))
    return out


def pixels(t):
    return [[int(v, 16) for v in m[2].split()]
            for m in re.finditer(r"row (\d+): ([0-9a-f ]+)", t)]


print("## 1. YUV fills: pixels against E037's conversion, texel x mod 16")
for stage, name in [("pk", "pk-e568")] + [("q181", n) for n in (
        "fy-28-p0-csc", "fy-29-p0-csc", "fy-28-p0-nocsc", "fy-29-p0-nocsc", "fy-28-p1-csc",
        "fy-29-p1-csc")]:
    rows = pixels(text(stage, name))
    pat = 1 if "-p1-" in name else 0       # pk-e568 is fy-28-p0-csc
    flat = [(x, v) for r in rows for x, v in enumerate(r)]
    hits = {k: sum(v == texels(pat, o)[x % 16] for x, v in flat) for k, o in ORDERS.items()}
    fmt = ORDERS["Y0 U Y1 V (fmt 28)" if "-28-" in name or name == "pk-e568" else "U Y0 V Y1 (fmt 29)"]
    clamp = sum(v == texels(pat, fmt)[15] for _, v in flat)
    black = sum(v == 0xFF000000 for _, v in flat)
    print(f"{name}: {len(flat)} pixels; " + ", ".join(f"{k} {h}" for k, h in hits.items()) +
          f"; E568's declared texel (15 at every pixel) {clamp}; black {black}")

print("\n## 2. q181 copies, in run order")
for n in ("c-copy-csc", "c-copy-none"):
    h = re.search(r"^target: \S+ hash (0x[0-9a-f]+)$", text("q181", n), re.M)[1]
    print(f"{n}: {h}")

print("\n## 3. steps fitting E476's and E492's ten links")
pts = {0x10000: 0x2002, 0x100000: 0x2, 0x1ff000: 0xfe02, 0x200000: 0x2, 0x400000: 0x2,
       0x2ff000: 0xfe02, 0x1a0000: 0x4002, 0x3a8000: 0x5002, 0x4ff000: 0xfe02, 0x300008: 0x3}
fit = [u for u in range(8, 0x1000001, 8) if all((x % u) // 8 + 2 == lk for x, lk in pts.items())]
print(f"{len(fit)} of {0x1000000 // 8} steps fit all ten: " + ", ".join(hex(u) for u in fit))

print("\n## 4. q019: changed scratch dwords not printed")
more = {}
for f in sorted(os.listdir(os.path.join(A, "q019"))):
    if re.match(r"q019-.*\.txt\.gz$", f):
        m = re.search(r"scratch (\d+) more changed", gzip.open(os.path.join(A, "q019", f)).read()
                      .decode())
        more[m[1] if m else "none"] = more.get(m[1] if m else "none", 0) + 1
print("rows by `scratch N more changed`: " + ", ".join(f"{k}: {v}" for k, v in sorted(more.items())))
