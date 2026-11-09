import sys, re, math, collections, pathlib
sys.path.insert(0,'recompute')
from recompute_p1134 import pixel_rows, rd, f32, BG
d=pathlib.Path('dumps/o23-tiles'); cfg=sys.argv[1]; K=int(sys.argv[2])
for ax in 'xy':
    r=pixel_rows(rd(d/f'{cfg}-{ax}.txt.gz')); H=len(r); W=len(r[0]); c=collections.Counter()
    for y in range(H):
        for x in range(W):
            v=r[y][x]
            if v==BG or (v&15)!=K: continue
            if ax=='x':
                s=round(f32(v&0xffff0000)*W/2+W/2-0.5); c[(s//32, x//32, s%32==x%32)]+=1
            else:
                s=round(f32(v&0xffff0000)*H/2+H/2-0.5); c[(s//16, y//16, s%16==y%16)]+=1
    print(ax, sorted(c.items()))
