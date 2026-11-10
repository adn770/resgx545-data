import gzip, numpy as np, collections
D='/Users/jtorra/src/scratch/resgx545/closing/s3/out/20261110-003114/s3-a-safe/'
b=gzip.open(D+'a4-ctl-320x400-te20.tri.param.bin.gz').read()
a=np.frombuffer(b,dtype='<u4')
var=collections.defaultdict(list)
for off in range(0x400,0xa000,0x80):
    blk=a[off//4:off//4+32]
    if blk.any():
        k=' '.join('%08x'%x for x in blk[:np.max(np.nonzero(blk)[0])+1])
        var[k].append(off)
for k,v in var.items():
    print(len(v), [hex(x) for x in v][:12], '\n   ', k)
for base in (0x422000,0x423000,0x463000):
    blk=a[base//4:base//4+1024]
    nz=np.nonzero(blk)[0]
    print(hex(base), len(nz), ' '.join('%x:%08x'%(base+4*i,blk[i]) for i in nz[:40]))
