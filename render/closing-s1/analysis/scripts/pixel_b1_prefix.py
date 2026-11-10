"""POST HOC: largest x-prefix of each row over which one line fits (grad_bounds, 1-ulp truncation band), clear depth
excluded; and the joint range over rows using only x < XMAX.  Not frozen."""
import math, pathlib, sys
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score")); sys.path.insert(0, str(S1 / "gen"))
import score_pix as P
from s1lib import Kept, load_preds, f32v
k = Kept(S1 / "out" / "p-b1"); preds = load_preds(None, "p-b1")
XMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 256
for n in k.names():
    z = P.depth_image(k.depth(n), 1024, 32)
    cov = (z != P.BG) & (z != 0) & (z != 0x3F800000)
    zf = z.view(np.float32).astype(np.float64)
    pref = []
    for r in (0, 16, 31):
        xs = np.nonzero(cov[r])[0]
        best = 0
        for e in range(16, len(xs) + 1, 16):
            w = zf[r, xs[:e]]; l, h = P.grad_bounds(w, P.ulp32(w), xs[:e] + 0.5)
            if l < h: best = e
            else: break
        pref.append(best)
    lo, hi, used = -np.inf, np.inf, 0
    for r in range(32):
        xs = np.nonzero(cov[r])[0]; xs = xs[xs < XMAX]
        if len(xs) < 48: continue
        w = zf[r, xs]; l, h = P.grad_bounds(w, P.ulp32(w), xs + 0.5)
        if max(lo, l) >= min(hi, h): break
        lo, hi, used = max(lo, l), min(hi, h), used + 1
    A = float(next(x for x, m, s in preds[n]["A_exact"])); u = 2.0 ** (math.floor(math.log2(A)) - 23)
    words = {m: int(x, 16) for x, m, s in preds[n]["rule_word"]}
    ins = sorted(m for m, w in words.items() if used and lo <= f32v(w) < hi)
    print(f"{n:9s} fit-prefix px rows0/16/31 {pref}; x<{XMAX}: rows {used}/32 width {(hi-lo)/u if used else float('nan'):.2f} ulps inside {' '.join(ins) or '-'}")
