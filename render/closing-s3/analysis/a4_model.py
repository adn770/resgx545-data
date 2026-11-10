"""Post hoc: E727's region model (resgx545-data texture/p1141/recompute/msaa_model.py, unchanged,
imported read-only) on the a4 control: 320x400, mode 2, TE 0x20000000, --tri-full."""
import sys
sys.path.insert(0, '/Users/jtorra/src/resgx545-data/texture/p1141/recompute')
import msaa_model as m
W, H = 320, 400
prims = m.tri_full(W, H)
print('prims (1/16 px)', prims)
for te in (0x20000000, 0xe0000000):
    out = m.predict(prims, W, H, 2, te)
    miss = sorted((y, x) for y in range(H) for x in range(W) if (x, y) not in out)
    print('te %#x: drawn %d background %d' % (te, len(out), len(miss)))
    if miss:
        print('  first (raster order) (%d, %d)' % (miss[0][1], miss[0][0]))
        tiles = {}
        for y, x in miss:
            tiles.setdefault((x // 32, y // 16), []).append((x, y))
        for k, v in sorted(tiles.items()):
            print('  tile', k, len(v), 'x', min(p[0] for p in v), '-', max(p[0] for p in v),
                  'y', min(p[1] for p in v), '-', max(p[1] for p in v))
        if len(miss) < 40:
            print('  pixels', [(x, y) for y, x in miss])
# the same with the TA's masks as dumped instead of the model's overlap test
