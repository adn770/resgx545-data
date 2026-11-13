# SPDX-License-Identifier: MIT
# lead/w10_look.py (numpy; post hoc, Mac only): E977 z242-a-f0 (word 10 = 0.5) against E981 z2-a-f0
# (word 10 = 0.25), the kept dumps of resgx545-data 1324301be: where the 0.25 ramp is 0.6 of the
# 0.5 one. Fixes zw's mask (gen/zbg.py). Usage: python3 -I -B lead/w10_look.py > lead/w10_look.out
import gzip, struct, glob, sys
D = "/Users/jtorra/src/resgx545-data/render"
a = glob.glob(D + "/closing-r9-x/out/*/zls/z242-a-f0.depth.1.bin.gz")[0]
b = glob.glob(D + "/closing-r9-z2/out/*/z2/z2-a-f0.depth.1.bin.gz")[0]
def ld(p):
    raw = gzip.open(p).read()
    return struct.unpack("<%dI" % (len(raw)//4), raw)
A, B = ld(a), ld(b)
f = lambda v: struct.unpack("<f", struct.pack("<I", v))[0]
fb = lambda x: struct.unpack("<I", struct.pack("<f", x))[0]
n = 32768
exact = 0; maxrel = 0; ulps = {}
for i in range(n):
    za, zb = f(A[i]), f(B[i])
    p = fb(0.6 * za)
    d = B[i] - p
    ulps[d] = ulps.get(d, 0) + 1
    if za: maxrel = max(maxrel, abs(zb/za - 0.6))
print(len(A), len(B), "ulp diffs of 0.6*z(0.5) vs z(0.25):", sorted(ulps.items())[:20], "maxrel", maxrel)
# t model: z(0.5) == (x+0.5)/512 ?
from itertools import product
def iti(x,y):
    i=0
    for k in range(4): i |= (y>>k&1)<<(2*k) | (x>>k&1)<<(2*k+1)
    return i | (x>>4&1)<<8
bad=0; ul={}
for y in range(128):
    for x in range(256):
        k = 512*((y>>4)*8+(x>>5)) + iti(x,y)
        t = (x+0.5)/512
        d = A[k]-fb(t); ul[d]=ul.get(d,0)+1
print("z(0.5) - (x+.5)/512 ulps:", sorted(ul.items())[:20])
print("--- z(0.25) along y=0 and y=127")
for y in (0, 64, 127):
    row = []
    for x in (0, 1, 2, 3, 64, 128, 200, 255):
        k = 512*((y>>4)*8+(x>>5)) + iti(x,y)
        row.append((x, f(B[k]), f(B[k])/((x+0.5)/512)))
    print(y, row)
import numpy as np
X=[];Z=[]
for y in range(128):
    for x in range(256):
        k = 512*((y>>4)*8+(x>>5)) + iti(x,y)
        X.append((x+0.5, y+0.5, 1.0)); Z.append(f(B[k]))
X=np.array(X); Z=np.array(Z)
c,res,_,_=np.linalg.lstsq(X,Z,rcond=None)
print("fit z = a x + b y + c:", c, "max resid", np.abs(X@c-Z).max())
print("--- map of pixels off 0.6 t (rel > 1e-6)")
off = np.zeros((128,256),bool)
for y in range(128):
    for x in range(256):
        k = 512*((y>>4)*8+(x>>5)) + iti(x,y)
        t=(x+0.5)/512
        off[y,x] = abs(f(B[k])/(0.6*t)-1) > 1e-6
print("off count", off.sum())
for y in range(0,128,8):
    print(y, "".join("#" if off[y,x] else "." for x in range(0,256,4)))
ys,xs=np.nonzero(off); print("min x+2y?", (xs+2*ys).min(), "x/512+y/256 min", (xs/512+ys/256).min())
print("--- interior ulps vs fb(0.6 t) (double), x/512+y/256 <= 0.75")
ul={}
for y in range(128):
    for x in range(256):
        if (x+0.5)/512+(y+0.5)/256 > 0.75: continue
        k = 512*((y>>4)*8+(x>>5)) + iti(x,y)
        d = B[k]-fb(0.6*(x+0.5)/512); ul[d]=ul.get(d,0)+1
print(sorted(ul.items()))
v = [f(B[512*((y>>4)*8+(x>>5)) + iti(x,y)]) for (x,y) in [(255,127),(240,127),(255,120),(220,127)]]
print("corner values", v)
