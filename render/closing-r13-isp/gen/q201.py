# SPDX-License-Identifier: MIT
"""q201.py: stage q201 (round 13 plan closing13/plan/rank-round13.md section 2, Q201; E1018).

Byte 0 of the render command's word 16 (CR_ISP_MULTISAMPLECTL, `--cmd 16=0x000000NN`, bytes 1 to 3
0 as the library's 0x88) set to 0x3c, 0x0f, 0xf0 and 0x5a, each read by two iteration programs on
one 64 x 64 triangle that is not the tool's default (vertices on the 1/256 grid, `--tri-v`):
  src0  E437's primary PDS program (DOUTI word 0 0x20400000: source 0, two components, the pixel
        position; render/closing-r10-x/bins/pos.bin, E1010's), pa0 = x + sx, pa1 = y + sy pixels;
  cset  the same program with DOUTI word 0 0x20400800 (source 1, coordinate set 0, two
        components; render/closing-r7-geo/bins/p1138-it-a0__0.bin, E606's) and the vertex shader
        vtx_coords.bin (o4, o5 = the vertex's clip x and y, --vtx-coords 2), so pa0 and pa1 are the
        iterated clip x and y: (x + sx) / 32 - 1 and (y + sy) / 32 - 1 on 64 x 64.
Every row has --vtx-coords 2 and the vtxuse slot (the two programs differ only in the PDS file's
DOUTI word). A pixel shader writes one register as the colour (pix_pa0.bin x, pix_pa1.bin y), so
each (value, program) takes two jobs, x and y (E1010's -x / -y form).

Frozen per row (predictions/q201.tsv):
  coverage  sha256 of predictions/q201/NAME.coverage.txt: the drawn set at E1018's sample point
            (sample0_rule.covers, a byte copy of closing12/plan/c6-q201's frozen rule, the point
            (lo/16, hi/16) of the row's byte 0), every model alike (E1018 is HW for coverage)
  offset    the component's offset s (pixel + s is the value read), a fraction of a pixel, per
            model: H-SAMPLE0 (lo/16 for x, hi/16 for y, both programs), H-CENTRE (1/2), H-SWAP
            (hi/16 for x, lo/16 for y), H-SPLIT (src0 as H-SAMPLE0, cset 1/2)
Controls (can fail): 0x88 cset x and y (E606: the coordinate set at the centre), 0x26 src0 x and
y (E1010: x + 0.375, y + 0.125; E1018's point (6, 2)/16), and the 0x88 cset x replicate last.
Held out: everything else, 0x26 cset x and y (the bridge) included."""
from fractions import Fraction as F

STAGE = "q201"
W = H = 64
TRI = (1355, 947, 15386, 4582, 3738, 14899)      # 1/256 pixel: (5.29, 3.70) (60.10, 17.90) (14.60, 58.20)
VALUES = (0x3C, 0x0F, 0xF0, 0x5A)
MODELS = ("H-SAMPLE0", "H-CENTRE", "H-SWAP", "H-SPLIT")
PROG = {"src0": "pos.bin", "cset": "cset.bin"}
SHADER = {"x": "pix_pa0.bin", "y": "pix_pa1.bin"}
BG = 0xFF203040


def args(byte0, prog, comp):
    return ("probe --tri pixpds:12 --temps 32 --pixels --width 64 --height 64 --tri-v %s "
            "--vtx-coords 2 --cmd 16=0x%08x --slot vtxuse=\"$S/bins/vtx_coords.bin\" "
            "--slot pixel=\"$S/bins/%s\" \"$S/bins/%s\""
            % (",".join(map(str, TRI)), byte0, SHADER[comp], PROG[prog]))


def point(byte0):
    """E1018: (sx, sy) in pixels, x the low nibble"""
    return F(byte0 & 15, 16), F(byte0 >> 4, 16)


def offset(model, byte0, prog, comp):
    lo, hi = point(byte0)
    if model == "H-SAMPLE0" or (model == "H-SPLIT" and prog == "src0"):
        return lo if comp == "x" else hi
    if model in ("H-CENTRE", "H-SPLIT"):
        return F(1, 2)
    if model == "H-SWAP":
        return hi if comp == "x" else lo
    raise ValueError(model)


def coverage(byte0, tri=TRI, w=W, h=H):
    """the drawn set at E1018's point: sample0_rule.covers in 1/512 pixel"""
    import sample0_rule as S0
    lo, hi = byte0 & 15, byte0 >> 4
    v2 = [(2 * tri[2 * i], 2 * tri[2 * i + 1]) for i in range(3)]
    return [S0.covers(512 * x + 32 * lo, 512 * y + 32 * hi, v2) for y in range(h) for x in range(w)]


def cov_text(c, w=W):
    return "".join("".join("1" if v else "0" for v in c[y * w:(y + 1) * w]) + "\n"
                   for y in range(len(c) // w))


def name(byte0, prog, comp, tag=""):
    return "q201-%02x-%s-%s%s" % (byte0, prog, comp, tag)


def jobs():
    """[(name, set, knobs, args, byte0, prog, comp)] in run order"""
    out = []
    ctl = "reads:pixels"
    for b, p in ((0x88, "cset"), (0x26, "src0")):
        for c in ("x", "y"):
            out.append((name(b, p, c), "control", ctl, args(b, p, c), b, p, c))
    for c in ("x", "y"):
        out.append((name(0x26, "cset", c), "heldout", "-", args(0x26, "cset", c), 0x26, "cset", c))
    for b in VALUES:
        for p in ("src0", "cset"):
            for c in ("x", "y"):
                out.append((name(b, p, c), "heldout", "-", args(b, p, c), b, p, c))
    out.append((name(0x88, "cset", "x", "-end"), "control", ctl, args(0x88, "cset", "x"), 0x88,
                "cset", "x"))
    return out
