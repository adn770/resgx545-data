#!/usr/bin/env python3
"""Q078, T3 bit 14 in smp on a strided texture (E566's kept dumps, data texture/p1132/tx-t3).
Read on the fit job s64x32-t3b14 (q078_b14_look.py): the dword read is the control's dword i plus
32 plus stride * c (c the control's column), 2048 of 2048 there by construction. Rivals declared
for the constant (W/2, stride/2, 32) and the multiplier (stride, W), frozen by hash below before
the held-out jobs s64x16-t3b14 and s32x32-t3b14 are read; tw32-t3b14 (twiddled) is scored as an
exploration with the same index arithmetic on the twiddled index.

    /Users/jtorra/src/resgx545/.venv/bin/python -B q078_b14.py freeze|score
"""
import hashlib, json, pathlib, sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))  # round 9 copy: q078_lib, the published model
from q078_lib import load_pix, SPECS, tm
HERE = pathlib.Path(__file__).resolve().parent
RIV = {f"K={k},M={m}": (k, m) for k in ("W/2", "S/2", "32") for m in ("S", "W")}

def geom(sp):
    st = ((sp["t0"] >> 9 & 7) | (sp["t0"] >> 17 & 0x3FF) << 3) + 1
    t = tm.Tex(sp["t0"], sp["t1"], 0, sp["t3"], 16, dict(tm.RULES))
    return t.w, t.h, st

def predict(name, k, m):
    sp = dict(SPECS[name]["spec"]); sp["t3"] &= ~(1 << 14)
    W, H, S = geom(sp)
    ctl = tm.render(sp, {})
    K = {"W/2": W // 2, "S/2": S // 2, "32": 32}[k]; M = {"S": S, "W": W}[m]
    out = []
    for v in ctl:
        i = v & 0x0FFFFFFF
        c = i % S if S > 1 else i % W
        out.append(0xD0000000 | (i + K + M * c))
    return out, (W, H, S)

def score(name, rv):
    hw = load_pix("tx-t3", name)
    px, g = predict(name, *RIV[rv])
    return sum(a == b for a, b in zip(px, hw)), g

if __name__ == "__main__":
    if sys.argv[1] == "freeze":
        fit = {rv: score("s64x32-t3b14", rv)[0] for rv in RIV}
        rule = {"question": "Q078", "bit": 14, "fit_job": "s64x32-t3b14", "fit": fit,
                "heldout": ["s64x16-t3b14", "s32x32-t3b14"], "explore": ["tw32-t3b14"],
                "prediction": "a rival exact on the fit job is exact (2048 of 2048) on each held-out job; the rivals tie on the fit job and the held-out geometry separates them where W, S differ"}
        blob = json.dumps(rule, sort_keys=True, indent=1) + "\n"
        (HERE / "q078_b14_rule.json").write_text(blob)
        (HERE / "q078_b14_rule.sha256").write_text(hashlib.sha256(blob.encode()).hexdigest() + "  q078_b14_rule.json\n")
        print(json.dumps(fit), hashlib.sha256(blob.encode()).hexdigest())
    else:
        blob = (HERE / "q078_b14_rule.json").read_text()
        assert hashlib.sha256(blob.encode()).hexdigest() == (HERE / "q078_b14_rule.sha256").read_text().split()[0]
        for n in ["s64x16-t3b14", "s32x32-t3b14", "tw32-t3b14"]:
            for rv in RIV:
                s, g = score(n, rv)
                print(f"{n:14s} W,H,S={g} {rv:12s} {s} of 2048")
