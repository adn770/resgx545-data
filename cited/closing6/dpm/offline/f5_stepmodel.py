#!/usr/bin/env python3
"""F5 (round 6 dpm offline stage, H-STEPMODEL [infer]): the steps S_k of the global page count
and the page need U of the tool's triangle with 1500 vertices, from f5lib's block-level replay
(constants read from dumps by F2 and F3, none fitted to a step), against F1's brackets.

One structural choice is fitted, on 2048x2048 only: the lag (objects the TA tiles after it has
written an object to the global list), the smallest of 0..4 that puts every 2048x2048 step in
its F1 bracket.  Held out (SEMI: E852 and E861 printed these steps before this script was
written): S_k and U at 4096x2048, 2048x4096, 3072x3072 and 4096x4096 (1350 vertices are not
modelled).  Also printed, as a reading for F4: per band the page count right after the first
object tiled after the step whose index is a multiple of 15 (the burst object), named B_k.
Refuted by: a step outside its bracket at a held-out target.  Read-only, standard library."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import f5lib as F
from f1_brackets import brackets

FIT = (2048, 2048)
HELD = [(4096, 2048), (2048, 4096), (3072, 3072), (4096, 4096)]
U_KEPT = {(2048, 2048): 0x213}      # E785; the others' U are not in F1's table


def bands(S, after, lag):
    """B_k: pages after tiling the first object >= b_k - lag + 1 with index % 15 == 0."""
    out = {}
    for k in S:
        t0 = F.bk(k) - lag
        b = next((t for t in range(max(t0, 0), F.OBJS) if t % 15 == 0 and t >= t0), None)
        if b is not None:
            out[k] = after[b]
    return out


def score(wh, S, iv):
    res = []
    for k, s in sorted(S.items()):
        L = iv.get((wh, 'tri1500', k))
        if not L:
            res.append((k, s, None)); continue
        lo = max(a for a, b, _ in L); top = min(b for a, b, _ in L)
        res.append((k, s, lo <= s <= top, lo, top))
    return res


def main():
    iv = brackets()
    w, h = FIT
    ents = F.entries(w, h)
    lag = None
    for cand in range(5):
        S, opens, after = F.replay(w, h, ents, cand)
        if all(r[2] for r in score(f'{w}x{h}', S, iv) if r[2] is not None):
            lag = cand; break
    print('fit 2048x2048: lag', lag)
    for (w, h) in [FIT] + HELD:
        wh = f'{w}x{h}'
        ents = F.entries(w, h) if (w, h) != FIT else ents
        S, opens, after = F.replay(w, h, ents, lag)
        sc = score(wh, S, iv)
        dec = [r for r in sc if r[2] is not None]
        side = 'fit' if (w, h) == FIT else 'held'
        print(f'{wh} {side}: U {after[-1]:#x}' + (f' (kept {U_KEPT[(w, h)]:#x})' if (w, h) in U_KEPT else '')
              + f'; steps in bracket {sum(r[2] for r in dec)} of {len(dec)}')
        for r in sc:
            if r[2] is None:
                print(f'   S{r[0]} {r[1]:#x} (no kept step)')
            else:
                print(f'   S{r[0]} {r[1]:#x} bracket [{r[3]:#x}, {r[4]:#x}] {"in" if r[2] else "OUT"}')
        B = bands(S, after, lag)
        print('   B_k (pages after the burst object):', ' '.join(f'B{k} {v:#x}' for k, v in sorted(B.items())))


if __name__ == '__main__':
    main()
