#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r13-dpm's generator (round 13, stage pr2: Q036's 0x0748 bit 2 against a controlled
partial-render count; closing13/plan/rank-round13.md sections 2 and 3). Writes tables/pr2.txt and
predictions/pr2.tsv (8 jobs, t10 under regtimeline, safe class, `#limit 0`).

  python3 gen/plan.py          write the tables and predictions
  python3 gen/plan.py --check  exit 1 when a written file differs from what it would write

One scene, 3072x2048 (1500 vertices, p1139-green.bin), at four partial-render counts PR set by
`dbg:render_pb_pages` (P = thr0 + 0x22): PR 0 (thr0 0x400, above the need), 1 (0x294), 2 (0x1a0) and
4 (0xc0). Counts are r8-ldpm's kept f9 and m6 readings of this scene (E-records of closing r8:
0x60 7, 0x90 6, 0xc0 4, 0x120 3, 0x1a0 2, 0x292..0x296 1, 0x400 0), so a count is a repeat, the
control of this stage's design; two replicates at each count (0, 1, 2, 4), 8 rows in all, run in
two rounds (the second in another order, so no row follows its own count).

FROZEN BEFORE THE RUN. CLR = the number of regtimeline lines with 0x0748 bit 2 clear in a job.
  H-PR-STRICT  the plan's R-PR (E1019): CLR >= PR at every row with PR > 0, and CLR = 0 at PR 0
  H-R-PR, H-R-LEN, H-CONST  E1019's three rivals, in its own form (closing12 c1-q036's score):
       P(a job has a clear line) = 1 - exp(-R_PR PR) | 1 - (1 - Q_LEN)^N | F_CONST, N the job's
       line count, clipped to [0.01, 0.99]; the fit constants are E1019's (fit rows r1 to r3).
       Ranked by the log-loss over the 8 rows; R-PR is ranked first when it has the lowest and
       beats each rival by at least MARGIN nats; else no ranking. All rows are held out (the fit
       constants are r1 to r3's); the kept 3072x2048 jobs of r8-ldpm were read by the builder
       before freezing (post hoc, see README).
  H-COUNT  the count PR (tally): the row's job reads exactly PR partial renders
  H0       0x0710 bits 31:16 = 0 at every line (E1019 held it to G 18)
CONTROLS (can fail): the two PR 0 rows: nparts 0 and CLR 0. A control off stops the stage when its
count is off (ctl:nparts=0, rc 24); a PR 0 row with CLR > 0 fails R-PR's "none at 0" clause and is
the finding.
Readings, no frozen value: the distinct values of 0x0700, 0x070c, 0x0710, 0x0720 to 0x0728 and
0x072c's high half (CR_DPM_3D_PAGE_COUNTS' global page count) at each count."""
from __future__ import annotations

import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent

RT = "0x012c,0x0624-0x0628,0x0658,0x0660,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"
LEAD = "0.3"
TOOL = '"$HOME/sgxfive-test-t10"'
PROG = '"$S/bins/p1139-green.bin"'
D_OFF = 0x22
W, H = 3072, 2048
STAGES = ("pr2",)
# PR -> thr0 (r8-ldpm's kept counts at 3072x2048)
THR0 = {0: 0x400, 1: 0x294, 2: 0x1A0, 4: 0xC0}
ORDER = (0, 1, 2, 4, 1, 0, 4, 2)             # round 1 then round 2 in another order
# E1019's fit constants (closing12 c1-q036 score, fit rows r1 to r3) and the rule's margin
Q_LEN, R_PR, F_CONST = 0.00108, 0.1708, 0.439
CLIP = (0.01, 0.99)
MARGIN = 1.0


def hx(v):
    return f"0x{v:x}"


def names():
    seen, out = {}, []
    for c in ORDER:
        seen[c] = seen.get(c, 0) + 1
        out.append((f"pr2-c{c}-{seen[c]}", c))
    return out


def reads(*keys):
    return "reads:" + ",".join(keys)


def rows():
    out = []
    for n, c in names():
        thr0 = THR0[c]
        words = [f"dbg:render_pb_pages={hx(thr0 + D_OFF)}", "expect:rc3-overflow"]
        if c == 0:
            words += [reads("nparts", "knob", "clr"), "ctl:nparts=0"]
        cmd = (f'0 {LEAD} {RT} -- {TOOL} probe --tri pixel --width {W} --height {H} --vertices 1500 {PROG}')
        out.append(dict(name=n, set="control" if c == 0 else "heldout", risk="safe",
                        knobs=" ".join(words), tool="rt", args=cmd, thr0=thr0, pr=c))
    return out


def tables():
    return {"pr2": rows()}


def thr0_of(r):
    k = r["knobs"] if isinstance(r["knobs"], list) else r["knobs"].split()
    return int(next(x for x in k if x.startswith("dbg:")).split("=")[1], 16) - D_OFF


def pr_of(r):
    return {v: k for k, v in THR0.items()}[thr0_of(r)]


def predictions(st, rs):
    P = []
    src = {"control": "r8-ldpm f9/m6 (PR 0 at 0x400), E1019's 'none at 0'",
           "heldout": "r8-ldpm's kept counts (3072x2048), E1019 (c1-q036) fit constants"}
    for r in rs:
        n, s, c = r["name"], r["set"], r["pr"]
        add = lambda q, v, m, ss=None: P.append((n, q, v, m, ss or s, src[s]))  # noqa: E731
        add("knob", hx(r["thr0"]), "CTL", "control")
        add("nparts", str(c), "H-COUNT")
        if c == 0:
            add("nparts", "0", "CTL", "control")
            add("clr", "0", "CTL", "control")
        else:
            add("clr", f">={c}", "H-PR-STRICT")
        add("hi10", "0", "H0")
        add("p_clear", f"1-exp(-{R_PR}*{c})", "H-R-PR")
        add("p_clear", f"1-(1-{Q_LEN})^N", "H-R-LEN")
        add("p_clear", f"{F_CONST}", "H-CONST")
    return P


HEAD = ("pr2 (8): one scene (3072x2048, 1500 vertices) at partial-render counts 0, 1, 2, 4 (two "
        "replicates each; thr0 0x400, 0x294, 0x1a0, 0xc0): 0x0748 bit 2 clears against the count; "
        "the PR 0 rows are the controls")


def table_text(st, rs):
    out = [f"#stage {st}", "#limit 0", f"# {HEAD}"]
    out += ["|".join((r["name"], r["set"], r["risk"], r["knobs"], r["tool"], r["args"])) for r in rs]
    return "\n".join(out) + "\n"


def extra_knobs(T_):
    return sorted({k for rs in T_.values() for r in rs for k in r["knobs"].split() if k.startswith("ctl:")})


def knob_values(T_):
    vals = {k.split("=", 1)[1] for rs in T_.values() for r in rs for k in r["knobs"].split()
            if k.startswith("dbg:render_pb_pages=")}
    return sorted(vals | {"0x422"}, key=lambda v: int(v, 16))


def outputs():
    T_ = tables()
    files = {}
    for st in STAGES:
        files[f"tables/{st}.txt"] = table_text(st, T_[st])
        files[f"predictions/{st}.tsv"] = "case\tquantity\tvalue\tmodel\tset\tsource\n" + "".join(
            "\t".join(p) + "\n" for p in predictions(st, T_[st]))
    return T_, files


def main(argv):
    T_, files = outputs()
    if argv[1:] == ["--check"]:
        bad = [f for f, t in files.items() if not (KP / f).exists() or (KP / f).read_text() != t]
        print("generator current" if not bad else "differs: " + " ".join(bad))
        return 1 if bad else 0
    for f, t in files.items():
        (KP / f).parent.mkdir(exist_ok=True)
        (KP / f).write_text(t)
    print(sum(len(v) for v in T_.values()), "jobs:", {s: len(v) for s, v in T_.items()})
    print("extra_knobs =", sorted(extra_knobs(T_)))
    print("render_pb_pages values =", knob_values(T_))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
