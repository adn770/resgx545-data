# SPDX-License-Identifier: MIT
"""f1.py: stage f1 (r13-flag, Q078 T3 bit 14 on a twiddled texture; closing13/plan/rank-round13.md
section 2 "F1"; planned faults, user OK R13-3 a). E566's tx_map form on named memory (scratch dword
i reads 0xD0000000 | i, so every read names its dword), a twiddled 32 x 32 32-bit texture (T1
0x0C01F01F, type 0) at the scratch's first dword, the probe's default 16-page (64 KiB) scratch.

The texel index of the bit-clear read is E561's tile law (gen/law.py; it gives E566's kept tw32-ctl
2048 of 2048, tests/test_gen.py). E1003 (strided): bit 14 moves the read by m = floor(4096 clamp(u,
0, 1)) texels. Where the move lands on a twiddled texture is the question. Frozen per row:

  H-TWIDX     the plan's H-TWMOVE: the move added to the twiddled index (index(s, t) + m)
  H-TWX       the move added to the texel column before the tile law, unwrapped (index(s + m, t)):
              at m = 4096 the read is index + 65536 dwords, 256 KiB past the texture, a fault at
              the scratch's page + 0x40000 [infer: E566's fault read this way, post hoc]
  H-TWX-WRAP  the move added to the column, then the u address mode (wrap): index((s + m) % W, t)
  H-FAULTANY  the plan's rival: bit 14 faults any twiddled read
  H-E566      (pair A only) E566's kept outcome replicated: the job faults

Pair A (E566's own pair, programs rebuilt byte for byte from texture/p1141 specs.json): tw32-ctl
(the control, its kept image) and tw32-t3b14 at u in (1, 2) (m = 4096 on every pixel). H-TWIDX's
reads stay inside the 16 pages (index + 4096 < 5120 dwords), so it predicts no fault there, against
E566's kept fault: the replicate parts H-TWIDX from H-TWX / H-FAULTANY.
Pair B (held out, never run): u = x / 4096 (m = x, 0 to 63; every pixel's texel column 0), v on row
y's centre; its bit-clear reference reads index(0, y). The three move models read inside the
scratch (no fault) and part on every pixel with x > 0; H-FAULTANY faults.

Rows, in run order (the references first: a control before the rows it gates): f1-ref-a, f1-tw32,
f1-ref-b, f1-small. The two bit-14 rows are the stage's planned rows (expectfault, #limit 2); the
references are controls without expectfault (a fault there stops the stage)."""
import json
from fractions import Fraction as F

import law
import pins
import tex

STAGE = "f1"
B14 = 1 << 14
SPEC_A_CTL, SPEC_A_B14 = "tw32-ctl", "tw32-t3b14"
E566_CTL = "data:texture/p1132/tx-t3/tw32-ctl.txt.gz"
PUB_CTL = "data:texture/p1132-recomp/raw/tx-t3bits/bins/tx-t3bits__33.bin"
W = H = 32
PAGES = 16                    # the probe's default scratch (--scratch-pages not given)
TWX_PAGE = 0x40000            # H-TWX's fault page on pair A, from the scratch's address
MOVE_MODELS = ("H-TWIDX", "H-TWX", "H-TWX-WRAP")
U_SMALL = tex.lin("x", F(1, 4096), 0)          # u = x / 4096: the move is x texels
V_ROW = tex.lin("y", F(1, 32), F(1, 64))       # v = (y + 1/2) / 32: texel row y


def specs():
    return json.loads(pins.blob(tex.SPECS))


def spec_b(t3):
    s = specs()[SPEC_A_CTL]["spec"]
    return dict(base=0, ins="none", t0=s["t0"], t1=s["t1"], t3=t3, u=U_SMALL, v=V_ROW)


def texel_b(x, y):
    """(s, t, m) of pair B's pixel: the bit-clear texel and the move."""
    u, v = tex.coord(U_SMALL, x, y), tex.coord(V_ROW, x, y)
    return int((u * W).__floor__()), int((v * H).__floor__()), int((4096 * min(max(u, 0), 1)).__floor__())


def name(i):
    return 0xD0000000 | i


def image_b(model):
    out = []
    for y in range(tex.H):
        for x in range(tex.W):
            s, t, m = texel_b(x, y)
            s, t = s % W, t % H
            i = {"REF": law.index(s, t, W, H),
                 "H-TWIDX": law.index(s, t, W, H) + m,
                 "H-TWX": law.index(s + m, t, W, H),
                 "H-TWX-WRAP": law.index((s + m) % W, t, W, H)}[model]
            out.append(name(i))
    return out


def ref_a():
    """pair A's bit-clear image (the tile law; = E566's kept tw32-ctl, tests)."""
    s = specs()[SPEC_A_CTL]["spec"]
    out = []
    for y in range(tex.H):
        for x in range(tex.W):
            u = F(law.ev(s["u"], x, y))
            v = F(law.ev(s["v"], x, y))
            out.append(name(law.index(int((u * W).__floor__()) % W, int((v * H).__floor__()) % H, W, H)))
    return out


def models_a():
    """pair A's bit-14 predictions: {model: ("ok", image) or ("fault", page offset or None)}.
    Every pixel's u is in (1, 2), so m = 4096."""
    ref = ref_a()
    return {"H-TWIDX": ("ok", [name((v & 0x0FFFFFFF) + 4096) for v in ref]),
            "H-TWX": ("fault", TWX_PAGE),
            "H-TWX-WRAP": ("ok", ref),
            "H-FAULTANY": ("fault", None),
            "H-E566": ("fault", None)}


def models_b():
    out = {m: ("ok", image_b(m)) for m in MOVE_MODELS}
    out["H-FAULTANY"] = ("fault", None)
    return out


def reach(images):
    """The largest dword any image reads."""
    return max(v & 0x0FFFFFFF for im in images for v in im)


def jobs():
    """[(name, set, knobs, spec, {model: (end, image or page)}, pages)], run order."""
    S = specs()
    kept = pins.kept_pixels(E566_CTL)
    a_ctl, a_b14 = S[SPEC_A_CTL]["spec"], S[SPEC_A_B14]["spec"]
    assert a_b14 == dict(a_ctl, t3=a_ctl["t3"] | B14), "E566's pair differs in more than bit 14"
    b_ref = spec_b(a_ctl["t3"])
    return [
        ("f1-ref-a", "control", "reads:pixels", a_ctl, {"H-E566": ("ok", kept)}, PAGES),
        ("f1-tw32", "replicate", "expectfault", a_b14, models_a(), PAGES),
        ("f1-ref-b", "control", "reads:pixels", b_ref, {"H-E561": ("ok", image_b("REF"))}, PAGES),
        ("f1-small", "heldout", "expectfault", dict(b_ref, t3=b_ref["t3"] | B14), models_b(), PAGES),
    ]


def args(row):
    return f'probe --temps 32 --coords --pixels "$S/bins/{row}.bin"'
