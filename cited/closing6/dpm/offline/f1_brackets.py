#!/usr/bin/env python3
"""F1 (round 6 dpm offline stage, H-IV, a reading rule): a step of the global page count (the
high half of 0x072c) between two samples of the first TA run whose page counts (high half of
0x0724) are a and b says only that S_k, the count before global page k appears, lies in
[a, max(a, b - 1)].  For every kept job of render/closing-*/out the brackets of each step k >= 2,
intersected per (target, scene, k): one value, a range, or EMPTY (the step itself moves, which
refutes H-IV).  Then the frozen point values of E852/E861 are tested by the rule: a frozen S
matches a job when it lies in that job's bracket.  Read-only, public data; standard library
only.  A timeline that cannot be read is an error, never skipped silently."""
import collections, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r6lib import load, hi, stretches, jobs, scene_of

# the frozen point values the round 5 session gated on (E861: a2b's calibrations, frozen 0x97
# for S2 at 4096x2048 from E852's table) and E852's table itself, by (target, scene, k)
FROZEN = {('4096x2048', 'tri1500', 2): 0x97, ('4096x2048', 'tri1500', 3): 0x126,
          ('4096x2048', 'tri1500', 4): 0x1b9,
          ('2048x4096', 'tri1500', 2): 0x9a, ('2048x4096', 'tri1500', 3): 0x12c,
          ('2048x4096', 'tri1500', 4): 0x1be, ('2048x4096', 'tri1500', 5): 0x255,
          ('3072x3072', 'tri1500', 2): 0xa9, ('3072x3072', 'tri1500', 3): 0x14d,
          ('3072x3072', 'tri1500', 4): 0x1ef, ('3072x3072', 'tri1500', 5): 0x293,
          ('2048x2048', 'tri1500', 2): 0x51, ('2048x2048', 'tri1500', 3): 0x9d,
          ('2048x2048', 'tri1500', 4): 0xe8, ('2048x2048', 'tri1500', 5): 0x132,
          ('4096x4096', 'tri1500', 2): 0x125, ('4096x4096', 'tri1500', 3): 0x240,
          ('4096x4096', 'tri1500', 4): 0x35b}
NEED = (0x724, 0x72c, 0x658)


def brackets():
    iv = collections.defaultdict(list)
    for ds, stg, name, d, m in jobs():
        cols, rows = load(f'{d}/{name}.txt.gz')
        if not rows or any(r not in rows[0][1] for r in NEED):
            continue                      # a job that did not sample the three registers
        st = stretches(rows)
        end = st[0][0] if st else len(rows)
        wh, sc = scene_of(m.get('args', ''))
        pg = pp = None
        for i in range(1, end):
            g = hi(rows[i][1], 0x72c); p = hi(rows[i][1], 0x724)
            if pg is not None and g == pg + 1 and g >= 2 and p >= pp:
                iv[(wh, sc, g)].append((pp, max(pp, p - 1), f'{ds[8:]}/{stg}/{name}'))
            pg, pp = g, p
    return iv


def main():
    iv = brackets()
    print('== H-IV table: every step k >= 2 of every kept first TA run, by (target, scene, k)')
    empty = 0
    for key in sorted(iv):
        L = iv[key]; lo = max(a for a, b, _ in L); top = min(b for a, b, _ in L)
        wid = collections.Counter((a, b) for a, b, _ in L)
        if lo == top: tag = 'ONE VALUE %#x' % lo
        elif lo < top: tag = 'range %#x..%#x' % (lo, top)
        else: tag = 'EMPTY (lo %#x > hi %#x)' % (lo, top); empty += 1
        print('%-10s %-14s S%d jobs %3d  %-22s brackets %s' % (key[0], key[1], key[2], len(L), tag,
              ' '.join('[%x,%x]x%d' % (a, b, n) for (a, b), n in sorted(wid.items()))))
    print('H-IV: %d keys, %d with an empty intersection' % (len(iv), empty))
    print('== frozen point values (E852 table, E861 gate) under H-IV: jobs whose bracket holds it')
    for key, s in sorted(FROZEN.items()):
        L = iv.get(key, [])
        held = [n for a, b, n in L if a <= s <= b]
        point = [n for a, b, n in L if max(a, b) == s]   # round 5's point rule max(a, b - 1)
        miss = [(n, '[%x,%x]' % (a, b)) for a, b, n in L if not a <= s <= b]
        print('%-10s S%d frozen %#x: in bracket %d of %d; point rule max(a, b - 1) equal in %d of %d%s'
              % (key[0], key[2], s, len(held), len(L), len(point), len(L),
                 ('; outside: %s' % miss) if miss else ''))
    print('== A2b (4096x2048 S2, the job a2b-cal-4x2 and every other kept job of the target)')
    for a, b, n in sorted(iv[('4096x2048', 'tri1500', 2)], key=lambda x: x[2]):
        print('   [%#x, %#x] %s %s' % (a, b, n, 'holds 0x97' if a <= 0x97 <= b else 'EXCLUDES 0x97'))


if __name__ == '__main__':
    main()
