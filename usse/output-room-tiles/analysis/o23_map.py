import sys, gzip, re, math, struct, collections
sys.path.insert(0,'recompute')
from recompute_p1134 import pixel_rows, rd, f32, BG
import pathlib
d=pathlib.Path('dumps/o23-tiles'); cfg=sys.argv[1]; K=int(sys.argv[2])
rx=pixel_rows(rd(d/(cfg+'-x.txt.gz'))); ry=pixel_rows(rd(d/(cfg+'-y.txt.gz')))
H=len(rx);W=len(rx[0]); c=collections.Counter()
for y in range(H):
  for x in range(W):
    vx,vy=rx[y][x],ry[y][x]
    if vx==BG or vy==BG: continue
    if (vx&15)!=K or (vy&15)!=K: continue
    sx=round(f32(vx&0xffff0000)*W/2+W/2-0.5); sy=round(f32(vy&0xffff0000)*H/2+H/2-0.5)
    c[((sx//32,sy//16),(x//32,y//16), (sx%32==x%32 and sy%16==y%16))]+=1
for k,v in sorted(c.items()): print(k,v)
