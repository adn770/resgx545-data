#!/usr/bin/env python3
"""Round 7 planner, Q210 (post hoc, exploratory): E874's replay at 2048x2048, the page count after
each object around the bursts, against the observed first one-page-left cells (E799, E862, E881).
Read-only; imports the frozen closing6 offline library."""
import sys
sys.path.insert(0, '/Users/jtorra/src/scratch/resgx545/closing6/dpm/offline')
import f5lib as F
w = h = 2048
ents = F.entries(w, h)
S, opens, after = F.replay(w, h, ents, 3)
OBS = {2: 0x97, 3: 0xe3, 4: 0x12e, 5: 0x178, 6: 0x1c3, 7: 0x20d}   # first thr0 with 1 page left
print('S', {k: hex(v) for k, v in S.items()})
for k in sorted(OBS):
    b = F.bk(k)
    print(f'band {k}: b_k {b} (written when tiling {b-3}); S {S[k]:#x}; first-1 obs {OBS[k]:#x} (+{OBS[k]-S[k]})')
    for t in range(b - 5, min(F.OBJS, b + 16)):
        mark = ' <= obs' if after[t] <= OBS[k] <= (after[t + 1] if t + 1 < F.OBJS else 9999) else ''
        print(f'    obj {t:3d} (mod15 {t%15:2d}) opens {opens[t]:3d} pages after {after[t]:#x}{mark}')
