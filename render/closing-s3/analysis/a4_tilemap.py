import gzip, numpy as np
D='/Users/jtorra/src/scratch/resgx545/closing/s3/out/20261110-003114/s3-a-safe/'
p=np.frombuffer(gzip.open(D+'a4-ctl-320x400-te20.tri.param.bin.gz').read(),dtype='<u4')
t=np.frombuffer(gzip.open(D+'a4-ctl-320x400-te20.tri.tadata.bin.gz').read(),dtype='<u4')
cls={}
names={}
tiles={}
for i in range(0x4000//4,0x6000//4,3):
    d0,d1=int(t[i]),int(t[i+1])
    if d0==0 and d1==0: continue
    x=(d0>>16)&0xff; y=d0&0xff; mt=(d0>>12)&0xf; fl=d0>>24
    tx,ty=x//2,y//2
    if fl&0x02: continue
    off=d1-0x1000
    blk=p[off//4:off//4+3]
    key=' '.join('%08x'%v for v in blk)
    tiles[(tx,ty)]=(key,mt,hex(d1))
keys=sorted(set(v[0] for v in tiles.values()))
sym={k:c for k,c in zip(keys,'ABCDEFGH')}
for k in keys: print(sym[k],k)
print('tiles',len(tiles))
for ty in range(25):
    print('%2d'%ty, ''.join(sym[tiles[(tx,ty)][0]] if (tx,ty) in tiles else '.' for tx in range(10)))
print(tiles[(9,8)])
