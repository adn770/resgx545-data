#!/usr/bin/env python3
"""Round 7 planner, Q211 (post hoc tally): the record cells of E625 / E779 (counts only) under the
walk order read from dumps (q211_walk64.py), with f7_replay's frozen replay and cell lists."""
import sys
sys.path.insert(0, '/Users/jtorra/src/scratch/resgx545/closing6/dpm/offline')
import f7_replay as F7
H = F7.H
key = lambda z: (z[1] // 4, z[0] // 2, z[1], z[0])
for nm, cl, w, h in (('E625 4096x4096', F7.E625, 4096, 4096), ('E779 4096x4096', F7.E779, 4096, 4096), ('E625 1024x768 U 19', F7.U19, 1024, 768)):
    tri = [H.default_tri(w, h)]
    rg = sorted(F7.regions(w, h, tri, 'row'), key=key)
    bad = [(hex(t), n, F7.replay(rg, t)) for t, n in cl if (rp := F7.replay(rg, t)) is None or rp[0] != n]
    print('%-20s walk64 count %d of %d %s' % (nm, len(cl) - len(bad), len(cl), bad))
