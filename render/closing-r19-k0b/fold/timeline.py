# SPDX-License-Identifier: MIT
"""fold/timeline.py (post hoc, the fold's, outside the freeze): per f0 row, when 0x0624 took the
final's N - 0x22 (ms from regtimeline's start) and, from that sample on, the highest page count
(0x0724 low half) and the partial renders (0x0658 stretches). Usage: python3 fold/timeline.py KEPT"""
import gzip
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "score"))
import r10read as R  # noqa: E402
P = {"f0-same": 0x200, "f0-up-h1": 0x60, "f0-up-h2": 0x422, "f0-up": 0x100, "f0-back": 0x100,
     "f0-down": 0x30}
d = sys.argv[1]
for f in sorted(os.listdir(d)):
    if not (f.startswith("f0-") and f.endswith(".txt.gz")) or ".words." in f:
        continue
    n = f[:-7]
    want = P[next(k for k in sorted(P, key=len, reverse=True) if n.startswith(k + "-"))] - 0x22
    regs, rows, start = R.parse(gzip.open(os.path.join(d, f)).read().decode(errors="replace"))
    # the first sample from start that takes the value after another (not a row before's left)
    i = next((k for k, (t, v) in enumerate(rows) if k and t >= start and v[0x624] == want
              and rows[k - 1][1][0x624] != want), None)
    if i is None:
        print(f"{n}: 0x0624 never {want:#x}")
        continue
    after = rows[i:]
    pk = max(v[0x724] & 0xFFFF for _, v in after)
    pk_before = max((v[0x724] & 0xFFFF for t, v in rows[:i] if t >= start), default=0)
    pr = sum(1 for k in range(1, len(after)) if after[k][1][0x658] & 1 and not after[k - 1][1][0x658] & 1)
    print(f"{n}: 0x0624 = {want:#x} from {(rows[i][0] - start) / 1e6:.1f} ms with {rows[i][1][0x724] & 0xFFFF} "
          f"pages held; then peak {pk} pages, {pr} partial renders (peak before: {pk_before})")
