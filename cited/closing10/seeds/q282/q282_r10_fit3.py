"""Third search: lerp as base + w' (other - base); base exact, the other operand floored on the shared grid."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import json, collections
from q282_r10_tab import *
from q282_r10_rules import *
def run(A,B,W,p):
    a,b=decode(A,p),decode(B,p); wb=W/64.0
    g=grid_for(a,b,p)
    bs=p["base"]
    if bs=="a": base,oth,wo=a,b,wb
    elif bs=="b": base,oth,wo=b,a,1-wb
    elif bs=="big": m=a>=b; base=np.where(m,a,b); oth=np.where(m,b,a); wo=np.where(m,wb,1-wb)
    elif bs=="small": m=a<b; base=np.where(m,a,b); oth=np.where(m,b,a); wo=np.where(m,wb,1-wb)
    elif bs=="wmax": m=wb<=0.5; base=np.where(m,a,b); oth=np.where(m,b,a); wo=np.where(m,wb,1-wb)
    if p["qo"]!="none": oth=rnd(oth/g,p["qo"])*g
    if p["qb"]!="none": base=rnd(base/g,p["qb"])*g
    d=oth-base
    pr=wo*d
    if p["qt"]!="none":
        s=g/2.0**p["X"]; pr=rnd(pr/s,p["qt"])*s
    r=base+pr
    return half_bits(np.maximum(r,0),p["out"])
if __name__=="__main__":
    A,B,W,H,J = table(FIT)
    res=[];n=0
    for base in ("a","b","big","small","wmax"):
     for dec in ("half","f32"):
      for M in range(9,18):
       for al in ("max","a","b"):
        for qo in ("floor","rne","none"):
         for qb in ("none","floor"):
          for qt,X in [("none",0)]+[(q,x) for q in ("floor","rne") for x in (0,2,4,8)]:
           for out in ("rne","rz","ru"):
            p=dict(base=base,dec=dec,M=M,align=al,qo=qo,qb=qb,qt=qt,X=X,out=out); n+=1
            o=run(A,B,W,p); res.append((int((o==H).sum()),p))
    res.sort(key=lambda t:-t[0])
    print("rules tried",n)
    for s,p in res[:12]: print(s,json.dumps(p,sort_keys=True))
    json.dump(res[:100],open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"q282_r10_top3.json"),"w"))
