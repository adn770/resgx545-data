#!/usr/bin/env python3
"""Q282 offline, family 3 (declared after q282_resid2.out on g-bl-st-a: errors of +-1 half ulp spread
over the exact value's position, misses clustered on texel columns with corners of very different
magnitude): a block-float filter. The corners decoded to half (RNE), aligned to a shared exponent
(the largest of the four, or of each lerp's pair) with M fraction bits (truncated or rounded), the
two lerps in integers with 1/64 weights (+32 >> 6 or truncating), the result to half (RNE or RZ).
Fit on g-bl-st-a only; frozen (q282_rule3.json + .sha256) before g-bl-st-b is read.

    /Users/jtorra/src/resgx545/.venv/bin/python -B q282_fit3.py
"""
import hashlib, json, math, sys
sys.dont_write_bytecode = True
from q282_fit import corners, hw, s2l, h2f, half_rne, half_rz, HERE

def ex(v):
    return math.frexp(v)[1] if v else -100

def align(vals, E, M, rnd):
    S = 2.0 ** (M - E)
    return [int(v * S + (0.5 if rnd else 0)) for v in vals], S

def model3(b4, fx, fy, m):
    ix, iy = int(fx * 64), int(fy * 64)
    d = [h2f(half_rne(s2l(b))) for b in b4]
    M, ar, lr, out, scope = m["M"], m["align"], m["lerp"], m["out"], m["scope"]
    add = 32 if lr == "rn" else 0
    L = lambda a, b, w: (a * (64 - w) + b * w + add) >> 6
    if scope == "all":
        q, S = align(d, max(ex(v) for v in d), M, ar == "rn")
        r = L(L(q[0], q[1], ix), L(q[2], q[3], ix), iy) / S
    else:
        def st(a, b, w):
            q, S = align([a, b], max(ex(a), ex(b)), M, ar == "rn")
            return L(q[0], q[1], w) / S
        r = st(st(d[0], d[1], ix), st(d[2], d[3], ix), iy)
    return (half_rne if out == "rne" else half_rz)(r)

FAM = [dict(M=M, align=a, lerp=l, out=o, scope=s) for M in range(9, 25) for a in ("rz", "rn")
       for l in ("rn", "rz") for o in ("rne", "rz") for s in ("all", "pair")]

def score(rec, pix, m):
    px = ch = 0
    for (c2, fx, fy), w in zip(rec, pix):
        g = [model3(c2[c], fx, fy, m) == (w >> 16 * c & 0xffff) for c in (0, 1)]
        ch += sum(g); px += all(g)
    return px, ch

if __name__ == "__main__":
    rec, pix = corners("g-bl-st-a"), hw("g-bl-st-a")
    res = sorted(((score(rec, pix, m), json.dumps(m, sort_keys=True)) for m in FAM), reverse=True)
    print(f"family 3: {len(FAM)} candidates on g-bl-st-a")
    for s, k in res[:15]:
        print(" ", s, k)
    best = res[0][0]; ties = [json.loads(k) for s, k in res if s == best]
    rule = {"question": "Q282", "family": 3, "fit_job": "g-bl-st-a", "fit_score": list(best), "tied_at_best": ties,
            "heldout_job": "g-bl-st-b", "prediction": "the first tied rule is exact on >= 2040 of 2048 pixels of g-bl-st-b"}
    blob = json.dumps(rule, sort_keys=True, indent=1) + "\n"
    (HERE / "q282_rule3.json").write_text(blob)
    (HERE / "q282_rule3.sha256").write_text(hashlib.sha256(blob.encode()).hexdigest() + "  q282_rule3.json\n")
    print("frozen", len(ties), "tied; sha256", hashlib.sha256(blob.encode()).hexdigest())
