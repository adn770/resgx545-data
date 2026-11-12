#!/usr/bin/env python3
"""Round 5 dpm planning, offline: for every kept DPM timeline, the samples around the first
abort (entry side) and around the end of the first partial render (resume side).
Read-only over resgx545-data/render/closing-*/out."""
import os, sys, csv, gzip, struct
sys.path.insert(0, os.path.dirname(__file__))
from tlc import load
ROOT = '/Users/jtorra/src/resgx545-data/render'
STAGES = [('closing-r3-geo', s) for s in ('g-c4', 'g-c5', 'g-c6', 'g-c7', 'g-d36')] + \
         [('closing-r2-geo', s) for s in ('g-c3', 'g-c2')] + \
         [('closing-r1-pixgeo', s) for s in ('g-c1', 'g-c1f', 'g-u1', 'g-u2')]
hi = lambda v, r: (v[r] >> 16) & 0xffff
def stretches(rows):
    out = []; a = None
    for i, (t, v) in enumerate(rows):
        on = v[0x658] & 1
        if on and a is None: a = i
        if not on and a is not None: out.append((a, i - 1)); a = None
    if a is not None: out.append((a, len(rows) - 1))
    return out
def jobs():
    for ds, stg in STAGES:
        d = f'{ROOT}/{ds}/out/{stg}'
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d)):
            if f.endswith('.txt.gz') and '.' not in f[:-7]:
                yield ds, stg, f[:-7], d
def main():
    verbose = len(sys.argv) > 1
    for ds, stg, name, d in jobs():
        try: hdr, cols, rows = load(f'{d}/{name}.txt.gz')
        except Exception as e: continue
        if not rows or 0x72c not in rows[0][1]: continue
        st = stretches(rows)
        if not st: continue
        b = gzip.open(f'{d}/{name}.after.buf09.bin.gz').read()
        d38 = struct.unpack_from('<I', b, 4 * 38)[0]
        a, e = st[0]
        # entry side: 0x628 values between the job start and the stretch start
        g628 = []
        for i in range(1, a + 1):
            x = rows[i][1][0x628]
            if not g628 or g628[-1] != x: g628.append(x)
        grow = any((x & 0xffff) < 0x10 for x in g628[1:])
        # GPS sequence over the stretch, with the time to the stretch end
        seq = []
        for i in range(a - 1, min(e + 3, len(rows))):
            g = hi(rows[i][1], 0x72c); p = hi(rows[i][1], 0x724)
            on = rows[i][1][0x658] & 1
            if not seq or seq[-1][0:3] != (g, on, None):
                seq.append((g, on, None, rows[i][0] - rows[e][0], p))
        gseq = []
        for g, on, _, dt, p in seq:
            if not gseq or gseq[-1][0] != g or gseq[-1][1] != on: gseq.append((g, on, dt, p))
        tail = ' '.join('%d%s@%+dus(ps %x)' % (g, '*' if on else '', dt // 1000, p) for g, on, dt, p in gseq[-6:])
        gapR = rows[e + 1][0] - rows[e][0] if e + 1 < len(rows) else -1
        print(f'{stg:6} {name:18} raised={int(d38 == 0x20)} nst={len(st)} grow={int(grow)} '
              f'thr={rows[a][1][0x624]:#x} gps: {tail}')
if __name__ == "__main__": main()
