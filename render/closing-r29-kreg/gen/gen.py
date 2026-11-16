#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen.py: r29-kreg's tables and predictions (Q024, CR_PDS_REG_0A78 timing), from one seed.

  python3 gen/gen.py          write tables/*.txt and predictions/*.tsv
  python3 gen/gen.py --check  exit 1 when a written file is not what this generates

s0 (safe): c0-tri, an exact 64x64 triangle (reads:diff), then r1-r8, 256x256 six renders each at
the register's reset value, no write (reads:diff,us). k1 (flagged): every value 0x00-0x3f twice,
pass A (fit) and pass B (held out), each pass its own shuffle of SEED; before every 8 value rows
a control writing 0x2c (16 in all, reads:diff,us); last c-end, an exact 64x64 triangle with no
write (reads:diff). A row's reading is the mean of renders 2-6 (E141, E396)."""
import os
import random
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 20261116
VALUES = [f"0x{v:02x}" for v in range(0x40)]
DEFAULT = "0x2c"
TIMED = "tri --width 256 --height 256 -n 6"
EXACT = "tri --width 64 --height 64"
EVERY = 8           # value rows between two 0x2c controls
BOUND_PCT = 1.0     # a value's reading against the controls' median, both passes
SPREAD_PCT = 0.5    # the controls' interquartile range against their median (the premise)
REF_PCT = 1.0       # the controls' median against s0's references' median (the write path)

S0_HEAD = """#stage s0
#limit 0
# s0 (safe): no register write. c0-tri, an exact 64x64 triangle (the core draws); r1-r8, the
# 256x256 triangle six renders a job at the register's reset value (0x2c by the preflight's read):
# the references k1's 0x2c controls are held to (within 1 percent) and REF for the hooks' wedge
# rule (a render mean above twice the stage's first timed row stops the stage).
"""
K1_HEAD = """#stage k1
#limit 0
# k1 (flagged, user-approved round 29): CR_PDS_REG_0A78 written before each job (kreg:0x0a78=V),
# restored to 0x2c after it. Pass A (a..., fit) and pass B (b..., held out): every value
# 0x00-0x3f once each, each pass its own frozen shuffle (gen/gen.py SEED). c01-c16 write 0x2c
# itself: the write path's control (within 1 percent of s0's references) and the bound's
# median. c-end: an exact 64x64 triangle with no write after the last row. No planned fault or
# hang: any is a stop (rc 4); a value that does not read back stops (rc 19); a render mean above
# twice c01's stops (rc 24, on_stop end).
"""


def passes():
    rng = random.Random(SEED)
    a, b = VALUES[:], VALUES[:]
    rng.shuffle(a)
    rng.shuffle(b)
    return a, b


def k1_rows():
    """[(name, set, value or None, args)] in run order."""
    out, nc = [], 0
    for tag, order in zip("ab", passes()):
        for i, v in enumerate(order):
            if i % EVERY == 0:
                nc += 1
                out.append((f"c{nc:02d}", "control", DEFAULT, TIMED))
            out.append((f"{tag}{v[2:]}", "fit" if tag == "a" else "held", v, TIMED))
    out.append(("c-end", "control", None, EXACT))
    return out


def tables():
    s0 = S0_HEAD + "c0-tri|control|safe|reads:diff|t10|" + EXACT + "\n"
    s0 += "".join(f"r{i}|control|safe|reads:diff,us|t10|{TIMED}\n" for i in range(1, 9))
    k1 = K1_HEAD
    for name, sset, v, args in k1_rows():
        reads = "reads:diff" if args == EXACT else "reads:diff,us"
        words = ([f"kreg:0x0a78={v}"] if v else []) + ([reads] if sset == "control" else [])
        k1 += f"{name}|{sset}|flagged|{' '.join(words) or '-'}|t10|{args}\n"
    return {"tables/s0.txt": s0, "tables/k1.txt": k1}


def predictions():
    head = "case\tquantity\tvalue\tmodel\tset\tsource\n"
    s0 = head + "c0-tri\tdiff\t0\tH-CTL\tcontrol\tE045 (every value drew the 64x64 triangle)\n"
    s0 += "".join(f"r{i}\tdiff\t0\tH-CTL\tcontrol\tE396 (the 256x256 triangle drew)\n"
                  for i in range(1, 9))
    k1 = head
    for name, sset, v, args in k1_rows():
        if sset == "control":
            k1 += f"{name}\tdiff\t0\tH-CTL\tcontrol\tE045\n"
            if v:
                k1 += (f"{name}\tref_pct_le\t{REF_PCT}\tH-CTL\tcontrol\t"
                       "E396 (0x2c's median within 0.3 percent of the others)\n")
        else:
            k1 += (f"{name}\tdev_pct_le\t{BOUND_PCT}\tH0\t{sset}\t"
                   "E396 (six values within 0.3 percent); E141's 2.6 and 5.5 percent outside\n")
    return {"predictions/s0.tsv": s0, "predictions/k1.tsv": k1}


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
