# Q139 preliminary: for each kept dump of ta/mtile-fields{,-risky} whose image is wrong, the
# 32x16 tiles with wrong pixels, whether each such tile is wholly wrong, and the tile-column /
# tile-row spans. Expected pixel: the job's own majority colour of the exact control (0xff00ff00).
import re, gzip, glob, os, sys, collections
root=sys.argv[1]
for ds in ('mtile-fields','mtile-fields-risky'):
    stats=collections.Counter(); rows_out=[]
    for f in sorted(glob.glob(f'{root}/{ds}/dumps/*.txt.gz')):
        W=H=None; img={}; job=None
        for line in gzip.open(f,'rt'):
            if line.startswith('target:'):
                W,H=map(int,line.split()[1].split('x'))
            elif line.startswith('job:'): job=line.split()[1]
            elif line.startswith('row '):
                k,v=line.split(':',1)
                vals=[]
                for x in v.split():
                    if not re.fullmatch(r'0x[0-9a-f]{8}',x): stats['row cut']+=1; break
                    vals.append(int(x,16))
                img[int(k[4:])]=vals
        if job!='ok' or not img: stats['not ok or no image']+=1; continue
        bad=collections.Counter(); tot=collections.Counter()
        for y,r in img.items():
            for x,p in enumerate(r):
                t=(x//32,y//16); tot[t]+=1
                if p!=0xff00ff00: bad[t]+=1
        if not bad: stats['exact']+=1; continue
        whole=sum(1 for t in bad if bad[t]==tot[t]); part=len(bad)-whole
        stats['wrong']+=1; stats['wrong, all tiles whole' if part==0 else 'wrong, partial tiles']+=1
        cols=sorted({t[0] for t in bad}); rws=sorted({t[1] for t in bad})
        rows_out.append(f"{os.path.basename(f)[:-7]} {W}x{H} badtiles={len(bad)} whole={whole} part={part} cols={cols[0]}-{cols[-1]} rows={rws[0]}-{rws[-1]}")
    print(ds,dict(stats)); print('\n'.join(rows_out))
