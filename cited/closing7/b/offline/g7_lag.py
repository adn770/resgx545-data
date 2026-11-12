#!/usr/bin/env python3
"""G7 (round 7 dpm offline stage, Q210, the lag of 3 objects; exploratory, no verdict).  In the
kept dumps of the tool's 1500-vertex scene (default vertex format, no --move, --geometry or
--vtx-coords) whose DPM state page names a global list (an overflowed job: the TA stopped at a
refused page), the global list's pages along the page table (dpm_words.state_lists entry 16,
list_chain), the object blocks on them by the head pair (0x04000004, 0x00030001), and the last
object any region's stream names (f3_streams.chain): the objects written to the global list
after the last one tiled.  E874's replay has the TA write object b just before it tiles object
b - 3.  Printed per dump and as a tally.  Read-only, public data; standard library only."""
import collections, gzip, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import olib as O
from f3_streams import chain, regions
from pbdump import PB_BASE
HEAD = (0x04000004, 0x00030001)


def main():
    tal = collections.Counter()
    for ds, stg, d, name, args, row in O.cases():
        if '--vertices 1500' not in args or any(x in args for x in ('--move', '--geometry', '--vtx-coords', '--tri-full')):
            continue
        w, h = int(O.opt(args, '--width')), int(O.opt(args, '--height'))
        for pre in O.dumps(d, name):
            param = gzip.open(pre + 'param.bin.gz').read()
            tad = gzip.open(pre + 'tadata.bin.gz').read()
            words = list(struct.unpack_from('<64I', tad, O.D.tadata_layout(w, h)['state']))
            pt = O.D.read_page_table(param, len(param) // 4096)
            gl = [l for l in O.D.state_lists(words) if l['index'] == 16]
            if not gl:
                continue
            pages = O.D.list_chain(pt, gl[0])
            heads = []
            for i, p in enumerate(pages):
                if not 1 <= p <= len(param) // 4096:
                    break
                ws = struct.unpack_from('<1024I', param, p * 4096 - PB_BASE)
                heads += [(i, p * 1024 + j) for j in range(1023) if (ws[j], ws[j + 1]) == HEAD]
            last = None
            try:
                for r in regions(tad, w, h):
                    if r.stream:
                        for addr, ents, used in chain(param, r.stream):
                            for pw, a, n, tiles in ents:
                                if a // 1024 in pages:
                                    k = (pages.index(a // 1024), a)
                                    last = k if last is None or k > last else last
            except RuntimeError as e:
                print('%-44s stream not read (%s)' % (f'{ds[8:]}/{stg}/{name}', e)); continue
            after = None if last is None else sum(1 for hd in heads if hd > last)
            tal[after] += 1
            print('%-44s %4dx%-4d P %-6s global pages %2d, object heads %3d, after the last object named: %s' % (
                f'{ds[8:]}/{stg}/{name}', w, h, row.get('P'), len(pages), len(heads), after))
    print('tally (objects after the last named: dumps):', ' '.join('%s:%d' % kv for kv in sorted(tal.items(), key=str)))


if __name__ == '__main__':
    main()
