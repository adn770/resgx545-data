#!/usr/bin/env python3
"""Q284 post hoc (after q284_st.py score): the frozen rule's 14 misses (8 fit, 6 held out) all sit
on exact texel boundaries? Variant RZ: q = c * RZ32(1 / |ma|), then floor((q + 1) * 8) in float32,
against variant RN (1/|ma| rounded to nearest) and the exact division. Standard library only."""
import importlib.util, struct, math
from fractions import Fraction as F
spec = importlib.util.spec_from_file_location("st", __file__.replace("q284_rcp.py", "q284_st.py"))
st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)
import json
rule = json.load(open(__file__.replace("q284_rcp.py", "q284_rule.json")))

def rz32(x):  # float32 toward zero of a positive Fraction
    f = struct.unpack("<f", struct.pack("<f", float(x)))[0]
    return f if F(f) <= x else math.nextafter(f, 0.0) if False else struct.unpack("<f", struct.pack("<I", struct.unpack("<I", struct.pack("<f", f))[0] - 1))[0]

def rn32(x):
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]

def r32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]

def pred(variant, u, v, w):
    c = (u, v, w); a = [abs(t) for t in c]
    ax = max(range(3), key=lambda i: a[i]); face = 2 * ax + (c[ax] < 0)
    r = rule[str(face)]; mi = [i for i in range(3) if i != ax]
    sa, ta = mi[r["s_minor"]], mi[1 - r["s_minor"]]
    out = []
    for comp, sg in ((sa, r["s_sign"]), (ta, r["t_sign"])):
        if variant == "exact":
            q = F(sg) * F(c[comp]) / F(a[ax]); k = math.floor((q + 1) * 8)
        else:
            rc = rz32(F(1) / F(a[ax])) if variant == "rz" else rn32(F(1) / F(a[ax]))
            q = r32(sg * c[comp] * rc); k = math.floor(r32((q + 1.0) * 8.0))
        out.append(min(max(k, 0), 15))
    return face * 256 + st.twid(out[0], out[1], r["order"])

for tag, table, d in (("fit", st.FIT, st.FIT_DIR), ("held(post hoc)", st.HELD, st.HELD_DIR)):
    for lab, rows in st.jobs(table, d):
        res = {v: sum(pred(v, u, vv, w) == idx for x, y, u, vv, w, idx in rows) for v in ("exact", "rn", "rz")}
        ties = sum(1 for x, y, u, vv, w, idx in rows
                   for comp in range(3) if (F(abs((u, vv, w)[comp])) / F(max(abs(u), abs(vv), abs(w))) * 8).denominator == 1)
        print(f"{tag} {lab}: exact {res['exact']}, rn {res['rn']}, rz {res['rz']} of {len(rows)}")
