#!/usr/bin/env python3
"""R3 offline models (gen/r3models.py) against the data they were fitted to: E783's six depth words, E782's four kept vertices, the
anchors, the layout and law numbers of the design note, and H-last on the kept timelines of rounds 1 and 2.  A reader check of the
FITS, never evidence.  Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import pathlib  # noqa: E402
from fractions import Fraction as F  # noqa: E402

R3 = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R3 / "gen"), str(R3 / "score")]
import r3models as M  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


T4 = [(-2.1, 3.0, 0x3E19999C), (-2.6, 3.0, 0x3D88888C), (-5.3, 7.0, 0x3DF8AF8C), (-0.0027, 0.003, 0x3D4CCCD0),
      (-0.83, 1.1, 0x3DFB5874), (-6.1, 7.0, 0x3D83A840)]
hits = {k: sum(M.depth_word(M.f32(z), M.f32(w), k) == dw for z, w, dw in T4) for k in M.RULES}
check("E783's six words: T26, T27 and K23 fit 6 of 6, D1 and D2 5 of 6 (the design's fit)",
      hits["T26"] == 6 and hits["T27"] == 6 and hits["K23"] == 6 and hits["D1"] == 5 and hits["D2"] == 5, str(hits))
check("D5 (RZ) fits 2 of 6 (E783 refuted it in 4 of 6)", hits["D5"] == 2, str(hits))
check("anchors: z = 0, w = 3 gives 0x3f000000 and z = -0.5, w = 1 gives 0x3e800000 under every rule",
      all(M.depth_word(F(0), F(3), k) == 0x3F000000 and M.depth_word(F(-1, 2), F(1), k) == 0x3E800000 for k in M.RULES))
check("w = 2 and w = 0.5 (powers of two): the product is exact and every rule gives one word",
      all(len({M.depth_word(z, M.f32(w), k) for k in M.RULES}) == 1 for z, w in ((M.rprec(M.f32(-1.3), 20, 'rz'), 2.0), (M.rprec(M.f32(-0.7), 20, 'rz'), 0.5), (M.rprec(M.f32(-1.7), 20, 'rz'), 2.0))))
check("frac of |z RZ(1/w)| of E783's pairs: 0.967 0.467 0.957 0.870 0.365 0.271 (the design's table)",
      [round(float(M.frac(M.f32(z), M.f32(w))), 3) for z, w, _ in T4] == [0.967, 0.467, 0.957, 0.870, 0.365, 0.271],
      str([round(float(M.frac(M.f32(z), M.f32(w))), 3) for z, w, _ in T4]))
check("T26 and T27 differ exactly for a fraction in (3/8, 7/16] and agree elsewhere (hand cases)",
      M.depth_word(M.f32(-2.6), M.f32(3.0), "T26") == M.depth_word(M.f32(-2.6), M.f32(3.0), "T27") == 0x3D88888C)
# the threshold rules on a synthetic product with a known fraction
p = F(-1, 2) - F(5, 12) * F(1, 2 ** 24)       # |p| = 0.5 + frac 5/12 ulp (ulp of [0.5, 1) is 2^-24)
check("thr_mag: fraction 5/12 is up for t = 3/8 and down for t = 7/16",
      abs(M.thr_mag(p, F(3, 8))) > abs(M.thr_mag(p, F(7, 16))), str((M.thr_mag(p, F(3, 8)) - p, M.thr_mag(p, F(7, 16)) - p)))
q = F(1, 2) + F(1, 2 ** 24) * F(1, 2)            # positive, floor fraction 1/2
check("thr_dir: the toward-+inf rule at a positive product (floor fraction g > 1 - t is up) differs from thr_mag in (t, 1 - t)",
      M.thr_dir(F(1, 2) + F(1, 2 ** 24) * F(1, 2), F(5, 8)) == F(1, 2) and M.thr_mag(q, F(3, 8)) == F(1, 2) + F(1, 2 ** 24))
check("thr_dir on a negative equals thr_mag with 1 - t (the same hardware data cannot separate them)",
      all(M.thr_dir(-F(x, 97) * F(1, 2 ** 24) - F(1, 2), F(5, 8)) == M.thr_mag(-F(x, 97) * F(1, 2 ** 24) - F(1, 2), F(3, 8)) for x in range(1, 97)))
check("sum modes: a tie (0.5 q' odd in units of 2^-25) rounds to even, toward zero and half up differently",
      len({M.rsum(F(3, 4) + F(3, 2 ** 25), m) for m in ("rn", "rz", "rh")}) == 3 or
      len({M.rsum(F(3, 4) + F(1, 2 ** 25), m) for m in ("rn", "rz", "rh")}) >= 2)
# the model's made-vertex relation of design 1.1
check("RZ reciprocal words of E782's made vertices: the made w values are unique per word (design 1.1)",
      M.made_w_candidates(0x3F400000) and all(M.rz_recip(M.wordval(w)) == M.wordval(0x3F400000) for w in M.made_w_candidates(0x3F400000)))
# layout and the laws of the design note section 1.3 / 4
L4, L2 = M.layout(4096, 4096), M.layout(2048, 2048)
check("layout 4096x4096: R 32768, side 256; 2048x2048: R 8192, side 128", (L4["R"], L4["side"], L2["R"], L2["side"]) == (32768, 256, 8192, 128), str((L4, L2)))
check("LT at 2048x2048 gives the last raise thr0 0xd4 (C 0xf4) and at the three g-c5 targets 0x1a8, 0x1a8, 0x1dd",
      [M.lt_last_thr0(*t) for t in ((2048, 2048), (4096, 2048), (2048, 4096), (3072, 3072))] == [0xd4, 0x1a8, 0x1a8, 0x1dd],
      str([hex(M.lt_last_thr0(*t)) for t in ((2048, 2048), (4096, 2048), (2048, 4096), (3072, 3072))]))
check("regions of 4096x2048 and 2048x4096 are equal (16384) with tail-pointer sides 128 and 256",
      (M.layout(4096, 2048)["R"], M.layout(2048, 4096)["R"], M.layout(4096, 2048)["side"], M.layout(2048, 4096)["side"]) == (16384, 16384, 128, 256),
      str((M.layout(4096, 2048), M.layout(2048, 4096))))
b = M.affine_brackets(4096, 2048)
check("affine-in-regions bracket at 4096x2048: raised-threshold C from 0x1bb to 0x1e5 (the design's table), i.e. last raise thr0 0x19b .. 0x1c5",
      (b["R"][0] + 0x20, b["R"][1] + 0x20) == (0x1bb, 0x1e5) or (b["R"][0], b["R"][1]) == (0x19b, 0x1c5), str({k: [hex(x) for x in v] for k, v in b.items()}))
check("every fixed cell of a g-c5 target lies inside one 63-wide bracket so six bisect cells can finish (2^6 = 64)",
      all(max(M.c5_fixed_cells(*t)) - min(M.c5_fixed_cells(*t)) < 64 for t in ((4096, 2048), (2048, 4096), (3072, 3072))))
check("H-last: max(c - 2, 0) of the count before the last abort", M.hlast([3, 4, 3]) == 1 and M.hlast([2]) == 0 and M.hlast([]) == 0)
sys.exit(0 if ok else 1)
