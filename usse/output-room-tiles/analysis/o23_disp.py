import re,sys,struct,collections
f=sys.argv[1]
rows={}
for line in open(f):
    m=re.match(r"probe (\S+): row (\d+): (.*)$",line)
    if m: rows.setdefault(m.group(1),{})[int(m.group(2))]=[int(v,16) for v in m.group(3).split()]
def fl(v): return struct.unpack('<f',struct.pack('<I',v&0xffff0000))[0]
def src(v,W):
    x=fl(v); return round(x*W/2+W/2-0.5)  # pixel index from normalized centre
for k in sorted(rows):
    r=rows[k]; H=len(r); W=len(r[0])
    ax = 'x' if int(k.split('__')[1])%2==0 else 'y'
    d=collections.defaultdict(collections.Counter)
    for y in range(H):
        for x in range(W):
            v=r[y][x]
            if v==0xff203040: continue
            tag=v&0xffff
            if not 1<=tag<=8: d['bad'][v]+=1; continue
            s=src(v,W if ax=='x' else H)
            d[tag][(x if ax=='x' else y)-s]+=1
    print(k,ax,{t:dict(sorted(c.items())) for t,c in sorted(d.items(),key=lambda a:str(a[0])) if t!='bad'}, 'bad',sum(d['bad'].values()))
