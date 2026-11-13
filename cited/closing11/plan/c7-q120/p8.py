from lib import *
import hashlib
R9="/Users/jtorra/src/resgx545-data/render/closing-r9-x/out/20261113-081821"
def runs(d):
    r=[];s=None
    for i,v in enumerate(d+[FILL]):
        if v!=FILL and s is None: s=i
        if v==FILL and s is not None: r.append((s,i-1)); s=None
    return r
S={}
for tag,d in (("r10 z2y-f7",dw("zst2","z2y-f7")),("r10 z2d-f7",dw("zst2","z2d-f7")),("r9 f7-s",dw("zst","z120-f7-s",R9)),("r9 f7-m",dw("zst","z120-f7-m",R9)),
  ("s00",dw("zst2","z2x-f7-s00")),("sff",dw("zst2","z2x-f7-sff")),("sa5",dw("zst2","z2x-f7-sa5"))):
    S[tag]=d
    print(tag,len(d),sum(v!=FILL for v in d),runs(d), hashlib.sha256(bytes(str(d),'ascii')).hexdigest()[:8])
print(S["r10 z2y-f7"]==S["r10 z2d-f7"], S["r10 z2y-f7"]==S["r9 f7-s"])
a=S["r10 z2y-f7"];b=S["r10 z2d-f7"]
print([(i,f"{a[i]:08x}",f"{b[i]:08x}") for i in range(len(a)) if a[i]!=b[i]])
