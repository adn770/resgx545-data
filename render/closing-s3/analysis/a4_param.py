import gzip, numpy as np
D='/Users/jtorra/src/scratch/resgx545/closing/s3/out/20261110-003114/s3-a-safe/'
b=gzip.open(D+'a4-ctl-320x400-te20.tri.param.bin.gz').read()
a=np.frombuffer(b,dtype='<u4')
nz=np.nonzero(a)[0]
print(len(b), hex(len(b)), 'nonzero', len(nz))
# runs of nonzero pages
pages=sorted(set((nz*4)//4096))
print('pages', [hex(p*4096) for p in pages][:80], len(pages))
