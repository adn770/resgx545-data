#!/usr/bin/env python3
"""Q282 offline, family 2 (declared after q282_fit.out's residuals on g-bl-st-a: hw 1 half ulp below
the lerp-in-half model on 531 channels, above on 62): decode to half (RNE), then the two lerps in half
with a rounding per stage and per operation, two forms (a(1-w) + bw, a + w(b - a)), and wider
intermediates (float32, fixed point with N fraction bits) truncated or rounded to half at the end.
Fit on g-bl-st-a only; the best set is frozen (q282_rule2.json + .sha256) before g-bl-st-b is read.

    /Users/jtorra/src/resgx545/.venv/bin/python -B q282_fit2.py
"""
import hashlib, json, sys
sys.dont_write_bytecode = True
from q282_fit import corners, hw, s2l, h2f, half_rne, half_rz, half_ru, f32, HERE

RD = {"rne": half_rne, "rz": half_rz, "ru": half_ru}
def H(v, r):
    return h2f(RD[r](v))

def model2(b4, fx, fy, m):
    ix, iy = int(fx * 64), int(fy * 64)
    d = [h2f(half_rne(s2l(b))) for b in b4] if m["dec"] == "half" else [f32(s2l(b)) for b in b4]
    wx, wy = ix / 64, iy / 64
    r1, r2, rp, form, order = m["r1"], m["r2"], m["rp"], m["form"], m["order"]
    def q(v, r):
        if r == "none":
            return v
        if r.startswith("fx"):
            n = int(r[2:]); S = 1 << n
            return int(v * S) / S
        return H(v, r)
    def lerp(a, b, w, r):
        if form == "mix":
            return q(q(a * (1 - w), rp) + q(b * w, rp), r)
        return q(a + q(w * q(b - a, rp), rp), r)
    if order == "xy":
        t, u = lerp(d[0], d[1], wx, r1), lerp(d[2], d[3], wx, r1)
        v = lerp(t, u, wy, r2)
    else:
        t, u = lerp(d[0], d[2], wy, r1), lerp(d[1], d[3], wy, r1)
        v = lerp(t, u, wx, r2)
    return RD[m["out"]](v)

R = ("rne", "rz", "none", "fx16", "fx20", "fx24")
FAM = [dict(dec=dec, r1=a, r2=b, rp=p, form=f, order=o, out=out)
       for dec in ("half", "f32") for a in R for b in R for p in ("none", "rne", "rz")
       for f in ("mix", "delta") for o in ("xy", "yx") for out in ("rne", "rz")]

def score(rec, pix, m):
    px = ch = 0
    for (c2, fx, fy), w in zip(rec, pix):
        g = [model2(c2[c], fx, fy, m) == (w >> 16 * c & 0xffff) for c in (0, 1)]
        ch += sum(g); px += all(g)
    return px, ch

if __name__ == "__main__":
    rec, pix = corners("g-bl-st-a"), hw("g-bl-st-a")
    res = sorted(((score(rec, pix, m), json.dumps(m, sort_keys=True)) for m in FAM), reverse=True)
    print(f"family 2: {len(FAM)} candidates on g-bl-st-a")
    for s, k in res[:20]:
        print(" ", s, k)
    best = res[0][0]; ties = [json.loads(k) for s, k in res if s == best]
    rule = {"question": "Q282", "family": 2, "fit_job": "g-bl-st-a", "fit_score": list(best), "tied_at_best": ties,
            "heldout_job": "g-bl-st-b", "prediction": "the first tied rule is exact on >= 2040 of 2048 pixels of g-bl-st-b"}
    blob = json.dumps(rule, sort_keys=True, indent=1) + "\n"
    (HERE / "q282_rule2.json").write_text(blob)
    (HERE / "q282_rule2.sha256").write_text(hashlib.sha256(blob.encode()).hexdigest() + "  q282_rule2.json\n")
    print("frozen", len(ties), "tied; sha256", hashlib.sha256(blob.encode()).hexdigest())
