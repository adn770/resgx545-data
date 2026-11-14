# SPDX-License-Identifier: MIT
"""fold/rust_rows.py [after the run]: every row of g14 and clipr as sgx-pipe isp.rs's GUARD_R14
rows (the target, the viewport (offset and scale per axis, 1/256 pixel), the vertices as the tool
submitted them rounded to 1/256 by E607 and E943 (half away from zero), the kept drawn count and
FNV-1a 64 of the kept image as '1'/'0' bytes in raster order), and the check that the guard a
quarter of the viewport past each edge, with the clip-made vertex rounded half away from zero
(the rule held: CLIP-HA 3 of 3), draws each kept image pixel for pixel.
  python3 -B fold/rust_rows.py > fold/rust_rows.out"""
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

A = os.path.join(KP, "out/20261114-060059")


def fnv(bits):
    h = 0xcbf29ce484222325
    for b in bits:
        h ^= ord("1") if b else ord("0")
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


def vp_of(args, W, H):
    vp = list(G.default_vp(W, H))
    a = args.split()
    for i, t in enumerate(a):
        if t == "--poke" and a[i + 1].startswith(("blk:6=", "blk:7=", "blk:8=", "blk:9=")):
            n, v = a[i + 1][4:].split("=")
            vp[int(n) - 6] = G.F(G.struct.unpack("<f", G.struct.pack("<I", int(v, 0)))[0])
    return tuple(vp)


ok = n = 0
for st in ("g14", "clipr"):
    for r in K.table(KP, st):
        a = r["args"].split()
        W, H = int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])
        unit = int(a[a.index("--tri-unit") + 1])
        vt = [int(t) for t in a[a.index("--tri-v") + 1].split(",")]
        vp = vp_of(r["args"], W, H)
        got = [p == SC.GREEN for p in SC.pixels(K.text(os.path.join(A, st), r["name"] + ".txt"), W * H)]
        V = G.variants(vt, unit, W, H, vp, "E607")[0]
        img = G.image(V, G.boxes(W, H, vp)["H-VP"], W, H, "HA")
        n += 1
        ok += img == got
        vpu = [int(c * 256) for c in vp]
        print('        ("%s", %d, %d, [%s], [%s], %d, 0x%016x),%s' % (
            r["name"], W, H, ", ".join(map(str, vpu)), ", ".join("%d" % c for p in V for c in p), sum(got), fnv(got),
            "" if img == got else "  // MISSES"))
print("H-VP with the clip vertex half away from zero draws %d of %d kept rows pixel for pixel" % (ok, n))
