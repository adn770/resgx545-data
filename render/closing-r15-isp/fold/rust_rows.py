# SPDX-License-Identifier: MIT
"""fold/rust_rows.py [after the run]: every depth row of zcut as sgx-pipe isp.rs's CUT_R15 rows (the
target, the vertices in 1/256 pixel as the tool submitted them rounded by E607 and E943, the three
vertex depths as the tool takes them, the kept drawn count and FNV-1a 64 of the kept image as
'1'/'0' bytes in raster order), and the check that H-POLYCLIP (gen/zcut.py) draws each kept image
pixel for pixel.   python3 -B fold/rust_rows.py > fold/rust_rows.out"""
import gzip
import os
import sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("gen", "kit", "score"):
    sys.path.insert(0, os.path.join(KP, d))
sys.dont_write_bytecode = True
import guard as G  # noqa: E402
import kitscore as K  # noqa: E402
import score as SC  # noqa: E402
import zcut as Z  # noqa: E402

A = os.path.join(KP, "out/20261114-073059/zcut")


def fnv(bits):
    h = 0xcbf29ce484222325
    for b in bits:
        h ^= ord("1") if b else ord("0")
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


ok = n = 0
for r in K.table(KP, "zcut"):
    a = r["args"].split()
    if "--tri-v" not in a:
        continue
    vt = [int(t) for t in a[a.index("--tri-v") + 1].split(",")]
    zt = a[a.index("--tri-z") + 1]
    got = [p == SC.GREEN for p in SC.pixels(K.text(A, r["name"] + ".txt"), Z.W, Z.H)]
    V = G.variants(vt, 8, Z.W, Z.H, Z.VP)[0]
    img = Z.model_of(vt, [float(t) for t in zt.split(",")], "H-POLYCLIP")["drawn"]
    n += 1
    ok += img == got
    print('("%s", [%s], [%s], %d, 0x%016x),' % (r["name"], ", ".join("%d, %d" % v for v in V), zt, sum(got), fnv(got)))
print("H-POLYCLIP draws %d of %d kept images pixel for pixel" % (ok, n), file=sys.stderr)
