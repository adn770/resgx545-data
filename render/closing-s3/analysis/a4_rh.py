import gzip, numpy as np
D='/Users/jtorra/src/scratch/resgx545/closing/s3/out/20261110-003114/s3-a-safe/'
b=gzip.open(D+'a4-ctl-320x400-te20.tri.tadata.bin.gz').read()
a=np.frombuffer(b,dtype='<u4')
r=a[0x4000//4:0x6000//4]
for i in range(0,len(r),12):
    row=r[i:i+12]
    if row.any(): print(hex(0x4000+4*i), ' '.join('%08x'%x for x in row))
