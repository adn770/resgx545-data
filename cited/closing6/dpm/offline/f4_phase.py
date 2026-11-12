#!/usr/bin/env python3
"""F4 (round 6 dpm offline stage, H-PHASE [infer]): the first partial render leaves 2 global
pages iff the refused page request falls after a global step and before the end of the burst
that follows it, else 1.  As a rule on thr0 (the first threshold, the last page the first run
may take): left = 2 iff S_k < thr0 < E_k for the band's step S_k (F1) and burst end E_k, left =
1 for E_k <= thr0 < S_k+1 and below S2; thr0 = S_k (a grow, E861's H-PEND sampling) is not scored.

The burst-end rule, from timelines only: in the target's reference job (the kept job whose first
TA run goes highest), gap(T) is the time from the first sample with page count >= T to the first
with >= T + 1; E_k is the smallest T >= S_k + 2 with gap(T) > X.  X is fitted on 2048x2048 bands
2 to 4 (S2 to S5) only, the smallest of the candidates with the fewest misses there.  Held out
(SEMI: the planner's left_table.out and gap_rule.out printed these rows): every other target and
band, and 4096x4096 with 1350 vertices.  F5's model burst ends B_k (f5_stepmodel.out, frozen
before this script) are scored on the same rows as a second rule.  Read-only, standard library."""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r6lib import jobs, scene_of, load, stretches, hi
from f1_brackets import brackets

XS = [25, 50, 75, 100, 150, 200, 300]


def rows_and_refs():
    rows, best = [], {}
    for ds, stg, name, d, m in jobs():
        args = m.get('args', ''); wh, sc = scene_of(args)
        if sc not in ('tri1500', 'tri1350'):
            continue
        cols, tl = load(f'{d}/{name}.txt.gz')
        if not tl or any(r not in tl[0][1] for r in (0x724, 0x72c, 0x658, 0x624)):
            continue
        st = stretches(tl)
        end = st[0][0] if st else len(tl)
        seq, mx = [], 0
        for i in range(end):
            p = hi(tl[i][1], 0x724)
            if p < mx: break
            if p > mx: seq.append((tl[i][0], p)); mx = p
        if (wh, sc) not in best or mx > best[(wh, sc)][0]:
            best[(wh, sc)] = (mx, seq, f'{ds[8:]}/{stg}/{name}')
        if not st:
            continue
        a, e = st[0]
        thr = tl[a][1][0x624] & 0xffff
        rows.append((wh, sc, thr, hi(tl[e][1], 0x72c), f'{ds[8:]}/{stg}/{name}'))
    return rows, best


def gap(seq, T):
    a = next((t for t, p in seq if p >= T), None); b = next((t for t, p in seq if p >= T + 1), None)
    return None if a is None or b is None else (b - a) / 1000.0


def ends(seq, S, X):
    out = {}
    for k, s in S.items():
        nxt = S.get(k + 1, 1 << 30)
        out[k] = next((T for T in range(s + 2, min(nxt, s + 0x200)) if (g := gap(seq, T)) is not None and g > X), None)
    return out


def predict(thr, S, E):
    ks = sorted(S)
    if not ks or thr < S[ks[0]]:
        return 1
    k = max(k for k in ks if S[k] <= thr)
    if thr == S[k]:
        return None
    if E.get(k) is None:
        return '?'
    return 2 if thr < E[k] else 1


def model_B():
    B, cur = {}, None
    for l in open(os.path.join(HERE, 'f5_stepmodel.out')):
        m = re.match(r'(\d+x\d+) (fit|held)', l)
        if m: cur = m.group(1)
        if 'B_k' in l:
            B[cur] = {int(k): int(v, 16) for k, v in re.findall(r'B(\d+) (0x[0-9a-f]+)', l)}
    return B


def main():
    iv = brackets()
    S = collections.defaultdict(dict)
    for (wh, sc, k), L in iv.items():
        lo = max(a for a, b, _ in L); top = min(b for a, b, _ in L)
        if lo == top: S[(wh, sc)][k] = lo
    rows, best = rows_and_refs()
    fitrows = [r for r in rows if r[0] == '2048x2048' and r[1] == 'tri1500' and 0x51 < r[2] < 0x132]
    ref = best[('2048x2048', 'tri1500')]
    score = []
    for X in XS:
        E = ends(ref[1], S[('2048x2048', 'tri1500')], X)
        miss = sum(1 for r in fitrows if (p := predict(r[2], S[(r[0], r[1])], E)) not in (None,) and p != r[3])
        score.append((miss, X))
    miss, X = min(score)
    print('fit: 2048x2048 bands 2-4, %d rows; misses by X %s; X = %d us' % (len(fitrows), score, X))
    B = model_B()
    tally = collections.defaultdict(lambda: [0, 0]); tb = collections.defaultdict(lambda: [0, 0])
    for key in sorted(best):
        mx, seq, nm = best[key]
        E = ends(seq, S[key], X)
        print('== %s %s reference %s (first run to %#x): S %s; E (timeline rule) %s; B (F5) %s' % (
            key[0], key[1], nm, mx, ' '.join('%d:%#x' % kv for kv in sorted(S[key].items())),
            ' '.join('%d:%s' % (k, hex(v) if v else '-') for k, v in sorted(E.items())),
            ' '.join('%d:%#x' % kv for kv in sorted(B.get(key[0], {}).items())) if key[1] == 'tri1500' else '-'))
        seen = set()
        for r in sorted(rows):
            if (r[0], r[1]) != key or (r[2], r[3]) in seen:
                continue
            seen.add((r[2], r[3]))
            p = predict(r[2], S[key], E)
            pb = predict(r[2], S[key], B.get(key[0], {})) if key[1] == 'tri1500' else '-'
            side = 'fit' if r in fitrows else 'held'
            if p in (1, 2):
                tally[side][0] += p == r[3]; tally[side][1] += 1
            if pb in (1, 2):
                tb[side][0] += pb == r[3]; tb[side][1] += 1
            print('   %-4s thr0 %#x left %d  timeline-rule %s  F5-rule %s  %s' % (side, r[2], r[3],
                  p if p is not None else 'grow', pb if pb is not None else 'grow', r[4]))
    for side in ('fit', 'held'):
        print('H-PHASE %s, timeline burst ends: %d of %d distinct (thr0, left) rows' % (side, *tally[side]))
        print('H-PHASE %s, F5 model burst ends: %d of %d distinct (thr0, left) rows' % (side, *tb[side]))


if __name__ == '__main__':
    main()
