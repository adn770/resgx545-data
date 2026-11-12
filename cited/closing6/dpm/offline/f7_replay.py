#!/usr/bin/env python3
"""F7 (round 6 dpm offline stage, H-REPLAY, Q211): a page-level replay of the TA for a scene of
one moved default triangle, with no fitted number.  HU1's regions (closing5/r5-dpm/gen/hu1.py,
E773, unchanged) are walked in an order W; each region takes one 128-byte stream from its
macrotile's current page (32 a page), the global page is page 1; a page request above the
threshold (thr0 in the first run, thr0 + 0x20 after the one raise) is refused: a partial render,
every page but the global one freed, the walk goes on at the same region (cnt_sim.py, O6).

The family is closed and frozen here: the six orders of the planner's cnt_sim.py.  W* is picked
on the 22 g-qf cells of E832 (R3-geo-c g-qf, U 287) by the count, then by the last run's peak.
Held out, scored with W* only: s275 (R3-geo-c g-qh; SEMI, counts seen by E854), s119 and s198
(R5-dpm d-b; counts seen by E863), their run peaks (SEMI: the planner's cnt_sim.out printed the
row order's peaks), E625's ten and E779's nine 4096x4096 cells and E625's 18 cells at 1024x768
(U 19), as closing5/dpm/qf_count2.py lists them (counts only).  R5-dpm's five g-qf repeats are
replicates of fit cells.  Every member's tally is printed for comparison, with E854's d = 7/4
and d = 1.  Read-only, public data; standard library only."""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DATA = os.environ.get('RESGX545_DATA', '/Users/jtorra/src/resgx545-data')
sys.path.insert(0, os.path.join(DATA, 'render', 'closing-r5-dpm', 'gen'))
import hu1 as H
from r6lib import jobs, load, stretches, hi

ORDERS = ['row', 'col', 'mt-row', 'mt-col', 'mtT-row', 'mtrow-row']
E625 = [(p - 0x22, n) for p, n in ((0x23, 10), (0x40, 5), (0x60, 3), (0x80, 2), (0x90, 2), (0xa0, 2),
                                   (0xb0, 1), (0xb8, 1), (0xc0, 1), (0x100, 1))]
E779 = [(p - 0x22, 1) for p in (0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8, 0xa9, 0xb0)] + [(0xa0 - 0x22, 2)]
U19 = [(p - 0x22, 1) for p in range(0x23, 0x35)]


def regions(w, h, tris, order):
    tx, ty, n, mx, my = H.tiling(w, h)
    out = []
    for r in range(ty):
        for c in range(tx):
            x0, y0 = 32.0 * c, 16.0 * r
            if any(H.tile_lists(t, x0, y0) or H.tile_lists(t, x0 + 16, y0) for t in tris):
                out.append((c, r, (c // mx) * n + r // my))
    key = {'row': lambda z: (z[1], z[0]), 'col': lambda z: (z[0], z[1]),
           'mt-row': lambda z: (z[2], z[1], z[0]), 'mt-col': lambda z: (z[2], z[0], z[1]),
           'mtT-row': lambda z: ((z[2] % n) * n + z[2] // n, z[1], z[0]),
           'mtrow-row': lambda z: (z[1] // my, z[1], z[0])}[order]
    return sorted(out, key=key)


def replay(regs, thr0, raise_=0x20, cap=32, keep=1):
    used = 1; cur = {}; peaks = []; n = 0; thr = thr0
    for c, r, m in regs:
        if cur.get(m, 0) == 0:
            if used + 1 > thr:
                peaks.append(used); n += 1; used = keep; cur = {}; thr = thr0 + raise_
                if used + 1 > thr:
                    return None
            used += 1; cur[m] = cap
        cur[m] -= 1
    peaks.append(used)
    return n, peaks


def dcount(thr0, U, d):
    n = 1
    while thr0 + n * (thr0 + 0x20 - d) < U: n += 1
    return n


def kept():
    out = []
    for ds, stg, name, d, m in jobs():
        if not ((ds == 'closing-r3-geo-c' and stg in ('g-qf', 'g-qh')) or (ds == 'closing-r5-dpm' and stg == 'a2/d-b')):
            continue
        args = m.get('args', '')
        if 's438' in name or '--geometry' in args:
            continue
        cols, rows = load(f'{d}/{name}.txt.gz')
        if not rows or 0x724 not in rows[0][1] or 0x658 not in rows[0][1]:
            raise SystemExit(f'{ds}/{stg}/{name}: no 0x0724 or 0x0658 sampled')
        st = stretches(rows)
        bounds = [(1, st[0][0] if st else len(rows))] + [(st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(rows)) for k in range(len(st))]
        peaks = [max(hi(rows[i][1], 0x724) for i in range(a, e)) for a, e in bounds if e > a]
        mv = re.search(r'--move 1:(-?\d+),(-?\d+)', args)
        dx, dy = (int(mv.group(1)), int(mv.group(2))) if mv else (0, 0)
        P = int(m.get('P', '0'), 0)
        if P - 0x22 < 2:
            continue
        side = ('fit' if stg == 'g-qf' else 'repeat' if name.startswith('b-qf') else 'held')
        out.append(((dx, dy), P - 0x22, len(st), peaks, f'{ds[8:]}/{stg}/{name}', side))
    return out


def main():
    K = kept()
    W = Hh = 4096
    regs = {(o, s): regions(W, Hh, H.moved(W, Hh, *s), o) for o in ORDERS for s in {k[0] for k in K}}
    u = {s: H.hu1(W, Hh, H.moved(W, Hh, *s))[0] for s in {k[0] for k in K}}
    rec = {}
    for o in ORDERS:
        t = collections.Counter()
        for s, thr0, n, peaks, name, side in K:
            rp = replay(regs[(o, s)], thr0)
            ok = rp is not None and rp[0] == n
            t[(side, 'cells')] += 1; t[(side, 'count')] += ok
            t[(side, 'last')] += ok and rp[1][-1] == peaks[-1]
            t[(side, 'all')] += ok and rp[1] == peaks
            t[(side, 'within3')] += ok and all(abs(a - b) <= 3 for a, b in zip(rp[1], peaks))
        rec[o] = t
        print('member %-10s fit count %d/%d last peak %d | repeats count %d/%d | held count %d/%d, all peaks %d, last peak %d, peaks within 3 %d'
              % (o, t[('fit', 'count')], t[('fit', 'cells')], t[('fit', 'last')], t[('repeat', 'count')], t[('repeat', 'cells')],
                 t[('held', 'count')], t[('held', 'cells')], t[('held', 'all')], t[('held', 'last')], t[('held', 'within3')]))
    best = max(ORDERS, key=lambda o: (rec[o][('fit', 'count')], rec[o][('fit', 'last')], -ORDERS.index(o)))
    print('W* =', best, '(picked on g-qf only)')
    print('== W* cell by cell: scene, thr0, read count and run peaks | replay')
    miss = collections.Counter(); cells = collections.Counter()
    for s, thr0, n, peaks, name, side in sorted(K):
        rp = replay(regs[(best, s)], thr0)
        ok = rp is not None and rp[0] == n
        cells[(side, s)] += 1; miss[(side, s)] += not ok
        print('%-6s U %d %s thr0 %#x read %d %s | replay %s %s %s %s' % (side, u[s], s, thr0, n, ' '.join('%x' % p for p in peaks),
              rp[0] if rp else None, ' '.join('%x' % p for p in rp[1]) if rp else '', 'COUNT' if not ok else
              ('peaks exact' if rp[1] == peaks else 'last exact' if rp[1][-1] == peaks[-1] else 'peaks off'), name))
    for (side, s), c in sorted(cells.items()):
        print('W* %s scene %s (U %d): count %d of %d' % (side, s, u[s], c - miss[(side, s)], c))
    print('== record cells (counts only), W* and the rivals')
    for nm, cl, w, h in (('E625 4096x4096', E625, 4096, 4096), ('E779 4096x4096', E779, 4096, 4096), ('E625 1024x768 U 19', U19, 1024, 768)):
        tri = [H.default_tri(w, h)]
        U = H.hu1(w, h, tri)[0]
        for o in [best] + [x for x in ORDERS if x != best]:
            rg = regions(w, h, tri, o)
            ok = sum(1 for t, n in cl if (rp := replay(rg, t)) is not None and rp[0] == n)
            print('%-20s U %d %-10s count %d of %d%s' % (nm, U, o, ok, len(cl), '  (W*)' if o == best else ''))
        for d in (1.75, 1.0):
            print('%-20s U %d d = %-6s count %d of %d' % (nm, U, d, sum(dcount(t, U, d) == n for t, n in cl), len(cl)))
    print('== rivals on the kept cells: E854 d = 7/4 and d = 1')
    for d in (1.75, 1.0):
        t = collections.Counter()
        for s, thr0, n, peaks, name, side in K:
            t[side] += dcount(thr0, u[s], d) == n; t[side + 'n'] += 1
        print('d = %s: fit %d/%d repeats %d/%d held %d/%d' % (d, t['fit'], t['fitn'], t['repeat'], t['repeatn'], t['held'], t['heldn']))


if __name__ == '__main__':
    main()
