"""Post hoc (fold): srgb2-sub's misses against R10-BF11, per half: corners, weights, kept vs rule (in half ulps)."""
import collections, gzip, os, sys
KP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KP, "gen")); sys.dont_write_bytecode = True
import pins, srgb as S, q282 as Q
ATT = os.path.join(KP, "out/20261113-102730/srgb2")
def kept(n):
    return pins.pixels(gzip.open(os.path.join(ATT, n + ".txt.gz"), "rt").read(), 2048)
for name, mk, models in S.ROWS:
    sp = mk(); hw = kept(name); pr = S.predict(sp, "R10-BF11")
    miss = collections.Counter(); ex = []
    halves = 0
    for p in range(2048):
        t, fx, fy = S.footprint(sp, p % 64, p // 64)
        kx, ky = S.WEIGHTS["R10-BF11"](fx), S.WEIGHTS["R10-BF11"](fy)
        for c in (0, 1):
            h, r = hw[p] >> 16 * c & 0xFFFF, pr[p] >> 16 * c & 0xFFFF
            if h != r:
                halves += 1
                b = [v >> 8 * c & 255 for v in t]
                miss[(h - r)] += 1
                if len(ex) < 12: ex.append((p % 64, p // 64, c, b, kx, ky, hex(h), hex(r), Q.h2f(h), Q.h2f(r)))
    print(f"{name}: {sum(a == b for a, b in zip(hw, pr))}/2048 pixels, {4096 - halves}/4096 halves; kept - rule (half ulps): {dict(sorted(miss.items()))}")
    for e in ex: print("   x %d y %d ch %d corners %s kx %d ky %d kept %s rule %s (%.6g vs %.6g)" % e)
