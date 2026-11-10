"""Post hoc: E727's region model (unchanged) at the S3 A sizes, TE 0x20 and 0xe0, mode 2, --tri-full."""
import sys
sys.path.insert(0, '/Users/jtorra/src/resgx545-data/texture/p1141/recompute')
import msaa_model as m
for W, H in ((320, 400), (256, 160), (320, 128), (64, 64)):
    for te in (0x20000000, 0xe0000000):
        out = m.predict(m.tri_full(W, H), W, H, 2, te)
        miss = sorted((y, x) for y in range(H) for x in range(W) if (x, y) not in out)
        print('%dx%d te %#x background %d first %s' % (W, H, te, len(miss), miss[0][::-1] if miss else '-'))
