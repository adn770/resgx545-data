#!/usr/bin/env python3
"""Q284 post hoc: which arithmetic sends 14 of 207 non-power-of-two ties down and 193 up.
Variants: rcp = RZ or RN float32 of 1/|ma|; q = RZ or RN float32 of |c| * rcp; texel from q exactly
(fixed point, no float add). Lists the tie pairs. Standard library."""
import importlib.util, json, math, struct
from fractions import Fraction as F
from collections import Counter, defaultdict
spec = importlib.util.spec_from_file_location("st", __file__.replace("q284_tievar.py", "q284_st.py"))
st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)
rule = json.load(open(__file__.replace("q284_tievar.py", "q284_rule.json")))
def detw(i, order):
    a = b = 0
    for k in range(4):
        a |= ((i >> (2 * k)) & 1) << k; b |= ((i >> (2 * k + 1)) & 1) << k
    return (b, a) if order == "ty" else (a, b)
def f32(x, mode):  # positive Fraction -> float32 as Fraction (0 -> 0)
    if x == 0: return F(0)
    m = x; e = 0
    while m >= 2: m /= 2; e += 1
    while m < 1: m *= 2; e -= 1
    s = m * (1 << 23); fl = math.floor(s)
    if mode == "rn":
        r = s - fl; fl = fl + (1 if r > F(1, 2) or (r == F(1, 2) and fl % 2) else 0)
    return F(fl, 1 << 23) * F(2) ** e
pairs = defaultdict(Counter)
for tag, table, d in (("fit", st.FIT, st.FIT_DIR), ("held", st.HELD, st.HELD_DIR)):
    for lab, rows in st.jobs(table, d):
        for x, y, u, v, w, idx in rows:
            c = (u, v, w); a = [abs(t) for t in c]
            ax = max(range(3), key=lambda i: a[i]); face = 2 * ax + (c[ax] < 0)
            r = rule[str(face)]; mi = [i for i in range(3) if i != ax]
            sa, ta = mi[r["s_minor"]], mi[1 - r["s_minor"]]
            hs, ht = detw(idx % 256, r["order"]); ma = F(a[ax])
            if (ma.numerator & (ma.numerator - 1)) == 0 and (ma.denominator & (ma.denominator - 1)) == 0: continue
            for comp, sg, hv in ((sa, r["s_sign"], hs), (ta, r["t_sign"], ht)):
                sc = F(sg) * F(c[comp]); ex = (sc / ma + 1) * 8
                if ex.denominator == 1 and 0 < ex < 16:
                    pairs[(float(sc), float(ma))]["up" if hv == int(ex) else "down"] += 1
res = Counter()
for (sc, ma), dirs in sorted(pairs.items()):
    obs = "down" if dirs["down"] else "up"
    line = f"c={sc:+.7f} ma={ma:.7f} {dict(dirs)}"
    for rm in ("rz", "rn"):
        for pm in ("rz", "rn"):
            rc = f32(1 / F(ma), rm); q = f32(abs(F(sc)) * rc, pm) * (1 if sc > 0 else -1)
            k = math.floor((q + 1) * 8); exk = (F(sc) / F(ma) + 1) * 8
            got = "up" if k == exk else "down"
            res[(rm, pm, got == obs)] += 1
            line += f" {rm}/{pm}:{got[0]}"
    print(line)
for k in sorted(res): print("variant rcp/prod", k, res[k])
