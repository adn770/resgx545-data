#!/usr/bin/env python3
"""Round 5 dpm planning, offline: where the global page count (0x072c high half) steps, in pages
of 0x0724, in the first TA run of every kept DPM timeline, and how far each job's first threshold
is from the nearest step.  Tests H-GREQ's kept-data side: a grow (0x0628 low half below 0x10
before the first abort) only where the threshold meets a step.  Read-only."""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from tlc import load
from endstretch import jobs, stretches, hi
import csv
def main():
    out = []
    for ds, stg, name, d in jobs():
        try: hdr, cols, rows = load(f'{d}/{name}.txt.gz')
        except Exception: continue
        if not rows or 0x72c not in rows[0][1]: continue
        st = stretches(rows)
        if not st: continue
        meta = {}
        cp = f'{d}/cases.tsv'
        if os.path.exists(cp):
            for r in csv.DictReader(open(cp), delimiter='\t'): meta[r['name']] = r
        args = meta.get(name, {}).get('args', '')
        m = re.search(r'--width (\d+) --height (\d+)', args); wh = f'{m.group(1)}x{m.group(2)}' if m else '?'
        v = re.search(r'--vertices (\d+)', args); nv = v.group(1) if v else '-'
        scene = 'full' if '--tri-full' in args else ('tri' + nv)
        a = st[0][0]; thr = rows[a][1][0x624]
        steps = []   # (gps_new, ps_before, ps_after)
        pg = None; pp = None
        for i in range(1, a):
            g = hi(rows[i][1], 0x72c); p = hi(rows[i][1], 0x724)
            if pg is not None and g > pg: steps.append((g, pp, p))
            pg, pp = g, p
        g628 = sorted({rows[i][1][0x628] for i in range(1, a + 1)})
        grow = any((x & 0xffff) < 0x10 for x in g628)
        gA = hi(rows[a - 1][1], 0x72c)
        out.append((wh, scene, thr, name, stg, gA, grow, steps))
    out.sort()
    for wh, scene, thr, name, stg, gA, grow, steps in out:
        s = ' '.join('%d:(%x,%x]' % (g, a, b) for g, a, b in steps)
        print(f'{wh:10} {scene:8} thr0={thr:#06x} gpsA={gA} grow={int(grow)} {stg}/{name:16} steps {s}')
if __name__ == '__main__': main()
