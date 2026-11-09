import sys, re, math, collections, pathlib
sys.path.insert(0,'recompute')
from recompute_p1134 import pixel_rows, rd, f32, BG
d=pathlib.Path('dumps/o23-tiles'); cfg=sys.argv[1]; K=int(sys.argv[2])
rx=pixel_rows(rd(d/(cfg+'-x.txt.gz'))); ry=pixel_rows(rd(d/(cfg+'-y.txt.gz')))
H=len(rx);W=len(rx[0]); tw=math.ceil(W/32)
c=collections.defaultdict(collections.Counter)
for y in range(H):
  for x in range(W):
    vx,vy=rx[y][x],ry[y][x]
    if vx==BG or vy==BG or (vx&15)!=K or (vy&15)!=K: continue
    sx=round(f32(vx&0xffff0000)*W/2+W/2-0.5); sy=round(f32(vy&0xffff0000)*H/2+H/2-0.5)
    ns=(sy//16)*tw+sx//32; nd=(y//16)*tw+x//32
    c[(ns, sy%16, sx%32//8)][ns-nd]+=1
for k,v in sorted(c.items()): print(k,dict(v))
