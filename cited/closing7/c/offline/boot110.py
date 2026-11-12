"""Round 7 offline scan (faults area): every BIF fault in the kernel logs of resgx545-data and
the boot that follows it. Read-only. Usage: boot110.py <data-root> > boot110.out
Events are de-duplicated by (top-level session dir, timestamp, text) because sessions keep both
whole logs and per-cell slices."""
import sys, re, gzip, os, collections
root = sys.argv[1]
ts = re.compile(r'^\[\s*(\d+\.\d+)\]\s*(.*)$')
pf = re.compile(r'BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)(?: \(PD (0x[0-9a-f]+)\))?')
preg = re.compile(r'reg (0x[0-9a-f]+) = (0x[0-9a-f]+)')
def is_log(f):
    return f.startswith('kernel.log') or f.endswith('.kmsg') or 'dmesg' in f or f.endswith('.kmsg.gz')
sess = collections.defaultdict(dict)   # session -> {(t, text): 1}
nfiles = 0
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
        nfiles += 1
        rel = os.path.relpath(p, root).split(os.sep)
        key = '/'.join(rel[:2])
        for line in t.splitlines():
            m = ts.match(line.strip())
            if not m:
                continue
            sess[key][(float(m.group(1)), m.group(2))] = 1
print('files', nfiles, 'sessions', len(sess))
rows = []
for key in sorted(sess):
    ev = sorted(sess[key])
    cur = None      # last fault
    boot = None
    for t, x in ev:
        m = pf.search(x)
        if m:
            cur = dict(sess=key, t=t, st=m.group(1), addr=m.group(2), pd=m.group(3), held=False,
                       boots=[])
            rows.append(cur)
            boot = None
            continue
        if cur is None:
            continue
        if 'recovery held' in x:
            cur['held'] = True
        elif 'bif_flush:' in x:
            cur['flush'] = True
        elif 'kicking the EDM' in x:
            boot = dict(t=t, res=None, regs={})
            cur['boots'].append(boot)
        elif boot is not None and 'EDM up after' in x:
            boot['res'] = 'up'
            boot['us'] = x.split('after')[1].strip()
        elif boot is not None and 'no INIT_COMPLETE' in x:
            boot['res'] = 'noinit'
        elif boot is not None and boot['res'] == 'noinit':
            r = preg.search(x)
            if r and r.group(1) not in boot['regs']:
                boot['regs'][r.group(1)] = r.group(2)
# table 1: first boot after each fault, by status word
c = collections.Counter()
for r in rows:
    b = r['boots'][0]['res'] if r['boots'] else 'noboot'
    c[(r['st'], b)] += 1
print('\n# first boot after a fault, by status: status result count')
for k in sorted(c):
    print(k[0], k[1], c[k])
# table 2: 0x90004 by page/SB (addr >> 4) and list
c = collections.Counter()
for r in rows:
    if r['st'] != '0x90004':
        continue
    a = int(r['addr'], 16)
    b = r['boots'][0]['res'] if r['boots'] else 'noboot'
    c[('0x%05x' % (a >> 12), (a >> 4) & 0xf, 'held' if r['held'] else 'auto', b)] += 1
print('\n# 0x90004: page SB held first-boot count')
for k in sorted(c):
    print(*k, c[k])
print('\n# every 0x90004 fault whose first boot timed out: session t addr held flush dump 0x008 0xc04 0xc08 0x12c 0xb14')
for r in rows:
    if r['st'] != '0x90004' or not r['boots'] or r['boots'][0]['res'] != 'noinit':
        continue
    g = r['boots'][0]['regs']
    print(r['sess'], '%.3f' % r['t'], r['addr'], 'held' if r['held'] else 'auto',
          'flush' if r.get('flush') else '-', g.get('0x008'), g.get('0xc04'), g.get('0xc08'),
          g.get('0x12c'), g.get('0xb14'), 'dt_kick=%.3f' % (r['boots'][0]['t'] - r['t']))
print('\n# every 0x90004 fault whose first boot came up: session t addr held us dt_kick')
for r in rows:
    if r['st'] != '0x90004' or not r['boots'] or r['boots'][0]['res'] != 'up':
        continue
    print(r['sess'], '%.3f' % r['t'], r['addr'], 'held' if r['held'] else 'auto',
          r['boots'][0].get('us'), 'dt_kick=%.3f' % (r['boots'][0]['t'] - r['t']))
