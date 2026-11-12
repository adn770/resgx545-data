#!/usr/bin/env python3
"""F2 (round 6 dpm offline stage, H-OBJPAGE [infer]): the global list holds the TA's object
blocks back to back, L dwords each, so global page k begins inside block
b_k = floor(1024 (k - 1) / L) and the request for page k comes while that block is written.
Per kept render dump (NAME.p1139-green.param.bin.gz with its tadata) of the tool's triangle with
1500 vertices (and --tri-full), read: L, the period of the first block's two head dwords in PB
page 1 (the global list's head); whether it is the only period on the page; and for each step k
whose S_k F1's table gives as one value (and that the first TA run reached, so the page is the
global one), whether the head pair recurs in PB page S_k + 1 exactly at the offsets o with
(1024 (k - 1) + o) % L == 0.  The global list's chain from the DPM state words where the dump
holds them (an overflowed job).  Fit side: r5-dpm a0-cal-2048 (L read there); every other dump
is held out for the phase test (L is read from each dump's own page 1, never carried over).
Read-only, public data; tools/usse-asm's dpm_words for the state words."""
import gzip, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TREE = os.environ.get('RESGX545_TREE', '/Users/jtorra/src/resgx545')
sys.path.insert(0, os.path.join(TREE, 'tools', 'usse-asm'))
import dpm_words as D
from r6lib import jobs, scene_of, load, stretches, hi
from f1_brackets import brackets

FIT = 'r5-dpm/a2/d-a0/a0-cal-2048'


def page(param, pg):
    return struct.unpack_from('<1024I', param, (pg - 1) * 4096)


def period(ws):
    occ = [i for i in range(1023) if ws[i] == ws[0] and ws[i + 1] == ws[1]]
    diffs = sorted(set(b - a for a, b in zip(occ, occ[1:])))
    return occ, diffs


def main():
    iv = brackets()
    S = {}
    for (wh, sc, k), L in iv.items():
        lo = max(a for a, b, _ in L); top = min(b for a, b, _ in L)
        S[(wh, sc, k)] = (lo, top)
    tally = {'fit': [0, 0], 'held': [0, 0]}
    Ls = {}
    print('job set L periods | k: page S_k+1, predicted first block offset, recurrences -> verdict')
    for ds, stg, name, d, m in jobs():
        pre = f'{d}/{name}.p1139-green'
        if not os.path.exists(pre + '.param.bin.gz'):
            continue
        args = m.get('args', '')
        if '--vertices 1500' not in args or '--move' in args or '--geometry' in args:
            continue
        wh, sc = scene_of(args)
        w, h = (int(x) for x in wh.split('x'))
        param = gzip.open(pre + '.param.bin.gz').read()
        tad = gzip.open(pre + '.tadata.bin.gz').read()
        job = f'{ds[8:]}/{stg}/{name}'
        side = 'fit' if job == FIT else 'held'
        occ, diffs = period(page(param, 1))
        Lb = diffs[0] if len(diffs) == 1 else None
        Ls.setdefault((wh, sc), set()).add(Lb)
        cols, rows = load(f'{d}/{name}.txt.gz')
        st = stretches(rows)
        end = st[0][0] if st else len(rows)
        peak1 = max(hi(rows[i][1], 0x724) for i in range(end))
        parts = []
        for k in range(2, 9):
            if (wh, sc, k) not in S:
                continue
            lo, top = S[(wh, sc, k)]
            if top + 1 > peak1:
                continue                  # the first run did not reach page S_k + 1
            for s in sorted({lo, top}):
                pg = s + 1
                if pg > len(param) // 4096 or Lb is None:
                    continue
                ws = page(param, pg)
                rec = [i for i in range(1023) if ws[i] == page(param, 1)[0] and ws[i + 1] == page(param, 1)[1]]
                first = (-1024 * (k - 1)) % Lb
                ok = bool(rec) and all((1024 * (k - 1) + o) % Lb == 0 for o in rec) and rec[0] == first
                if lo == top:
                    tally[side][0] += ok; tally[side][1] += 1
                parts.append('S%d %#x->pg %#x first %d rec %s %s' % (k, s, pg, first, rec[:3],
                             'ok' if ok else ('NO' if lo == top else 'no (range)')))
        chain = ''
        words = list(struct.unpack_from('<64I', tad, D.tadata_layout(w, h)['state']))
        pt = D.read_page_table(param, len(param) // 4096)
        for l in D.state_lists(words):
            if l['index'] == 16:
                chain = 'global chain ' + ' '.join('%x' % c for c in D.list_chain(pt, l)[:8])
        print('%-40s %-4s L %s diffs %s | %s | %s' % (job, side, Lb, diffs[:3], '; '.join(parts), chain))
    print('L by (target, scene):', {k: sorted(x for x in v if x is not None) for k, v in sorted(Ls.items())},
          'unreadable' if any(None in v for v in Ls.values()) else '')
    for side in ('fit', 'held'):
        print('phase test (one-value steps) %s: %d of %d pages begin where H-OBJPAGE puts them'
              % (side, tally[side][0], tally[side][1]))


if __name__ == '__main__':
    main()
