# SPDX-License-Identifier: MIT
"""f1.py: stage f1 (r14-flag, Q078 T3 bit 14 on a twiddled texture with the reach mapped;
closing14/plan/rank-round14.md section 2 "F1"; planned faults, user OK R14-5 a). r13-flag f1's form
(E1033): E566's tx_map form on named memory (scratch dword i reads 0xD0000000 | i, so every read
names its dword), a twiddled 32 x 32 32-bit texture (T1 0x0C01F01F, type 0) at the scratch's first
dword, now with t14's `probe --scratch-pages 256` (1 MiB, dwords 0 to 262143): both of E1033's
fault pages (scratch + 0x21000 and + 0x40000) lie inside it, so a read that went there names its
dword in the image instead of faulting.

Frozen address forms, POST HOC on E1033's two fault pages [infer] (fit/fit_e1033.py lists the
family tried). Let s = floor(32 u) mod 32, t = floor(32 v) mod 32 (the bit-clear texel, wrap), fr
= u - floor(u) (u wrapped to [0, 1)), and index(s', t, P) E561's tile law with a tile-row pitch of
P texels: morton16(s' mod 16, t mod 16) + 256 (s' div 16 + (P / 16)(t div 16)):

  H-TWP4096     s' = s + floor(4096 fr), P = 4096: bit 14 widens the texture by 4096 texels
                [infer: E1003's floor(4096 clamp(u, 0, 1)) on a strided texture is the same
                widening, the strided row pitch being the stride, not the width]
  H-TWP4128     s' as H-TWP4096, P = W + 4096 = 4128 (the widened width as the pitch)
  H-TWP4096-NS  s' = floor(4096 fr) (no bit-clear column), P = 4096
  H-FAULTANY    E1033's H-FAULTANY carried: every bit-14 twiddled read faults the job, whatever
                is mapped (2 of 2 in E1033)
  H-MOVE0       f1-zero only: E1003's move is 0 at u = 0, so the bit-clear image (every move
                model of E1033: the move in the index, in the column, wrapped)

Each form puts every unmapped read of E1033's f1-small (16 pages and the 3 coordinate pages
mapped: dwords below 19456) on page + 0x40000 or the page after it, + 0x40000 the lowest; and
f1-tw32's pixel (16, 0), the first pixel of the fill's second 16 x 16 pixel tile, on page +
0x21000 [infer: E1033 keeps only each job's first faulting page; pixels 11 to 15 of the first
tile read unmapped pages below it, so the form holds only if the second tile's first read
faulted first]. With 256 pages every form reads inside the scratch: an image, no fault.

Rows, in run order (each reference before the rows it gates): f1-ref-a (control: E566's tw32-ctl
program byte for byte, its kept image, now at 256 pages), f1-tw32 (E566's tw32-t3b14, u in (1, 2):
replicate of E1033's first planned row), f1-ref-b (control: u = x / 4096 with bit 14 clear, the
tile law's column 0, E1033's f1-ref-b at 256 pages), f1-small (E1033's held-out row at 256 pages),
f1-zero (held out: u = 0 on every pixel, bit 14; never run). The three bit-14 rows are the
stage's planned rows (expectfault, #limit 3); the references are controls without expectfault (a
fault there stops the stage)."""
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
PAGES = 256                   # t14's probe --scratch-pages (16 to 256)
E1033_PAGES = 16              # E1033's scratch (the probe's default)
E1033_MAPPED = (16 + 3) * 1024  # dwords mapped from the scratch's first in E1033 (+ coordinates)
E1033_FPAGE = {"f1-tw32": 0x21000, "f1-small": 0x40000}
FORMS = ("H-TWP4096", "H-TWP4128", "H-TWP4096-NS")
U_SMALL = tex.lin("x", F(1, 4096), 0)          # u = x / 4096: E1003's move is x texels
U_ZERO = tex.lin("x", 0, 0)                    # u = 0 on every pixel: no move
V_ROW = tex.lin("y", F(1, 32), F(1, 64))       # v = (y + 1/2) / 32: texel row y
ARGS = 'probe --temps 32 --coords --pixels --scratch-pages {pages} "$S/bins/{row}.bin"'


def specs():
    return json.loads(pins.blob(tex.SPECS))


def spec_b(t3, u=None):
    s = specs()[SPEC_A_CTL]["spec"]
    return dict(base=0, ins="none", t0=s["t0"], t1=s["t1"], t3=t3, u=u or U_SMALL, v=V_ROW)


def name(i):
    return 0xD0000000 | i


def fl(q):
    return int(F(q).__floor__())


def tl(s, t, pitch):
    """E561's tile law with a tile-row pitch of `pitch` texels (law.index at W = pitch)."""
    return law.morton(s % 16, t % 16, 16, 16) + 256 * (s // 16 + (pitch // 16) * (t // 16))


def form_index(model, u, v):
    s, t = fl(u * W) % W, fl(v * H) % H
    fr = F(u) - fl(u)
    if model == "REF":
        return law.index(s, t, W, H)
    if model == "H-TWP4096":
        return tl(s + fl(4096 * fr), t, 4096)
    if model == "H-TWP4128":
        return tl(s + fl(4096 * fr), t, W + 4096)
    if model == "H-TWP4096-NS":
        return tl(fl(4096 * fr), t, 4096)
    raise ValueError(model)


def coords(row, x, y):
    """(u, v) of a pixel: E566's map coordinates (pair A) or the lin forms (f1-small, f1-zero)."""
    if row in ("f1-ref-a", "f1-tw32"):
        s = specs()[SPEC_A_CTL]["spec"]
        return F(law.ev(s["u"], x, y)), F(law.ev(s["v"], x, y))
    u = U_ZERO if row == "f1-zero" else U_SMALL
    return tex.coord(u, x, y), tex.coord(V_ROW, x, y)


def indices(row, model):
    """The dword index each of the fill's 2048 pixels reads, raster order."""
    return [form_index(model, *coords(row, x, y)) for y in range(tex.H) for x in range(tex.W)]


def image(row, model):
    return [name(i) for i in indices(row, model)]


def reach(rows_models):
    return max(i for r, m in rows_models for i in indices(r, m))


def e1033_pages(row, model):
    """{page offset from the scratch} of the unmapped reads the form gives E1033's row."""
    return sorted({(i * 4) & ~0xFFF for i in indices(row, model) if i >= E1033_MAPPED})


def models(row):
    """{model: ("ok", image) or ("fault", None)} of a bit-14 row."""
    out = {m: ("ok", image(row, m)) for m in FORMS}
    out["H-FAULTANY"] = ("fault", None)
    if row == "f1-zero":
        out["H-MOVE0"] = ("ok", image(row, "REF"))
    return out


def jobs():
    """[(name, set, knobs, spec, {model: (end, image or None)}, pages)], run order."""
    S = specs()
    kept = pins.kept_pixels(E566_CTL)
    a_ctl, a_b14 = S[SPEC_A_CTL]["spec"], S[SPEC_A_B14]["spec"]
    assert a_b14 == dict(a_ctl, t3=a_ctl["t3"] | B14), "E566's pair differs in more than bit 14"
    b_ref = spec_b(a_ctl["t3"])
    return [
        ("f1-ref-a", "control", "reads:pixels", a_ctl, {"H-E566": ("ok", kept)}, PAGES),
        ("f1-tw32", "replicate", "expectfault", a_b14, models("f1-tw32"), PAGES),
        ("f1-ref-b", "control", "reads:pixels", b_ref, {"H-E561": ("ok", image("f1-ref-b", "REF"))},
         PAGES),
        ("f1-small", "replicate", "expectfault", dict(b_ref, t3=b_ref["t3"] | B14),
         models("f1-small"), PAGES),
        ("f1-zero", "heldout", "expectfault", spec_b(a_ctl["t3"] | B14, U_ZERO), models("f1-zero"),
         PAGES),
    ]


def args(row, pages=PAGES):
    return ARGS.format(pages=pages, row=row)
