"""Round 7 fold F1 (faults area, Q003): boot110's tables frozen as a fit, scored on r6-held.
Usage: f1_fit.py <data-root> > f1_fit.out (reads ../offline/boot110.py beside this file).

Frozen 2026-11-12 before its first run (sha256 in FROZEN-f1.sha256). Honest label: the rule
was read off the corpus by the planner's scans (offline/boot_page.out), which already
included r6-held, so the held-out part is SEMI (seen, not blind), never held out.

Rule R-PAGE (exp-faults-r7.md 1.2 F1, not tuned): the first boot after a BIF fault with status
0x90004 and SB ((addr >> 4) & 0xf) 6 times out (no INIT_COMPLETE) iff the fault's page
(addr >> 12) is 0x20006 to 0x20008; every other fault word's first boot comes up.
Fit: every session but render/closing-r6-held. Scored: render/closing-r6-held, as it falls.
Control that can fail: no first boot after a 0x90008 or 0x90100 fault times out.
Out of the rule's domain and reported only: 0x90004 with SB other than 6 (the dpm sessions'
SB 5 at page 0x10000)."""
import collections
import contextlib
import io
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HELD = 'render/closing-r6-held'
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    g = runpy.run_path(os.path.join(HERE, '..', 'offline', 'boot110.py'))
rows = [r for r in g['rows'] if r['boots']]


def predict(r):
    a = int(r['addr'], 16)
    if r['st'] != '0x90004':
        return 'up'
    if (a >> 4) & 0xf != 6:
        return None
    return 'noinit' if 0x20006 <= a >> 12 <= 0x20008 else 'up'


def table(part):
    c = collections.Counter()
    miss = []
    for r in part:
        p = predict(r)
        if p is None:
            continue
        got = r['boots'][0]['res']
        kind = 'SB6' if r['st'] == '0x90004' else 'other'
        c[(kind, p, got)] += 1
        if got != p:
            miss.append(r)
    return c, miss


for name, part in (('fit', [r for r in rows if r['sess'] != HELD]),
                   ('scored (r6-held, SEMI)', [r for r in rows if r['sess'] == HELD])):
    c, miss = table(part)
    print(f'# {name}: kind predicted observed count')
    for k in sorted(c):
        print(*k, c[k])
    n = sum(c.values())
    print(f'{name}: {n - len(miss)} of {n} first boots as R-PAGE says, {len(miss)} not')
    for r in miss:
        print('  miss', r['sess'], '%.3f' % r['t'], r['st'], r['addr'],
              'held' if r['held'] else 'auto', r['boots'][0]['res'])
ctl = [r for r in rows if r['st'] in ('0x90008', '0x90100')]
bad = [r for r in ctl if r['boots'][0]['res'] != 'up']
print(f'control: {len(ctl) - len(bad)} of {len(ctl)} first boots after 0x90008/0x90100 came up:',
      'PASS' if ctl and not bad else 'FAILED')
out = collections.Counter((r['sess'] == HELD, r['boots'][0]['res']) for r in rows
                          if r['st'] == '0x90004' and (int(r['addr'], 16) >> 4) & 0xf != 6)
print('outside the domain (0x90004, SB not 6): r6-held? result count')
for k in sorted(out):
    print(*k, out[k])
