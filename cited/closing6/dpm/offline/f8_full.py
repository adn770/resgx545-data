#!/usr/bin/env python3
"""F8 (round 6 dpm offline stage, E802): does F5's replay explain why the --tri-full scene at
2048x2048 holds one global page at every cell E802 ran (thr0 0xd2 to 0xf3)?  The scene: the
full-target triangle (0,0) (3w,0) (0,3h) (sgxfive-test.c, --tri-full) with 1500 vertices, the
copies moved j/16 pixel as F5's.  Its constants are read from R3-geo g-c7's own dumps, not from
F5's scene: L, the period of the object block's head pair in a dump whose PB page 1 is the
list's head (c7-L-16, c7-L-4), and the entry forms, tallied over every region stream of
c7-cal; every region of the target has an entry for every object (the triangle covers it).
Then F5's replay (lag 3, frozen by F5's fit) gives S2 and S3, against F1's brackets
([0x200, 0x201] and 0x302, from c7-cal only).  Post hoc: E852 printed S2 = 0x200.  Read-only."""
import collections, gzip, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import f5lib as F
from f3_streams import chain, regions
from r6lib import ROOT

G = os.path.join(ROOT, 'closing-r3-geo', 'out', 'g-c7')
HEAD = (0x04000004, 0x00030001)
LAG = 3


def period(name):
    ws = struct.unpack_from('<1024I', gzip.open(f'{G}/{name}.p1139-green.param.bin.gz').read(), 0)
    occ = [i for i in range(1023) if (ws[i], ws[i + 1]) == HEAD]
    return occ, sorted(set(b - a for a, b in zip(occ, occ[1:])))


def main():
    Ls = set()
    for nm in ('c7-L-16', 'c7-L-4'):
        occ, diffs = period(nm)
        print(f'{nm}: head pair at {occ[:6]}; periods {diffs}')
        Ls.add(diffs[0])
    L = min(Ls)
    param = gzip.open(f'{G}/c7-cal.p1139-green.param.bin.gz').read()
    tad = gzip.open(f'{G}/c7-cal.p1139-green.tadata.bin.gz').read()
    forms = collections.Counter(); nreg = 0
    for r in regions(tad, 2048, 2048):
        if not r.stream:
            continue
        nreg += 1
        for addr, ents, used in chain(param, r.stream):
            for pw, a, n, tiles in ents:
                forms[(tiles & ~0x20, n - ((tiles >> 5) & 1))] += 1
    print(f'c7-cal: {nreg} regions with a stream; entry forms (PRIM_TILES without bit 5, dwords): '
          + ', '.join(f'{t:#x}/{n}: {c}' for (t, n), c in forms.most_common()))
    dw = forms.most_common(1)[0][0][1]
    tx, ty, n, mx, my = F.H.tiling(2048, 2048)
    ents = {b: [(c, r, dw) for r in range(ty) for c in range(tx)] for b in range(F.OBJS)}
    F.L = L
    S, opens, after = F.replay(2048, 2048, ents, LAG)
    print(f'replay: L {L}, entry dwords {dw}, lag {LAG}: S ' + ' '.join(f'{k}:{v:#x}' for k, v in sorted(S.items()))
          + f'; U {after[-1]:#x}; objects opening blocks ' + ' '.join(f'{b}:{o}' for b, o in opens.items() if o))
    print('S2 in [0x200, 0x201]:', 0x200 <= S[2] <= 0x201, '| S3 == 0x302:', S[3] == 0x302,
          '| one global page at every E802 cell (thr0 0xd2 to 0xf3 below S2):', S[2] > 0xf3)


if __name__ == '__main__':
    main()
