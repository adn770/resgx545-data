from lib import *
import struct
for n in ("s00","sff","sa5"):
    s=dw("zst2","z2x-f7-"+n)
    S={"s00":0,"sff":255,"sa5":0xa5}[n]
    for k in (0,1):
        b=b"".join(struct.pack("<I",v) for v in s[256*k:256*k+12])
        print(n,k,[i for i in range(48) if b[i]==0x3f],[i for i in range(48) if b[i]==0x1f],[i for i in range(48) if b[i]==S and S not in(0x3f,0x1f)])
