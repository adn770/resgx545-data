#!/usr/bin/env python3
"""cubegen.py: the cube-map probe programs of stage c (Q113's held-out row) and the face rule they test.

The program text is the p1141 template (resgx545-data texture/p1141 templates/tx_map.s) filled the way gen/build.py of that
session fills it (`axis_code`: a coordinate from the pixel's x or y, or a constant; the three coordinates go to r24, r25, r26,
the four state words of the TEXTYPE 2 texture to r20 to r23, then one smp3d).  tests/test_gen.py rebuilds E726's six axis cases
with this code and compares the text and the assembled bytes with the published ones: the builder is faithful or the test fails.

THE RULE UNDER TEST [infer, post hoc from E726's 8 jobs]: a pixel reads the face of the coordinate of largest magnitude, and its
sign: face = 2 * axis + (coordinate < 0) with axis 0, 1, 2 = u, v, w: +x, -x, +y, -y, +z, -z are faces 0 to 5; a face is 256
consecutive dwords of the scratch buffer, so a pixel's value 0xD0000000 | index names its face as index // 256.
"""
import hashlib
import struct
import subprocess

import numpy as np

W, H = 64, 32
T_WORDS = ("mov r20, #0x07fe0000", "mov r21, #0x4c00f00f", "mov r22, #0x5caf0000", "mov r23, #0x00800800")
SMP = "smp3d r10, r24, r20, drc0"


def fbits(b):
    return struct.unpack("<f", struct.pack("<I", b))[0]


def axis_code(spec, dst):
    """spec: ("bits", B) | ("lin", "x" | "y", K, C): the lines of p1141's build.py for the two kinds the cube cases use."""
    if spec[0] == "bits":
        return ["mov.skipinv %s, #0x%08x" % (dst, spec[1])]
    _, ax, kb, cb = spec
    return ["and.skipinv r1, pa0, #0x3f" if ax == "x" else "shr.skipinv r1, pa0, #16",
            "shl.skipinv r1, r1, #%d" % (17 if ax == "x" else 18), "or.skipinv r1, r1, #0x3f800000",
            "mov.skipinv r2, #0x%08x" % kb, "mov.skipinv r3, #0x%08x" % cb, "fmad.skipinv %s, r1, r2, r3" % dst]


def setup_text(u, v, w):
    return "\n".join(axis_code(u, "r24") + axis_code(v, "r25") + axis_code(w, "r26") + list(T_WORDS))


def program_text(template, u, v, w):
    return template.replace("{PRE}", "").replace("{SETUP}", setup_text(u, v, w)).replace("{SMP}", SMP)


def assemble(asm, text, out):
    r = subprocess.run([asm, "-l", "-o", out, "-"], input=text, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("assembler: " + r.stderr.strip())
    return open(out, "rb").read()


def coords(u, v, w):
    """The three coordinates of the 2048 pixels (raster order) in float32, as the program computes them (all products exact:
    the pixel fractions are dyadic)."""
    x = np.tile(np.arange(W), H).astype(np.float64)
    y = np.repeat(np.arange(H), W).astype(np.float64)
    out = []
    for s in (u, v, w):
        if s[0] == "bits":
            out.append(np.full(W * H, fbits(s[1]), np.float32))
        elif s[0] == "lin":
            r = 1.0 + (x / 64 if s[1] == "x" else y / 32)
            out.append((r * np.float32(fbits(s[2])) + np.float32(fbits(s[3]))).astype(np.float32))
        else:                       # ("map_x16", W_CONST) of cu-w02 / cu-w11's u: 1 + (2 * (x & 15) + 1) / 32
            out.append((1.0 + (2 * (x.astype(int) & 15) + 1) / 32).astype(np.float32))
    return out


def faces(u, v, w):
    """The rule: the face of each pixel, and the gap between the two largest magnitudes (the margin of the call)."""
    c = coords(u, v, w)
    a = np.stack([np.abs(t) for t in c])
    s = np.stack(c)
    ax = a.argmax(0)
    srt = np.sort(a, 0)
    sg = np.take_along_axis(s, ax[None], 0)[0]
    return (ax * 2 + (sg < 0)).astype(int), (srt[2] - srt[1])


def hist(f):
    return [int((f == i).sum()) for i in range(6)]


def faces_sha256(f):
    return hashlib.sha256("".join(str(int(x)) for x in f).encode()).hexdigest()


def observed(text):
    """The faces of the 2048 pixels of a kept probe output ('row Y: v v v ...' lines), or None; -1 for a value that is no read."""
    vals = []
    import re
    for m in re.finditer(r"row (\d+): ([0-9a-f ]+)$", text or "", re.M):
        vals += [int(t, 16) for t in m.group(2).split()]
    if len(vals) != W * H:
        return None
    return np.array([((v & 0x00ffffff) // 256) if (v >> 24) == 0xD0 and (v & 0x00ffffff) < 6 * 256 else -1 for v in vals])


# E726's eight jobs as specs (the fit set): u, v, w
ONE = ("bits", 0x3f800000)
NEG = ("bits", 0xbf800000)
RX = ("lin", "x", 0x3fc00000, 0xc0100000)
RY = ("lin", "y", 0x3fc00000, 0xc0100000)
E726 = {
    "cu-zp": (RX, RY, ONE), "cu-xp": (ONE, RX, RY), "cu-yp": (RX, ONE, RY),
    "cu-zn": (RX, RY, NEG), "cu-xn": (NEG, RX, RY), "cu-yn": (RX, NEG, RY),
}
E726_BIN = {"cu-zp": 0, "cu-xp": 1, "cu-yp": 2, "cu-zn": 3, "cu-xn": 4, "cu-yn": 5, "cu-w02": 6, "cu-w11": 7}
W02 = (("map_x16", 0), ("bits", 0x3f080000), ("lin", "y", 0x40000000, 0xc0000000))
W11 = (("map_x16", 0), ("bits", 0x3f080000), ("lin", "y", 0x40000000, 0xc0400000))

# the two held-out jobs (stage c).  Both are off-axis in every pixel: all three coordinates are non-zero, one is a constant, two
# ramp with different slopes or offsets, the dominant axis changes inside the image, and no pixel is within 0.0078 of a tie
# (tests/test_gen.py asserts it: the hardware's compare cannot be on the wrong side of a margin that large in float32).
CA = (("lin", "x", 0x3fc00000, 0xc0200000),      # u: x ramp 1.5 (1 + x / 64) - 2.5   -0.75 .. +0.73
      ("bits", 0xbf000000),                       # v: constant -0.5
      ("lin", "y", 0x3fc00000, 0xc0100000))       # w: y ramp 1.5 (1 + y / 32) - 2.25  -0.75 .. +0.70
CB = (("bits", 0x3f000000),                       # u: constant +0.5
      ("lin", "x", 0x3fc00000, 0xc0100000),       # v: x ramp 1.5 (1 + x / 64) - 2.25  -0.75 .. +0.73
      ("lin", "y", 0x3fc00000, 0xc0200000))       # w: y ramp 1.5 (1 + y / 32) - 2.5   -1.0 .. +0.45
HELDOUT = {"r4g-cube-a": CA, "r4g-cube-b": CB}
