#!/usr/bin/env python3
"""O2: what the global list holds.  For a kept render dump (param + tadata) of a job, the DPM
state lists, the global list's page chain, and per global page: used dwords (up to the last
non-zero), and the first words.  Read-only, public data."""
import sys, gzip, struct
sys.path.insert(0, '/Users/jtorra/src/resgx545/tools/usse-asm')
import dpm_words as D, pbdump as P
def rd(p): return gzip.open(p).read()
def main(prefix, w, h, pages):
    param = rd(prefix + '.param.bin.gz'); tad = rd(prefix + '.tadata.bin.gz')
    lay = D.tadata_layout(w, h)
    words = list(struct.unpack_from('<64I', tad, lay['state']))
    pt = D.read_page_table(param, pages)
    for l in D.state_lists(words):
        ch = D.list_chain(pt, l)
        print(l['list'], 'count', l['PAGE_COUNT'], 'head %#x tail %#x' % (l['HEAD'], l['TAIL']),
              'chain', ' '.join('%x' % c for c in ch[:40]), '...' if len(ch) > 40 else '')
        if l['index'] == 16:
            for pg in ch:
                ws = struct.unpack_from('<1024I', param, (pg - 1) * 4096)
                last = max((i for i, x in enumerate(ws) if x), default=-1)
                print('   global page %#x: used dwords %d; head %s' % (pg, last + 1, ' '.join('%08x' % x for x in ws[:12])))
if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4], 0))
