#!/usr/bin/env python3
"""Round 7 planner (post hoc, exploratory): the object blocks of the r-v calibration dumps
(--vtx-coords 4 and 8), PB page 1: where the head pair recurs and how a 187-dword block differs
from a 198-dword one.  Read-only, public data (render/closing-r6-dpm)."""
import gzip, struct, sys
D = '/Users/jtorra/src/resgx545-data/render/closing-r6-dpm/out/a2/r-v/'
HEAD = (0x04000004, 0x00030001)
for n in ('v-cal-c4', 'v-cal-c8'):
    p = gzip.open(D + n + '.p1139-green.param.bin.gz').read()
    ws = struct.unpack_from('<2048I', p, 0)
    r = [i for i in range(2047) if (ws[i], ws[i + 1]) == HEAD]
    print(n, 'head pair at', r[:12], 'diffs', [b - a for a, b in zip(r, r[1:])][:11])
    blocks = [ws[a:b] for a, b in zip(r, r[1:])][:8]
    for i, b in enumerate(blocks[:7]):
        print('  block %d len %d head: %s' % (i, len(b), ' '.join('%08x' % x for x in b[:34])))
        print('           tail: %s' % ' '.join('%08x' % x for x in b[-14:]))
