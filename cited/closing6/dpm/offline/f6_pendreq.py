#!/usr/bin/env python3
"""F6 (round 6 dpm offline stage, H-PENDREQ [infer], a reading): at a cell whose first threshold
is a step (thr0 = S_k, the first entry grows the global list, E861), the refused request is the
global page itself, so it is not in the list while the partial render runs and is served when
the TA restarts.  Read from the timelines: for every kept job of the 1500-vertex (and 1350) scene
whose first TA run shows 0x0628's low half below 0x10 (a grow), and for the cells S_k - 1 and
S_k + 1 of the same target: the global count at the abort (the last sample before the first
stretch of 0x0658), its minimum and last value inside the stretch, and the first sample after
the stretch, with the time of the first change of the global count after the stretch ends
relative to the first change of the page count.  Refuted by a non-grow cell with the same late
page.  Read-only, public data."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r6lib import jobs, scene_of, load, stretches, hi
from f1_brackets import brackets


def main():
    iv = brackets()
    S = {}
    for (wh, sc, k), L in iv.items():
        lo = max(a for a, b, _ in L); top = min(b for a, b, _ in L)
        if lo == top: S.setdefault((wh, sc), {})[lo] = k
    print('job target thr0 cell | gps at abort, min and last in stretch | after the stretch: (us, ps, gps) of the first 4 samples | grow')
    tally = {}
    for ds, stg, name, d, m in jobs():
        wh, sc = scene_of(m.get('args', ''))
        if sc not in ('tri1500', 'tri1350'):
            continue
        cols, tl = load(f'{d}/{name}.txt.gz')
        if not tl or any(r not in tl[0][1] for r in (0x724, 0x72c, 0x658, 0x624, 0x628)):
            continue
        st = stretches(tl)
        if not st:
            continue
        a, e = st[0]
        thr = tl[a][1][0x624] & 0xffff
        steps = S.get((wh, sc), {})
        cell = ('S%d' % steps[thr] if thr in steps else 'S%d-1' % steps[thr + 1] if thr + 1 in steps
                else 'S%d+1' % steps[thr - 1] if thr - 1 in steps else None)
        if cell is None:
            continue
        grow = any((tl[i][1][0x628] & 0xffff) < 0x10 for i in range(1, a + 1))
        g_in = [hi(tl[i][1], 0x72c) for i in range(a, e + 1)]
        t_end = tl[e][0]
        post = [((tl[i][0] - t_end) // 1000, hi(tl[i][1], 0x724), hi(tl[i][1], 0x72c)) for i in range(e + 1, min(e + 5, len(tl)))]
        kind = ('grow' if grow else 'no grow') + (' at S' if '-' not in cell and '+' not in cell else ' beside S')
        late = bool(post) and post[0][2] == min(g_in) and any(p[2] > min(g_in) for p in post)
        tally.setdefault(kind, [0, 0]); tally[kind][0] += late; tally[kind][1] += 1
        print('%-36s %-9s %#x %-6s | %d, %d, %d | %s | %s%s' % (f'{ds[8:]}/{stg}/{name}', wh, thr, cell, hi(tl[a - 1][1], 0x72c),
              min(g_in), g_in[-1], ' '.join('(%d,%#x,%d)' % p for p in post), 'grow' if grow else '-',
              ' late global page' if late else ''))
    for k, (n, c) in sorted(tally.items()):
        print('%s: %d of %d jobs take a global page right after the partial render (count at the stretch minimum, then up)' % (k, n, c))


if __name__ == '__main__':
    main()
