# SPDX-License-Identifier: MIT
"""Round 6 planning, Q230: EXPLORATION on the FIT set only (100 mantissas; the 30 HELD OUT deltas are not parsed).
For each mantissa M: frac = fractional part of 2^47 / M (how far the exact reciprocal is above RZ, in ulp of the stored word)."""
import rw6_data as D
f = D.load()
rows = sorted(((1 << 47) % M / M if M != 1 << 23 else 0.0, M, d) for M, d in f.items())
print("frac      M        delta   (sorted by frac)")
for fr, M, d in rows: print(f"{fr:.5f}  {M:#08x}  {d}")
for lo in range(10):
    s = [d for fr, M, d in rows if lo / 10 <= fr < (lo + 1) / 10]
    print(f"frac in [{lo/10:.1f},{(lo+1)/10:.1f}): n {len(s)} RZ+1 {sum(s)}")
