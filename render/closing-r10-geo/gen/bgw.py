# SPDX-License-Identifier: MIT
"""bgw.py: stage bgw (round 10 seeds plan section 7, S10-geo, Q066): finite values in words 9 and
11 to 14 of the layered background object, in r9-k1's s3 form (tool t9, `dbg:render_bg_layer=Y
dbg:render_bg_src=0x3e800000 expectdiff`, `tri --bg-layer --pixels --keep-going --dump-render $W
--kpoke-render 1:bg:N=V`; the 64 x 64 one-triangle render, the layer's source texel (x, y) at
pixel (x, y) under H-VM, E971).

What E973 read (r9-k1 s3): words 9 and 11 to 14 at 1.0 change nothing; at 0xffffffff (a NaN)
word 12 makes every v-texel 0, word 14 every u-texel 0, word 11 every u-texel 0 and v at 35
values; 9 and 13 change nothing. The object's words 9 and 11 to 14 are 0 as the kernel builds
it (r9-k1's kept c-tex dump), so 0 is the control and a plain factor (the seeds plan's H-SCALE,
the texel at w times the coordinate) is refuted by the control itself. Frozen per pixel (the
3034 background pixels of gen/bgmask.txt, gen/bgl_model.py's scoring: right at <= 1 % of the
predicted pixels wrong, wrong above 10 %):
  H-INERT   finite values change nothing: every pixel its own texel (E973's reading, held out on
            new values)
  H-SCALE0  the word scales one coordinate, 0 read as 1 (the only factor reading E973 leaves):
            word 12 v, words 11 and 14 u (E973's NaN reading; 11's v left unchanged), the texel
            floor(64 f c) with c = (p + 0.5) / 64, clamped to 0 .. 63 outside [0, 1) (E974); a
            pixel within 1/64 texel of an inner texel edge not predicted
Values: 0.25, 0.5, 1.5, -1.0 for words 11, 12, 14 (the plan's 0 is the control and its 2.0 puts
every pixel centre on a texel edge under H-SCALE0: 1.5 and 0.25 in their place); 2.0 and -1.0 for
words 9 and 13 (H-INERT only: no coordinate reading). Controls (can fail): the unpoked layer at
the start and at the end, identity texels at >= 3000 of 3034 (r9-k1's H-TEX)."""
import math
import os
import struct
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bgl_model as M  # noqa: E402

STAGE = "bgw"
KNOBS = "dbg:render_bg_layer=Y dbg:render_bg_src=0x3e800000 expectdiff"
CMD = "tri --bg-layer --pixels --keep-going --dump-render $W"
COORD = {11: "u", 12: "v", 14: "u"}
VALUES = {11: (0.25, 0.5, 1.5, -1.0), 12: (0.25, 0.5, 1.5, -1.0), 14: (0.25, 0.5, 1.5, -1.0),
          9: (2.0, -1.0), 13: (2.0, -1.0)}
ORDER = (12, 14, 11, 9, 13)
MODELS = ("H-INERT", "H-SCALE0")


def bits(f):
    return struct.unpack("<I", struct.pack("<f", f))[0]


def vname(f):
    return ("m" if f < 0 else "") + ("%g" % abs(f)).replace(".", "p")


def scaled_index(t):
    """The texel index of 64 f c (a Fraction): clamped outside [0, 64), None near an inner edge."""
    if t < 0:
        return 0
    if t >= 64:
        return 63
    f = math.floor(t)
    if (t - f < M.EDGE and f > 0) or (f + 1 - t < M.EDGE and f < 63):
        return None
    return f


def predict(model, word, value, mask):
    """{(x, y): (tx, ty)} of the predicted pixels."""
    out = {}
    for x, y in mask:
        tx, ty = x, y
        if model == "H-SCALE0" and word in COORD:
            f = Fraction(value) if value != 0 else Fraction(1)
            if COORD[word] == "u":
                tx = scaled_index(f * (2 * x + 1) / 2)
            else:
                ty = scaled_index(f * (2 * y + 1) / 2)
        if tx is not None and ty is not None:
            out[(x, y)] = (tx, ty)
    return out


def jobs():
    """[(name, set, knobs, args, word, value, {model: prediction})]"""
    mask = M.load_mask()
    ident = predict("H-INERT", None, None, mask)
    out = [("bgw-ctl", "control", KNOBS + " reads:job,diff,inplace,layer", CMD, None, None,
            {"H-INERT": ident})]
    for w in ORDER:
        for v in VALUES[w]:
            models = {m: predict(m, w, v, mask) for m in MODELS if m == "H-INERT" or w in COORD}
            out.append(("bgw-w%d-%s" % (w, vname(v)), "heldout", KNOBS,
                        "%s --kpoke-render 1:bg:%d=0x%08x" % (CMD, w, bits(v)), w, v, models))
    out.append(("bgw-ctl-end", "control", KNOBS + " reads:job,diff,inplace,layer", CMD, None, None,
                {"H-INERT": ident}))
    return out
