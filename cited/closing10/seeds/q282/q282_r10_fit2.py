"""Second search: weighted-term alignment (terms aligned to the larger term's exponent), plus qin none."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import json, itertools, collections
from q282_r10_tab import *
from q282_r10_rules import *
A,B,W,H,J = table(FIT)
def run(A,B,W,p):
    a,b=decode(A,p),decode(B,p); wb=W/64.0; wa=1-wb
    if p["fam"]=="bfin0":   # inputs unquantised, aligned grid of the max, applied to the exact weighted terms
        g=grid_for(a,b,p); 
        ta,tb=wa*a,wb*b
        r=rnd(ta/g,p["qt"])*g+rnd(tb/g,p["qt"])*g
        if p["qs"]!="none": r=rnd(r/g,p["qs"])*g
    elif p["fam"]=="bfterm": # grid from the larger weighted term
        ta,tb=wa*a,wb*b
        e=np.maximum(expo(np.where(wa==0,1e-300,ta)),expo(np.where(wb==0,1e-300,tb)))
        # a zero-weight term contributes nothing and does not set the exponent
        ea=np.where(wa==0,-10**6,expo(ta)); eb=np.where(wb==0,-10**6,expo(tb)); e=np.maximum(ea,eb)
        g=2.0**(e-p["M"])
        r=rnd(ta/g,p["qt"])*g+rnd(tb/g,p["qt"])*g
        if p["qs"]!="none": r=rnd(r/g,p["qs"])*g
    elif p["fam"]=="bfdiff":  # a + w*(b-a): diff aligned/truncated on the grid of max(a,b), zero weight exact
        g=grid_for(a,b,p)
        d=rnd(wb*(b-a)/g,p["qt"])*g
        r=a+d
        if p["qs"]!="none": r=rnd(r/g,p["qs"])*g
    elif p["fam"]=="bfdiffb":  # base the larger operand: result = big + w'*(small-big)
        g=grid_for(a,b,p)
        big=np.where(a>=b,a,b); small=np.where(a>=b,b,a); wsm=np.where(a>=b,wb,wa)
        d=rnd(wsm*(small-big)/g,p["qt"])*g
        r=big+d
        if p["qs"]!="none": r=rnd(r/g,p["qs"])*g
    return half_bits(np.maximum(r,0),p["out"])
res=[];n=0
for fam in ("bfin0","bfterm","bfdiff","bfdiffb"):
  for dec in ("half","f32"):
    for M in range(8,19):
      for al in (("max","a","b") if fam!="bfterm" else ("max",)):
        for qt in ("floor","rne","ceil"):
          for qs in ("none","floor","rne"):
            for out in ("rne","rz","ru"):
              p=dict(fam=fam,dec=dec,M=M,align=al,qt=qt,qs=qs,out=out); n+=1
              o=run(A,B,W,p); res.append((int((o==H).sum()),p))
res.sort(key=lambda t:-t[0])
print("rules tried",n)
for s,p in res[:12]: print(s,json.dumps(p,sort_keys=True))
json.dump(res[:100],open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"q282_r10_top2.json"),"w"))
