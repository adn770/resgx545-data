#!/usr/bin/env python3
"""Q284 post hoc: at every exact texel boundary (exact (q + 1) * 8 an integer) does the hardware take
the upper texel (floor) or the lower one, split by |ma| a power of two or not. Standard library."""
import importlib.util, json, math
from fractions import Fraction as F
from collections import Counter
spec = importlib.util.spec_from_file_location("st", __file__.replace("q284_ties.py", "q284_st.py"))
st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)
rule = json.load(open(__file__.replace("q284_ties.py", "q284_rule.json")))

def detw(i, order):
    a = b = 0
    for k in range(4):
        a |= ((i >> (2 * k)) & 1) << k; b |= ((i >> (2 * k + 1)) & 1) << k
    return (b, a) if order == "ty" else (a, b)   # (s, t)

cnt = Counter(); other = Counter()
for tag, table, d in (("fit", st.FIT, st.FIT_DIR), ("held", st.HELD, st.HELD_DIR)):
    for lab, rows in st.jobs(table, d):
        for x, y, u, v, w, idx in rows:
            c = (u, v, w); a = [abs(t) for t in c]
            ax = max(range(3), key=lambda i: a[i]); face = 2 * ax + (c[ax] < 0)
            if idx // 256 != face:
                other[(tag, lab, "face")] += 1; continue
            r = rule[str(face)]; mi = [i for i in range(3) if i != ax]
            sa, ta = mi[r["s_minor"]], mi[1 - r["s_minor"]]
            hs, ht = detw(idx % 256, r["order"])
            ma = F(a[ax]); p2 = (ma.numerator & (ma.numerator - 1)) == 0 and (ma.denominator & (ma.denominator - 1)) == 0
            for comp, sg, hv in ((sa, r["s_sign"], hs), (ta, r["t_sign"], ht)):
                ex = (F(sg) * F(c[comp]) / ma + 1) * 8
                k = min(max(math.floor(ex), 0), 15)
                if ex.denominator == 1 and 0 < ex < 16:
                    cnt[(tag, "pow2" if p2 else "npow2", "up" if hv == k else ("down" if hv == k - 1 else "other"))] += 1
                elif hv != k:
                    other[(tag, lab, "nontie", hv - k)] += 1
for k in sorted(cnt): print("tie", k, cnt[k])
for k in sorted(other): print("off", k, other[k])
