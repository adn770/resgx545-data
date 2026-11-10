"""POST HOC re-reading of p-b1: the frozen scorer counts the cleared depth 1.0 (0x3f800000) as covered.

Same code as score_pix.score_b1 except the coverage mask also excludes 0x3f800000.  Not frozen; a later
frozen run must confirm anything printed here.
Run: ../../../pixel-faults/.venv/bin/python -I pixel_b1_posthoc.py
"""
import math
import pathlib
import sys

import numpy as np

S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score"))
sys.path.insert(0, str(S1 / "gen"))
import score_pix as P  # noqa: E402
from s1lib import Kept, load_preds, f32v  # noqa: E402

CLEAR = 0x3F800000


def row_ranges(z, minpix=48):
    cov = (z != P.BG) & (z != 0) & (z != CLEAR)
    zf = z.view(np.float32).astype(np.float64)
    out = []
    for k in range(z.shape[0]):
        m = cov[k]
        if m.sum() < minpix:
            continue
        w = zf[k][m]
        s = np.arange(z.shape[1])[m] + 0.5
        lo, hi = P.grad_bounds(w, P.ulp32(w), s)
        out.append((k, lo, hi, int(m.sum())))
    return out


def main():
    k = Kept(S1 / "out" / "p-b1")
    preds = load_preds(None, "p-b1")
    allin = {}
    for n in k.names():
        z = P.depth_image(k.depth(n), 1024, 32)
        rr = row_ranges(z)
        lo, hi, used, bad = -np.inf, np.inf, 0, None
        for r, l, h, _ in rr:
            if l >= h or max(lo, l) >= min(hi, h):
                bad = r
                break
            lo, hi, used = max(lo, l), min(hi, h), used + 1
        A = float(next(x for x, m, s in preds[n]["A_exact"]))
        u = 2.0 ** (math.floor(math.log2(A)) - 23)
        words = {m: int(x, 16) for x, m, s in preds[n]["rule_word"]}
        inside = sorted(m for m, w in words.items() if used and lo <= f32v(w) < hi)
        allin[n] = set(inside)
        print(f"{n:9s} rows {used}/{len(rr)} bad {bad} cov/row {rr[0][3] if rr else 0}..{rr[-1][3] if rr else 0} "
              f"range [{lo:.10e},{hi:.10e}] width {(hi - lo) / u:.2f} ulps  A={A:.10e} f32(A)={np.float32(A):.10e}")
        print(f"          inside: {' '.join(inside)}")
        dist = sorted({f'{w:#010x}' for w in words.values()})
        print(f"          distinct rule words: {dist}")
    ramps = [f"g-r{i}" for i in (2, 4, 6, 7, 9, 11, 12, 13)]
    rules = set.union(*(set(m for x, m, s in preds[r]["rule_word"]) for r in ramps))
    print("rules inside on all 8 ramps:", sorted(m for m in rules if all(m in allin[r] for r in ramps)))
    print("g-r2 == g-r2-rep depth:", k.depth("g-r2") == k.depth("g-r2-rep"))


if __name__ == "__main__":
    main()
