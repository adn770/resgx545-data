#!/usr/bin/env python3
"""Round 7 planner, Q210 (POST HOC, written after reading E881's r-m table): H-SPAN.
The first partial render leaves 2 global pages iff S_k < thr0 < A_k, A_k the page count of E874's
replay once object b_k = floor(1024 (k - 1) / 67), the block that straddles global pages k - 1 and
k, has been tiled (E874's B_k took the first object with index % 15 == 0 instead; the two agree
for k = 2..4).  Scored on every kept 1500-vertex first partial render (all closing sessions,
r6-dpm included).  Read-only; imports closing6's frozen offline library, public data only."""
import collections, sys
sys.path.insert(0, '/Users/jtorra/src/scratch/resgx545/closing6/dpm/offline')
import f5lib as F
from f4_phase import rows_and_refs
LAG = 3
def model(w, h):
    ents = F.entries(w, h)
    S, opens, after = F.replay(w, h, ents, LAG)
    A = {k: after[F.bk(k)] for k in S if F.bk(k) < F.OBJS}
    B = {}
    for k in S:
        t0 = F.bk(k) - LAG
        b = next((t for t in range(max(t0, 0), F.OBJS) if t % 15 == 0), None)
        if b is not None: B[k] = after[b]
    return S, A, B, after[-1]
def pred(thr, S, E):
    ks = [k for k in sorted(S) if S[k] <= thr]
    if not ks: return 1
    k = ks[-1]
    if thr == S[k]: return None
    if k not in E: return '?'
    return 2 if thr < E[k] else 1
rows, best = rows_and_refs()
tal = collections.defaultdict(lambda: [0, 0, 0, 0])
M = {}
seen = set()
for wh, sc, thr, left, nm in sorted(rows):
    if sc != 'tri1500': continue
    if wh not in M:
        w, h = map(int, wh.split('x')); M[wh] = model(w, h)
        S, A, B, U = M[wh]
        print('== %s U %#x S %s | A %s | B %s' % (wh, U, ' '.join('%d:%#x' % x for x in sorted(S.items())),
              ' '.join('%d:%#x' % x for x in sorted(A.items())), ' '.join('%d:%#x' % x for x in sorted(B.items()))))
    S, A, B, U = M[wh]
    pa, pb = pred(thr, S, A), pred(thr, S, B)
    if pa is None: continue
    band = max([k for k in S if S[k] <= thr], default=1)
    key = (wh, 'b5+' if band >= 5 else 'b2-4' if band >= 2 else 'b1')
    t = tal[key]; t[0] += pa == left; t[1] += pb == left; t[2] += 1
    d = (wh, thr, left) in seen; seen.add((wh, thr, left))
    if pa != left or pb != left:
        print('   %s thr0 %#x band %d left %d  SPAN %s  E874-B %s  %s' % (wh, thr, band, left, pa, pb, nm))
print('target band-class: H-SPAN held, E874 B held, of rows (jobs, repeats included)')
tot = [0, 0, 0]
for key in sorted(tal):
    t = tal[key]; print('  %-10s %-5s %3d %3d of %3d' % (key[0], key[1], t[0], t[1], t[2]))
    for i in range(3): tot[i] += t[i]
print('  all: %d %d of %d; distinct (target, thr0, left): %d' % (*tot, len(seen)))
