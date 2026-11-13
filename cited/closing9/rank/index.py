import sys,re,glob,tomllib,os
rows=[]
for f in sorted(glob.glob('questions/*/*.md')):
    t=open(f).read()
    fm=t.split('+++')[1]
    d=tomllib.loads(fm)
    body=t.split('+++',2)[2]
    ev=d.get('evidence',[])
    nums=[int(e[1:]) for e in ev if isinstance(e,str) and e.startswith('E')]
    rows.append((d['id'],d.get('kind'),d.get('value'),d.get('unit'),max(nums) if nums else 0,len(body),os.path.basename(f),d['question'][:200]))
for r in rows: print('|'.join(map(str,r)))
