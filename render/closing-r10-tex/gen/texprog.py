# SPDX-License-Identifier: MIT
"""texprog.py: the probe programs of r8-geo's texture stages (cube, addr) and the pixel values the
program computes, standard library only.

The program text is the p1141 template (resgx545-data texture/p1141/templates/tx_map.s, pinned)
filled as render/closing-r4-render4x/gen/cubegen.py fills it: three coordinates in r24, r25, r26
from the pixel's x or y or a constant, the four T words in r20 to r23, one sample into r10. A
coordinate spec is
  ("bits", B)          a constant, the float32 of bits B
  ("lin", "x", K, C)   K * (1 + x / 64) + C, K and C float32 bits (cubegen's form, byte for byte)
  ("lin", "y", K, C)   K * (1 + y / 32) + C
  ("p7", K, C)         K * (1 + p / 128) + C, p = x | (y & 1) << 6: 128 positions on two rows
Every K and C the session uses makes each product and sum exact in float32 (dyadic, few bits),
so the value is the exact rational one; tests/test_gen.py checks that for every pixel.
pa0 = (y << 16) | x for the fill's 64 x 32 pixels (probe --coords)."""
import fractions
import struct
import subprocess

W, H = 64, 32
F = fractions.Fraction


def fbits(b):
    return struct.unpack("<f", struct.pack("<I", b))[0]


def bits(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def axis_code(spec, dst):
    if spec[0] == "bits":
        return ["mov.skipinv %s, #0x%08x" % (dst, spec[1])]
    if spec[0] == "lin":
        _, ax, kb, cb = spec
        return ["and.skipinv r1, pa0, #0x3f" if ax == "x" else "shr.skipinv r1, pa0, #16",
                "shl.skipinv r1, r1, #%d" % (17 if ax == "x" else 18),
                "or.skipinv r1, r1, #0x3f800000",
                "mov.skipinv r2, #0x%08x" % kb, "mov.skipinv r3, #0x%08x" % cb,
                "fmad.skipinv %s, r1, r2, r3" % dst]
    if spec[0] == "p7":
        _, kb, cb = spec
        return ["and.skipinv r1, pa0, #0x3f", "shr.skipinv r2, pa0, #10",
                "and.skipinv r2, r2, #0x40", "or.skipinv r1, r1, r2",
                "shl.skipinv r1, r1, #16", "or.skipinv r1, r1, #0x3f800000",
                "mov.skipinv r2, #0x%08x" % kb, "mov.skipinv r3, #0x%08x" % cb,
                "fmad.skipinv %s, r1, r2, r3" % dst]
    raise ValueError(spec)


def setup_text(coords, twords):
    regs = ("r24", "r25", "r26")
    out = []
    for spec, r in zip(coords, regs):
        out += axis_code(spec, r)
    return "\n".join(out + ["mov r%d, #0x%08x" % (20 + i, w) for i, w in enumerate(twords)])


def program_text(template, coords, twords, smp):
    return (template.replace("{PRE}", "").replace("{SETUP}", setup_text(coords, twords))
            .replace("{SMP}", smp))


def assemble(asm, text, out):
    r = subprocess.run([asm, "-l", "-o", out, "-"], input=text, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("assembler: " + r.stderr.strip())
    with open(out, "rb") as f:
        return f.read()


def coord(spec, x, y):
    """The exact value (a Fraction) the program computes for pixel (x, y)."""
    if spec[0] == "bits":
        return F(fbits(spec[1]))
    if spec[0] == "lin":
        _, ax, kb, cb = spec
        r = 1 + (F(x, 64) if ax == "x" else F(y, 32))
        return r * F(fbits(kb)) + F(fbits(cb))
    if spec[0] == "p7":
        _, kb, cb = spec
        return (1 + F(x | (y & 1) << 6, 128)) * F(fbits(kb)) + F(fbits(cb))
    raise ValueError(spec)


def exact_f32(q):
    """Is the rational q a float32 value (so the program's rounding cannot move it)?"""
    return F(fbits(bits(float(q)))) == q


def pixels(text, width=W, height=H):
    """{(x, y): value} of a kept output's `row N: v v ...` lines (probe or tri form), or None when
    the rows are not all there."""
    import re
    out = {}
    for m in re.finditer(r"row (\d+): ([0-9a-fx ]+)$", text or "", re.M):
        y = int(m.group(1))
        for x, t in enumerate(m.group(2).split()):
            out[(x, y)] = int(t, 16)
    if len(out) != width * height:
        return None
    return out
