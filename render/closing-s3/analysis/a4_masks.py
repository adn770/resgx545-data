"""a4: per 16x16 tile, the TA's primitive mask (CSTREAM 0x88/0x90 forms, glossary G0463) against
the pixels each of the two primitives of the clipped quad covers (vertex fields decoded below)."""
import gzip, numpy as np
D='/Users/jtorra/src/scratch/resgx545/closing/s3/out/20261110-003114/s3-a-safe/'
p=np.frombuffer(gzip.open(D+'a4-ctl-320x400-te20.tri.param.bin.gz').read(),dtype='<u4')
t=np.frombuffer(gzip.open(D+'a4-ctl-320x400-te20.tri.tadata.bin.gz').read(),dtype='<u4')
raw=p[16:26].tobytes()
for v in range(4):
    bb=raw[10*v:10*v+10]
    A=int.from_bytes(bb[0:3],'little'); B=int.from_bytes(bb[3:6],'little')
    z=np.frombuffer(bb[6:10],dtype='<f4')[0]
    print('vertex',v,'fieldA %#x -> %g'%(A,A/256-4096),'fieldB %#x -> %g'%(B,B/256-4096),'z',z)
masks={}
for i in range(0x4000//4,0x6000//4,3):
    d0,d1=int(t[i]),int(t[i+1])
    if (d0>>24)&2 or d1==0: continue
    rx,ry=((d0>>16)&0xff)//2,(d0&0xfff)//2
    s=p[(d1-0x1000)//4:(d1-0x1000)//4+3]
    w=int(s[0]); form=(w>>16)&0xff
    if form==0x90: l=r=3
    elif form==0x88: l,r=int(s[2])&0xffff,int(s[2])>>16
    else: raise SystemExit('form %x'%form)
    masks[(2*rx,ry)]=l; masks[(2*rx+1,ry)]=r
print('tiles',len(masks))
def cover(c, cx, cy):
    # prim0 upper-left: x + 0.8 y < c ; prim1: >= c (exact edge: both edge pixels taken by one)
    s=cx+0.8*cy
    return (s<c), (s>=c)
def compare(c, verbose=False):
    bad=[]
    for (tx,ty),m in masks.items():
        xs=np.arange(16*tx,16*tx+16)+0.5; ys=np.arange(16*ty,16*ty+16)+0.5
        X,Y=np.meshgrid(xs,ys)
        p0,p1=cover(c,X,Y)
        need=(1 if p0.any() else 0)|(2 if p1.any() else 0)
        if need!=m:
            miss=need&~m
            lost=(p0 if miss&1 else np.zeros_like(p0))|(p1 if miss&2 else np.zeros_like(p1))
            # pixels drawn by no listed primitive
            drawn=(p0 & bool(m&1))|(p1 & bool(m&2))
            n=int((~drawn).sum())
            bad.append(((tx,ty),m,need,n, (int(X[~drawn].min()-0.5),int(Y[~drawn].min()-0.5)) if n else None))
    return bad
for c in (400.0,):
    b=compare(c)
    print('c',c,'tiles whose mask differs',len(b))
    for x in sorted(b,key=lambda r:(r[0][1],r[0][0])): print('  tile',x[0],'px',(16*x[0][0],16*x[0][1]),'mask',x[1],'needed',x[2],'pixels drawn by none',x[3],'first',x[4])
