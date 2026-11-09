#!/usr/bin/env python3
"""p1141/ta serv_diff.py: USE0_SERV_EVENT (0x0b14 low 16) minus HostCtl dword 12 ('ticks') in alive blocks.

Walks resgx545-data/firmware-tasks/**/*.json for dicts with parallel lists serv_event and ticks;
per record the MODE of the per-read differences (three reads, one may race by +1).  Histogram of
modes per top-level file group.  Claims to check (Opus): after arm+boot 4; after a page-command
run with no job 5; after stock gate + fill + triangle 20.  Fit/held-out split of the +15 gate
delta (trc-first vs trc-repeat) is by file name, only reported.
Usage: python3 serv_diff.py
"""
import collections, json, os, re
ROOT = os.path.expanduser('~/src/resgx545-data/firmware-tasks')
def walk(o, p=''):
    if isinstance(o, dict):
        s, t = o.get('serv_event'), o.get('ticks')
        if isinstance(s, list) and isinstance(t, list) and s and len(s) == len(t): yield p, s, t
        for k, v in o.items(): yield from walk(v, p + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from walk(v, p + f'/{i}')
rows = collections.defaultdict(collections.Counter)
for dp, _, fn in os.walk(ROOT):
    for f in sorted(fn):
        if not f.endswith('.json'): continue
        try: d = json.load(open(os.path.join(dp, f)))
        except Exception: continue
        grp = os.path.relpath(os.path.join(dp, f), ROOT)
        for p, s, t in walk(d):
            diffs = [((a & 0xffff) - (b & 0xffff)) & 0xffff for a, b in zip(s, t)]
            mode = collections.Counter(diffs).most_common(1)[0][0]
            rows[re.sub(r'\d+', 'N', grp)][mode] += 1
for g in sorted(rows): print(f'{g:70s}', dict(sorted(rows[g].items())))
tot = collections.Counter()
for g in rows: tot.update(rows[g])
print('all records, mode of diff:', dict(sorted(tot.items())))
