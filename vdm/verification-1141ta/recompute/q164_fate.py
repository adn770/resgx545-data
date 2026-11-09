#!/usr/bin/env python3
"""p1141/ta q164_fate.py: Q164 (bit-21 object = first part on another PB page) and Q094 capacity.

Uses the LANDED decoder recompute_p1131 (regions, stream, stream_objects, first_object) for the
byte layout only; the page test and the per-vertex fate are rewritten here.
Vertex identity: packed (x, y) floats -> index i = 3t + c, corners (-.75,-.75), (.75,-.375),
(-.375,.75), + t/512.  Object word address a (dword, file = a - 0x400), nv vertices of 'per' dwords
before the ISP word at file f; the bytes that fit between the page start and f are the object's
tail; if more are needed and the stream's extra word e is set, the missing head is the end of PB
page (e >> 10) - 1 in file terms (the claim tested; page claim PC), vs the alternative "head is
the page before the tail's page" (ALT).
Per job: lost / duplicated / unreadable vertices of the 126 (42 triangles), grouped by R*V.
Fit status: the page claim and 'C in 33..35' were fitted on these 61+12 jobs (no held-out here).
Usage: python3 q164_fate.py
"""
import collections, gzip, pathlib, struct, sys
ROOT = pathlib.Path.home() / 'src/resgx545-data/vdm/vtask-capacity'
sys.path.insert(0, str(ROOT / 'analysis'))
import recompute_p1131 as R
CORN = [(-0.75, -0.75), (0.75, -0.375), (-0.375, 0.75)]; DT = 1 / 512
def fl(u): return struct.unpack('<f', struct.pack('<I', u))[0]
def vid(a, b):
    for c, (cx, cy) in enumerate(CORN):
        t = round((a - cx) / DT)
        if 0 <= t < 42 and abs(a - (cx + t * DT)) < 1e-4 and abs(b - (cy + t * DT)) < 1e-4: return 3 * t + c
    return None
def objects(p, td):
    per = R.first_object(p, td)['per']; ws = R.words(p, 0, len(p) // 4); out = {}
    for (_i, x, y, _f, st) in R.regions(td):
        if st:
            for (pw, ow, e, m) in R.stream_objects(R.stream(p, st)):
                out[ow & 0x3ffffff] = (((pw >> 25) & 0xf) + 1, e)
    return per, ws, out
def verts(ws, per, a, nv, e, alt=False):
    f = a - 0x400; pg = f & ~0x3ff; tot = per * nv; have = f - pg
    if e is not None and tot > have:
        page = (e >> 10) - 1 if not alt else (pg >> 10) - 1
        rem = tot - have; seq = ws[(page + 1) * 0x400 - rem:(page + 1) * 0x400] + ws[pg:f]
    else:
        seq = ws[f - tot:f]
    return [vid(fl(seq[i * per + 1]), fl(seq[i * per + 2])) if len(seq) == tot else None for i in range(nv)]
def main():
    rows = [l.split() for l in (ROOT / 'analysis/vtask-table.txt').read_text().splitlines()[1:]]
    byrv = collections.defaultdict(lambda: [0, 0, 0, 0, 0])  # jobs, lost, dup, unreadable, jobs-with-loss
    page_ok = page_n = alt_ok = 0
    for q in rows:
        N, Rr, V, sc, name = int(q[0]), int(q[1]), int(q[3]), q[5], q[6]
        d = ROOT / 'dumps' / sc
        p = gzip.open(d / f'{name}.param.bin.gz').read(); td = gzip.open(d / f'{name}.tadata.bin.gz').read()
        per, ws, O = objects(p, td)
        seen, unread = collections.Counter(), 0
        for a, (nv, e) in O.items():
            for alt in (False, True):
                vs = verts(ws, per, a, nv, e, alt)
                if e is not None and not alt:
                    page_n += 1; page_ok += all(v is not None for v in vs)
                if e is not None and alt: alt_ok += all(v is not None for v in vs)
                if not alt:
                    for v in vs:
                        if v is None: unread += 1
                        else: seen[v] += 1
        lost = sum(1 for i in range(126) if not seen[i]); dup = sum(1 for c in seen.values() if c > 1)
        b = byrv[Rr * V]; b[0] += 1; b[1] += lost; b[2] += dup; b[3] += unread; b[4] += lost > 0
    print(f'objects with bit 21: fully identified with page claim {page_ok}/{page_n}; with ALT page {alt_ok}/{page_n}')
    print('R*V : jobs  lost  dup  unreadable  jobs-with-loss')
    for k in sorted(byrv): print(f'{k:4d}: ' + ' '.join(f'{x:5d}' for x in byrv[k]))
    le = [k for k in byrv if k <= 33]; print('R*V<=33 totals (jobs, lost, dup, unreadable):',
          [sum(byrv[k][i] for k in le) for i in range(4)])
if __name__ == '__main__': main()
