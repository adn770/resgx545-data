import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q282_r10_tab import *
from q282_r10_rules import *
import collections
A,B,W,H,J=table(FIT)
p=dict(fam="bf",dec="half",M=11,align="max",qin="floor",form="A",X=8,qprod="floor",qsum="none",out="rne")
o=apply_rule(A,B,W,p); bad=o!=H
print(bad.sum())
d=(H-o)
print(collections.Counter(d[bad].tolist()))
a=decode(A,p); b=decode(B,p)
ea=expo(a); eb=expo(b)
print("by exp(a)-exp(b):")
c=collections.Counter(); t=collections.Counter()
for x,y in zip((ea-eb)[bad],(ea-eb)): pass
for de in range(-12,13):
    m=(ea-eb)==de
    if m.sum(): print(de,m.sum(),(bad&m).sum(), "bad frac %.3f"%((bad&m).sum()/m.sum()))
print("by W:")
for k in (0,1,2,8,16,31,32,33,48,62,63): 
    m=W==k; print(k,m.sum(),(bad&m).sum())
print("a>b:",(bad&(a>b)).sum(),(a>b).sum(),"a<b",(bad&(a<b)).sum(),(a<b).sum())
for i in np.where(bad)[0][:25]: print(A[i],B[i],W[i],a[i],b[i],hex(H[i]),hex(o[i]))
