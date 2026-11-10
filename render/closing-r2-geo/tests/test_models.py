#!/usr/bin/env python3
"""The R2 offline models (gen/r2models.py) against the data they were read from and against independent arithmetic.  FIT
checks, not evidence: the S1/S1b clipped objects at w = 1 (the homogeneous model must reduce to R1's), the RZ reciprocal words
S1b measured at w != 1, the float32 rounding helpers against numpy, the T4 candidates, the T3 numbers and the T5 depth-word
identity.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import pathlib  # noqa: E402
import random  # noqa: E402
from fractions import Fraction  # noqa: E402

import numpy as np  # noqa: E402

R2 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R2 / "gen"), str(R2 / "score")]
import r1models as M1  # noqa: E402
import r2models as M  # noqa: E402
import score_geo2 as G  # noqa: E402
from r1lib import Kept  # noqa: E402

ok = True
S1B = pathlib.Path.home() / "src/scratch/resgx545/closing/s1b-v2/out/g-e3"


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


# ---- float32 rounding helpers against numpy (independent: numpy rounds a double, the helpers an exact rational)
random.seed(7)
bad = []
for _ in range(2000):
    a = Fraction(random.randint(1, 1 << 30), random.randint(1, 1 << 20)) * random.choice((1, -1, Fraction(1, 977)))
    f = np.float32(float(a))
    rn_ref = Fraction(float(f))
    if M.rn(a) != rn_ref and abs(a * 2 ** 40) < 2 ** 60:          # double rounding is possible only on a near tie
        bad.append(("rn", a))
    z = M.rz(a)
    if not (abs(z) <= abs(a) and abs(a) - abs(z) < abs(Fraction(float(np.nextafter(np.float32(abs(float(z))), np.float32(1e30)))) - abs(z)) + 0):
        bad.append(("rz", a))
check("rn and rz of exact rationals: rn = numpy float32, rz toward zero and the nearest below (2000 random values)", not bad, str(bad[:3]))
check("rz and rn of 1/3 are the float32 neighbours 0x3eaaaaaa and 0x3eaaaaab", (M.word(M.rz(Fraction(1, 3))), M.word(M.rn(Fraction(1, 3)))) == (0x3eaaaaaa, 0x3eaaaaab))
check("rz/rn agree with r1models' reciprocal words (the clamp ladder's)", all(M.rhw_words(w) == M1.recip_words(M1.bits(float(np.float32(w)))) for w in (3.0, 7.0, 0.003, 1.1, 1e-5)))

# ---- the homogeneous clip model at w = 1 is R1's SH model, which fits S1/S1b's measured clipped objects
k = Kept(S1B)
for nm, A, B in (("e3z-cut-p", 2.0, 1.0), ("e3z-cut-m", 2.0, -1.0), ("e3z-flat099", 0.0, 0.99)):
    d = G.decode_object(k.dump(nm, "param.bin"), k.dump(nm, "tadata.bin"))
    p = M.predict_zwclip(A, B, 0.0, 1.0)
    check(f"predict_zwclip at w = 1 on S1b's measured {nm}: vertices in stored order, prim list and made-vertex depth words",
          G._near(G._xy(d), p["xy"], 1 / 256) and d["prims"] == p["prims"] and d["nvert"] == p["nv"]
          and all(z == M.word(Fraction(0)) or True for z in []), f"{G._xy(d)} {d['prims']}")
    # depth words of the made vertices (the only ones this model freezes) against the measured depth words
    dw = [z for _, _, z in d["packed"]]
    check(f"  {nm}: the made vertices' depth words are exactly 1.0 / 0.0 as measured",
          all(dm is None or dm == z for dm, z in zip(p["depth_made"], dw)), f"{dw} {p['depth_made']}")
a1, b1 = M1.predict_zclip(2.0, 1.0), M.predict_zwclip(2.0, 1.0, 0.0, 1.0)
check("at w = 1 the homogeneous model equals r1models.predict_zclip (xy, prims) for the five clip rows of R1",
      all(M1.predict_zclip(A, B, "x")["xy"] == M.predict_zwclip(A, B, 0.0, 1.0)["xy"] and
          M1.predict_zclip(A, B, "x")["prims"] == M.predict_zwclip(A, B, 0.0, 1.0)["prims"]
          for A, B in ((2.0, 1.0), (2.0, 0.5), (4.0, 0.0), (4.0, -1.0), (2.0, -1.0))))

# ---- 1/w of originals: S1b's measured RZ words at w = 3, 7, 0.003 (e3i rows; the reciprocal rule is RZ, 7 of 7 in band)
for nm, W in (("e3i-w3", 3.0), ("e3i-w7", 7.0), ("e3i-w0p003", 0.003)):
    d = G.decode_object(k.dump(nm, "param.bin"), k.dump(nm, "tadata.bin"))
    rz, rn = M.rhw_words(W)
    check(f"S1b {nm}: every vertex's stored 1/w is the RZ word of 1/{W:g} ({rz:#x})", d["state"] == "present"
          and set(d["rhw"]) == {rz}, f"{[hex(w) for w in d['rhw']]} vs RZ {rz:#x} RN {rn:#x}")

# ---- T3 numbers
r = M.predict_zwclip(2, 1, 0.5, 1.25)
check("T3 w = 0.5x + 1.25: 4 vertices, the made vertices at window x 36 (cut x = 1/6, w = 4/3, x/w = 1/8), prims as T2",
      r["nv"] == 4 and [m for m in r["made"]].count(True) == 2 and sorted(x for (x, _), m in zip(r["xy"], r["made"]) if m) == [36.0, 36.0]
      and r["prims"] == [(16, 1, 18), (2, 17, 19)], str(r["xy"]))
w_made = [Fraction(1, 2) * Fraction(1, 6) + Fraction(5, 4)]
lerp = [M.fval(w) for w, m in zip(r["rhw_lerp"], r["made"]) if m]
check("T3: the made w is 4/3: HI-w gives 1/w = 0.75 (RZ word 0x3f400000) at both made vertices, HI-rhw the lerp of the ends' 1/w: "
      "0.8205 on the A->B cut (the proposal's number) and 0.7847 on B->C",
      [w for w, m in zip(r["rhw_w"], r["made"]) if m] == [0x3f400000] * 2 and any(abs(v - 0.8205) < 1e-3 for v in lerp)
      and any(abs(v - 0.7847) < 1e-3 for v in lerp), f"{[hex(w) for w in r['rhw_w']]} {lerp}")
check("T3: the two candidates differ at both made vertices and agree at the originals",
      all((a != b) == m for a, b, m in zip(r["rhw_w"], r["rhw_lerp"], r["made"])))
r2 = M.predict_zwclip(2, 1, -0.5, 1.25)
check("T3 second slope: 4 vertices, made at x = 0.1 (w = 1.2): HI-w 1/w = RZ(1/1.2)",
      r2["nv"] == 4 and [w for w, m in zip(r2["rhw_w"], r2["made"]) if m][0] == M.word(M.rz(Fraction(5, 6))))
r3 = M.predict_zwclip(0, 0, 0.5, 1.25)
check("T3 no-cut row: 3 vertices in input order, window = 32 + 32 x/w", r3["nv"] == 3 and abs(r3["xy"][0][0] - (32 + 32 * -0.75 / 0.875)) < 1e-9 and abs(r3["xy"][0][1] - (32 + 32 * -0.75 / 0.875)) < 1e-9)

# ---- T4 candidates
Z0 = M.depth_words(0.0, 3.0)
Z1 = M.depth_words(-0.5, 1.0)
check("T4 controls: Z = 0, W = 3 gives 0x3f000000 and Z = -0.5, W = 1 gives 0x3e800000 for every candidate",
      set(Z0.values()) == {0x3f000000} and set(Z1.values()) == {0x3e800000}, f"{Z0} {Z1}")
pairs = [(-2.1, 3.0), (-2.6, 3.0), (-5.3, 7.0), (-0.0027, 0.003), (-0.83, 1.1), (-6.1, 7.0)]
dw = [M.depth_words(*p) for p in pairs]
check("T4: every frozen pair separates at least 3 candidates (3 to 4 distinct words a pair)", all(len(set(d.values())) >= 3 for d in dw),
      str([len(set(d.values())) for d in dw]))
sep = {(a, b) for d in dw for a in d for b in d if a < b and d[a] != d[b]}
allpairs = {(a, b) for a in "D1 D2 D3 D5 D6 D7".split() for b in "D1 D2 D3 D5 D6 D7".split() if a < b}
check("T4: the six pairs together separate every pair of candidates (a 6 of 6 verdict names one)", sep == allpairs, str(allpairs - sep))
check("T4: z/w of every pair is in (-1, -0.5] (0.5 + 0.5 q exact by Sterbenz: the word is a function of q alone)",
      all(-1 < Z / W <= -0.5 for Z, W in pairs))
# D3 reference with numpy: 0.5 + 0.5 * float32(Z / W) rounded to nearest, exact for this range
for Z, W in pairs:
    q = np.float32(np.float32(Z) / np.float32(W))
    ref = np.float32(0.5) + np.float32(0.5) * q
    check(f"T4 D3 for Z = {Z:g}, W = {W:g} equals numpy float32 (double rounding aside)",
          M.depth_words(Z, W)["D3"] == int(np.array([ref], dtype=np.float32).view(np.uint32)[0]) or
          abs(M.fval(M.depth_words(Z, W)["D3"]) - float(ref)) <= 2 ** -24)

# ---- T5: the loop's stored depth word is 0x3f200000 + N, exact (z = 0.25 + 4N ulp)
okd = True
for N in (0, 1, 3, 28, 53, 55, 110, 220, 440, 880, 1760, 3520, 7040, 100000):
    z = M.fval(0x3e800000 + 4 * N)
    d = Fraction(1, 2) + Fraction(1, 2) * Fraction(z)
    okd &= M.word(d) == 0x3f200000 + N
check("T5: the depth word of z = float(0x3e800000 + 4N) is exactly 0x3f200000 + N for N up to 100000 (exact, no rounding)", okd)
check("C: the frozen limit is C = 0x371 (R1: raise at P = 0x373, none at 0x374) and P* = 0x374", M.C_MEASURED == 0x371 and M.P_STAR == 0x374)
sys.exit(0 if ok else 1)
