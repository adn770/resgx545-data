#!/usr/bin/env python3
"""G3 (round 7 dpm offline stage, H-SPAN, Q210).  The first partial render of the tool's
1500-vertex scene leaves 2 global pages iff S_k < thr0 < A_k, else 1 (thr0 = S_k, a grow cell,
is not scored), where S_k are the steps of E874's frozen replay (f5lib.replay, lag 3, from the
published round 6 library, unchanged) and A_k is the replay's page count once object
b_k = floor(1024 (k - 1) / 67) has been tiled: the object block that straddles global pages
k - 1 and k.  Rival (tally): E874's B_k, the page count after the first object with index
divisible by 15 from b_k - 3 on (H-PHASE as landed).

Rows (the planner's q210_phase2.py rule: f4_phase.rows_and_refs, the 1500-vertex scene of every
kept closing session with 0x0724, 0x072c, 0x0658 and 0x0624 sampled, thr0 from 0x0624 at the
first partial render and the pages left from 0x072c at its end), with two exclusions fixed here
before scoring: rows of jobs run with --vtx-coords (another scene: R6-dpm's r-v), and rows at the
threshold clamp (thr0 >= 0x400, E753).  Labels: the 15 rows of R6-dpm a2/r-m are the fit (H-SPAN
was written after E881's table of them); every other row is SEMI (the planner's run printed the
tally).  Verdict: H-SPAN HELD iff every scored row equals its prediction, else REFUTED.
Read-only, public data; standard library only."""
import collections, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import olib as O                       # noqa: F401  (paths)
import f5lib as F
from f4_phase import rows_and_refs
from r6lib import jobs
LAG = 3


def model(w, h):
    ents = F.entries(w, h)
    S, opens, after = F.replay(w, h, ents, LAG)
    A = {k: after[F.bk(k)] for k in S if F.bk(k) < F.OBJS}
    B = {}
    for k in S:
        b = next((t for t in range(max(F.bk(k) - LAG, 0), F.OBJS) if t % 15 == 0), None)
        if b is not None:
            B[k] = after[b]
    return S, A, B, after[-1]


def pred(thr, S, E):
    ks = [k for k in sorted(S) if S[k] <= thr]
    if not ks:
        return 1
    k = ks[-1]
    if thr == S[k]:
        return None
    if k not in E:
        return '?'
    return 2 if thr < E[k] else 1


def main():
    args = {f'{ds[8:]}/{stg}/{name}': m.get('args', '') for ds, stg, name, d, m in jobs()}
    rows, best = rows_and_refs()
    tal = collections.defaultdict(lambda: [0, 0, 0])
    M, off, excl = {}, [], []
    for wh, sc, thr, left, nm in sorted(rows):
        if sc != 'tri1500':
            continue
        if '--vtx-coords' in args.get(nm, '') or thr >= 0x400:
            excl.append('   not scored: %s thr0 %#x left %d %s' % (wh, thr, left, nm))
            continue
        if wh not in M:
            w, h = map(int, wh.split('x'))
            M[wh] = model(w, h)
            S, A, B, U = M[wh]
            print('== %s U %#x S %s | A %s | B %s' % (wh, U, ' '.join('%d:%#x' % x for x in sorted(S.items())),
                  ' '.join('%d:%#x' % x for x in sorted(A.items())), ' '.join('%d:%#x' % x for x in sorted(B.items()))))
        S, A, B, U = M[wh]
        pa, pb = pred(thr, S, A), pred(thr, S, B)
        if pa is None:
            continue
        band = max([k for k in S if S[k] <= thr], default=1)
        lab = 'fit' if '/a2/r-m/' in nm and nm.startswith('r6-dpm/') else 'SEMI'
        key = (lab, wh, 'b5+' if band >= 5 else 'b2-4' if band >= 2 else 'b1')
        t = tal[key]; t[0] += pa == left; t[1] += pb == left; t[2] += 1
        if pa != left or pb != left:
            print('   %-4s %s thr0 %#x band %d left %d  SPAN %s  E874-B %s  %s' % (lab, wh, thr, band, left, pa, pb, nm))
        if pa != left:
            off.append(nm)
    print('\n'.join(excl))
    print('label target band-class: H-SPAN held, E874 B held, of rows')
    tot = [0, 0, 0]
    for key in sorted(tal):
        t = tal[key]
        print('  %-4s %-10s %-5s %3d %3d of %3d' % (*key, *t))
        for i in range(3):
            tot[i] += t[i]
    print('  all: H-SPAN %d, E874 B %d, of %d rows; not scored %d' % (*tot, len(excl)))
    print('VERDICT H-SPAN:', 'HELD' if not off and tot[2] else 'REFUTED', '(%d rows off; fit 15 r-m rows, the rest SEMI)' % len(off))


if __name__ == '__main__':
    main()
