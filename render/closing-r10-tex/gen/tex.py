# SPDX-License-Identifier: MIT
"""tex.py: the probe programs of r10-tex's stages t3b and srgb2 (r9-x's gen/tex.py, resgx545-data render/closing-r9-x). A case's spec (the p1141 form:
t0, t1, t3, u, v, base, ins and an optional inject {dword: value}) becomes USSE text through the
published builder (resgx545-data texture/p1141/support/build.py, pinned) in the published template
(texture/p1141/templates/tx_map.s, pinned), assembled by resgx545's usse-asm. tests/test_gen.py
checks that this path rebuilds E566's published s64x32-t3b14 and s64x32-ctl programs byte for byte.
pa0 = (y << 16) | x over the fill's 64 x 32 pixels (probe --coords)."""
import fractions
import os
import struct
import subprocess
import tempfile

import pins

W, H = 64, 32
TEMPLATE = "data:texture/p1141/templates/tx_map.s"
BUILD = "data:texture/p1141/support/build.py"
TEXMODEL = "data:texture/p1141/support/texmodel.py"
SPECS = "data:texture/p1141/support/specs.json"
ASM = os.path.join(pins.MAIN, "tools/usse-asm/usse-asm")
PROBE = "probe --temps 32 --coords --pixels"
F = fractions.Fraction


def text(spec):
    pre, setup, smp = pins.module(BUILD).case_inputs(spec)
    return (pins.blob(TEMPLATE).decode().replace("{PRE}", pre).replace("{SETUP}", setup)
            .replace("{SMP}", smp))


def assemble(src):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "p.bin")
        r = subprocess.run([ASM, "-l", "-o", out, "-"], input=src, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError("usse-asm: " + r.stderr.strip())
        return open(out, "rb").read()


def fbits(b):
    return struct.unpack("<f", struct.pack("<I", b))[0]


def coord(spec, x, y):
    """The exact value (a Fraction) of a ("lin", AXIS, K, C) coordinate at pixel (x, y): the
    program computes K * (1 + x / 64) + C (or y / 32), exact in float32 for the K and C used here
    (tests/test_gen.py checks every pixel)."""
    kind, ax, kb, cb = spec
    assert kind == "lin", spec
    r = 1 + (F(x, 64) if ax == "x" else F(y, 32))
    return r * F(fbits(kb)) + F(fbits(cb))


def exact_f32(q):
    return F(fbits(struct.unpack("<I", struct.pack("<f", float(q)))[0])) == q


def lin(ax, scale, offset):
    """("lin", ax, K, C) with value scale * (pixel index along ax) + offset: K = scale * 64 (x) or
    32 (y), C = offset - K."""
    k = F(scale) * (64 if ax == "x" else 32)
    c = F(offset) - k
    kb = struct.unpack("<I", struct.pack("<f", float(k)))[0]
    cb = struct.unpack("<I", struct.pack("<f", float(c)))[0]
    assert F(fbits(kb)) == k and F(fbits(cb)) == c, (ax, scale, offset)
    return ["lin", ax, kb, cb]


def strided(w, h, s, t0=0x000E0E00, t3=0xA0800000):
    """The T0 and T1 of a strided w x h texture with a stride of s dwords (T0 bits 11:9 the
    stride's low three bits, 26:17 the rest, minus one; T1 bits 23:12 width - 1, 11:0 height - 1,
    E566's encoding, as texmodel decodes it), the other T0 bits as given."""
    lo, hi = (s - 1) & 7, (s - 1) >> 3
    t0 = (t0 & ~(7 << 9) & ~(0x3FF << 17)) | lo << 9 | hi << 17
    return t0, 0xCC000000 | (w - 1) << 12 | (h - 1), t3
