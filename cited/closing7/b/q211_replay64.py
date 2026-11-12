#!/usr/bin/env python3
"""Round 7 planner, Q211 (POST HOC; exploratory tally, not a verdict): E875's page replay
(f7_replay.replay, frozen, unchanged) with the walk order READ from dumps by q211_walk64.py
(strips of 64 pixel rows, 64 x 64 blocks left to right, regions row by row inside a block)
instead of a guessed one, on every kept one-triangle count cell at 4096x4096: g-qf (22 + 5
repeats), s275, s198, s119 (29) and r6-dpm's r-b (4 controls + 32).  Row and column order beside
it.  Read-only, public data."""
import collections, re, sys
sys.path.insert(0, '/Users/jtorra/src/scratch/resgx545/closing6/dpm/offline')
import f7_replay as F7
from r6lib import jobs, load, stretches, hi
H = F7.H
def cells():
    out = []
    for ds, stg, name, d, m in jobs():
        if not ((ds == 'closing-r3-geo-c' and stg in ('g-qf', 'g-qh')) or (ds == 'closing-r5-dpm' and stg == 'a2/d-b')
                or (ds == 'closing-r6-dpm' and stg == 'a2/r-b')):
            continue
        args = m.get('args', '')
        if 's438' in name or '--geometry' in args: continue
        cols, rows = load(f'{d}/{name}.txt.gz')
        st = stretches(rows)
        bounds = [(1, st[0][0] if st else len(rows))] + [(st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(rows)) for k in range(len(st))]
        peaks = [max(hi(rows[i][1], 0x724) for i in range(a, e)) for a, e in bounds if e > a]
        mv = re.search(r'--move 1:(-?\d+),(-?\d+)', args)
        s = (int(mv.group(1)), int(mv.group(2))) if mv else (0, 0)
        P = int(m.get('P', '0'), 0)
        if P - 0x22 < 2 or not st: continue
        out.append((s, P - 0x22, len(st), peaks, f'{ds[8:]}/{stg}/{name}'))
    return out
KEYS = {'walk64': lambda z: (z[1] // 4, z[0] // 2, z[1], z[0]), 'row': lambda z: (z[1], z[0]), 'col': lambda z: (z[0], z[1])}
K = cells(); W = 4096
scenes = sorted({k[0] for k in K})
base = {s: F7.regions(W, W, H.moved(W, W, *s), 'row') for s in scenes}
u = {s: H.hu1(W, W, H.moved(W, W, *s))[0] for s in scenes}
variants = [('keep1', dict(keep=1))]
for o, key in KEYS.items():
    t = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    lines = []
    for s, thr0, n, peaks, name in sorted(K):
        rp = F7.replay(sorted(base[s], key=key), thr0)
        ok = rp is not None and rp[0] == n
        for g in (s, 'all'):
            x = t[g]; x[0] += 1; x[1] += ok; x[2] += ok and rp[1] == peaks
            x[3] += ok and all(abs(a - b) <= 3 for a, b in zip(rp[1], peaks)); x[4] += ok and rp[1][-1] == peaks[-1]
        if o == 'walk64' and not (ok and rp[1] == peaks):
            lines.append('   U %d %s thr0 %#x read %d [%s] | replay %s [%s] %s' % (u[s], s, thr0, n, ' '.join('%x' % p for p in peaks),
                         rp[0] if rp else None, ' '.join('%x' % p for p in rp[1]) if rp else '', name))
    print('order %-7s' % o, ' | '.join('%s U %s: count %d/%d peaks exact %d within3 %d' % (g, u.get(g, ''), x[1], x[0], x[2], x[3])
                                        for g, x in sorted(t.items(), key=lambda kv: str(kv[0]))))
    print('\n'.join(lines))
