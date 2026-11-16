#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""gen.py: r32-kreg3's tables and predictions (Q024's last clause: does CR_PDS_REG_0A78 change
the render time of many small triangles?), from one seed.

  python3 gen/gen.py          write tables/*.txt and predictions/*.tsv
  python3 gen/gen.py --check  exit 1 when a written file is not what this generates

The load (the question's, as asked; user decision 2026-11-16, answer a): t30's
`probe --tri pixel --width 64 --height 64 --vertices 1500` (the triangle and 499 copies, each
moved c/16 pixel: 500 small triangles in one 64x64 render) with the program file given N times,
so N renders a job, each on its own context, each printing `tri 64x64 #1: T us` (verified on
t30's library mock, debug/probe). E1125: one render about 0.72 ms, references spread 8.27
percent, so six renders a job could not time it. This session times the median of MORE renders.

s0 (safe, no register write): c0-tri, an exact 64x64 triangle; then the CALIBRATION: every
candidate form (FORMS, in their frozen order) eight times, v<form>-1..8, in eight rounds, each
round the six forms in its own frozen shuffle (drift falls on every form alike). The frozen PICK
rule (score.py pick()): the first form, in FORMS order, whose eight references all draw (N timed
renders, no failed line, one image within the job and across the eight) and whose spread (the
interquartile range of the eight readings in percent of their median, E1124's and E1125's
measure) is at most PICK_PCT. The 64x64 forms come first (the question's load); only when none
qualifies the same list at 1024x768 (E438: 1500 vertices complete there in the default
parameter buffer); when none of the six qualifies, no flagged stage runs (every gate is shut).

k<form> (flagged, one a form, each gated on s0 picking it, so at most one runs): as r31-kreg2's
k2 (E1125) with the picked form: every value 0x00-0x3f twice, pass A (fit) and pass B (held out),
each pass its own shuffle of SEED; a `kreg:0x0a78=0x2c` control before every 8 value rows (16);
last c-end, an exact 64x64 triangle with no write.

A row's reading (frozen, E1124's rule): the MEDIAN of renders 2-N."""
import os
import random
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 20261118                 # s0's rounds from SEED, every k stage's passes from SEED + 1
VALUES = [f"0x{v:02x}" for v in range(0x40)]
DEFAULT = "0x2c"
PROG = '"$S/bins/p1139-green.bin"'
# the candidate forms in their frozen order: (id, width, height, renders a job)
FORMS = [("10", 64, 64, 10), ("20", 64, 64, 20), ("40", 64, 64, 40),
         ("l10", 1024, 768, 10), ("l20", 1024, 768, 20), ("l40", 1024, 768, 40)]
FORM = {f[0]: f for f in FORMS}
REFS = 8                        # references a form in s0
PICK_PCT = 0.8                  # a form qualifies when its references' IQR is at most this
EXACT = "tri --width 64 --height 64"
EVERY = 8                       # value rows between two 0x2c controls
# the bound (E1125's rule, kept): BOUND = max(FLOOR_PCT, K x the picked form's reference IQR in
# percent of their median); the controls' band is BOUND, their spread premise BOUND / 2; BOUND
# above CAP_PCT (E141's smaller excursion, 2.6 percent, would not be resolved) is cannot tell.
# With the pick at most 0.8 percent, BOUND is at most 2.4 percent.
FLOOR_PCT = 1.0
K = 3.0
CAP_PCT = 2.5
OUTLIERS = 1                    # at most one 0x2c control a stage outside its band (excluded)


def timed(form):
    _, w, h, n = FORM[form]
    return f"probe --tri pixel --width {w} --height {h} --vertices 1500 " + " ".join([PROG] * n)


def load(form):
    _, w, h, n = FORM[form]
    return f"500 triangles (1500 vertices) at {w}x{h}, {n} renders a job"


def stage_of(form):
    return "k" + form


def rounds():
    """s0's calibration order: REFS rounds, each a frozen shuffle of the forms."""
    rng = random.Random(SEED)
    out = []
    for i in range(1, REFS + 1):
        ids = [f[0] for f in FORMS]
        rng.shuffle(ids)
        out += [(f"v{f}-{i}", f) for f in ids]
    return out


def passes():
    rng = random.Random(SEED + 1)
    a, b = VALUES[:], VALUES[:]
    rng.shuffle(a)
    rng.shuffle(b)
    return a, b


def k_rows(form):
    """[(name, set, value or None, tool, args)] in run order."""
    args = timed(form)
    out, nc = [], 0
    for tag, order in zip("ab", passes()):
        for i, v in enumerate(order):
            if i % EVERY == 0:
                nc += 1
                out.append((f"c{nc:02d}", "control", DEFAULT, "t30", args))
            out.append((f"{tag}{v[2:]}", "fit" if tag == "a" else "held", v, "t30", args))
    out.append(("c-end", "control", None, "t10", EXACT))
    return out


S0_HEAD = """#stage s0
#limit 0
# s0 (safe): no register write. c0-tri, an exact 64x64 triangle (the core draws). Then the
# calibration of the many-small-triangles load (Q024's last clause): six candidate forms of t30's
# probe --tri --vertices 1500 (64x64 at 10, 20, 40 renders a job, then 1024x768 at 10, 20, 40),
# eight references each in eight rounds, every round its own frozen shuffle of the forms. A
# reading: the median of renders 2-N. The frozen pick (score.py pick): the first form whose eight
# references draw and spread (IQR in percent of their median) at most 0.8 percent; its flagged
# stage alone runs (gates); none: no flagged row runs.
"""
K_HEAD = """#stage {st}
#limit 0
# {st} (flagged, user-approved round 29; this session user decision 2026-11-16): runs only when
# s0 picked form {form}.
# The load: {load}.
# CR_PDS_REG_0A78 written before each job (kreg:0x0a78=V), restored to 0x2c after it.
# Pass A (a..., fit) and pass B (b..., held out): every value 0x00-0x3f once each, each pass its
# own frozen shuffle (gen/gen.py). c01-c16 write 0x2c itself: the write path's control
# (in the band of s0's references of the form; one outside is allowed and dropped, two fail the
# stage's controls) and the bound's median. c-end: an exact 64x64 triangle with no write.
# No planned fault or hang: any is a stop (rc 4); a value that does not read back stops (rc 19); a
# failed render or a median above twice the stage's first timed row stops (rc 24, on_stop end).
"""


def tables():
    s0 = S0_HEAD + f"c0-tri|control|safe|reads:diff|t10|{EXACT}\n"
    s0 += "".join(f"{n}|control|safe|reads:img,us|t30|{timed(f)}\n" for n, f in rounds())
    out = {"tables/s0.txt": s0}
    for form, *_ in FORMS:
        st = stage_of(form)
        t = K_HEAD.format(st=st, form=form, load=load(form))
        for name, sset, v, tool, args in k_rows(form):
            words = ([f"kreg:0x0a78={v}"] if v else []) + (
                ["reads:diff" if args == EXACT else "reads:img,us"] if sset == "control" else [])
            t += f"{name}|{sset}|flagged|{' '.join(words)}|{tool}|{args}\n"
        out[f"tables/{st}.txt"] = t
    return out


def predictions():
    head = "case\tquantity\tvalue\tmodel\tset\tsource\n"
    s0 = head + "c0-tri\tdiff\t0\tH-CTL\tcontrol\tE045 (every value drew the 64x64 triangle)\n"
    s0 += "".join(f"{n}\timg\tsame\tH-CTL\tcontrol\tthe form's renders draw one image within the "
                  "job and across its eight references [infer] (one program, one scene; E1125's "
                  "v1-v8 did at 64x64)\n" for n, _ in rounds())
    out = {"predictions/s0.tsv": s0}
    for form, *_ in FORMS:
        k = head
        for name, sset, v, tool, args in k_rows(form):
            if sset == "control" and v is None:
                k += f"{name}\tdiff\t0\tH-CTL\tcontrol\tE045\n"
            elif sset == "control":
                k += (f"{name}\timg\tsame\tH-CTL\tcontrol\tthe image of s0's v{form}-1\n"
                      f"{name}\tref_pct_le\tBOUND\tH-CTL\tcontrol\t"
                      f"s0's v{form}-1..8 (BOUND = max({FLOOR_PCT}, {K} x IQR %), at most "
                      f"{CAP_PCT}; at most {OUTLIERS} control outside a stage, E1124's rule)\n")
            else:
                k += (f"{name}\tdev_pct_le\tBOUND\tH0\t{sset}\t"
                      "E396, E1124 (no value moved the 256x256 triangle by 1 percent); s0's "
                      f"v{form}-1..8 fix BOUND (at most {CAP_PCT}, below E141's 2.6 percent)\n")
        out[f"predictions/{stage_of(form)}.tsv"] = k
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
