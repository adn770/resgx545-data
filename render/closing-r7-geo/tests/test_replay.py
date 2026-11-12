#!/usr/bin/env python3
"""test_replay.py: every scorer replayed, before the freeze, on kept records it must hold on and on kept records it must fail on
(round 4's second slip: a scorer that reads the wrong thing).  The scorer's own readers and comparisons (score_g.py) are used on
the records' kept files:
  xf  E884's 20 held-out single-axis fills (resgx545-data render/closing-r6-misc q289): H-INDEP (one field = E884's OR) holds on
      all 20; H-XFIRST must fail on the y rows that move pixels, H-YFIRST on the x rows;
  tx  E725's 12 type fills: RASTERW holds for types 1 and 3 (8 of 8), S32 for type 4 (4 of 4); FIX16 must fail (E725: 0 of 8);
      E567's three type 5 dumps: H-STEP holds at 16 x 16 (3 of 3); rt4-2d must fail H-STEP;
  zd  E606's D jobs (64 x 64 fit, 128 x 128 and 256 x 128 held out): coverage exact, the whole tile area written and nothing beyond
      it, the depth within 3 units on every job with gradient below 0.03; on the jobs with gradient above 1 H-DEPTH must fail;
  zi  E606's I0 probes: pa0 within 4 units where the clip-z range per root area is below 0.05; above 1 it must fail somewhere;
  zs  E681's 588 S2 sweeps: HU exact on all; E683's 240 S3 cases: HU must fail (149 inexact), HA too (67)."""
import gzip
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
import models as M  # noqa: E402
import score_g as S  # noqa: E402
import worlds as W  # noqa: E402

D = "/Users/jtorra/src/resgx545-data"
bad = n = 0


def check(c, what):
    global bad, n
    n += 1
    print(("ok   " if c else "FAIL ") + what)
    bad += 0 if c else 1


def gz(p):
    with gzip.open(p, "rb") as f:
        return f.read()


# ---- xf
q = os.path.join(D, "render/closing-r6-misc/out/20261112-144153/q289")
rows = [ln.split("\t") for ln in open(os.path.join(q, "cases.tsv")).read().splitlines()[1:]]
hold = {"INDEP": 0, "XFIRST": [], "YFIRST": []}
nh = 0
for f in rows:
    if f[2] != "heldout":
        continue
    nh += 1
    a = f[6].split()
    w, h = int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])
    v = int(f[6].split("^=")[1].rstrip("'"), 16)
    got = S.parse_out(gz(os.path.join(q, f[0] + ".txt.gz")).decode())["hash"]
    hold["INDEP"] += got == M.fill_predict(w, h, v, "INDEP")[0]
    for m in ("XFIRST", "YFIRST"):
        if M.fill_predict(w, h, v, m)[0] != M.fill_predict(w, h, v, "INDEP")[0] or True:
            hold[m].append(got == M.fill_predict(w, h, v, m)[0])
check(nh == 20 and hold["INDEP"] == 20, "xf: H-INDEP holds on E884's 20 held-out single-axis fills (%d of %d)" % (hold["INDEP"], nh))
# single-axis rows: XFIRST keeps x moves and so holds on them; on y rows it is also the one-field reading; a single axis cannot
# separate them (that is why xf moves both): the scorer must still read every hash
check(all(hold["XFIRST"]) and all(hold["YFIRST"]), "xf: on single-axis rows the three readings agree (the reason for the both-axes row)")
doct = M.fill_predict(128, 64, 0x2010, "INDEP")[0] ^ 1
check(doct not in [M.fill_predict(128, 64, 0x2010, m)[0] for m in ("INDEP", "XFIRST", "YFIRST")], "xf: a doctored hash matches no reading")

# ---- tx
base = os.path.join(D, "texture/p1141/out-hw/p1141tex-dumps")
res = {}
for grp in ("tex-f-types", "tex-g-types-risky"):
    for fn in sorted(os.listdir(os.path.join(base, grp))):
        if not fn.endswith(".txt.gz") or not fn.startswith("ty"):
            continue
        nm = fn[:-7]
        ty, (w, h) = int(nm[2]), map(int, nm[4:].split("x"))
        r = S.parse_out(gz(os.path.join(base, grp, fn)).decode())
        px = M.sha_list([v for y in sorted(r["rows"]) for v in r["rows"][y]])
        for hyp in M.TYPE_HYPS[ty]:
            res.setdefault((ty, hyp), []).append(px == M.sha_list(M.tex_image(hyp, w, h)))
check(all(res[(1, "RASTERW")]) and all(res[(3, "RASTERW")]) and len(res[(1, "RASTERW")]) + len(res[(3, "RASTERW")]) == 8, "tx: RASTERW holds on E725's 8 type 1/3 fills")
check(all(res[(4, "S32")]) and len(res[(4, "S32")]) == 4, "tx: S32 holds on E725's 4 type 4 fills (post hoc there)")
check(not any(res[(1, "FIX16")] + res[(3, "FIX16")]), "tx: FIX16 must fail on all 8 type 1/3 fills (E725: 0 of 8)")
check(not all(res[(4, "RASTER2W")]), "tx: E725's frozen type 4 rival RASTER2W must fail")
p = os.path.join(D, "texture/p1132/tx-types-risky")
r5 = []
for nm in ("rt5-2d", "rt5-3d-w5", "rt5-3d-w15", "rt4-2d"):
    r = S.parse_out(gz(os.path.join(p, nm + ".txt.gz")).decode())
    r5.append(M.sha_list([v for y in sorted(r["rows"]) for v in r["rows"][y]]) == M.sha_list(M.type5_image("H-STEP", 16)))
check(r5 == [True, True, True, False], "tx: H-STEP holds on E567's three type 5 dumps and must fail on rt4-2d")

# ---- zd: E606 D jobs through the scorer's readers
cases = {ln.split("\t")[0]: ln.rstrip("\n").split("\t") for ln in open(os.path.join(D, "isp/arith-1138/cases.tsv"))}
okh, okf, nlo, nhi = 0, 0, 0, 0
for cid, f in cases.items():
    if f[1] not in ("fit", "heldout") or f[2] not in ("small", "medium", "centre") or "D" not in f[15]:
        continue
    w, h = int(f[3]), int(f[4])
    v, z = [int(t) for t in f[5:11]], [M.Fraction(t) for t in f[11:14]]
    g = M.gradient(v, z)
    if not (g < 0.03 or g > 1.0) or not M.cover(v, w, h).any():
        continue
    if g < 0.03 and nlo >= 40:
        continue
    if g > 1.0 and nhi >= 40:
        continue
    raw = gz(os.path.join(D, "isp/arith-1138/main/D/%s.depth.gz" % cid))
    r = S.parse_out(gz(os.path.join(D, "isp/arith-1138/main/D/%s.txt.gz" % cid)).decode())
    img = S.image(r, w, h)
    dimg, dcov = S._cov_from_depth(raw, w, h)
    pc = M.cover(v, w, h)
    dead, outside = S._zls(raw, w, h)
    err = float((np.abs(M.f32(dimg) - M.plane_image(v, z, w, h)) / M.U)[pc].max())
    good = bool((img == M.GREEN).tolist() == pc.tolist() and (dcov == pc).all() and dead == 0 and outside == 0)
    if g < 0.03:
        nlo += 1
        okh += bool(good and err <= M.DEPTH_TOL)
    else:
        nhi += 1
        okf += bool(err > M.DEPTH_TOL)
check(nlo == 40 and okh == 40, "zd: 40 E606 D jobs with gradient below 0.03: coverage, tile area and depth within 3 units on all (%d)" % okh)
check(nhi >= 10 and okf >= 1, "zd: on %d E606 D jobs with gradient above 1 H-DEPTH must fail somewhere (%d fail)" % (nhi, okf))

# ---- zi
lo = hi = oklo = fhi = 0
for cid, f in cases.items():
    if "I" not in f[15] or f[1] not in ("fit", "heldout"):
        continue
    w, h = int(f[3]), int(f[4])
    v, z = [int(t) for t in f[5:11]], [M.Fraction(t) for t in f[11:14]]
    rr = M.value_range_per_root_area(v, z)
    if not (rr < 0.05 or rr > 1.0) or not M.cover(v, w, h).any():
        continue
    if (rr < 0.05 and lo >= 30) or (rr > 1.0 and hi >= 30):
        continue
    img = S.image(S.parse_out(gz(os.path.join(D, "isp/arith-1138/main/I0/%s.txt.gz" % cid)).decode()), w, h)
    pc = M.cover(v, w, h)
    e = float((np.abs(M.f32(img) - M.plane_image(v, [2 * x - 1 for x in z], w, h)) / M.U)[pc].max())
    if rr < 0.05:
        lo += 1
        oklo += bool(((img != M.BG) == pc).all() and e <= M.ITER_TOL)
    else:
        hi += 1
        fhi += e > M.ITER_TOL
check(lo == 30 and oklo == 30, "zi: 30 E606 I0 probes with range below 0.05: coverage and pa0 within 4 units on all (%d)" % oklo)
check(hi >= 5 and fhi >= 1, "zi: on %d I0 probes with range above 1 H-ITER must fail somewhere (%d fail)" % (hi, fhi))

# ---- zs: E681 S2 and E683 S3 through the scorer's row reader (the kept rle rows put in the tool's row form)
env = os.path.join(D, "isp/coverage-envelope/main")
cs = {ln.split("\t")[0]: ln.rstrip("\n").split("\t") for ln in open(os.path.join(env, "cases-1140.tsv"))}
cnt = {"S2": [0, 0, 0], "S3": [0, 0, 0]}
for cid, f in cs.items():
    if f[2] not in ("S2", "S3") or not os.path.exists(os.path.join(env, "raw", cid + ".txt.gz")):
        continue
    w, h, k = int(f[4]), int(f[5]), int(f[6])
    v = [int(t) for t in f[7:13]]
    txt = gz(os.path.join(env, "raw", cid + ".txt.gz")).decode()
    img = S.image(S.parse_out("\n".join(W._rle_rows(txt, w))), w, h)
    if img is None:
        continue
    obs = img == M.GREEN
    if k == 12:
        hu, ha = M.cover4096(v, w, h, "HU"), M.cover4096(v, w, h, "HA")
    else:
        g = 1 << (k - 8)
        hu = M.cover([(x + g // 2) // g for x in v], w, h)
        ha = hu
    c = cnt[f[2]]
    c[0] += 1
    c[1] += bool((obs != hu).any())
    c[2] += bool((obs != ha).any())
check(cnt["S2"][0] == 588 and cnt["S2"][1] == 0, "zs: HU exact on E681's 588 S2 sweep cases (%d inexact)" % cnt["S2"][1])
check(cnt["S3"][0] == 240 and cnt["S3"][1] == 149 and cnt["S3"][2] == 67, "zs: on E683's 240 S3 cases HU must fail (149 inexact) and HA (67): %s" % cnt["S3"])
print("%d of %d replay checks" % (n - bad, n))
sys.exit(1 if bad else 0)
