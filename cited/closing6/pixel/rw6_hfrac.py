# SPDX-License-Identifier: MIT
"""Round 6 planning, Q230: H-FRAC on the HELD OUT half of E859's dense table (30 mantissas).  Predictions: rw6_hfrac.predictions.txt,
hashed with this script before it ran (rw6_hfrac.sha256).  Prints counts only.  Standard library only."""
import math, sys
sys.dont_write_bytecode = True
import rw6_data as D
h = D.load(held=True)
fr = {M: ((1 << 47) % M) / M for M in h}
n = len(h); low = [M for M in h if fr[M] < 0.5]; k = sum(h.values()); klow = sum(h[M] for M in low)
assert set(h.values()) <= {0, 1}
print(f"HELD OUT mantissas {n}; frac < 0.5: {len(low)}; RZ + 1: {k}; RZ + 1 with frac < 0.5: {klow}")
for a, b in ((0.5, 0.75), (0.75, 1.0)):
    s = [h[M] for M in h if a <= fr[M] < b]
    print(f"  frac in [{a}, {b}): {len(s)} mantissas, RZ + 1 {sum(s)}")
p = math.comb(n - len(low), k) / math.comb(n, k) if k else 1.0
print(f"chance of 0 below 0.5 if the delta were independent of frac: {p:.4f}")
ok = k >= 3 and len(low) >= 8
print("H-FRAC:", "cannot tell (too few words)" if not ok else "HELD" if klow == 0 else "REFUTED")
