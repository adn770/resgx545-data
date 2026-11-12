#!/usr/bin/env python3
"""Round 5 dpm planning, offline: every TA run (job start to first partial render, and each run
between partial renders) of every kept DPM timeline: the steps of the global page count, the page
count at the run's end, the step the run's own period predicts next, and any grow of 0x0628
(low half below 0x10).  Kept-data side of H-GREQ beyond the first run.  Read-only."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from tlc import load
from endstretch import jobs, stretches, hi
def main():
    ngrow = 0; nruns = 0; hits = []
    for ds, stg, name, d in jobs():
        try: hdr, cols, rows = load(f'{d}/{name}.txt.gz')
        except Exception: continue
        if not rows or 0x72c not in rows[0][1]: continue
        st = stretches(rows)
        if not st: continue
        bounds = [(1, st[0][0])] + [(st[k][1] + 1, st[k + 1][0] if k + 1 < len(st) else len(rows)) for k in range(len(st))]
        for k, (a, b) in enumerate(bounds):
            if b - a < 2: continue
            nruns += 1
            steps = []; pg = pp = None; grow = False; thrs = set(); raised = False
            base628 = rows[a][1][0x628]
            for i in range(a, b):
                v = rows[i][1]; g = hi(v, 0x72c); p = hi(v, 0x724)
                if (v[0x628] & 0xffff) < 0x10 and v[0x628] != 0: grow = True
                if pg is not None and g > pg and p >= (pp or 0): steps.append((g, pp, p))
                pg, pp = g, p
                thrs.add(v[0x624])
            ended_abort = b < len(rows) and k < len(st)
            psend = hi(rows[b - 1][1], 0x724); thr = rows[b - 1][1][0x624]
            pred = None
            if len(steps) >= 2 and steps[-2][1] is not None: pred = steps[-1][1] + (steps[-1][1] - steps[-2][1])
            ngrow += grow
            tag = ''
            if ended_abort and pred is not None and abs(psend - pred) <= 1: tag = 'AT-STEP d=%+d' % (psend - pred)
            if grow or tag:
                hits.append(f'{stg}/{name} run {k + 1} of {len(bounds)} thr={thr:#x} ps_end={psend:#x} '
                            f'steps={[(g, hex(x or 0)) for g, x, y in steps]} pred_next={pred and hex(pred)} grow={int(grow)} {tag}')
    print('runs', nruns, 'runs with a grow of 0x0628', ngrow)
    for h in hits: print(h)
main()
