from lib import *
import zst2 as Z
for n in ("z2y-f6",):
    d=dw("zst2",n); ref=dw("zst2",Z.ref_of(n))
    print([f"{ref[Z.in_tile_index(0,y)]:08x}" for y in range(16)])
    print([f"{ref[512+Z.in_tile_index(0,y)]:08x}" for y in range(16)])
    for k in range(4):
        blk=d[k*512:(k+1)*512]
        idx=[i for i,v in enumerate(blk) if v!=FILL]
        print(k,idx)
        print(" ".join(f"{blk[i]:08x}" for i in idx))
