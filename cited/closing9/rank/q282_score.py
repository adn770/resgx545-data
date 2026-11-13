#!/usr/bin/env python3
"""Q282: score the frozen best of each family (q282_rule*.json, hashes checked) on the held-out job
g-bl-st-b, read here for the first time."""
import hashlib, json, sys
sys.dont_write_bytecode = True
from q282_fit import corners, hw, model, HERE
import q282_fit2 as F2, q282_fit3 as F3
rec, pix = corners("g-bl-st-b"), hw("g-bl-st-b")
for f, fn, mod in (("q282_rule.json", None, model), ("q282_rule2.json", None, F2.model2), ("q282_rule3.json", None, F3.model3)):
    blob = (HERE / f).read_text()
    want = (HERE / f.replace(".json", ".sha256")).read_text().split()[0]
    assert hashlib.sha256(blob.encode()).hexdigest() == want, f
    r = json.loads(blob)
    m = r.get("rule") or r["tied_at_best"][0]
    px = ch = 0
    for (c2, fx, fy), w in zip(rec, pix):
        g = [mod(c2[c], fx, fy, m) == (w >> 16 * c & 0xffff) for c in (0, 1)]
        ch += sum(g); px += all(g)
    print(f"{f}: fit {r['fit_score']} on g-bl-st-a; held out g-bl-st-b: {px} of 2048 pixels, {ch} of 4096 channels; rule {json.dumps(m, sort_keys=True)}")
