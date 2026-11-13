import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import json
from q282_r10_tab import *
from q282_r10_rules import *
A,B,W,H,J = table(FIT)
res=[]; n=0
for p in grid():
    n+=1
    try: o=apply_rule(A,B,W,p)
    except Exception as e: print("ERR",p,e); continue
    ok=(o==H); res.append((int(ok.sum()), p))
res.sort(key=lambda t:-t[0])
print("rules tried",n,"of",len(A),"halves per fit set (4 jobs x 4096)")
import collections
fams=collections.Counter(p["fam"] for _,p in res); print(dict(fams))
for fam in ("bf","fx","mant"):
    print("best",fam,[ (s,p) for s,p in res if p["fam"]==fam][:3])
print("TOP10"); 
for s,p in res[:10]: print(s,json.dumps(p,sort_keys=True))
json.dump([ (s,p) for s,p in res[:200]], open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"q282_r10_top.json"),"w"))
