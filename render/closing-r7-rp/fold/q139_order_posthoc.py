#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/q139_order_posthoc.py: added at the fold (2026-11-12), AFTER the held-out read
(fold/q139_heldout.out), so post hoc and not held out.  R7-BLK's one held-out miss is stride 4; this
replays R7-BLK's slot rule (fold/q139_fit.py) under five write orders over all 21 fit, replicate
and held-out rows and counts the rows whose every target tile has the predicted header slot (or
none): row by row (R7-BLK's own), by macrotile N, by 4 x 4 tile block (block rows of four tile
rows, blocks across, rows and columns inside), the same with the block's rows and columns by bits,
and by tile-row pairs.

  q139_order_posthoc.py        (from the session directory; reads out/20261112-205431/q139)
"""
import sys,gzip,re
import os
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(KP)
sys.path.insert(0, "score"); sys.path.insert(0, "fold")
import lib_dump as L, q139_fit as F
def predict(w,h,args,key):
    tx,ty=F.cdiv(w,32),F.cdiv(h,16); m1,m2,s=F.words(w,h,args); n,bx,by=F.bounds(m1,m2); fx,fy=bx[1],by[1]
    ws=[]
    for r in range(max(ty,by[-1]+fy)):
        for c in range(max(tx,bx[-1]+fx)):
            mcol,lx=F.place(c,bx); mrow,ly=F.place(r,by)
            sl=(mcol*n+mrow)*s+((ly>>2)*(fx>>2)+(lx>>2))*16+(r&3)*4+(c&3)
            ws.append((key(r,c,mcol,mrow,n),sl,(c,r)))
    ws.sort(key=lambda t:t[0]); own={}
    for _,sl,t in ws: own[sl]=t
    pr={(c,r):None for r in range(ty) for c in range(tx)}
    for sl,t in own.items():
        if t in pr: pr[t]=sl
    return pr
keys={"raster":lambda r,c,mc,mr,n:(r,c),"N":lambda r,c,mc,mr,n:(mc*n+mr,r,c),"rowblk":lambda r,c,mc,mr,n:(r>>2,c>>2,r,c),
      "blkcol":lambda r,c,mc,mr,n:(r>>2,c>>2,r&3,c&3),"pair":lambda r,c,mc,mr,n:(r>>1,c,r)}
tab=F.table()
for k,f in keys.items():
    res=[]
    for name,(st,args) in sorted(tab.items()):
        if st not in("fit","replicate","heldout"): continue
        w=int(re.search(r"--width (\d+)",args).group(1)); h=int(re.search(r"--height (\d+)",args).group(1))
        td=gzip.open("out/20261112-205431/q139/%s.tri.tadata.bin.gz"%name,"rb").read()
        obs=L.observed_slots(td,L.header_base(td),w,h); pr=predict(w,h,args,f)
        ok=sum(1 for t,v in pr.items() if (v is None and not obs.get(t)) or (v is not None and obs.get(t)==[v]))
        res.append(ok==len(pr))
    print(k, sum(res), "of", len(res))
