#!/usr/bin/env python3
"""Compressed view of a kept register timeline (read-only; round 5 dpm planning)."""
import gzip, sys
def load(path):
    cols = None; rows = []; hdr = []
    for l in gzip.open(path, 'rt', errors='replace'):
        if l.startswith('timeline:'):
            hdr.append(l.strip()[:300])
            cols = [int(x, 16) for x in l.split('regs ')[1].split(' samples')[0].split()]
        elif l.startswith('tl '):
            p = l.split(); rows.append((int(p[1]), dict(zip(cols, (int(x, 16) for x in p[2:])))))
    return hdr, cols, rows
if __name__ == '__main__':
    hdr, cols, rows = load(sys.argv[1])
    show = [int(x, 16) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else cols
    print(hdr, len(rows)); print('t_us(rel) dt ' + ' '.join('%x' % c for c in show))
    prev = None; t0 = rows[0][0]; pt = t0
    for i, (t, v) in enumerate(rows):
        key = tuple(v[c] for c in show)
        if key != prev:
            print(i, t - t0, t - pt, ' '.join('%x' % k for k in key)); pt = t
        prev = key
    print('last', len(rows) - 1, rows[-1][0] - t0)
