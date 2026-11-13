"""POST HOC (after the run, not frozen): srgb3-tri read none of TRI-OUT, TRI-NOFLUSH (1137 of
2048) or TRI-LO (0). Per half: the kept value against the two levels' FTZ-OUT results (A level
1, B level 2) and a few lerp forms of the level weight."""
import collections, gzip, math, os, sys
KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import pins, srgb as S, tex
R = S.rule()
px = pins.pixels(gzip.open(os.path.join(KP, "out/20261113-214825/srgb3/srgb3-tri.txt.gz"), "rt").read())
sp = S.tri_spec()
F = tex.F
forms = collections.Counter()
miss_ulps = collections.Counter()
n = 0
for p, v in enumerate(px):
    x, y = p % 64, p // 64
    u, vv = tex.coord(sp["u"], x, y), tex.coord(sp["v"], x, y)
    a = S.level_bilinear(R, u, vv, 1, "out")
    b = S.level_bilinear(R, u, vv, 2, "out")
    for c in (0, 1):
        got = v >> 16 * c & 0xFFFF
        A, B = R.h2f(a[c]), R.h2f(b[c])
        n += 1
        cand = {
            "stage f16": R.half_rne(S.stage(R, A, B, 16, "out")),
            "stage f16 B<->A": R.half_rne(S.stage(R, B, A, 48, "out")),
            "exact lerp RNE": R.half_rne(float(F(A) + F(16, 64) * (F(B) - F(A)))),
            "exact lerp trunc": R.half_rne(float(F(A))) if False else None,
            "level 1": a[c], "level 2": b[c],
        }
        # truncation of the exact lerp toward zero
        ex = F(A) + F(16, 64) * (F(B) - F(A))
        h = R.half_rne(float(ex))
        if F(R.h2f(h)) > ex:
            h -= 1
        cand["exact lerp trunc"] = h
        for k in range(0, 65):
            cand[f"stage k{k}"] = R.half_rne(S.stage(R, A, B, k, "out"))
        for k, val in cand.items():
            if val == got:
                forms[k] += 1
        miss_ulps[got - cand["stage f16"]] += 1
print(f"halves {n}")
for k, c in forms.most_common(12):
    print(f"  {k}: {c}")
print("kept less TRI-OUT's half, in half ulps:", sorted(miss_ulps.items())[:12])


def grid_stage(A, B, k, bits, rnd):
    """The stage with both halves floored to 2^(e - bits) (R10-BF11: bits 11), the lerp exact,
    rounded to half by rnd (rhu: ties up; rne)."""
    if k == 0:
        return R.half_rne(A)
    g = F(2) ** (max(R.expo(A), R.expo(B)) - bits)
    qa, qb = math.floor(F(A) / g) * g, math.floor(F(B) / g) * g
    r = qa + F(k, 64) * (qb - qa)
    return R.half_rhu(r) if rnd == "rhu" else R.half_rne(float(r))


fits = collections.Counter()
for p, v in enumerate(px):
    x, y = p % 64, p // 64
    u, vv = tex.coord(sp["u"], x, y), tex.coord(sp["v"], x, y)
    a = S.level_bilinear(R, u, vv, 1, "out")
    b = S.level_bilinear(R, u, vv, 2, "out")
    for c in (0, 1):
        got = v >> 16 * c & 0xFFFF
        A, B = R.h2f(a[c]), R.h2f(b[c])
        for bits in (11, 12, 13, 14, 16, 20, 24):
            for rnd in ("rhu", "rne"):
                fits[(bits, rnd)] += grid_stage(A, B, 16, bits, rnd) == got
print("third stage on a finer grid (bits, rounding): halves exact of 4096")
for k, c in sorted(fits.items(), key=lambda kv: -kv[1])[:8]:
    print(f"  {k}: {c}")
