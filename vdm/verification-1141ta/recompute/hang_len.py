#!/usr/bin/env python3
"""p1141/ta hang_len.py: does the 'job hung, recovering' kernel line follow job length?

Per wide-* case: timeline length (first sample with page status != 0 or partial render on, to the
last such sample, seconds) and whether the kernel log section of the case (from its 'resgx545 case
NAME' line to the next one) holds 'hung, recovering'.  SGXFIVE_JOB_TIMEOUT_MS = 500 per the kernel
source (not re-read here; plan.md states it as Opus's reading).  Reports the length range of each
class; the claim is separation by length, one run per case.  Cases without a timeline are skipped.
Usage: python3 hang_len.py
"""
import glob, gzip, os, re
D = os.path.expanduser('~/src/resgx545-data/dpm/partial-model-batch/dumps')
def sections(klog):
    cur, out = None, {}
    for l in open(klog, errors='replace'):
        m = re.search(r'resgx545 case (\S+)', l)
        if m: cur = m[1]; out[cur] = []
        elif cur: out[cur].append(l)
    return out
res = []
for f in sorted(glob.glob(D + '/wide-*/wd-*.txt.gz')):
    n = os.path.basename(f)[:-7]
    t = gzip.open(f, 'rt', errors='replace').read()
    m = re.search(r'^timeline: regs (.*?) samples', t, re.M)
    if not m: continue
    regs = m[1].split()
    if '0x0724' not in regs or '0x0658' not in regs: continue
    ist, ip = regs.index('0x0724') + 1, regs.index('0x0658') + 1
    ts = []
    for l in t.splitlines():
        if l.startswith('tl '):
            x = l.split();
            if int(x[ist], 16) & 0xffff or int(x[ip], 16): ts.append(int(x[1], 0))
    if not ts: continue
    kl = os.path.join(os.path.dirname(f), 'kernel.log')
    hung = os.path.exists(kl) and any('hung, recovering' in l for l in sections(kl).get(n, []))
    res.append((n, (ts[-1] - ts[0]) / 1e9, hung))
for cls in (True, False):
    xs = [r for r in res if r[2] == cls]
    if xs: print('hung-line' if cls else 'no hung-line', len(xs), 'jobs, length', f'{min(r[1] for r in xs):.3f}..{max(r[1] for r in xs):.3f} s')
for r in sorted(res, key=lambda r: -r[1])[:5]: print(r)
