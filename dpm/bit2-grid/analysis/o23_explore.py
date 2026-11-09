import re,sys,struct
f=sys.argv[1]; case=int(sys.argv[2]) if len(sys.argv)>2 else 0
rows={}; cur=None
for line in open(f):
    m=re.match(r"probe (\S+): row (\d+): (.*)$",line)
    if m:
        rows.setdefault(m.group(1),{})[int(m.group(2))]=[int(v,16) for v in m.group(3).split()]
for k in sorted(rows)[:3]:
    r=rows[k]; print(k,len(r),len(r[0]))
k=sorted(rows)[case]; r=rows[k]
def fl(v): return struct.unpack('<f',struct.pack('<I',v&0xffff0000))[0]
for y in range(0,3):
    print([ "%.3f/%d"%(fl(v),v&0xffff) for v in r[y][8:18]])
