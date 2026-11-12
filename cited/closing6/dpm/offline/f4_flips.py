#!/usr/bin/env python3
"""F4 side reading (post hoc: the flips were known): with H-PHASE and R-5's guard the last raise
of the first threshold is the last cell that leaves 2 global pages with 3 at the abort, so the
first silent cell (C - 0x1f) is the band-3 burst end.  Compares F5's model burst end B3
(f5_stepmodel.out) with the flips of E774, E799 and E801 (last raise, first silent)."""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
FLIPS = {'4096x4096': (0x351, 0x352), '2048x2048': (0xe2, 0xe3), '4096x2048': (0x1b2, 0x1b3),
         '2048x4096': (0x1b6, 0x1b7), '3072x3072': (0x1e8, 0x1e9)}
B, cur = {}, None
for l in open(os.path.join(HERE, 'f5_stepmodel.out')):
    m = re.match(r'(\d+x\d+) (fit|held)', l)
    if m: cur = m.group(1)
    if 'B_k' in l:
        B[cur] = {int(k): int(v, 16) for k, v in re.findall(r'B(\d+) (0x[0-9a-f]+)', l)}
ok = 0
for wh, (last, first) in FLIPS.items():
    hit = B[wh][3] == first
    ok += hit
    print(f'{wh}: last raise {last:#x}, first silent {first:#x}; F5 B3 {B[wh][3]:#x} {"equals" if hit else "DIFFERS"}')
print(f'first silent cell = B3 at {ok} of {len(FLIPS)} targets')
