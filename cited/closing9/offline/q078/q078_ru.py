#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Q078 T3 bit 14, round 9 offline (O9-1, E968), POST HOC: after q078_b14.py froze its six rivals
(fbd25356...) and scored them (s64x16 2048 of 2048 for all six, s32x32 0 of 2048 for all six), the
ranking's reading R-U (closing9/rank/q078_b14_post.out, no script kept) is re-derived here and
one more reading is added, on the same three kept dumps of E566 (texture/p1132/tx-t3):
  R-U    dword' = i + S * S * (c + 1/2) / W, c the control's column (clamped to the texture);
  R-URAW dword' = i + floor(S * S * u), u the pixel's raw coordinate (texmodel.ev, unclamped);
  R-U01  dword' = i + floor(S * S * min(max(u, 0), 1)), the raw u clamped to [0, 1] (formed after
         looking at s32x32's pixel columns 32 to 63, so in sample on every job).
i is the control's dword (texmodel, bit 14 cleared), S the stride, W the width. Standard library.
    /Users/jtorra/src/resgx545/.venv/bin/python -I -B q078_ru.py > q078_ru.out"""
import math, pathlib, sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from q078_lib import load_pix, SPECS, tm  # noqa: E402

for name in ("s64x32-t3b14", "s64x16-t3b14", "s32x32-t3b14", "tw32-t3b14"):
    hw = load_pix("tx-t3", name)
    if hw is None:
        print(f"{name}: no whole image kept (E566: the job faulted)")
        continue
    sp = dict(SPECS[name]["spec"]); sp["t3"] &= ~(1 << 14)
    st = ((sp["t0"] >> 9 & 7) | (sp["t0"] >> 17 & 0x3FF) << 3) + 1
    t = tm.Tex(sp["t0"], sp["t1"], 0, sp["t3"], 16, dict(tm.RULES))
    W, S = t.w, st
    ctl = tm.render(sp, {})
    ru = raw = r01 = 0
    miss_ru, miss_raw, miss01 = set(), set(), set()
    for p, (cv, hv) in enumerate(zip(ctl, hw)):
        x, y = p % 64, p // 64
        i = cv & 0x0FFFFFFF
        c = i % S
        a = 0xD0000000 | (i + S * S * (2 * c + 1) // (2 * W))
        u = tm.ev(sp["u"], x, y)
        b = 0xD0000000 | (i + math.floor(S * S * u))
        d = 0xD0000000 | (i + math.floor(S * S * min(max(u, 0.0), 1.0)))
        r01 += d == hv
        if d != hv:
            miss01.add(x)
        ru += a == hv
        raw += b == hv
        if a != hv:
            miss_ru.add(x)
        if b != hv:
            miss_raw.add(x)
    print(f"{name}: W {W} S {S}: R-U {ru} of 2048 (pixel columns off: {sorted(miss_ru) or 'none'}); "
          f"R-URAW {raw} of 2048 (pixel columns off: {sorted(miss_raw) or 'none'}); "
          f"R-U01 {r01} of 2048 (pixel columns off: {sorted(miss01) or 'none'})")
