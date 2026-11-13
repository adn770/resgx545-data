import glob,re,tomllib,os,subprocess
qs={}
for f in sorted(glob.glob('questions/*/*.md')):
    t=open(f).read(); d=tomllib.loads(t.split('+++')[1])
    qs[d['id']]=set(e for e in d.get('evidence',[]) if isinstance(e,str))
cites={q:set() for q in qs}
for f in glob.glob('evidence/*/*.md'):
    t=open(f).read(); eid=os.path.basename(f).split('-')[0]
    for q in set(re.findall(r'\bQ\d{3}\b',t)):
        if q in cites: cites[q].add(eid)
crate={q:0 for q in qs}
out=subprocess.run(['grep','-rhoE',r'\bQ[0-9]{3}\b','crates','--include=*.rs','--include=*.py'],capture_output=True,text=True).stdout.split()
for q in out:
    if q in crate: crate[q]+=1
for q in sorted(qs):
    ev=qs[q]; mx=max([int(e[1:]) for e in ev if e.startswith('E')] or [0])
    extra=sorted(e for e in cites[q]-ev if int(e[1:])>mx)
    print(f"{q}|crate={crate[q]}|cited_by={len(cites[q])}|newer_uncited={','.join(extra)}")
