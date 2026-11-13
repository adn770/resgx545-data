"""Post hoc (fold, [fitted] on srgb2-sub): R10-BF11 with every stage output below 2^-14 (a subnormal
half) flushed to +0 (FTZ-OUT), and variants; scored on every srgb2 row and r9-x's six kept rows."""
import gzip, os, sys
KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import pins, srgb as S, q282 as Q
ATT = os.path.join(KP, "out/20261113-102730/srgb2")
TINY = 2.0 ** -14
def stage(a, b, k, mode):
    if mode == "in" and (abs(a) < TINY): a = 0.0
    if mode == "in" and (abs(b) < TINY): b = 0.0
    r = Q.stage(a, b, k)
    return 0.0 if mode in ("out", "in") and abs(r) < TINY else r
def two(b4, kx, ky, mode):
    d = [Q.decode(b) for b in b4]
    return Q.half_rne(stage(stage(d[0], d[1], kx, mode), stage(d[2], d[3], kx, mode), ky, mode))
def pred(sp, mode):
    out = []
    for p in range(2048):
        t, fx, fy = S.footprint(sp, p % 64, p // 64)
        kx, ky = int(fx * 64 // 1), int(fy * 64 // 1)
        out.append(sum(two([v >> 8 * c & 255 for v in t], kx, ky, mode) << 16 * c for c in (0, 1)))
    return out
rows = {n: mk() for n, mk, _ in S.ROWS}
r9 = pins.module("data:render/closing-r9-x/gen/srgb.py", "r9x_srgb")
ra, rb = r9.pair_rows(9051), r9.pair_rows(9052)
r9specs = {"srgb-a1": r9.spec_a(ra), "srgb-a2": r9.spec_a(rb), "srgb-b1": r9.spec_b(r9.pair_rows(9053)),
           "srgb-b2": r9.spec_b(r9.pair_rows(9054)), "srgb-c1": r9.spec_a(ra, 21), "srgb-c2": r9.spec_a(rb, 43)}
for mode in ("none", "out", "in"):
    res = []
    for n, sp in rows.items():
        hw = pins.pixels(gzip.open(os.path.join(ATT, n + ".txt.gz"), "rt").read(), 2048)
        res.append(f"{n} {sum(a == b for a, b in zip(hw, pred(sp, mode)))}")
    for n, sp in r9specs.items():
        hw = pins.kept_pixels(f"data:render/closing-r9-x/out/20261113-081821/srgb/{n}.txt.gz")
        res.append(f"{n} {sum(a == b for a, b in zip(hw, pred(sp, mode)))}")
    print(f"mode {mode}: " + ", ".join(res))
