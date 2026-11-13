from lib import *
import struct,sys
n=sys.argv[1]; blkn=int(sys.argv[2]); bs=int(sys.argv[3]); per=int(sys.argv[4]) if len(sys.argv)>4 else 12
d=dw("zst2",n)
blk=d[blkn*bs:(blkn+1)*bs]
last=max(i for i,v in enumerate(blk) if v!=FILL)
for i in range(0,last+1,per):
    print(f"{i:4d}"," ".join(f"{v:08x}" if v!=FILL else "........" for v in blk[i:i+per]))
