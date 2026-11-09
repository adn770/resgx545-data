import sys, math, collections, pathlib
sys.path.insert(0,'recompute')
from recompute_p1134 import pixel_rows, rd, f32, BG
d=pathlib.Path('dumps/o23-tiles'); cfg=sys.argv[1]; K=int(sys.argv[2])
rx=pixel_rows(rd(d/(cfg+'-x.txt.gz'))); ry=pixel_rows(rd(d/(cfg+'-y.txt.gz')))
H=len(rx);W=len(rx[0]); c=collections.Counter(); per=collections.defaultdict(collections.Counter)
for y in range(H):
  for x in range(W):
    vx,vy=rx[y][x],ry[y][x]
    if vx==BG or vy==BG or (vx&15)!=K or (vy&15)!=K: continue
    sx=round(f32(vx&0xffff0000)*W/2+W/2-0.5); sy=round(f32(vy&0xffff0000)*H/2+H/2-0.5)
    if sx%32!=x%32 or sy%16!=y%16: c['inplace-differs']+=1; continue
    v=(x//32-sx//32, y//16-sy//16); c[v]+=1; per[(sx//32,sy//16)][v]+=1
print(sorted(c.items(), key=lambda a:-a[1]))
for t in sorted(per, key=lambda t:(t[1],t[0])): print(t, dict(per[t]))
