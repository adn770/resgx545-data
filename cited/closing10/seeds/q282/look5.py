import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from q282_r10_tab import *
from q282_r10_rules import *
import collections
A,B,W,H,J=table(FIT)
base=dict(fam="bf",dec="half",M=11,align="max",qin="floor",form="A",X=8,qprod="floor",qsum="none",out="rne")
o=apply_rule(A,B,W,base); ex=apply_rule(A,B,W,dict(base,qin="rne",M=40,X=8))  # exact (no loss)
bad=(o!=H)&(W>0)
print("bad W>0",bad.sum(),"hw==exact-lerp rne:",(bad&(H==ex)).sum(), "hw==o+1",(bad&(H==o+1)).sum(), "hw==ex+? other", (bad&(H!=ex)).sum())
# among all with W>0: where o!=ex (loss active) -> hw==o or ==ex?
act=(o!=ex)&(W>0)
print("loss-changing cases",act.sum(),"hw==o",(act&(H==o)).sum(),"hw==ex",(act&(H==ex)).sum(),"neither",(act&(H!=o)&(H!=ex)).sum())
a=decode(A,base); b=decode(B,base)
# neither cases: hw relative to o
nei=act&(H!=o)&(H!=ex)
print(collections.Counter((H-o)[nei].tolist()).most_common(8))
# is the mismatch tied to the mantissa fraction of the lerp (near a half-rounding boundary)?
l=a+(W/64)*(b-a)
hv=h2f(o); 
# ties: how close is exact-floored value to a rounding midpoint
for i in np.where(bad)[0][:15]:
    print(A[i],B[i],W[i],"o",hex(o[i]),"hw",hex(H[i]),"ex",hex(ex[i]))
