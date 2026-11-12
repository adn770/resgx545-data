#!/usr/bin/env python3
"""G2 (round 7 dpm offline stage, H-REPLAY64, Q211).  E875's page replay (f7_replay.replay and
f7_replay.regions from the published round 6 library, unchanged: HU1's regions, one 128-byte
stream each from its macrotile's current page, 32 a page, a refused page starting a partial
render that keeps the global page, the threshold raised by 0x20 once) with the regions walked in
G1's order (strips of 64 pixel rows, 64 x 64 blocks left to right, regions row by row inside a
block) instead of a guessed one.  No number is fitted.

Cells (the planner's q211_replay64.py and q211_records64.py rules, unchanged): every kept
one-triangle count cell at 4096x4096 of R3-geo-c g-qf and g-qh (s438 and --geometry left out),
R5-dpm a2/d-b and R6-dpm a2/r-b with thr0 = P - 0x22 >= 2 and at least one partial render; per
cell the count of 0x0658 stretches and every TA run's peak of 0x0724.  Record cells: E625's ten
and E779's nine at 4096x4096 and E625's 18 at 1024x768 (U 19), counts only.
Labels: every cell is SEMI (the planner's tally printed all of them before this freeze).
Verdict: H-REPLAY64 HELD iff every cell's count and every run's peak equal the replay's and
every record count equals it, else REFUTED.  Row order, column order and E854's d = 7/4 and
d = 1 are printed as a tally.  Read-only, public data; standard library only."""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import olib as O                       # noqa: F401  (paths)
import f7_replay as F7
from r6lib import jobs, load, stretches, hi
H = F7.H
KEYS = {'walk64': lambda z: (z[1] // 4, z[0] // 2, z[1], z[0]),
        'row': lambda z: (z[1], z[0]),
        'col': lambda z: (z[0], z[1])}


def cells():
    out = []
    for ds, stg, name, d, m in jobs():
        if not ((ds == 'closing-r3-geo-c' and stg in ('g-qf', 'g-qh')) or (ds == 'closing-r5-dpm' and stg == 'a2/d-b')
                or (ds == 'closing-r6-dpm' and stg == 'a2/r-b')):
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
        s = (int(mv.group(1)), int(mv.group(2))) if mv else (0, 0)
        P = int(m.get('P', '0'), 0)
        if P - 0x22 < 2 or not st:
            continue
        out.append((s, P - 0x22, len(st), peaks, f'{ds[8:]}/{stg}/{name}'))
    return out


def main():
    K = cells()
    W = 4096
    scenes = sorted({k[0] for k in K})
    base = {s: F7.regions(W, W, H.moved(W, W, *s), 'row') for s in scenes}
    u = {s: H.hu1(W, W, H.moved(W, W, *s))[0] for s in scenes}
    off = 0
    for o, key in KEYS.items():
        t = collections.defaultdict(lambda: [0, 0, 0, 0])
        for s, thr0, n, peaks, name in sorted(K):
            rp = F7.replay(sorted(base[s], key=key), thr0)
            ok = rp is not None and rp[0] == n
            ex = ok and rp[1] == peaks
            for g in (s, 'all'):
                x = t[g]; x[0] += 1; x[1] += ok; x[2] += ex
                x[3] += ok and all(abs(a - b) <= 3 for a, b in zip(rp[1], peaks))
            if o == 'walk64':
                off += not ex
                print('cell U %3d %-12s thr0 %#5x read %d [%s] | replay %s [%s] %s %s' % (
                    u[s], s, thr0, n, ' '.join('%x' % p for p in peaks), rp[0] if rp else None,
                    ' '.join('%x' % p for p in rp[1]) if rp else '', 'exact' if ex else 'OFF', name))
        print('order %-7s' % o, ' | '.join('%s U %s: count %d/%d peaks exact %d within3 %d' % (
            g, u.get(g, ''), x[1], x[0], x[2], x[3]) for g, x in sorted(t.items(), key=lambda kv: str(kv[0]))))
    for d in (1.75, 1.0):
        print('E854 d = %-5s count %d/%d' % (d, sum(F7.dcount(thr0, u[s], d) == n for s, thr0, n, _, _ in K), len(K)))
    rec_off = 0
    for nm, cl, w, h in (('E625 4096x4096', F7.E625, 4096, 4096), ('E779 4096x4096', F7.E779, 4096, 4096),
                         ('E625 1024x768 U 19', F7.U19, 1024, 768)):
        tri = [H.default_tri(w, h)]
        for o, key in KEYS.items():
            rg = sorted(F7.regions(w, h, tri, 'row'), key=key)
            bad = [(hex(t), n) for t, n in cl if (rp := F7.replay(rg, t)) is None or rp[0] != n]
            if o == 'walk64':
                rec_off += len(bad)
            print('%-20s %-7s count %d of %d %s' % (nm, o, len(cl) - len(bad), len(cl), bad))
    print('VERDICT H-REPLAY64:', 'HELD' if not off and not rec_off and K else 'REFUTED',
          '(%d of %d cells off, %d record cells off; SEMI)' % (off, len(K), rec_off))


if __name__ == '__main__':
    main()
