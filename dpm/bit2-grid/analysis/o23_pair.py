import re,sys,struct,collections
f=sys.argv[1]
rows={}
for line in open(f):
    m=re.match(r"probe (\S+): row (\d+): (.*)$",line)
    if m: rows.setdefault(m.group(1),{})[int(m.group(2))]=[int(v,16) for v in m.group(3).split()]
def fl(v): return struct.unpack('<f',struct.pack('<I',v&0xffff0000))[0]
def src(v,W): return round(fl(v)*W/2+W/2-0.5)
ks=sorted(rows)
for a in range(0,len(ks),2):
    rx,ry=rows[ks[a]],rows[ks[a+1]]; H=len(rx); W=len(rx[0])
    c=collections.defaultdict(collections.Counter)
    for y in range(H):
        for x in range(W):
            vx,vy=rx[y][x],ry[y][x]
            tx,ty=vx&0xffff,vy&0xffff
            if tx==ty and tx in (2,3):
                sx=src(vx,W); sy=src(vy,H)
                c[tx][(sx//32,sy//16,'->',x//32,y//16, 'inx',sx%32==x%32,'iny',sy%16==y%16)]+=1
    print(ks[a])
    for t in c: print(' tag',t,c[t].most_common(12))
