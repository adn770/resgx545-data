#!/usr/bin/env python3
"""F3 (round 6 dpm offline stage; no verdict, it feeds H-BURST-PAGE against H-BURST-CAP): the
control streams of the tool's 1500-vertex triangle, read from the render dumps of kept jobs
that completed in one TA run (DPM state lists empty), so no page was reused.  A stream block is
128 bytes (32 dwords); its entries are a primitive word and an object word (CSTREAM), plus one
dword when PRIM_TILES has bit 5 (word bit 21: the new base of the objects, a global page's
address) and one when PRIM_TILES is 0x88, 0x8a or 0x8c (a mask dword); a word without bit 30
after the entries is the link to the next block (its slot offset), 0xc0000000 ends the stream.
The object of an entry is placed in the global list by its address: page S_k + 1 is global
page k (F1's one-valued S_k), offset 18 is the first block's ISP words (FIT dump), L = 67.

Prints per dump: the regions with a stream, blocks per region, the entry dwords per block, and
by object index the count of regions whose entry for that object opens a new block (the burst
profile in objects) and the count of base-carrying entries; then where the global list's page
changes (objects b_k of F2).  Read-only, public data; standard library only.

Fixed after its first run (FIX-f3.md): every region header (the as-run version read the first
TA data page's only), and the mask forms with bit 5 (0xa8, 0xaa, 0xac) counted as 4 dwords."""
import collections, gzip, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
TREE = os.environ.get('RESGX545_TREE', '/Users/jtorra/src/resgx545')
sys.path.insert(0, os.path.join(TREE, 'tools', 'usse-asm'))
import dpm_words as D, pbdump as P
from r6lib import jobs, scene_of
from f1_brackets import brackets

L, ISP0 = 67, 18


def chain(param, addr):
    """[(block slot offset, [(prim, objaddr, dwords)])] of one region's stream."""
    out = []
    for _ in range(4096):
        ws = struct.unpack_from('<32I', param, addr - P.PB_BASE)
        ents, i, nxt = [], 0, None
        while i < 32:
            w = ws[i]
            if w == P.FILLER or w == 0:
                break
            if not (w >> 30) & 1:
                nxt = w; break
            tiles = (w >> 16) & 0xff
            n = 2 + ((tiles >> 5) & 1) + ((tiles & ~0x20) in P.THIRD_DWORD_TILES)
            ents.append((w, ws[i + 1] & 0x3ffffff, n, tiles))
            i += n
        out.append((addr, ents, i))
        if nxt is None:
            return out
        if not P.PB_BASE <= nxt < P.PB_BASE + len(param) - 128:
            raise RuntimeError(f'link {nxt:#x} outside the dump in block {addr:#x}')
        addr = nxt
    raise RuntimeError('stream chain does not end')


def regions(tad, w, h):
    """Every region header of the target (pbdump.regions reads the first TA data page only):
    REGION_HDR words at the TA data's region header offset, three dwords each."""
    lay = D.tadata_layout(w, h)
    n, mx, my = D.mtile_grid(w, h)
    cnt = n * n * mx * my
    ws = struct.unpack_from(f'<{3 * cnt}I', tad, lay['rgn'])
    return [P.Region(i, (ws[3 * i] >> 16) & 0xff, ws[3 * i] & 0xffff, ws[3 * i] >> 24, ws[3 * i + 1])
            for i in range(cnt) if ws[3 * i] or ws[3 * i + 1]]


def main():
    iv = brackets()
    for ds, stg, name, d, m in jobs():
        pre = f'{d}/{name}.p1139-green'
        args = m.get('args', '')
        if not os.path.exists(pre + '.param.bin.gz') or '--vertices 1500' not in args:
            continue
        if '--move' in args or '--geometry' in args or '--tri-full' in args:
            continue
        wh, sc = scene_of(args)
        w, h = (int(x) for x in wh.split('x'))
        param = gzip.open(pre + '.param.bin.gz').read()
        tad = gzip.open(pre + '.tadata.bin.gz').read()
        words = list(struct.unpack_from('<64I', tad, D.tadata_layout(w, h)['state']))
        if any(l['PAGE_COUNT'] for l in D.state_lists(words)):
            continue                          # overflowed: pages were reused
        kof = {1: 1}
        for (t, s, k), Lb in iv.items():
            lo = max(a for a, b, _ in Lb); top = min(b for a, b, _ in Lb)
            if (t, s) == (wh, sc) and lo == top:
                kof[lo + 1] = k
        def obj(a):
            k = kof.get(a // 1024)
            return None if k is None else ((k - 1) * 1024 + a % 1024 - ISP0) // L
        opens = collections.Counter(); bases = collections.Counter(); fill = collections.Counter()
        nblk = collections.Counter(); nreg = 0; unplaced = 0; ent_per = collections.Counter()
        for r in regions(tad, w, h):
            if not r.stream:
                continue
            nreg += 1
            ch = chain(param, r.stream)
            nblk[len(ch)] += 1
            for bi, (addr, ents, used) in enumerate(ch):
                if bi + 1 < len(ch):
                    fill[used] += 1
                ent_per[len(ents)] += 1
                for ei, (pw, a, n, tiles) in enumerate(ents):
                    o = obj(a)
                    if o is None:
                        unplaced += 1; continue
                    if ei == 0:
                        opens[o] += 1
                    if (tiles >> 5) & 1:
                        bases[o] += 1
        bk = {k: (1024 * (k - 1)) // L for k in range(2, 9)}
        print(f'== {ds[8:]}/{stg}/{name} ({wh}): {nreg} regions with a stream; blocks per region '
              f'{dict(sorted(nblk.items()))}; entry dwords of full blocks {dict(sorted(fill.items()))}; '
              f'entries per block {dict(sorted(ent_per.items()))}; entries unplaced {unplaced}')
        print('   global page k begins in object b_k:', ' '.join(f'k{k}:{b}' for k, b in bk.items()))
        print('   objects opening blocks (object: regions):', ' '.join(f'{o}:{n}' for o, n in sorted(opens.items())))
        print('   objects with a base dword (object: regions):', ' '.join(f'{o}:{n}' for o, n in sorted(bases.items())))


if __name__ == '__main__':
    main()
