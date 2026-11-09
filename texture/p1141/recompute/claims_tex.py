#!/usr/bin/env python3
"""Goal 1a/1b: the claims of opus/texture.md A1 to A4, A6 to A8 recomputed on the stored 11.32 dumps with my own
tex2.py (options: tile law, operand pairing, two-stage bilinear, sRGB to half, T3 model, ETC1, raster types).
Each line says which jobs are 'found on' (the report fixed the rule on them), which are 'held out' (not looked at
before the rule, by the report's own account) and the exact count. In-sample counts are not evidence."""
import sys
from tex2 import *
import tex2

dec = declared()


def cnt(n, rules=None, **o):
    pix = load_pix(dec[n][0], n)
    px = render(n, rules or {}, **o)
    return sum(a == b for a, b in zip(px, pix))


def row(title, names, rules, kind, **o):
    r = [cnt(n, rules, **o) for n in names]
    print(f"  {title:44s} {kind:10s} exact {sum(x == 2048 for x in r):2d} of {len(r):2d}   {dict(zip(names, r)) if any(x != 2048 for x in r) else ''}")


print("A1 operand pairing (op0,op2),(op1,op3), euclid of the larger; tile law")
fit = ["gr-vx-k2", "gr-vx-k4"]
row("gradient jobs, E563's order (control)", ["gr-uu-k2", "gr-vv-k2", "gr-uvy-k2"], {"lodf": "euc"}, "in-sample", pair=False)
row("gradient jobs, paired", ["gr-uu-k2", "gr-vv-k2", "gr-uvy-k2"], {"lodf": "euc"}, "in-sample", foot="P")
row("gradient jobs, paired, and gr-all/neg (both rules)", ["gr-all-k2", "gr-neg-k2", "gr-all-k4"], {"lodf": "euc"}, "in-sample", foot="P")
row("gr-vx (no discrimination: max4 also exact)", fit, {"lodf": "euc"}, "in-sample", foot="P")
row("gr-vx under max4", fit, {"lodf": "max4"}, "in-sample")
lodauto = [n for n in SPECS if SPECS[n]["group"] == "lod-auto"]
row("lod-auto, euclid, tile law, no pairing (the quad)", lodauto, {"lodf": "euc"}, "mixed", srgb=True)
print("  note: 'ab-t43' needs T0 bit 27 (srgb); the quad's own derivatives do not test the operand order")
print("A2 two-stage bilinear: an-ctl, an-r1..r5 (the 45-form search jobs); then the landed vectors (vec_bilinear.py)")
row("two-stage P=64 xy, tile, paired", ["an-ctl", "an-r1", "an-r2", "an-r3", "an-r4", "an-r5"], {"lodf": "euc"}, "in-sample", foot="P", two_stage=True)
row("joint rounding (control)", ["an-ctl", "an-r1", "an-r2", "an-r3", "an-r4", "an-r5"], {"lodf": "euc"}, "in-sample", foot="P")
print("A3 T0 bit 27 = sRGB decode to half floats")
row("s64x32-t0b27 (found on)", ["s64x32-t0b27"], {}, "in-sample", srgb=True)
row("ind-t0b27, ab-t43", ["ind-t0b27"], {}, "held out", srgb=True)
row("ab-t43 (the job that drew the report's eye)", ["ab-t43"], {"lodf": "euc"}, "in-sample", srgb=True, foot="P")
row("an-t0b27 (bilinear: report says open)", ["an-t0b27"], {"lodf": "euc"}, "open", srgb=True, foot="P", two_stage=True)
print("A4 T3 address model (level offset by W*H, shift by 19:18, bit 10 = 0)")
row("s64x32, s64x16, s32x32, tw32 t3b18/t3b28", ["s64x32-t3b27", "s64x32-t3b28", "s64x32-t3b18", "s64x16-t3b27", "s64x16-t3b28", "s64x16-t3b18", "s32x32-t3b27", "s32x32-t3b28", "s32x32-t3b18", "tw32-t3b18", "tw32-t3b28", "tw32-t3b27"], {"t3off": "pre"}, "in-sample", t3model=True)
row("ind-t3b10/b18/b27/b28 (16x16 twiddled, smp3d)", ["ind-t3b10", "ind-t3b18", "ind-t3b27", "ind-t3b28"], {"t3off": "pre"}, "held out", t3model=True)
row("r-b18-19, r-b27-28 (first rows read before)", ["r-b18-19", "r-b27-28"], {"t3off": "pre"}, "part-seen", t3model=True)
print("A6 T3 7:0 offset before the address mode, tile law (the 24 tv-* jobs)")
tv = [n for n in SPECS if n.startswith("tv-")]
row("tv-*, t3off=pre, tile law", tv, {"t3off": "pre"}, "held out")
row("tv-*, t3off=post, tile law", tv, {"t3off": "post"}, "held out")
print("A7 format 27 = ETC1, block words as stored, Morton y-low, alpha 0xff, 0xAARRGGBB")
row("fb-27-base, ordA, ordB (found on)", ["fb-27-base", "fb-27-ordA", "fb-27-ordB"], {}, "in-sample", etc1=True)
row("fb-27-lo, fb-27-hi, fn-27", ["fb-27-lo", "fb-27-hi", "fn-27"], {}, "held out", etc1=True)
print("A8 TEXTYPE 1/3 (stride 16) and 4 (stride 32) rasters that wrap, 16x16 only")
for nm in ("rt1-2d", "rt1-3d-w5", "ty3-2d", "ty3-3d-w10", "rt4-2d", "rt4-3d-w15"):
    pix = load_pix(dec[nm][0], nm)
    st = 32 if nm.startswith("rt4") else 16
    ok = sum(pix[y * 64 + x] == (0xD0000000 | (y % 16) * st + x % 16) for y in range(32) for x in range(64))
    print(f"  {nm:12s} exact {ok} of 2048")
