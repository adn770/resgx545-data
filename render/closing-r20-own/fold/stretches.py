#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""fold/stretches.py DIR: per row of a kept stage, the stretches of 0x062c in its regtimeline with 0x0724's peak U and the samples where 0x0694 or 0x0698 is non-zero (r20-own fold, post hoc)."""
import gzip,sys,os
d=sys.argv[1]
for f in sorted(os.listdir(d)):
    if not f.endswith('.txt.gz') or f.count('.')!=2: continue
    t=gzip.open(os.path.join(d,f),'rt').read().splitlines()
    regs=None; runs=[]; cur=None
    for ln in t:
        s=ln.split()
        if ln.startswith('timeline: regs'): regs=[int(x,16) for x in s[2:s.index('samples')]]
        elif regs and s[:1]==['tl']:
            v=dict(zip(regs,(int(x,16) for x in s[2:])))
            b=v[0x62c]
            if cur is None or cur[0]!=b: cur=[b,0,0,0]; runs.append(cur)
            if 0x724 in v: cur[1]=max(cur[1],v[0x724]>>16)
            cur[2]+=1
            if v.get(0x694) or v.get(0x698): cur[3]+=1
    print(f.split('.')[0], ' '.join(f'{b:08x}:U{u:#x}:n{n}:tw{w}' for b,u,n,w in runs))
