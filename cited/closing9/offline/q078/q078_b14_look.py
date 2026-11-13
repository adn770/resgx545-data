#!/usr/bin/env python3
"""Q078 bit 14 (fit job s64x32-t3b14 only, E566's kept dump): per pixel the dword the control model
reads (texmodel, bit 14 clear) and the dword the hardware read with bit 14 set, as (col, row) of the
strided texture. Look only; nothing frozen here."""
import collections, sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))  # round 9 copy: q078_lib, the published model
from q078_lib import load_pix, SPECS, tm
name = sys.argv[1] if len(sys.argv) > 1 else "s64x32-t3b14"
sp = dict(SPECS[name]["spec"]); sp["t3"] &= ~(1 << 14)
ctl = tm.render(sp, {})
hw = load_pix("tx-t3", name)
t = tm.Tex(sp["t0"], sp["t1"], 0, sp["t3"], 16, dict(tm.RULES)) if False else None
st = ((sp["t0"] >> 9 & 7) | (sp["t0"] >> 17 & 0x3FF) << 3) + 1
print(name, "stride", st, "t1", hex(sp["t1"]))
d = collections.Counter()
rows = []
for i, (c, h) in enumerate(zip(ctl, hw)):
    x, y = i % 64, i // 64
    ci, hi = c & 0x0FFFFFFF, h & 0x0FFFFFFF
    if h >> 28 != 0xD:
        d["noname"] += 1; continue
    dc, dr = hi % st - ci % st, hi // st - ci // st
    d[(dc, dr)] += 1
    rows.append((x, y, ci % st, ci // st, hi % st, hi // st))
print("distinct (dcol, drow):", len(d), d.most_common(12))
for r in rows[:5] + rows[60:70] + rows[64*5:64*5+5] + rows[64*17:64*17+5]:
    print(r)
