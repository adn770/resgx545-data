#!/usr/bin/env python3
"""Goal 1b: the 21 landed texture-sampler-smp-bilinear vectors against the joint rounding and the
two-stage form (P = 64/128/256, xy and yx), with my own reading of the vector: T0..T3 = r20..r23,
(u, v) = r24, r25, a 16 x 32 strided format-12 texture at dword base T2/4 whose dword i reads
0xD0000000|i, output the four channel bytes as floats (E037-style F32 conversion, T3 bits 17:16)."""
import json, struct
import tex2
from tex2 import *

V = json.load(open(DATA / "vectors/texture/sampler/texture-sampler-smp-bilinear.vec.json"))["vectors"]
f32 = lambda b: struct.unpack("<f", struct.pack("<I", int(b, 16)))[0]
rows = []
for v in V:
    r = {k: int(x, 16) for k, x in v["init"]["regs"].items()}
    sc = v["readback"]["scratch"]
    want = [f32(sc[f"0x{4*i:03x}"]) for i in range(4)]
    rows.append((v["id"].split("__")[1], r, want))

def run(form, P=64, order="xy"):
    tex2.OPT.update(two_stage=form == "two", P=P, order=order)
    ok = 0; bad = []
    for i, r, want in rows:
        t = Tex2(r["r20"], r["r21"], (r["r22"] & 0xFFFF) // 4, r["r23"], 16, dict(tm.RULES))
        u, v = tm.fb(r["r24"]), tm.fb(r["r25"])
        px = t.level_read(u, v, 0, True)
        got = [float(px >> 8 * c & 255) for c in range(4)]
        if got == want:
            ok += 1
        else:
            bad.append(i)
    return ok, bad

use_tile_law(True)
print("vectors", len(rows))
print("joint (sum+2048)>>12        ", run("joint"))
for P in (64, 128, 256):
    for o in ("xy", "yx"):
        print(f"two-stage P={P:3d} {o}", run("two", P, o))
# how discriminating: pixels (vectors) where joint and two-stage predict different values
tex2.OPT.update(two_stage=False); a = {}
for i, r, want in rows:
    t = Tex2(r["r20"], r["r21"], (r["r22"] & 0xFFFF) // 4, r["r23"], 16, dict(tm.RULES))
    a[i] = t.level_read(tm.fb(r["r24"]), tm.fb(r["r25"]), 0, True)
tex2.OPT.update(two_stage=True, P=64, order="xy"); d = []
for i, r, want in rows:
    t = Tex2(r["r20"], r["r21"], (r["r22"] & 0xFFFF) // 4, r["r23"], 16, dict(tm.RULES))
    if t.level_read(tm.fb(r["r24"]), tm.fb(r["r25"]), 0, True) != a[i]:
        d.append(i)
print("vectors where joint and two-stage(64,xy) predict different words:", d)
