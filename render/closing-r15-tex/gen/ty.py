# SPDX-License-Identifier: MIT
"""ty.py: stage ty (r15-tex, Q177; closing15/plan/rank-round15.md section 2 "ty", decision R15-5 a:
one pass, narrow): texture types 1, 3 and 4 in u modes 4 to 7, E1039's type programs (E567's 16 x 16
rt1-2d, ty3-2d and rt4-2d, p1132 tx-types and tx-types-risky, rebuilt by gen/tex.py) at a new size
and in the other modes, every row at base 0 of a 32-page named scratch (dword i = 0xD0000000 | i).

E1039 (post hoc, render/closing-r14-tex/fold/types_post.py): with u mode 4 at 16 x 16 every pixel is a
named dword with each byte halved, rounded up ((b + 1) >> 1), the 32 rows alike. Fitted here before
the freeze (debug/fit_name16.py, README.md "Deviations" 4): the name is c + U on every pixel of all
three rows, U = floor(16 u) the unwrapped texel column (16 to 31: E567's `map` u lies in [1, 2)),
c = 660 for types 1 and 3, 644 for type 4 (and c - 256: the halves cannot part them).

Rows (all 32 pages; the controls first):
  ty-ctl        E1000's addr3-16x64-u4 (r14-tex's addr5-ctl program), its kept image
  ty-ty1u4r     E1039's addr5-ty1-u4 rerun (r14-tex's program), its kept image
  ty-16-tyT-uM  types 1 and 4 at 16 x 16, u mode 5, 6, 7 (E567's program, T0's u mode only)
  ty-16-ty1-n16 type 1 at 16 x 16, u mode 4, U = x - 24 (-24 to 39; v as E567's): H-NAME16
  ty-32-tyT-u0  types 1, 3, 4 at 32 x 32 (`map` u and v of 5 bits), mode 0: the reference
  ty-32-tyT-u4  the same with u mode 4
Frozen (form level, the name map has no size form yet; score.py `form` and `rel` lines):
  H-HALF    every pixel a name below 32768 with each byte halved, rounded up, and the 32 rows alike
            (E1039 post hoc; tested)
  H-LIN1    H-HALF with the name c + U, one c for the row (E1039's map, slope 1, held at 16 x 16)
  H-WHOLE   every pixel a name, unhalved (rival)
  H-MODE0   the row reads its mode 0 image (E1039's T-MODE0, a negative: E567's kept image at 16 x
            16, the reference row of this run at 32 x 32)
  H-AS-U4   (modes 5 to 7) E1039's kept u mode 4 image of the type, every pixel [infer: the
            twiddled type reads modes 4, 6 and 7 alike and mode 5 inside the texture as 4]
  NAME-U    (the n16 row) half(660 + U) on every pixel: E1039's map, linear in U (tested)
  NAME-WRAP (the n16 row) half(676 + (U mod 16)): the map of the fraction of u only
  R-W, R-16 (32 x 32 references, types 1 and 3) dword W t + s or 16 t + s: E567's 16 x 16 image
            (16 t + s) as a raster of the row's width or of 16 [infer]
  R-2W, R-32 (type 4) dword 2 W t + s or 32 t + s (E567: 32 t + s at 16 x 16)"""
import json

import pins
import tex

PAGES = 32
LIMIT = PAGES * 1024
E1000_BIN = "data:render/closing-r14-tex/bins/addr5-ctl.bin"
E1000_KEPT = "data:render/closing-r10-tex/out/20261113-102730/addr3/addr3-16x64-u4.txt.gz"
R14 = "data:render/closing-r14-tex/"
R14_OUT = R14 + "out/20261114-054258/addr5/%s.txt.gz"
TY1U4_BIN = R14 + "bins/addr5-ty1-u4.bin"
TYPES = {  # type: (E567's case, its kept mode 0 image)
    1: ("rt1-2d", "data:texture/p1132/tx-types-risky/rt1-2d.txt.gz"),
    3: ("ty3-2d", "data:texture/p1132/tx-types/ty3-2d.txt.gz"),
    4: ("rt4-2d", "data:texture/p1132/tx-types-risky/rt4-2d.txt.gz"),
}
NAME_C = {1: 660, 3: 660, 4: 644}        # E1039's map fitted before the freeze: n = c + U
N16_LO = -24                             # the n16 row: U = x - 24


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


def e567_spec(ty):
    return dict(json.loads(pins.blob(tex.SPECS))[TYPES[ty][0]]["spec"])


def spec(ty, umode, size=16, u=None):
    sp = e567_spec(ty)
    sp["t0"] = sp["t0"] & ~(7 << 6) | umode << 6
    if size != 16:
        a = size.bit_length() - 1
        sp["t1"] = sp["t1"] & ~0xFFFFFF | (size - 1) << 12 | (size - 1)
        sp["u"] = ["map", "x", a, 0, 0x3F800000]
        sp["v"] = ["map", "y", a, 0, 0x3F800000]
    if u is not None:
        sp["u"] = list(u)
    return sp


def n16_u():
    """u = (x - 24 + 1/2) / 16: U = x - 24 at the texel centres (tex.lin: exact in float32)."""
    return tex.lin("x", tex.F(1, 16), tex.F(2 * N16_LO + 1, 32))


def raster(stride, size):
    return ["%08x" % (0xD0000000 | (stride * y + (x % size))) for y in range(32) for x in range(64)]


def kept_tokens(pin):
    return ["%08x" % v for v in pins.kept_pixels(pin)]


def name_tokens(ty, rule):
    out = []
    for y in range(32):
        for x in range(64):
            U = x + N16_LO
            n = NAME_C[ty] + U if rule == "NAME-U" else NAME_C[ty] + 16 + U % 16
            out.append("%08x" % half(0xD0000000 | n))
    return out


def forms(width):
    return {"H-HALF": f"half<{LIMIT}", "H-LIN1": f"lin1:map:{width}<{LIMIT}",
            "H-WHOLE": f"whole<{LIMIT}"}


def jobs():
    """[(name, set, spec or None, published bin pin or None, {model: tokens}, {model: (quantity,
    value)}, source)] in run order."""
    out = [("ty-ctl", "control", None, E1000_BIN, {"H-E1000": kept_tokens(E1000_KEPT)}, {},
            "E1000's addr3-16x64-u4 kept image (r10-tex); r14-tex's addr5-ctl program"),
           ("ty-ty1u4r", "control", None, TY1U4_BIN,
            {"H-E1039": kept_tokens(R14_OUT % "addr5-ty1-u4")}, {},
            "E1039's addr5-ty1-u4 kept image (r14-tex), its program")]
    for ty in (1, 4):
        for m in (5, 6, 7):
            out.append((f"ty-16-ty{ty}-u{m}", "heldout", spec(ty, m), None,
                        {"H-MODE0": kept_tokens(TYPES[ty][1]),
                         "H-AS-U4": kept_tokens(R14_OUT % f"addr5-ty{ty}-u4")},
                        {k: ("form", v) for k, v in forms(16).items()},
                        "E1039's form (post hoc, types_post.py), E567's and E1039's kept images"))
    out.append(("ty-16-ty1-n16", "heldout", spec(1, 4, u=n16_u()), None,
                {k: name_tokens(1, k) for k in ("NAME-U", "NAME-WRAP")},
                {"H-HALF": ("form", f"half<{LIMIT}")},
                "E1039's name map fitted on addr5-ty1-u4 before the freeze (debug/fit_name16.py)"))
    for ty in (1, 3, 4):
        ref = f"ty-32-ty{ty}-u0"
        rs = (("R-W", 32), ("R-16", 16)) if ty != 4 else (("R-2W", 64), ("R-32", 32))
        out.append((ref, "heldout", spec(ty, 0, 32), None,
                    {m: raster(st, 32) for m, st in rs}, {},
                    "E567's 16 x 16 image as a raster [infer]"))
        rel = {k: ("form", v) for k, v in forms(32).items()}
        rel["H-MODE0"] = ("rel", f"{ref}+0")
        out.append((f"ty-32-ty{ty}-u4", "heldout", spec(ty, 4, 32), None, {}, rel,
                    "E1039's form (post hoc); H-MODE0 on this run's reference"))
    return out
