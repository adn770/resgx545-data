import sys, runpy, collections, io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    g = runpy.run_path('boot_clk.py')
rows = g['rows']
print('# 0x90004 faults: page SB held | first boot, its 0x008 | was the previous event in the session a timed-out boot | n')
c = collections.Counter()
prev = {}
for r in rows:
    if r['st'] == '0x90004' and r['boots']:
        a = int(r['addr'], 16)
        b = r['boots'][0]
        p = prev.get(r['sess'])
        pk = '-' if p is None else ('after-noinit' if (p['boots'] and p['boots'][0]['res'] == 'noinit' and p['st'] == '0x90004') else 'after-up' if p['st'] == '0x90004' else 'after-other')
        c[('0x%05x' % (a >> 12), (a >> 4) & 0xf, 'held' if r['held'] else 'auto', b['res'], b['regs'].get('0x008'), pk)] += 1
    prev[r['sess']] = r
for k in sorted(c, key=str):
    print(*k, c[k])
