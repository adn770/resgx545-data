#!/usr/bin/env python3
"""F2 (round 6 dpm offline stage, H-OBJPAGE [infer]), fixed version: the global list holds the
TA's object blocks back to back, L dwords each, so global page k begins inside block
b_k = floor(1024 (k - 1) / L) and the request for page k comes while that block is written.

The as-run version (f2_objpage.as-run.py, frozen sha256 in FREEZE-f2.sha256, output
f2_objpage.as-run.out) read PB page 1 as the global list's head in every dump; after a partial
render the list's head moves (the partial render frees the list's first pages), so in overflowed
dumps it read stream blocks there (period 32), and it stopped on a job without 0x0658.  This
version (see FIX-f2.md) takes the list's pages from the DPM state words when the dump holds them
and PB page 1 when the lists read empty (a job that completed), and looks for the block head
pair read in the fit dump, frozen below; a page is tested only when F1 gives its S_k as one
value and the first TA run reached it (so the page is global page k, taken in the first run).
Test: the head pair recurs in the page at exactly the offsets o with (1024 (k - 1) + o) % L == 0,
L the period of the pair in the dump's own list head page 1 (complete jobs) or the fit dump's
(overflowed).  Fit side: r5-dpm a0-cal-2048.  Read-only, public data."""
import gzip, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TREE = os.environ.get('RESGX545_TREE', '/Users/jtorra/src/resgx545')
sys.path.insert(0, os.path.join(TREE, 'tools', 'usse-asm'))
import dpm_words as D
from r6lib import jobs, scene_of, load, stretches, hi
from f1_brackets import brackets

FIT = 'r5-dpm/a2/d-a0/a0-cal-2048'
HEAD = (0x04000004, 0x00030001)    # the first block's two head dwords in FIT's PB page 1
L_FIT = 67                         # their period there (glob_pages.py / page_peek.py, O2)


def page(param, pg):
    return struct.unpack_from('<1024I', param, (pg - 1) * 4096)


def rec(ws):
    return [i for i in range(1023) if (ws[i], ws[i + 1]) == HEAD]


def main():
    iv = brackets()
    S = {}
    for (wh, sc, k), L in iv.items():
        lo = max(a for a, b, _ in L); top = min(b for a, b, _ in L)
        if lo == top:
            S[(wh, sc, k)] = lo
    tally = {'fit': [0, 0], 'held': [0, 0]}
    Lseen = {}
    for ds, stg, name, d, m in jobs():
        pre = f'{d}/{name}.p1139-green'
        if not os.path.exists(pre + '.param.bin.gz'):
            continue
        args = m.get('args', '')
        if '--vertices 1500' not in args or '--move' in args or '--geometry' in args:
            continue
        job = f'{ds[8:]}/{stg}/{name}'
        side = 'fit' if job == FIT else 'held'
        wh, sc = scene_of(args)
        w, h = (int(x) for x in wh.split('x'))
        param = gzip.open(pre + '.param.bin.gz').read()
        tad = gzip.open(pre + '.tadata.bin.gz').read()
        cols, rows = load(f'{d}/{name}.txt.gz')
        if not rows or 0x658 not in rows[0][1] or 0x724 not in rows[0][1]:
            print('%-40s %-4s no 0x0658 or 0x0724 sampled: not tested' % (job, side))
            continue
        st = stretches(rows)
        end = st[0][0] if st else len(rows)
        peak1 = max(hi(rows[i][1], 0x724) for i in range(end))
        words = list(struct.unpack_from('<64I', tad, D.tadata_layout(w, h)['state']))
        pt = D.read_page_table(param, len(param) // 4096)
        chain = []
        for l in D.state_lists(words):
            if l['index'] == 16:
                chain = D.list_chain(pt, l)
        r1 = rec(page(param, 1))
        diffs = sorted(set(b - a for a, b in zip(r1, r1[1:])))
        if not chain:
            src = 'lists empty: PB page 1'
            L = diffs[0] if len(diffs) == 1 and r1 and r1[0] == 0 else None
            pages = [1] + [S[(wh, sc, k)] + 1 for k in range(2, 9) if (wh, sc, k) in S]
        else:
            src = 'list ' + ' '.join('%x' % c for c in chain[:6])
            L = L_FIT
            pages = chain
        Lseen.setdefault((wh, sc), set()).add(L)
        parts = []
        for k in range(2, 9):
            s = S.get((wh, sc, k))
            if s is None or s + 1 > peak1 or s + 1 not in pages or L is None:
                continue
            r = rec(page(param, s + 1))
            first = (-1024 * (k - 1)) % L
            ok = bool(r) and r[0] == first and all((1024 * (k - 1) + o) % L == 0 for o in r)
            tally[side][0] += ok; tally[side][1] += 1
            parts.append('k%d pg %#x first %d at %s %s' % (k, s + 1, first, r[:2], 'ok' if ok else 'NO'))
        print('%-40s %-4s %s; L %s (page 1 pair %s, diffs %s) | %s' % (job, side, src, L, 'yes' if r1 else 'no',
              diffs[:3], '; '.join(parts) or 'no page tested'))
    print('L by (target, scene):', {k: sorted(str(x) for x in v) for k, v in sorted(Lseen.items())})
    for side in ('fit', 'held'):
        print('phase test %s: %d of %d global pages begin where H-OBJPAGE puts them'
              % (side, tally[side][0], tally[side][1]))


if __name__ == '__main__':
    main()
