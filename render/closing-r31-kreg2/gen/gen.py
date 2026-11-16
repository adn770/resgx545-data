#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen.py: r31-kreg2's tables and predictions (Q024, CR_PDS_REG_0A78 timing), from one seed.

  python3 gen/gen.py          write tables/*.txt and predictions/*.tsv
  python3 gen/gen.py --check  exit 1 when a written file is not what this generates

Two loads. L1 (k1, as r29-kreg, E1114): t10's 256x256 triangle, six renders a job. L2 (k2, new):
t30's many small triangles, `probe --tri pixel --width 64 --height 64 --vertices 1500` (the
triangle and 499 copies of it, each moved c/16 pixel) with the program file given six times, so
six renders a job, each printing `tri 64x64 #1: T us` (t30, resgx545 2cc9c5b).

s0 (safe, no write): c0-tri, an exact 64x64 triangle; r1-r8 the L1 references, v1-v8 the L2
references, at the register's reset value. k1 and k2 (flagged): every value 0x00-0x3f twice, pass A
(fit) and pass B (held out), each pass its own shuffle of the stage's seed; a `kreg:0x0a78=0x2c`
control before every 8 value rows (16); last c-end, an exact 64x64 triangle with no write.

A row's reading (frozen, both loads): the MEDIAN of renders 2-6 (E1114: one slow render moved a
mean by up to 4.8 percent; the median of renders 2-6 put every E1114 value within 0.82 percent)."""
import os
import random
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 20261117                 # k1's passes from SEED, k2's from SEED + 1
VALUES = [f"0x{v:02x}" for v in range(0x40)]
DEFAULT = "0x2c"
RENDERS = 6
TIMED1 = f"tri --width 256 --height 256 -n {RENDERS}"
PROG = '"$S/bins/p1139-green.bin"'
TIMED2 = "probe --tri pixel --width 64 --height 64 --vertices 1500 " + " ".join([PROG] * RENDERS)
EXACT = "tri --width 64 --height 64"
EVERY = 8                       # value rows between two 0x2c controls
# L1 (k1): fixed, from E396 and E1114
BOUND1_PCT = 1.0                # a value's reading against MED, both passes, same side
REF1_PCT = 1.0                  # a 0x2c control's band around s0's r1-r8 median
SPREAD1_PCT = 0.5               # the in-band controls' interquartile range against MED
# L2 (k2): no earlier timing of this load, so the band is fixed by a frozen rule on s0's v1-v8:
# BOUND2 = max(FLOOR2, K2 x the interquartile range of v1-v8 in percent of their median); the
# controls' band is BOUND2, their spread premise BOUND2 / 2; BOUND2 above CAP2 (E141's smaller
# excursion, 2.6 percent, would not be resolved) makes k2 "cannot tell" (no retirement)
FLOOR2_PCT = 1.0
K2 = 3.0
CAP2_PCT = 2.5
OUTLIERS = 1                    # at most one 0x2c control a stage outside its band (excluded)

S0_HEAD = """#stage s0
#limit 0
# s0 (safe): no register write. c0-tri, an exact 64x64 triangle (the core draws). r1-r8: L1, the
# 256x256 triangle six renders a job (t10); v1-v8: L2, 500 small triangles six renders a job
# (t30, probe --tri --vertices 1500, the program given six times). Both at the register's reset
# value (0x2c, the preflight's read): the references k1's and k2's 0x2c controls are held to, and
# v1-v8's spread fixes k2's bound (gen/gen.py, frozen). Readings: the median of renders 2-6.
"""
K_HEAD = """#stage {st}
#limit 0
# {st} (flagged, user-approved round 29): CR_PDS_REG_0A78 written before each job (kreg:0x0a78=V),
# restored to 0x2c after it.
# Load {load}.
# Pass A (a..., fit) and pass B (b..., held out): every value 0x00-0x3f once each, each pass its
# own frozen shuffle (gen/gen.py). c01-c16 write 0x2c itself: the write path's control (in the
# band of s0's references; one outside is allowed and dropped, two fail the stage's controls) and
# the bound's median. c-end: an exact 64x64 triangle with no write. No planned fault or hang: any
# is a stop (rc 4); a value that does not read back stops (rc 19); a failed render or a median
# above twice the stage's first timed row stops (rc 24, on_stop end).
"""
LOADS = {"k1": ("L1: the 256x256 triangle (t10, as r29-kreg)", "t10", TIMED1, 0),
         "k2": ("L2: 500 small triangles at 64x64 (t30)", "t30", TIMED2, 1)}


def passes(stage):
    rng = random.Random(SEED + LOADS[stage][3])
    a, b = VALUES[:], VALUES[:]
    rng.shuffle(a)
    rng.shuffle(b)
    return a, b


def k_rows(stage):
    """[(name, set, value or None, tool, args)] in run order."""
    tool, args = LOADS[stage][1:3]
    out, nc = [], 0
    for tag, order in zip("ab", passes(stage)):
        for i, v in enumerate(order):
            if i % EVERY == 0:
                nc += 1
                out.append((f"c{nc:02d}", "control", DEFAULT, tool, args))
            out.append((f"{tag}{v[2:]}", "fit" if tag == "a" else "held", v, tool, args))
    out.append(("c-end", "control", None, "t10", EXACT))
    return out


def reads(args):
    return "reads:diff" if args == EXACT else "reads:diff,us" if args == TIMED1 else "reads:img,us"


def tables():
    s0 = S0_HEAD + f"c0-tri|control|safe|reads:diff|t10|{EXACT}\n"
    s0 += "".join(f"r{i}|control|safe|{reads(TIMED1)}|t10|{TIMED1}\n" for i in range(1, 9))
    s0 += "".join(f"v{i}|control|safe|{reads(TIMED2)}|t30|{TIMED2}\n" for i in range(1, 9))
    out = {"tables/s0.txt": s0}
    for st in ("k1", "k2"):
        t = K_HEAD.format(st=st, load=LOADS[st][0])
        for name, sset, v, tool, args in k_rows(st):
            words = ([f"kreg:0x0a78={v}"] if v else []) + ([reads(args)] if sset == "control"
                                                            else [])
            t += f"{name}|{sset}|flagged|{' '.join(words)}|{tool}|{args}\n"
        out[f"tables/{st}.txt"] = t
    return out


def predictions():
    head = "case\tquantity\tvalue\tmodel\tset\tsource\n"
    s0 = head + "c0-tri\tdiff\t0\tH-CTL\tcontrol\tE045 (every value drew the 64x64 triangle)\n"
    s0 += "".join(f"r{i}\tdiff\t0\tH-CTL\tcontrol\tE396, E1114 (the 256x256 triangle drew)\n"
                  for i in range(1, 9))
    s0 += "".join(f"v{i}\timg\tsame\tH-CTL\tcontrol\tthe six renders and v1-v8 draw one image "
                  "[infer] (one program, one scene)\n" for i in range(1, 9))
    out = {"predictions/s0.tsv": s0}
    for st in ("k1", "k2"):
        k = head
        for name, sset, v, tool, args in k_rows(st):
            if sset == "control":
                k += (f"{name}\tdiff\t0\tH-CTL\tcontrol\tE045\n" if args != TIMED2 else
                      f"{name}\timg\tsame\tH-CTL\tcontrol\tv1's image (s0)\n")
                if v and st == "k1":
                    k += (f"{name}\tref_pct_le\t{REF1_PCT}\tH-CTL\tcontrol\t"
                          f"E1114 (15 of 16 controls within 0.54 percent; at most {OUTLIERS} "
                          "outside a stage)\n")
                elif v:
                    k += (f"{name}\tref_pct_le\tBOUND2\tH-CTL\tcontrol\t"
                          f"s0's v1-v8 (BOUND2 = max({FLOOR2_PCT}, {K2} x IQR %), at most "
                          f"{CAP2_PCT}; at most {OUTLIERS} outside a stage)\n")
            elif st == "k1":
                k += (f"{name}\tdev_pct_le\t{BOUND1_PCT}\tH0\t{sset}\t"
                      "E396 (six values within 0.3 percent), E1114 (median of 2-6 within 0.82); "
                      "E141's 2.6 and 5.5 percent outside\n")
            else:
                k += (f"{name}\tdev_pct_le\tBOUND2\tH0\t{sset}\t"
                      "no earlier timing of L2: s0's v1-v8 fix BOUND2 (at most "
                      f"{CAP2_PCT}, below E141's 2.6 percent)\n")
        out[f"predictions/{st}.tsv"] = k
    return out


def main(argv):
    files = {**tables(), **predictions()}
    if "--check" in argv:
        bad = [p for p, t in files.items()
               if not os.path.exists(os.path.join(KP, p)) or open(os.path.join(KP, p)).read() != t]
        print("\n".join(f"{p}: not what gen/gen.py writes" for p in bad) or "gen: current")
        return 1 if bad else 0
    for p, t in files.items():
        with open(os.path.join(KP, p), "w") as f:
            f.write(t)
    print("wrote " + ", ".join(files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
