#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""out/fold/tx5_read.py (added at the fold, 2026-11-13; POST HOC): stage tx5's explore rows. Each image
against the same-size format-12 point-filter image (the 8 x 8 and 16 x 16 controls), and for the
format 9 row a scan of 'the pixel is 0x0000ffff iff bit B of 16-bit word floor(t / K) of the tag
fill is set' (K 1 to 64, B 0 to 15, words little endian: word 2i = i & 0xffff, 2i + 1 = 0xD000)
and of the same over dwords (B 0 to 31). Reads only the kept files.
  python3 out/fold/tx5_read.py ATT_DIR"""
import os
import sys
sys.dont_write_bytecode = True
KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "score"))
import score as S  # noqa: E402
T, K = S.T, S.K


def img(d, n):
    return T.probe_rows(K.text(d, n + ".txt"))


def fits(im, w, unit):
    out = []
    for k in range(1, 65):
        for b in range(32 if unit == 32 else 16):
            ok = True
            for y in range(32):
                for x in range(64):
                    t = (y % w) * w + (x % w)
                    i = t // k
                    word = (0xD0000000 | i) if unit == 32 else ((i // 2) & 0xFFFF if i % 2 == 0 else 0xD000)
                    if (im[y * 64 + x] == 0xFFFF) != bool(word >> b & 1):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                out.append((k, b))
    return out


def main(att):
    d = os.path.join(att, "tx5")
    ref = {8: img(d, "tx5-ctl-8x8"), 16: img(d, "tx5-ctl-16x16")}
    for n, w in (("tx5-x-fmt9-16x16", 16), ("tx5-x-fmt18-16x16", 16), ("tx5-x-bil-16x16", 16), ("tx5-x-bil-8x8", 8)):
        im = img(d, n)
        print("%s: %s the format-12 point-filter %d x %d control's image; lit %d of 2048" % (
            n, "equals" if im == ref[w] else "differs from", w, w, sum(p == 0xFFFF for p in im)))
    im = img(d, "tx5-x-fmt9-16x16")
    print("format 9: 16-bit word fits (K, B):", fits(im, 16, 16))
    print("format 9: dword fits (K, B):", fits(im, 16, 32))


if __name__ == "__main__":
    main(sys.argv[1])
