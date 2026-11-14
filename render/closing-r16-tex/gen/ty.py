# SPDX-License-Identifier: MIT
"""ty.py: stage ty2 (r16-tex, Q177; closing16/plan/rank-round16.md section 2 "ty2", decision R16-7 a:
three more sizes, narrow): texture types 1, 3 and 4, E1055's type programs (E567's 16 x 16 rt1-2d,
ty3-2d and rt4-2d, rebuilt by gen/tex.py) at 8 x 8, 64 x 64 and 64 x 16, each mode 4 row right
after its mode 0 reference, every row at base 0 of a 32-page named scratch (dword i = 0xD0000000 | i).

E1055 (post hoc, render/closing-r15-tex/fold/types_post.py, held on both sizes it was fitted on, the
kept files pinned here): with u mode 4 every pixel is a named dword with each byte halved, rounded
up ((b + 1) >> 1), the 32 rows alike; the name is c + U with U = W + (x mod W) the unwrapped column
of E567's `map` u in [1, 2), c = 660 at 16 x 16 and 1300 - 32 at 32 x 32 for types 1 and 3, 644
and 1268 for type 4: two sizes give exactly, for types 1 and 3 (N13) and type 4 (N4),
    N13 = 39 W + 52 + (x mod W)      N4 = 40 W + 20 + (x mod W)
Modes 6 and 7 read mode 4's last column (W - 1) on every pixel; mode 5 one other halved name (163
at 16 x 16, type 1). Fitted before the freeze on the two kept sizes (tests/test_gen.py replays it
on all of E1055's kept rows: 10 of 10); every size here is held out.

Frozen models (per-pixel files predictions/ty/NAME.MODEL.txt; form and rel lines of ty.tsv):
  N13 / N4     the fit above (tested); NQ13 / NQ4  the other two-point form c0 + k W^2 through the same
               two sizes (types 1, 3: 468 + 13 W^2 / 16 + (x mod W): 520 at 8, 3796 at 64; type 4:
               500 and 3860, W^2 5 / 6 less 160 / 3840 steps): the rival
  N13-H        64 x 16 only: the N13 form in H (676 + (x mod W)), against the width (and max(W, H)
               = W here: they are not parted; README.md "Deviations" 3)
  L13          modes 6 and 7 (64 x 64): every pixel N13's name at column W - 1; rival LQ13 (NQ13's)
               and H-AS-U4, the mode 4 image (E1055: 0 of 6 at 16 x 16)
  H-AS-U4      modes 5: the mode 4 image of the row's size; H-FLAT: one value on every pixel, a
               halved name; H-HALF: names halved, rows alike; H-MODE0: the mode 0 image (rel)
  H-LIN1       H-HALF with the names c + U, one c for the row, U = W + (x mod W); H-WHOLE: names
  R-W, R-16, R-32 (types 1, 3), R-32, R-2W, R-W, R-16 (type 4): the mode 0 reference reads dword
               stride * (y mod H) + (x mod W) with the stride W (E1055: R-W at 16 x 16 and 32 x 32,
               types 1 and 3), the constant 16 or 32, or 2 W (type 4: R-32 held at both sizes)
Rows (all 32 pages; the control first; the pixels are 64 x 32):
  ty-ty1u4r      E1055's ty-ty1u4r rerun (r14-tex's addr5-ty1-u4), its kept image
  ty-SS-tyT-u0   type T at size SS (08 = 8 x 8, 64 = 64 x 64, 6416 = 64 x 16), mode 0: the reference
  ty-SS-tyT-u4   the same with u mode 4 (T0 bits 8:6), right after its reference
  ty-08-ty1-u5, ty-64-ty1-u5, -u6, -u7   type 1 mode 5 (8 x 8, 64 x 64) and modes 6 and 7 (64 x 64)"""
import json

import pins
import tex

PAGES = 32
LIMIT = PAGES * 1024
R14 = "data:render/closing-r14-tex/"
R14_OUT = R14 + "out/20261114-054258/addr5/%s.txt.gz"
R15 = "data:render/closing-r15-tex/"
R15_OUT = R15 + "out/20261114-073318/ty/%s.txt.gz"
CTL_BIN = R15 + "bins/ty-ty1u4r.bin"
CTL_KEPT = R15_OUT % "ty-ty1u4r"
TYPES = {1: "rt1-2d", 3: "ty3-2d", 4: "rt4-2d"}     # E567's cases (published specs.json)
FIT = {1: (39, 52), 3: (39, 52), 4: (40, 20)}      # N = a M + b + (x mod W), M the side
SIZES = {"08": (8, 8), "64": (64, 64), "6416": (64, 16)}
STRIDE_W = {1: "R-W", 3: "R-W", 4: "R-32"}         # the tested reference model of a type


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


def name_tokens(n_of_x):
    return ["%08x" % half(0xD0000000 | n_of_x(x)) for y in range(32) for x in range(64)]


def n_fit(ty, m, w, x):
    a, b = FIT[ty]
    return a * m + b + x % w


def n_quad(ty, m, w, x):
    """NQ: c0 + k m^2 through the 16 x 16 and 32 x 32 fits (k = 13 / 16, c0 = 468 on types 1 and
    3: 676 and 1300 less the column; k = 5 / 6, c0 = 660 - 640 / 3 on type 4: 660, 1300)."""
    if ty == 4:
        return 660 + (5 * (m * m - 256)) // 6 + x % w
    return 468 + 13 * m * m // 16 + x % w


def e567_spec(ty):
    return dict(json.loads(pins.blob(tex.SPECS))[TYPES[ty]]["spec"])


def spec(ty, umode, w, h):
    sp = e567_spec(ty)
    sp["t0"] = sp["t0"] & ~(7 << 6) | umode << 6
    sp["t1"] = sp["t1"] & ~0xFFFFFF | (w - 1) << 12 | (h - 1)
    sp["u"] = ["map", "x", w.bit_length() - 1, 0, 0x3F800000]
    sp["v"] = ["map", "y", h.bit_length() - 1, 0, 0x3F800000]
    return sp


def raster(stride, w, h):
    return ["%08x" % (0xD0000000 | (stride * (y % h) + x % w)) for y in range(32) for x in range(64)]


def forms(w):
    return {"H-HALF": f"half<{LIMIT}", "H-LIN1": f"lin1:map:{w}<{LIMIT}",
            "H-WHOLE": f"whole<{LIMIT}"}


def ref_models(ty, w, h):
    """{model: tokens} of a mode 0 reference, the tested model first."""
    strides = [("R-W", w), ("R-16", 16), ("R-32", 32), ("R-2W", 2 * w)]
    keep = ["R-W", "R-16", "R-32"] if ty != 4 else ["R-32", "R-2W", "R-W", "R-16"]
    d = dict(strides)
    return {m: raster(d[m], w, h) for m in keep}


def src(what):
    return f"E1055's fit, post hoc, held out at this size ({what}); E1055's kept rows, tests/test_gen.py"


def jobs():
    """[(name, set, spec or None, published bin pin or None, {model: tokens}, {model: (quantity,
    value)}, source)] in run order."""
    out = [("ty-ty1u4r", "control", None, CTL_BIN, {"H-E1055": ["%08x" % v for v in
                                                                 pins.kept_pixels(CTL_KEPT)]}, {},
            "E1055's ty-ty1u4r kept image (r15-tex), its program")]

    def ref(ty, sz):
        w, h = SIZES[sz]
        name = f"ty-{sz}-ty{ty}-u0"
        out.append((name, "heldout", spec(ty, 0, w, h), None, ref_models(ty, w, h), {},
                    f"E1055's references (raster of the width; type 4: 32) at {w} x {h} [infer]"))
        return name

    def mode4(ty, sz, rname):
        w, h = SIZES[sz]
        n = "N13" if ty != 4 else "N4"
        q = "NQ13" if ty != 4 else "NQ4"
        pix = {n: name_tokens(lambda x: n_fit(ty, w, w, x)),
               q: name_tokens(lambda x: n_quad(ty, w, w, x))}
        if sz == "6416":
            pix["N13-H"] = name_tokens(lambda x: n_fit(ty, h, w, x))
        rel = {k: ("form", v) for k, v in forms(w).items()}
        rel["H-MODE0"] = ("rel", f"{rname}+0")
        out.append((f"ty-{sz}-ty{ty}-u4", "heldout", spec(ty, 4, w, h), None, pix, rel,
                    src(f"{w} x {h}")))

    def other(sz, mode, rname):
        w, h = SIZES[sz]
        pix = {"H-AS-U4": name_tokens(lambda x: n_fit(1, w, w, x))}
        if mode in (6, 7):
            pix = {"L13": name_tokens(lambda x: n_fit(1, w, w, w - 1)),
                   "LQ13": name_tokens(lambda x: n_quad(1, w, w, w - 1)), **pix}
        rel = {"H-HALF": ("form", f"half<{LIMIT}"), "H-MODE0": ("rel", f"{rname}+0")}
        if mode == 5:
            rel["H-FLAT"] = ("form", f"flat<{LIMIT}")
        out.append((f"ty-{sz}-ty1-u{mode}", "heldout", spec(1, mode, w, h), None, pix, rel,
                    src(f"modes 5 to 7 at {w} x {h}")))

    for sz in ("08", "64"):
        for ty in (1, 4):
            r = ref(ty, sz)
            mode4(ty, sz, r)
            if ty == 1:
                other(sz, 5, r)
                if sz == "64":
                    other(sz, 6, r)
                    other(sz, 7, r)
    r = ref(1, "6416")
    mode4(1, "6416", r)
    return out
