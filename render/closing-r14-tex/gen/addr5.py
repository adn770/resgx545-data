# SPDX-License-Identifier: MIT
"""addr5.py: stage addr5 (r14-tex, Q177; closing14/plan/rank-round14.md section 2 "addr5"):
r13-tex's gen/addr.py (resgx545-data render/closing-r13-tex/gen/addr.py, copied unchanged) at six
new shapes in its uv5 form, and texture types 1, 3 and 4 in u mode 4 against their mode 0
references. Standard library only.

Corner rows (u and v both mode 5, swept past both ends: every region holds pixels; twiddled,
32-bit, at page 12 of a 32-page named scratch, T2 0x5CAFC000): 8 x 8, 32 x 32, 128 x 32,
32 x 128, 128 x 128, 256 x 32. The corners (s and t both outside) read c + 0 (above left),
1 (above right), 2 (below left), 3 (below right) dwords past the base; frozen bases:
  C-LOG4     c = 4 log2 max(W, H)        (E1026's post hoc form, 4 of 4 kept shapes)
  C-SAT24    c = min(4 log2 M, 24)
  C-FLOOR16  c = max(16, 4 log2 M)
  CO-WH2, CO-12M4, CO-12W4  E1026's failed forms ((W + H) / 2, 12 + M / 4, 12 + W / 4)
The other regions, as r13-tex froze them (IN / LR / AB with M, W or H; E1026 held M on two
shapes): held out again at the six shapes.

Type rows (E567's 16 x 16 programs, texture/p1132 tx-types and tx-types-risky, rebuilt byte for
byte by gen/tex.py: base 0, `map` coordinates, the texture read once): the mode 0 reference of
each type (a replicate of E567's rt1-2d, ty3-2d and rt4-2d, its kept image as H-E567) and the same
program with T0's u mode 4 (`--scratch-pages 32`). Frozen, scored against the reference's image
of this run (score.py `rel` quantity):
  T-MODE0    the mode 4 image equals the reference's (read as mode 0, as type 6 does: E565's
             bd-st rows, E1026)
  T-OFFSET   every pixel reads the reference's dword plus 8 max(W, H) + 52 = 180 (E1000's offset
             past the type's own index) [infer: the type's index is what its mode 0 reads]"""
import json
import math

import addr as A
import forms5 as F5
import pins
import tex
import texprog as T

STAGE = "addr5"
E1000_BIN = "data:render/closing-r10-tex/bins/addr3-16x64-u4.bin"
E1000_KEPT = "data:render/closing-r10-tex/out/20261113-102730/addr3/addr3-16x64-u4.txt.gz"
BDUV5_BIN = "data:texture/p1132-recomp/raw/tx-border/bins/tx-border__17.bin"
BDUV5_KEPT = "data:texture/p1132/tx-border/bd-uv5.txt.gz"
TYPES = {  # type: (E567's case, its published program, its kept image)
    1: ("rt1-2d", "data:texture/p1132-recomp/raw/tx-types-risky/bins/tx-types-risky__0.bin",
        "data:texture/p1132/tx-types-risky/rt1-2d.txt.gz"),
    3: ("ty3-2d", "data:texture/p1132-recomp/raw/tx-types/bins/tx-types__10.bin",
        "data:texture/p1132/tx-types/ty3-2d.txt.gz"),
    4: ("rt4-2d", "data:texture/p1132-recomp/raw/tx-types-risky/bins/tx-types-risky__6.bin",
        "data:texture/p1132/tx-types-risky/rt4-2d.txt.gz"),
}
TYPE_OFFSET = 8 * 16 + 52
TYPE_PAGES = 32

FORMS = F5.FORMS
CORNER = ("C-LOG4", "C-SAT24", "C-FLOOR16", "CO-WH2", "CO-12M4", "CO-12W4")
REGION = tuple(f"{r}-{m}" for r in ("IN", "LR", "AB") for m in ("M", "W", "H"))
MODELS = REGION + CORNER
# run order: the 256-wide row last (the only side above 128 the laptop has not read)
SHAPES = ((8, 8), (32, 32), (128, 32), (32, 128), (128, 128))
LAST = ((256, 32),)


def base_c(model, w, h):
    m = max(w, h)
    l4 = 4 * int(math.log2(m))
    assert 2 ** int(math.log2(m)) == m
    return {"C-LOG4": l4, "C-SAT24": min(l4, 24), "C-FLOOR16": max(16, l4),
            "CO-WH2": (w + h) // 2, "CO-12M4": 12 + m // 4, "CO-12W4": 12 + w // 4}[model]


def job(w, h):
    return (f"addr5-{w}x{h}-uv5", "heldout", w, h, 5, 5, "uv5", A.FMT32)


def predict(j, model, x, y):
    if model in CORNER:
        _, _, w, h = j[:4]
        s, t = A.texel(w, h, "uv5", x, y)
        if 0 <= s < w or 0 <= t < h:
            return None
        return base_c(model, w, h) + (0 if t < 0 else 2) + (0 if s < 0 else 1)
    return A.predict(j, model, x, y)


def image(j, model):
    out = []
    for y in range(T.H):
        for x in range(T.W):
            i = predict(j, model, x, y)
            out.append(None if i is None else A.value(j[7], i))
    return out


def farthest(j):
    return max(i for m in MODELS for i in
               (predict(j, m, x, y) for y in range(T.H) for x in range(T.W)) if i is not None)


def with_forms():
    """addr.py's UV5_FORM with this stage's shapes (the module's dict, extended once)."""
    F5.install(A.UV5_FORM)


def corner_jobs(shapes):
    with_forms()
    return [(job(w, h), {m: image(job(w, h), m) for m in MODELS}) for w, h in shapes]


def type_spec(ty, umode):
    sp = dict(json.loads(pins.blob(tex.SPECS))[TYPES[ty][0]]["spec"])
    sp["t0"] = sp["t0"] & ~(7 << 6) | umode << 6
    return sp


def type_jobs():
    """[(name, set, spec, pin of the published program or None, pages, {model: value or
    tokens}, quantity)] for the six type rows, reference first."""
    out = []
    for ty, (case, binpin, kept) in TYPES.items():
        ref = f"addr5-ty{ty}-u0"
        out.append((ref, "replicate", type_spec(ty, 0), binpin, None,
                    {"H-E567": ["%08x" % v for v in pins.kept_pixels(kept)]}, "pixels"))
        out.append((f"addr5-ty{ty}-u4", "heldout", type_spec(ty, 4), None, TYPE_PAGES,
                    {"T-MODE0": f"{ref}+0", "T-OFFSET": f"{ref}+{TYPE_OFFSET}"}, "rel"))
    return out
