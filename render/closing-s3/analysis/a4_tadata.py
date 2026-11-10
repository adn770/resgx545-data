import gzip, sys, numpy as np
sys.path.insert(0, '/Users/jtorra/src/scratch/resgx545/closing/s3/score')
import s3lib
D='/Users/jtorra/src/scratch/resgx545/closing/s3/out/20261110-003114/s3-a-safe/'
b=gzip.open(D+'a4-ctl-320x400-te20.tri.tadata.bin.gz').read()
a=np.frombuffer(b,dtype='<u4')
print('len',hex(len(b)))
for wh in [(320,400),(544,400)]:
    print(wh, {k:hex(v) if k!='n' else v for k,v in s3lib.layout(*wh).items()})
nz=np.nonzero(a)[0]
print('nonzero dwords',len(nz))
# per page counts
for p in range(len(b)//4096):
    c=np.count_nonzero(a[p*1024:(p+1)*1024])
    print('page',hex(p*4096),c)
for rs in (0x1800,0x2400):
    print('slots rs',hex(rs), s3lib.tadata_slots(b,0x4000,rs))
