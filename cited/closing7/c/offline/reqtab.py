import runpy, collections, io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    g = runpy.run_path('boot110.py')
rows = g['rows']
c = collections.Counter(); s = collections.defaultdict(set)
for r in rows:
    st = int(r['st'], 16); a = int(r['addr'], 16)
    req = [b for b in range(16) if st >> b & 1]
    k = (r['st'], ','.join(map(str, req)), (st >> 16) & 7, (a >> 4) & 0xff, a & 0xf, '0x%02x' % (a >> 24))
    c[k] += 1; s[k].add(r['sess'])
print('# status req type BIF_FAULT[11:4] BIF_FAULT[3:0] addr[31:24] faults sessions')
for k in sorted(c):
    print(*k, c[k], len(s[k]))
