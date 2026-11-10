"""POST HOC: tile-segment gradient ranges for p-b1.  For every row and every 32-pixel tile segment with >= 8 covered
pixels: grad_bounds (some T0 with w <= T0 + g s < w + ulp), intersected over all segments of the job.  Reports the
joint range in ulps of A and the rule words inside.  Not frozen."""
import math, pathlib, sys
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score")); sys.path.insert(0, str(S1 / "gen"))
import score_pix as P
from s1lib import Kept, load_preds, f32v
k = Kept(S1 / "out" / "p-b1")
preds = load_preds(None, "p-b1")
allin = {}
for n in k.names():
    z = P.depth_image(k.depth(n), 1024, 32)
    cov = (z != P.BG) & (z != 0) & (z != 0x3F800000)
    zf = z.view(np.float32).astype(np.float64)
    lo, hi, seg, empty_at = -np.inf, np.inf, 0, None
    for r in range(32):
        for t in range(32):
            m = cov[r, 32 * t:32 * t + 32]
            if m.sum() < 8:
                continue
            w = zf[r, 32 * t:32 * t + 32][m]
            s = np.arange(32)[m] + 0.5
            l, h = P.grad_bounds(w, P.ulp32(w), s)
            seg += 1
            if max(lo, l) >= min(hi, h) and empty_at is None:
                empty_at = (r, t, l, h)
            lo, hi = max(lo, l), min(hi, h)
    A = float(next(x for x, m, s in preds[n]["A_exact"]))
    u = 2.0 ** (math.floor(math.log2(A)) - 23)
    words = {m: int(x, 16) for x, m, s in preds[n]["rule_word"]}
    inside = sorted(m for m, w in words.items() if lo <= f32v(w) < hi)
    allin[n] = set(inside)
    print(f"{n:9s} segs {seg} joint [{lo:.12e},{hi:.12e}] width {(hi-lo)/u:.3f} ulps(A) empty_at {empty_at}")
    print(f"          A in ulps from lo: {(A-lo)/u:.3f}; inside: {' '.join(inside) or '-'}")
ramps = [f"g-r{i}" for i in (2, 4, 6, 7, 9, 11, 12, 13)]
rules = set.union(*(set(m for x, m, s in preds[r]["rule_word"]) for r in ramps))
print("rules inside on all 8 ramps:", sorted(m for m in rules if all(m in allin[r] for r in ramps)))
print("per rule, ramps where inside:")
for m in sorted(rules):
    print(f"  {m:7s} {sum(m in allin[r] for r in ramps)}/8 ctl:{m in allin['g-ctl']} dyadic:{m in allin['g-dyadic']}")
