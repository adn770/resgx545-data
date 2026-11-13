from lib import *
import zst2 as Z, struct,sys
n=sys.argv[1]; blkn=int(sys.argv[2]); nd=int(sys.argv[3])
d=dw("zst2",n)
blk=d[blkn*(512 if n[-1]=='6' else 640):][:nd]
b=b"".join(struct.pack("<I",v) for v in blk)
for g in range(0,len(b),48):
    print(g//48," ".join(b[g+i:g+i+4].hex() for i in range(0,min(48,len(b)-g),4)))
