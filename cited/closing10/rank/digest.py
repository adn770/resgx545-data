import glob,re,tomllib,os
for f in sorted(glob.glob('questions/*/*.md'), key=lambda p: os.path.basename(p)):
    t=open(f).read(); d=tomllib.loads(t.split('+++')[1]); body=t.split('+++',2)[2].strip()
    paras=[p.replace('\n',' ') for p in body.split('\n\n') if p.strip()]
    op=[p for p in paras if re.match(r'(Open|Status|Left|Remaining|What is left)',p)]
    tail=(op[-1] if op else paras[-1]) if paras else ''
    ev=[int(e[1:]) for e in d.get('evidence',[]) if isinstance(e,str) and e.startswith('E')]
    print(f"## {d['id']} {d.get('unit')}/{d.get('kind')}/{d.get('value')} maxE={max(ev or [0])} nE={len(ev)} len={len(body)}")
    print("Q: "+d['question'])
    print("T: "+tail[:600])
