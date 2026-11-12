#!/usr/bin/env python3
"""G5 (round 7 dpm offline stage, Q210, larger objects; a reading, then H-CUM [infer]).  The two
calibration dumps of R6-dpm r-v (2048x2048, the tool's 1500-vertex triangle with --vtx-coords 4
and 8, P 0x422, one TA run, no partial render), read with no model:
- every region's stream (f3_streams.chain from the published round 6 library: entries of a
  primitive word, an object word, a base dword when PRIM_TILES bit 5 is set, a mask dword for
  the third-dword forms; the link after the entries);
- the global list's pages in object order (each stream names its objects in order; a page
  precedes another when some stream names an object on it first), and each object's ISP address
  (object word, dwords) placed on that order: an object's index is its rank;
- the object block sizes, as the differences of consecutive ISP addresses on one continuous
  global list (a page change adds the rest of the page), and, separately, the head pair
  (0x04000004, 0x00030001) recurrence on each global page (the planner's q210_n8blocks.py
  reading, all pages);
- the objects whose entries carry the base dword (by region count), and the objects that open a
  stream block (by region count): the block-open sequence;
- the steps S_k of the job's own first TA run (F1's bracket rule on 0x0724 and 0x072c).
Then H-CUM: global page k is requested by the object b_k whose block holds global dword
1024 (k - 1), from the read sizes (block 0 at dword 0); test (a) b_k against the base-dword
objects, (b) the steps of f5lib's replay (E874's: lag 3, 31 entry dwords a block, 32 blocks a
page, the entries model unchanged) with that b_k, against the brackets.  Fit N 4 (v-cal-c4),
SEMI N 8 (v-cal-c8: its PB page 1 was printed by the planner).  H-CUM would be frozen for the
session only if (a) and (b) hold at both N; otherwise it is not frozen.  Exploratory, no verdict
on any landed hypothesis.  Read-only, public data; standard library only."""
import collections, gzip, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import olib as O
import f5lib as F
from f3_streams import chain, regions
from r6lib import load, stretches, hi
from pbdump import PB_BASE        # the slot offset of the dump's first byte; object words are slot dwords
DIR = os.path.join(O.RENDER, 'closing-r6-dpm', 'out', 'a2', 'r-v')
HEAD = (0x04000004, 0x00030001)
W = Hh = 2048


def steps(name):
    cols, rows = load(os.path.join(DIR, name + '.txt.gz'))
    for r in (0x724, 0x72c, 0x658):
        if not rows or r not in rows[0][1]:
            raise SystemExit(f'{name}: {r:#x} not sampled')
    st = stretches(rows)
    if st:
        raise SystemExit(f'{name}: a partial render in a calibration')
    out, pg, pp = {}, None, None
    for i in range(1, len(rows)):
        g, p = hi(rows[i][1], 0x72c), hi(rows[i][1], 0x724)
        if pg is not None and g == pg + 1 and g >= 2 and p >= pp:
            out[g] = (pp, max(pp, p - 1))
        pg, pp = g, p
    return out, max(hi(r[1], 0x724) for r in rows)


def replay(gk, lag=3, objs=F.OBJS):
    """f5lib.replay with the global-page objects gk {object: k} given (the logic unchanged)."""
    ents = ENTS
    used, mt_blocks, pages, S, after = {}, {}, 1, {}, []
    writes = {}
    for b in range(objs):
        writes.setdefault(max(0, b - lag), []).append(b)
    for t in range(objs):
        for b in writes.get(t, []):
            if b in gk:
                S[gk[b]] = pages; pages += 1
        for c, r, dw in ents[t]:
            dw += 1 if t in gk else 0
            if (c, r) not in used or used[(c, r)] + dw > F.CAP:
                used[(c, r)] = 0
                m = F.mtile(W, Hh, c, r)
                nb = mt_blocks.get(m, 0)
                if nb % F.BPP == 0:
                    pages += 1
                mt_blocks[m] = nb + 1
            used[(c, r)] += dw
        after.append(pages)
    return S, after


ENTS = F.entries(W, Hh)


def read(name, lab):
    pre = os.path.join(DIR, name + '.p1139-green.')
    param = gzip.open(pre + 'param.bin.gz').read()
    tad = gzip.open(pre + 'tadata.bin.gz').read()
    seqs, base_of, opens, nreg = [], collections.Counter(), collections.Counter(), 0
    for r in regions(tad, W, Hh):
        if not r.stream:
            continue
        nreg += 1
        seq = []
        for bi, (addr, ents, used) in enumerate(chain(param, r.stream)):
            for ei, (pw, a, n, tiles) in enumerate(ents):
                seq.append((a, ei == 0, (tiles >> 5) & 1))
        seqs.append(seq)
    # page order: a precedes b when a stream names an object on a first, then one on b
    pages = sorted({a // 1024 for s in seqs for a, _, _ in s})
    before = collections.defaultdict(set)
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
            raise SystemExit(f'{name}: global page order not total ({len(nxt)} candidates)')
        order.append(nxt[0]); left.discard(nxt[0])
    gpos = {p: i for i, p in enumerate(order)}
    lin = lambda a: gpos[a // 1024] * 1024 + a % 1024          # noqa: E731
    addrs = sorted({lin(a) for s in seqs for a, _, _ in s})
    idx = {x: i for i, x in enumerate(addrs)}
    for s in seqs:
        for a, op, bs in s:
            o = idx[lin(a)]
            opens[o] += op
            base_of[o] += bs
    sizes = [b - a for a, b in zip(addrs, addrs[1:])]
    isp0 = addrs[0]
    # head pair recurrence on every global page (the planner's reading, all pages)
    heads = []
    for p in order:
        ws = struct.unpack_from('<1024I', param, p * 4096 - PB_BASE)
        heads.append([i for i in range(1023) if (ws[i], ws[i + 1]) == HEAD])
    S, peak = steps(name)
    print(f'== {name} ({lab}): {nreg} regions with a stream, {len(addrs)} objects, global pages {len(order)}, '
          f'first ISP address at dword {isp0}; run peak {peak:#x}')
    print('   block sizes (dwords, by ISP address):', ' '.join(f'{n}x{c}' for n, c in
          sorted(collections.Counter(sizes).items())), '| first 12:', sizes[:12])
    print('   head pair offsets per global page:', '; '.join(','.join(map(str, h[:4])) + (',..' if len(h) > 4 else '')
          for h in heads[:6]))
    cum = [0]
    for s_ in sizes:
        cum.append(cum[-1] + s_)
    last = cum[-1] + (sizes[-1] if sizes else 0)
    bk = {}
    for k in range(2, 40):
        g = 1024 * (k - 1)
        if g >= last:
            break
        bk[k] = max(i for i, c in enumerate(cum) if c <= g)
    based = sorted(o for o, n in base_of.items() if n)
    print('   objects with a base dword (object: regions):', ' '.join(f'{o}:{base_of[o]}' for o in based))
    print('   H-CUM b_k (block holding dword 1024 (k - 1)):', ' '.join(f'k{k}:{b}' for k, b in bk.items()))
    print('   objects opening blocks (object: regions):', ' '.join(f'{o}:{n}' for o, n in sorted(opens.items()) if n))
    a_ok = sorted(bk.values()) == [o for o in based if base_of[o] * 2 > nreg] if based else False
    print('   (a) H-CUM b_k equal to the objects whose base dword most regions carry:', 'yes' if a_ok else 'NO')
    gk = {b: k for k, b in bk.items()}
    Sm, after = replay(gk)
    hit = 0
    for k in sorted(S):
        lo, hi_ = S[k]
        m = Sm.get(k)
        ok = m is not None and lo <= m <= hi_
        hit += ok
        print(f'   S{k}: bracket [{lo:#x}, {hi_:#x}] replay {m:#x}' if m is not None else f'   S{k}: bracket [{lo:#x}, {hi_:#x}] replay none',
              '' if ok else 'OFF')
    print(f'   (b) steps placed {hit} of {len(S)}; replay need {after[-1]:#x} against the peak {peak:#x}')
    return a_ok and hit == len(S) and after[-1] == peak


def main():
    res = [read('v-cal-c4', 'fit, N 4'), read('v-cal-c8', 'SEMI, N 8')]
    print('H-CUM:', 'frozen for the session (placed both calibrations)' if all(res) else
          'NOT frozen (does not place both calibrations)')


if __name__ == '__main__':
    main()
