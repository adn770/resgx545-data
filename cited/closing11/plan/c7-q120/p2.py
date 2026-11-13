from lib import *
import zst2 as Z, struct
n="z2y-f6"
d=dw("zst2",n); ref=dw("zst2",Z.ref_of(n))
for k in (0,):
    blk=d[k*512:k*512+48]
    b=b"".join(struct.pack("<I",v) for v in blk)
    print(b.hex(" ",1))
    for y in range(16):
        v=ref[Z.in_tile_index(0,y)]
        pat=struct.pack("<I",v)
        # find
        pos=[i for i in range(len(b)) if b[i:i+4]==pat]
        pos2=[i for i in range(len(b)) if b[i:i+3]==pat[:3]]
        print(y,f"{v:08x}",pos,pos2)
