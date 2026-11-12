"""Round 7 fold F5 (faults area, Q003), post hoc: what the kernel's reset read in the fault
registers before each first boot after a 0x90004 fault, by the boot's result.
Usage: f5_latch.py <data-root> > f5_latch.out (boot110.py's walk and de-duplication).
The fork's sgxfive_clear_faults (3f0b3e74) logs 'SGX reset: BIF_FAULT x BIF_INT_STAT y' after
the halt (deinit script, SOFT_RESET all: every block held in reset) and before CLEAR_FAULT,
then 'after the fault clear ...', then the boot kicks the EDM."""
import collections
import re
import sys
import os

root = sys.argv[1]
ts = re.compile(r'^\[\s*(\d+\.\d+)\]\s*(.*)$')
pf = re.compile(r'BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)')
pre = re.compile(r'SGX reset: BIF_FAULT (0x[0-9a-f]+) BIF_INT_STAT (0x[0-9a-f]+)')
post = re.compile(r'SGX reset: after the fault clear BIF_FAULT (0x[0-9a-f]+) BIF_INT_STAT (0x[0-9a-f]+)')


def is_log(f):
    return f.startswith('kernel.log') or f.endswith('.kmsg') or 'dmesg' in f or f.endswith('.kmsg.gz')


import gzip
sess = collections.defaultdict(dict)
for dp, dn, fn in os.walk(root):
    dn[:] = [d for d in dn if d != '.git']
    for f in fn:
        if not is_log(f):
            continue
        p = os.path.join(dp, f)
        try:
            t = (gzip.open(p).read() if p.endswith('.gz') else open(p, 'rb').read()).decode('utf8', 'replace')
        except Exception:
            continue
        key = '/'.join(os.path.relpath(p, root).split(os.sep)[:2])
        for line in t.splitlines():
            m = ts.match(line.strip())
            if m:
                sess[key][(float(m.group(1)), m.group(2))] = 1
c = collections.Counter()
for key in sorted(sess):
    cur = None
    for t, x in sorted(sess[key]):
        m = pf.search(x)
        if m:
            cur = dict(st=m.group(1), pre=None, post=None, done=False) if m.group(1) == '0x90004' else None
            continue
        if cur is None or cur['done']:
            continue
        if (m := post.search(x)):
            cur['post'] = m.groups()
        elif (m := pre.search(x)):
            cur['pre'] = m.groups()
        elif 'EDM up after' in x or 'no INIT_COMPLETE' in x:
            cur['done'] = True
            res = 'up' if 'EDM up' in x else 'noinit'
            c[(res, 'pre=%s/%s' % cur['pre'] if cur['pre'] else 'pre=none',
               'post=%s/%s' % cur['post'] if cur['post'] else 'post=none')] += 1
print('# first boot after a 0x90004 fault: result, reset read (BIF_FAULT/BIF_INT_STAT) before and after CLEAR_FAULT, count')
for k in sorted(c):
    print(*k, c[k])
