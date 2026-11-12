#!/usr/bin/env python3
"""O6 (post hoc, a FIT of structure, no numeric constant fitted): a page-level replay of the
TA for a one-triangle scene.  HU1's regions (closing5/r5-dpm/gen/hu1.py, unchanged), walked in
an ORDER; every region takes one 128-byte stream from its macrotile's current page (32 a page);
a page request beyond the threshold (thr0 in the first run, thr0 + 0x20 after the one raise) is
refused: partial render, every page but the global one freed, the walk goes on at the same
region.  Output per cell: partial renders and the peak of each run, against the kept timelines
(g-qf, g-qh s275, r5-dpm d-b).  Orders tried are listed, none tuned per scene."""
import sys, collections
sys.path.insert(0, '/Users/jtorra/src/scratch/resgx545/closing5/r5-dpm/gen')
import hu1 as H
from r6lib import *
W = Hh = 4096
def regions(tris, order):
    tx, ty, n, mx, my = H.tiling(W, Hh)
    out = []
    for r in range(ty):
        for c in range(tx):
            x0, y0 = 32.0 * c, 16.0 * r
            if any(H.tile_lists(t, x0, y0) or H.tile_lists(t, x0 + 16, y0) for t in tris):
                out.append((c, r, (c // mx) * n + r // my))
    if order == 'row':      # rows of the whole target, left to right
        out.sort(key=lambda z: (z[1], z[0]))
    elif order == 'col':    # columns of the whole target, top to bottom
        out.sort(key=lambda z: (z[0], z[1]))
    elif order == 'mt-row':  # macrotile by macrotile (index order), rows inside
        out.sort(key=lambda z: (z[2], z[1], z[0]))
    elif order == 'mtrow-row':  # macrotile rows (all columns of a macrotile row together), rows inside
        out.sort(key=lambda z: (z[1] // my, z[1], z[0]))
    elif order == 'mt-col':
        out.sort(key=lambda z: (z[2], z[0], z[1]))
    elif order == 'mtT-row':  # macrotiles row-major
        out.sort(key=lambda z: ((z[2] % n) * n + z[2] // n, z[1], z[0]))
    return out
def replay(regs, thr0, raise_=0x20, cap=32, keep=1):
    used = 1; cur = {}; peaks = []; n = 0; thr = thr0
    for c, r, m in regs:
        if cur.get(m, 0) == 0:
            if used + 1 > thr:
                peaks.append(used); n += 1; used = keep; cur = {}; thr = thr0 + raise_
                if used + 1 > thr: return None
            used += 1; cur[m] = cap
        cur[m] -= 1
    peaks.append(used)
    return n, peaks
def kept():
    out = []
    for ds, stg, name, d, m in jobs():
        if not ((ds == 'closing-r3-geo-c' and stg in ('g-qf', 'g-qh')) or (ds == 'closing-r5-dpm' and stg == 'a2/d-b')): continue
        args = m.get('args', '')
        if 's438' in name or '--geometry' in args: continue
        try: cols, rows = load(f'{d}/{name}.txt.gz')
        except Exception: continue
        if not rows or 0x724 not in rows[0][1] or 0x658 not in rows[0][1]: continue
        st = stretches(rows)
        bounds = [(1, st[0][0] if st else len(rows))] + [(st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(rows)) for k in range(len(st))]
        peaks = [max(hi(rows[i][1], 0x724) for i in range(a, e)) for a, e in bounds if e > a]
        mv = re.search(r'--move 1:(-?\d+),(-?\d+)', args)
        dx, dy = (int(mv.group(1)), int(mv.group(2))) if mv else (0, 0)
        P = int(m.get('P', '0'), 0)
        mts = [rows[a][1].get(0x720, 0) for a, b in st]
        out.append(((dx, dy), P - 0x22, len(st), peaks, f'{ds[8:]}/{stg}/{name}', mts))
    return out
if __name__ == '__main__':
    K = kept()
    orders = ['row', 'col', 'mt-row', 'mt-col', 'mtT-row', 'mtrow-row']
    scenes = sorted({k[0] for k in K})
    print('scene (move) -> HU1 U, regions per macrotile')
    for s in scenes:
        u, per = H.hu1(W, Hh, H.moved(W, Hh, *s)); print('  ', s, 'U', u, dict(sorted(per.items())))
    for o in orders:
        tot = collections.Counter(); miss = []
        for s, thr0, n, peaks, name, mts in K:
            if thr0 < 2: continue
            rg = regions(H.moved(W, Hh, *s), o); rp = replay(rg, thr0)
            ok_n = rp is not None and rp[0] == n
            ok_last = ok_n and n > 0 and rp[1][-1] == peaks[-1]
            tot[(s, 'cells')] += 1; tot[(s, 'count ok')] += ok_n; tot[(s, 'last peak ok')] += ok_last
            if not ok_n: miss.append((name.split('/')[-1], hex(thr0), n, rp[0] if rp else None))
        print('ORDER', o, ' '.join('%s: count %d/%d, last-run peak %d/%d;' % (s, tot[(s, 'count ok')], tot[(s, 'cells')], tot[(s, 'last peak ok')], tot[(s, 'cells')]) for s in scenes))
        print('     count misses (job, thr0, read, replay):', miss[:14])
    if '-v' in sys.argv:
        o = sys.argv[sys.argv.index('-v') + 1]
        for s, thr0, n, peaks, name, mts in sorted(K):
            rp = replay(regions(H.moved(W, Hh, *s), o), thr0)
            print(s, hex(thr0), 'read', n, ' '.join('%x' % p for p in peaks), '| replay', rp[0] if rp else None, ' '.join('%x' % p for p in rp[1]) if rp else '', '| abort mtile reg', ' '.join('%x' % x for x in mts), name)
