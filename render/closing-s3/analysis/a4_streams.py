import gzip, numpy as np
D='/Users/jtorra/src/scratch/resgx545/closing/s3/out/20261110-003114/s3-a-safe/'
b=gzip.open(D+'a4-ctl-320x400-te20.tri.param.bin.gz').read()
a=np.frombuffer(b,dtype='<u4')
def show(off,n):
    print(hex(off), ' '.join('%08x'%x for x in a[off//4:off//4+n]))
show(0,32)
for off in range(0x1000,0x2000,0x40):
    if a[off//4:off//4+16].any(): show(off,16)
for off in (0x2000,0x2080,0x2100,0x3000,0x3080,0x3800,0x3880,0x3900,0x8800,0x8880,0xa380):
    show(off,32)
