from lib import *
import zst2 as Z, struct
n="z2y-f6"
d=dw("zst2",n); ref=dw("zst2",Z.ref_of(n))
for k in (0,1):
    blk=d[k*512:k*512+48]
    b=b"".join(struct.pack("<I",v) for v in blk)
    for y in range(16):
        v=ref[512*k+Z.in_tile_index(0,y)]
        pat=struct.pack("<I",v)
        pos=[i for i in range(len(b)-1) if b[i:i+2]==pat[2:]]
        print(k,y,f"{v:08x}",pos)
