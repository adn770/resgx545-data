"""Post hoc: E727's region model with the a4 TA dump's own per-tile primitive masks in place of the
model's overlap test; and the model's masks against the dump's (500 tiles)."""
import gzip, sys
import numpy as np
sys.path.insert(0, '/Users/jtorra/src/resgx545-data/texture/p1141/recompute')
import msaa_model as m
# the four sample offsets of the 2x2 multisample pattern, in 1/16 pixel (msaa_model's table)
SUBSAMPLE_OFFSETS = [(6, 2), (14, 6), (2, 10), (10, 14)]
D ='/Users/jtorra/src/scratch/resgx545/closing/s3/out/20261110-003114/s3-a-safe/'
p = np.frombuffer(gzip.open(D + 'a4-ctl-320x400-te20.tri.param.bin.gz').read(), dtype='<u4')
t = np.frombuffer(gzip.open(D + 'a4-ctl-320x400-te20.tri.tadata.bin.gz').read(), dtype='<u4')
masks = {}
for i in range(0x4000 // 4, 0x6000 // 4, 3):
    d0, d1 = int(t[i]), int(t[i + 1])
    if (d0 >> 24) & 2 or d1 == 0:
        continue
    rx, ry = ((d0 >> 16) & 0xff) // 2, (d0 & 0xfff) // 2
    s = p[(d1 - 0x1000) // 4:(d1 - 0x1000) // 4 + 3]
    form = (int(s[0]) >> 16) & 0xff
    l, r = (3, 3) if form == 0x90 else (int(s[2]) & 0xffff, int(s[2]) >> 16)
    masks[(rx, ry)] = (l, r)
W, H = 320, 400
prims = m.tri_full(W, H)
agree = 0
for (rx, ry), (l, r) in masks.items():
    x0, y0 = 32 * rx, 16 * ry
    ml = sum(1 << k for k, tr in enumerate(prims) if m.overlaps(tr, x0, y0, x0 + 16, y0 + 16))
    mr = sum(1 << k for k, tr in enumerate(prims) if m.overlaps(tr, x0 + 16, y0, x0 + 32, y0 + 16))
    agree += (ml, mr) == (l, r)
print('regions', len(masks), 'model masks equal to the dump', agree)
miss = []
for ty in range(25):
    for tx in range(10):
        l, r = masks[(tx, ty)]
        for b in range(16):
            for a in range(32):
                X, Y = 32 * tx + a, 16 * ty + b
                s = SUBSAMPLE_OFFSETS[a % 2 + 2 * (b % 2)]
                P = ((32 * tx + a // 2) * 16 + s[0], (16 * ty + b // 2) * 16 + s[1])
                mk = l if a < 16 else r
                if not any(m.covers(tr, *P) for k, tr in enumerate(prims) if mk >> k & 1):
                    miss.append((Y, X))
miss.sort()
print('background with the dump masks', len(miss), 'first', miss[0][::-1] if miss else None)
