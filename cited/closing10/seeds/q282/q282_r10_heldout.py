import sys, os, hashlib; HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import json
import numpy as np
from q282_r10_tab import h2f
from q282_r10_data import rows
from q282_r10_frozen import decode_half, stage
want=open(HERE+"/q282_r10_rule.sha256").read().split()[0]
assert hashlib.sha256(open(HERE+"/q282_r10_rule.json","rb").read()).hexdigest()==want, "rule changed"
def bits(v): return np.asarray(v,dtype=np.float64).astype(np.float16).view(np.uint16).astype(np.int64)
def two_stage(b, kx, ky, order):
    """b: 4 arrays of corner bytes (00,10,01,11); returns half values"""
    h=[decode_half(x) for x in b]
    if order=="XY":
        top=stage(h[0],h[1],kx); bot=stage(h[2],h[3],kx); return stage(top,bot,ky)
    l=stage(h[0],h[2],ky); r=stage(h[1],h[3],ky); return stage(l,r,kx)
def report(name, b, kx, ky, hw, tag):
    out={}
    for o in ("XY","YX"):
        r=bits(two_stage(b,kx,ky,o)); ok=(r==hw)
        out[o]=(int(ok.sum()), int(ok.reshape(-1,2).all(axis=1).sum()), ok)
        print(f"{name} [{tag}] {o}: halves {out[o][0]} of {len(hw)}, pixels {out[o][1]} of {len(hw)//2}")
    return out
res={}
for n in ("srgb-c1","srgb-c2"):
    R=rows(n)
    b=[np.array([t[k] for c,t,ix,iy,hw in R],dtype=np.float64) for k in range(4)]
    kx=np.array([ix for c,t,ix,iy,hw in R]); ky=np.array([iy for c,t,ix,iy,hw in R]); hw=np.array([r[4] for r in R])
    res[n]=report(n,b,kx,ky,hw,"HELD-OUT")
    ok=res[n]["XY"][2]; ky0=ky[0]
    print("   XY misses by ky:",np.unique(ky[~ok],return_counts=True)[1].tolist()[:5], "by kx bins:", np.histogram(kx[~ok],bins=8,range=(0,64))[0].tolist())
# E723 g-bl-st-b via the closing9 reader
sys.path.insert(0,"/Users/jtorra/src/scratch/resgx545/closing9/rank")
from q282_fit import corners, hw as hwread
rec=corners("g-bl-st-b"); pix=hwread("g-bl-st-b")
cb=[[],[],[],[]]; fxs=[]; fys=[]; hws=[]
for p,((c2,fx,fy),w) in enumerate(zip(rec,pix)):
    for c in (0,1):
        for k in range(4): cb[k].append(c2[c][k])
        fxs.append(fx); fys.append(fy); hws.append((w>>16*c)&0xFFFF)
b=[np.array(x,dtype=np.float64) for x in cb]; fx=np.array(fxs); fy=np.array(fys)
print("g-bl-st-b off-grid fx",int((fx*64!=np.floor(fx*64)).sum()),"fy",int((fy*64!=np.floor(fy*64)).sum()))
kx=np.floor(fx*64).astype(int); ky=np.floor(fy*64).astype(int)
res["g-bl-st-b"]=report("g-bl-st-b",b,kx,ky,np.array(hws),"HELD-OUT")
import collections
ok=res["g-bl-st-b"]["XY"][2]
print("   XY misses: kx==0",int((~ok&(kx==0)).sum()),"ky==0",int((~ok&(ky==0)).sum()),"both nonzero",int((~ok&(kx>0)&(ky>0)).sum()))
