#!/usr/bin/env python3
"""G4 (round 7 dpm offline stage, Q211, exploratory, no verdict).  Scenes of several kicks or
renders of the tool's triangle (--geometry N, or -n above 1): the last render's dump of every
kept job, every region's whole stream (f3_streams.chain), every block placed by its address.
Per macrotile the blocks in address order are walked with G1's key (strip of 64 pixel rows,
64-pixel block, region row, region column; a chained block after its region's earlier ones):
a descent of the key starts a new walk.  Printed per dump: blocks, walks seen (the most
descents of any macrotile, plus one), and at each descent whether the block that follows went
into the page the previous block left with room (same page) or opened a page; with one walk,
G1's placement of the first blocks (olib.place) as a check.  A dump whose job had a partial
render (0x0658 stretches in its timeline) is marked.  Read-only, public data; standard library
only."""
import collections, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import olib as O
import gzip
from f3_streams import chain
KEY = lambda c, r: (r // 8, c // 4, r, c)      # noqa: E731  (G1's walk64 on header units)


def main():
    for ds, stg, d, name, args, row in O.cases():
        t = args.split()
        v, n, g = O.opt(args, '--vertices'), O.opt(args, '-n'), O.opt(args, '--geometry')
        if not (g or (n and int(n) > 1)) or (v and int(v) != 3) or '--aa4' in t:
            continue
        pres = [p for p in O.dumps(d, name) if not O.re.search(r'\.\d+\.$', p)]
        if len(pres) != 1:
            continue
        w, h = int(O.opt(args, '--width')), int(O.opt(args, '--height'))
        tl = os.path.join(d, name + '.txt.gz')
        rows = O.load(tl)[1] if os.path.exists(tl) else []
        part = ('partial' if O.stretches(rows) else 'one run') if rows and 0x658 in rows[0][1] else 'run unread'
        regs = O.regions_of(pres[0], w, h)
        param = gzip.open(pres[0] + 'param.bin.gz').read()
        blocks = collections.defaultdict(list)
        for x in regs:
            for j, (addr, ents, used) in enumerate(chain(param, x['addr'])):
                blocks[x['m']].append((addr, KEY(x['c'], x['r']) + (j,)))
        walks, same, newp, nb = 1, 0, 0, 0
        for m, bl in blocks.items():
            bl.sort()
            nb += len(bl)
            dsc = 0
            for (a0, k0), (a1, k1) in zip(bl, bl[1:]):
                if k1 < k0:
                    dsc += 1
                    if a1 >> 12 == a0 >> 12:
                        same += 1
                    else:
                        newp += 1
            walks = max(walks, dsc + 1)
        first = O.place(regs, lambda c, r: KEY(c, r))
        print('%-12s %-30s %-22s %4dx%-4d %-10s blocks %5d (first %5d) walks %d | at a new walk: same page %3d, new page %3d | first blocks by G1 %d of %d' % (
            ds[8:], stg, name, w, h, part, nb, len(regs), walks, same, newp, first[0], first[1]),
            '|', ' '.join(a for a in t if a in ('-n', '--geometry', '--move') or a[:1].isdigit() or ':' in a)[:60])


if __name__ == '__main__':
    main()
