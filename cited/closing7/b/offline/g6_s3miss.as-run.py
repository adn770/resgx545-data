#!/usr/bin/env python3
"""G6 (round 7 dpm offline stage, Q210, exploratory, no verdict): the 2048x4096 S3 miss (E874's
replay gives 0x129, the brackets read 0x12c).  G5's reading on the kept 2048x4096 dumps of the
1500-vertex scene (R3-geo g-c5, c5b-*): the objects every region's stream names, placed in
global-list order, the objects that open stream blocks and those that carry the base dword, by
region count, against E874's replay (f5lib, unchanged) at that target: its b_k and its blocks
opened per object.  In an overflowed dump only the objects since the last partial render are
named.  Read-only, public data; standard library only."""
import collections, gzip, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import olib as O
import f5lib as F
from f3_streams import chain, regions
W, Hh = 2048, 4096


def read(pre):
    param = gzip.open(pre + 'param.bin.gz').read()
    tad = gzip.open(pre + 'tadata.bin.gz').read()
    seqs = []
    for r in regions(tad, W, Hh):
        if r.stream:
            seqs.append([(a, ei == 0, (tiles >> 5) & 1) for addr, ents, used in chain(param, r.stream)
                         for ei, (pw, a, n, tiles) in enumerate(ents)])
    before = collections.defaultdict(set)
    pages = sorted({a // 1024 for s in seqs for a, _, _ in s})
    for s in seqs:
        ps = []
        for a, _, _ in s:
            if not ps or ps[-1] != a // 1024:
                ps.append(a // 1024)
        for x, y in zip(ps, ps[1:]):
            before[y].add(x)
    order, left = [], set(pages)
    while left:
        nxt = sorted(p for p in left if not (before[p] & left))
        if len(nxt) != 1:
            return None
        order.append(nxt[0]); left.discard(nxt[0])
    gpos = {p: i for i, p in enumerate(order)}
    addrs = sorted({gpos[a // 1024] * 1024 + a % 1024 for s in seqs for a, _, _ in s})
    idx = {x: i for i, x in enumerate(addrs)}
    opens, bases = collections.Counter(), collections.Counter()
    for s in seqs:
        for a, op, bs in s:
            o = idx[gpos[a // 1024] * 1024 + a % 1024]
            opens[o] += op; bases[o] += bs
    return len(seqs), len(addrs), opens, bases


def main():
    S, mopens, after = F.replay(W, Hh, F.entries(W, Hh), 3)
    print('model: S', ' '.join('%d:%#x' % x for x in sorted(S.items())), '| b_k',
          ' '.join('k%d:%d' % (k, F.bk(k)) for k in sorted(S)))
    print('model blocks opened per object:', ' '.join('%d:%d' % (o, n) for o, n in sorted(mopens.items()) if n))
    for ds, stg, d, name, args, row in O.cases():
        if '--width 2048 --height 4096' not in args or '--vertices 1500' not in args or '--vtx-coords' in args:
            continue
        for pre in O.dumps(d, name):
            r = read(pre)
            if r is None:
                print('== %s/%s: global page order not total' % (stg, name)); continue
            nreg, nobj, opens, bases = r
            print('== %s/%s P %s: %d regions, %d objects named' % (stg, name, row.get('P'), nreg, nobj))
            print('   opens:', ' '.join('%d:%d' % (o, n) for o, n in sorted(opens.items()) if n))
            print('   bases:', ' '.join('%d:%d' % (o, n) for o, n in sorted(bases.items()) if n))


if __name__ == '__main__':
    main()
