#!/usr/bin/env python3
"""Round 7 planner, Q211 (exploratory reading, no model): the TA's walk order READ from kept
dumps of completed one-triangle jobs.  Each region header holds the address of the region's
stream block; a block is 128 bytes, 32 a page; sorting a scene's regions by that address gives
the order in which the blocks were taken inside each page, and the pages' order in the DPM's
free list gives the order of the pages.  Prints, per dump, the first regions in address order,
and how the sequence compares with row order, column order and macrotile orders.
Read-only, public data."""
import gzip, os, struct, sys
sys.path.insert(0, '/Users/jtorra/src/resgx545/tools/usse-asm')
import pbdump as P, dpm_words as D
R = '/Users/jtorra/src/resgx545-data/render/'
def find(ds, name):
    for d, _, fs in os.walk(R + ds + '/out'):
        for f in fs:
            if f.startswith(name + '.') and f.endswith('param.bin.gz'):
                return d + '/' + f[:-len('param.bin.gz')]
JOBS = [('closing-r1-pixgeo', 'u-2048', 2048, 2048), ('closing-r1-pixgeo', 'u-2048-1536', 2048, 1536),
        ('closing-r1-pixgeo', 'u-1280', 1280, 1024), ('closing-r4-render4x', 'o8-1x-4096x4096-p422', 4096, 4096)]
for ds, name, w, h in JOBS:
    pre = find(ds, name)
    if not pre: print(name, 'no dump'); continue
    param = gzip.open(pre + 'param.bin.gz').read(); tad = gzip.open(pre + 'tadata.bin.gz').read()
    lay = D.tadata_layout(w, h)
    n, mx, my = D.mtile_grid(w, h)
    ws = struct.unpack_from('<%dI' % ((lay['zls'] - lay['rgn']) // 4), tad, lay['rgn'])
    regs = []
    for i in range(len(ws) // 3):
        w0, w1 = ws[3 * i], ws[3 * i + 1]
        if w1 and not (w0 >> 24) & 0x0a:      # not outside, not empty
            regs.append((w1, (w0 >> 16) & 0xff, w0 & 0xfff, (w0 >> 12) & 0xf, i))
    regs.sort()
    base = min(r[0] for r in regs) & ~0xfff
    print('== %s %dx%d: %d regions with a stream, headers %d, grid %d x (%d x %d tiles)' % (name, w, h, len(regs), len(ws) // 3, n, mx, my))
    pages = sorted({r[0] >> 12 for r in regs})
    print('   pages (address order):', len(pages))
    for pg in pages[:6]:
        rs = [r for r in regs if r[0] >> 12 == pg]
        print('   page %#x: %2d blocks, mtile(hdr) %s: %s' % (pg & 0xfffff, len(rs), sorted({r[3] for r in rs}),
              ' '.join('(%d,%d)' % (r[1], r[2]) for r in rs[:34])))
    # order tests inside pages
    def frac(key):
        ok = tot = 0
        for pg in pages:
            rs = [r for r in regs if r[0] >> 12 == pg]
            for a, b in zip(rs, rs[1:]):
                tot += 1; ok += key(a) < key(b)
        return '%d/%d' % (ok, tot)
    print('   consecutive blocks in a page ascending by: row-major (row, col) %s; col-major (col, row) %s; header index %s'
          % (frac(lambda r: (r[2], r[1])), frac(lambda r: (r[1], r[2])), frac(lambda r: r[4])))
