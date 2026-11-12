#!/usr/bin/env python3
"""Round 7 planner, Q211 (POST HOC reading; the order was named after q211_walk.py printed the
u-2048 pages, the other dumps are SEMI held out: their pages were printed by the same run).
H-WALK64: the TA takes stream blocks walking the target in strips of 64 pixel rows, each strip in
64 x 64-pixel blocks left to right, each block's regions (32 x 16) row by row, two a row; a
macrotile's blocks fill its current page, 32 a page, a new page when the next block does not fit.
Test without any model of the triangle: replay the allocation over the regions the dump itself
shows with a stream (sorted by the order key) and compare every region's (page rank, slot) with
its real address.  Read-only, public data."""
import gzip, os, struct, sys
sys.path.insert(0, '/Users/jtorra/src/resgx545/tools/usse-asm')
import dpm_words as D
R = '/Users/jtorra/src/resgx545-data/render/'
def find(ds, name):
    for d, _, fs in os.walk(R + ds + '/out'):
        for f in sorted(fs):
            if f.startswith(name + '.') and f.endswith('param.bin.gz'):
                return d + '/' + f[:-len('param.bin.gz')]
ORDERS = {
    'walk64': lambda c, r: (r // 8, c // 4, r, c),
    'row':    lambda c, r: (r, c),
    'col':    lambda c, r: (c, r),
    'hdr':    None,
}
JOBS = [('closing-r1-pixgeo', 'u-2048', 2048, 2048), ('closing-r1-pixgeo', 'u-2048-1536', 2048, 1536),
        ('closing-r1-pixgeo', 'u-1280', 1280, 1024), ('closing-r1-pixgeo', 'u-640', 640, 480),
        ('closing-r1-pixgeo', 'u-512-m128', 512, 384),
        ('closing-r4-render4x', 'o8-1x-4096x4096-p422', 4096, 4096)] + [tuple(a.split(',')[:2]) + (int(a.split(',')[2]), int(a.split(',')[3])) for a in sys.argv[1:]]
for ds, name, w, h in JOBS:
    pre = find(ds, name)
    if not pre: print(name, 'no dump'); continue
    tad = gzip.open(pre + 'tadata.bin.gz').read()
    lay = D.tadata_layout(w, h)
    ws = struct.unpack_from('<%dI' % ((lay['zls'] - lay['rgn']) // 4), tad, lay['rgn'])
    regs = []
    for i in range(len(ws) // 3):
        w0, w1 = ws[3 * i], ws[3 * i + 1]
        if w1 and not (w0 >> 24) & 0x0a:
            regs.append(dict(addr=w1, c=(w0 >> 16) & 0xff, r=w0 & 0xfff, m=(w0 >> 12) & 0xf, i=i))
    pages = sorted({x['addr'] >> 12 for x in regs})
    rank = {p: i for i, p in enumerate(pages)}
    out = []
    for oname, key in ORDERS.items():
        seq = sorted(regs, key=(lambda x: x['i']) if key is None else (lambda x: key(x['c'], x['r'])))
        cur = {}; npg = 0; ok = 0
        for x in seq:
            m = x['m']
            if m not in cur or cur[m][1] == 32:
                cur[m] = [npg, 0]; npg += 1
            pg, slot = cur[m]; cur[m][1] += 1
            ok += (rank[x['addr'] >> 12], (x['addr'] & 0xfff) // 128) == (pg, slot)
        out.append('%s %d/%d (pages %d)' % (oname, ok, len(regs), npg))
    print('%-24s %dx%d real pages %d | exact (page rank, slot): %s' % (name, w, h, len(pages), '; '.join(out)))
