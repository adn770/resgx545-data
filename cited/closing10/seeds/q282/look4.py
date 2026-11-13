import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q282_r10_tab import *
from q282_r10_rules import *
import collections
A,B,W,H,J=table(FIT)
base=dict(fam="bf",dec="half",M=11,align="max",qin="floor",form="A",X=8,qprod="floor",qsum="none",out="rne")
ok={}
for M in range(9,17):
    p=dict(base,M=M); ok[M]=(apply_rule(A,B,W,p)==H)
o11=ok[11]; bad=~o11
print("bad at 11:",bad.sum()," fixed by M=12:",(bad&ok[12]).sum()," by 13:",(bad&ok[13]).sum()," by 16:",(bad&ok[16]).sum(), "ok at 11 but fail at 12:",(o11&~ok[12]).sum())
a=decode(A,base); b=decode(B,base)
# the exponent diff and which is larger for bad vs ok where flooring is active
ea,eb=expo(a),expo(b); sm=np.where(a>=b,b,a); big=np.where(a>=b,a,b)
ws=np.where(a>=b,W/64,1-W/64)  # weight of small
act = np.floor(sm/ (2.0**(np.maximum(ea,eb)-11)))*(2.0**(np.maximum(ea,eb)-11))!=sm   # flooring active
print("active",act.sum(),"bad among active",(bad&act).sum(),"bad inactive",(bad&~act).sum())
for k in (0,1,2,8,16,32,48,62,63):
    m=act&(W==k); print("W",k,"active",m.sum(),"bad",(bad&m).sum())
# bad for active: by weight of the small operand ws
for q in (0,1/64,2/64,.25,.5,.75,62/64,63/64,1.0):
    m=act&(np.abs(ws-q)<1e-9); print("ws",q,m.sum(),(bad&m).sum())
