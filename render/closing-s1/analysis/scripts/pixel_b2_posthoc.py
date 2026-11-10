"""POST HOC re-reading of p-b2: b2model.deviation counts the cleared depth 1.0 (0x3f800000) as covered.  Here the
clear value is excluded (and pixels whose centre lies outside the declared triangle are reported apart).  Jaccard
of d-shift against the frozen HT / HV sets.  Not frozen."""
import pathlib, sys
from fractions import Fraction
import numpy as np
S1 = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(S1 / "score")); sys.path.insert(0, str(S1 / "gen"))
import b2model as M
import score_pix as P
from s1lib import Kept
k = Kept(S1 / "out" / "p-b2")
sets = {nm: np.unpackbits(np.frombuffer((S1 / "predictions" / f"p-b2-set-{nm}.bits").read_bytes(), dtype=np.uint8))
        [:128 * 256].reshape(128, 256).astype(bool) for nm in ("ctl", "ht_shift", "hv_shift")}
devs = {}
for n in k.names():
    w, h, V, Z = P.parse_depth_job(n, k.cases)
    raw = k.depth(n)
    z = np.frombuffer(raw, dtype="<u4")[M.idx_map(w, h)]
    d, cov = M.deviation(raw, w, h, V, Z)
    clear = z == 0x3F800000
    cov2 = cov & ~clear
    dev = (d != 0) & cov2
    devs[n] = dev
    vals, cnt = np.unique(d[cov2], return_counts=True)
    per = [int(dev[16 * t:16 * t + 16].sum()) for t in range(h // 16)]
    ys = [y for y in range(h) if dev[y].any()]
    line = "-"
    if len(ys) > 2:
        c1, c0 = np.polyfit(ys, [int(np.nonzero(dev[y])[0].min()) for y in ys], 1)
        line = f"xmin = {c0:.2f} {c1:+.3f} y"
    # per macrotile column (x >= 128)
    print(f"{n}: clear px {int(clear.sum())}, covered {int(cov2.sum())}, dev {dict((int(a), int(b)) for a, b in zip(vals, cnt) if a)}")
    print(f"   per tile row {per}; x>=128 {int(dev[:, 128:].sum())}; line {line}")
    if n in ("d-tall", "d-ygrad"):
        # does the region continue below row 128?  rows where x+2y>=319 (control line) inside the triangle
        yy, xx = np.mgrid[0:h, 0:w]
        line_set = (xx + 2 * yy >= 319) & cov2
        print(f"   vs control line x+2y>=319 within covered: Jaccard {(dev & line_set).sum() / max(1, (dev | line_set).sum()):.3f}")
        print(f"   first 128 rows equal to d-ctl's map: {np.array_equal(dev[:128], devs.get('d-ctl', dev[:128]))}")
o = devs["d-shift"]
for lab in ("ht_shift", "hv_shift"):
    j = (o & sets[lab]).sum() / max(1, (o | sets[lab]).sum())
    print(f"d-shift vs {lab}: Jaccard {j:.3f} (observed {int(o.sum())}, set {int(sets[lab].sum())}, both {int((o & sets[lab]).sum())})")
print("d-ctl equals frozen ctl set:", np.array_equal(devs["d-ctl"], sets["ctl"]))
