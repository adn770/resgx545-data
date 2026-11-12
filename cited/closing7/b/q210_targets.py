#!/usr/bin/env python3
"""Round 7 planner: E874's replay at candidate targets never run; where H-SPAN's A_k and E874's
B_k part (cells B_k <= thr0 < A_k: SPAN leaves 2, E874 leaves 1).  Model output, not data."""
import sys
sys.path.insert(0, '/Users/jtorra/src/scratch/resgx545/closing6/dpm/offline')
import f5lib as F
for w, h in [(1024, 1024), (1536, 1024), (1024, 1536), (2560, 1536), (3072, 2048), (2048, 3072), (2560, 2560), (3072, 3072), (2048, 4096), (1024, 2048), (1536, 1536)]:
    ents = F.entries(w, h); S, opens, after = F.replay(w, h, ents, 3)
    out = []
    for k in sorted(S):
        a = after[F.bk(k)]; b = after[next(t for t in range(F.bk(k) - 3, F.OBJS) if t % 15 == 0)]
        out.append('S%d %#x B %#x A %#x%s' % (k, S[k], b, a, ' *%d' % (a - b) if a != b else ''))
    print('%dx%d U %#x: %s' % (w, h, after[-1], '; '.join(out)))
