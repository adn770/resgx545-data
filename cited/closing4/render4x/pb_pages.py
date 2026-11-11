#!/usr/bin/env python3
"""Count non-zero 4 KiB pages of a --dump-render parameter dump (tri.param.bin.gz).
Read-only scratch analysis (closing4/render4x)."""
import gzip, sys
for p in sys.argv[1:]:
    d = gzip.open(p, 'rb').read()
    n = len(d) // 4096
    nz = [i for i in range(n) if d[i*4096:(i+1)*4096].strip(b'\0')]
    # runs
    runs = []
    for i in nz:
        if runs and runs[-1][1] == i - 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    print(p.split('/')[-1], 'pages', n, 'nonzero', len(nz),
          'runs', ' '.join('%x-%x' % (a, b) for a, b in runs[:14]), '...' if len(runs) > 14 else '')
