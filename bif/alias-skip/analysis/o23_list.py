import sys,gzip,collections,pathlib
sys.path.insert(0,'recompute'); sys.path.insert(0,'../p1131/recompute')
import recompute_p1131 as r
from recompute_p1134 import pixel_rows, rd, f32, BG
d=pathlib.Path('dumps/o23-order'); cfg=sys.argv[1][4:]; K=int(sys.argv[2])
td=rd(d/f'o23d-{cfg}-x.tadata.bin.gz')
rs=r.regions(td); L=[(x//32,y//16) for (i,x,y,fl,st) in rs if st]   # stream regions in index order
pos={t:i for i,t in enumerate(L)}
rx=pixel_rows(rd(d/f'o23d-{cfg}-x.txt.gz')); ry=pixel_rows(rd(d/f'o23d-{cfg}-y.txt.gz'))
H=len(rx);W=len(rx[0]); c=collections.defaultdict(collections.Counter)
for y in range(H):
  for x in range(W):
    vx,vy=rx[y][x],ry[y][x]
    if vx==BG or vy==BG or (vx&15)!=K or (vy&15)!=K: continue
    sx=round(f32(vx&0xffff0000)*W/2+W/2-0.5); sy=round(f32(vy&0xffff0000)*H/2+H/2-0.5)
    if sx%32!=x%32 or sy%16!=y%16: c['x']['inplace']+=1; continue
    s=(sx//32,sy//16); dd=(x//32,y//16)
    c[(sy%16)//8][(pos.get(s,'?'),)] if False else None
    c['half%d'%((sy%16)//8)][pos.get(s,-99)-pos.get(dd,-99) if dd in pos else 'dest-not-in-L']+=1
print(cfg,K,'L=',len(L)); 
for k,v in sorted(c.items(),key=str): print(' ',k,dict(v))
# detail: for each source region, list dest regions and index positions among all headers
allr=[(i,(x//32,y//16),fl,st) for (i,x,y,fl,st) in rs]
idx={t:i for (i,t,fl,st) in allr}; info={t:(i,fl,hex(st)) for (i,t,fl,st) in allr}
cc=collections.defaultdict(collections.Counter)
for y in range(H):
  for x in range(W):
    vx,vy=rx[y][x],ry[y][x]
    if vx==BG or vy==BG or (vx&15)!=K or (vy&15)!=K: continue
    sx=round(f32(vx&0xffff0000)*W/2+W/2-0.5); sy=round(f32(vy&0xffff0000)*H/2+H/2-0.5)
    if sx%32!=x%32 or sy%16!=y%16: continue
    cc[(sx//32,sy//16,(sy%16)//8)][(x//32,y//16)]+=1
if len(sys.argv)>3:
  for s in sorted(cc, key=lambda t:idx.get((t[0],t[1]),0)): print(s,'hdr',info.get((s[0],s[1])),'->',[(d,idx.get(d),info.get(d)) for d in cc[s]],dict(cc[s]))
