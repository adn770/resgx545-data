# Q289 offline look: per case of the end-of-tile DOUTU1 x/y sweeps (resgx545-data
# pds/end-of-tile), the job result, diff count, first wrong pixel and hash. Read-only.
import re, sys, collections
def cases(path):
    cur=None
    for line in open(path):
        if line.startswith('=== case '):
            if cur: yield cur
            cur={'case':line[9:].strip()}
        elif cur is not None:
            m=re.match(r'job: (\S+)',line)
            if m: cur['job']=m.group(1)
            m=re.match(r'target: \S+ hash (\S+)',line)
            if m: cur['hash']=m.group(1)
            m=re.match(r'diff: (\d+) of \d+ pixels(?:, first \((\d+), (\d+)\) (\S+))?',line)
            if m: cur['diff']=int(m.group(1)); cur['first']=(m.group(2),m.group(3),m.group(4))
            m=re.match(r'outside: (\d+)',line)
            if m: cur['out']=int(m.group(1))
    if cur: yield cur
for p in sys.argv[1:]:
    cs=list(cases(p)); print(p,len(cs))
    groups=collections.OrderedDict()
    for c in cs:
        k=(c.get('job'),c.get('diff'),c.get('first'),c.get('out'),c.get('hash'))
        groups.setdefault(k,[]).append(c['case'].split('^=')[-1])
    for k,v in groups.items():
        print(' ',k,len(v),' '.join(v[:6]),'...' if len(v)>6 else '')
