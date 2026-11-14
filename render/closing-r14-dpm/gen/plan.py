#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r14-dpm's generator (round 14, stage pr3: Q036's 0x0748 bit 2 sampled ALONE, at
controlled partial-render counts; closing14/plan/rank-round14.md r14-dpm). Writes tables/pr3.txt and
predictions/pr3.tsv (10 jobs, t10 under regtimeline over the one register 0x0748, safe class,
`#limit 0`).

  python3 gen/plan.py          write the tables and predictions
  python3 gen/plan.py --check  exit 1 when a written file differs from what it would write

r13-dpm (E1032) sampled 16 registers (period 7.5 us) and saw 1 clear line in 14 partial renders. The
[check] of the plan, resolved on the kept timelines (end / samples over every kept regtimeline job
of resgx545-data): the period is about 0.46 us per register (16 regs 7.5 us, 14 7.5, 8 4.7, 5 4.6,
3 1.4), so ONE register samples about every 0.46 us, 16 times shorter [infer: one register was never
sampled alone before]. Same scene as r13-dpm (3072x2048, 1500 vertices, p1139-green.bin), partial
renders PR set by `dbg:render_pb_pages` (P = thr0 + 0x22): PR 0 (thr0 0x400), 1 (0x294), 4 (0xc0) and
7 (0x60). The plan's PR 8 is replaced by PR 7: the scene has no kept reading of 8 partial renders
(r8-ldpm f9 kept 0x60 -> 7, 0x90 -> 6), and with one register the count cannot be read back (0x0658
is not sampled), so every count must be a repeat of a kept one. PR is the row's label (the knob), not
a reading; the knob proof is the job's rc (0 at PR 0, 3 with the overflow line otherwise).

FROZEN BEFORE THE RUN. CLR = the lines from the command's start on with 0x0748 bit 2 clear, PULSES =
the runs of such lines (score/read.py).
  R-PULSE  the plan's: at least one clear event per partial render once the period is short:
           PULSES >= PR at every row with PR > 0 (strict; reported as held only if 8 of 8)
  R-RARE   a clear is rare, Poisson with LAMBDA per partial render whatever the period (E1032's 0.07
           and E1019's 0.17 bracket it; LAMBDA is their geometric mean, 0.109): P(a job has a clear)
           = 1 - exp(-LAMBDA PR), clipped; the total PULSES over the 8 PR > 0 rows (35 partial renders)
           lies in the central 95% Poisson interval of LAMBDA x 35 (frozen as TOTAL_LO..TOTAL_HI)
  R-CONST  P(a job has a clear) = 0.439 (E1019's constant)
  Ranking  per-job log-loss over the 10 rows, P(clear) clipped to [0.01, 0.99]; R-PULSE's is 0.99 at
           PR > 0 and 0.01 at PR 0; the strict form is a verdict of its own; R-RARE is RANKED FIRST
           when its log-loss is the lowest and each rival's is at least MARGIN nats above, else NO
           RANKING.
CONTROLS (can fail): the two PR 0 rows: CLR 0 (a clear at PR 0 refutes "none at 0" and gates every
verdict) and `short` = 1 (the period is at most 1000 ns: without it R-PULSE is not tested; a control
whose period is long stops the stage, hook_check rc 24). Each job's knob proof is its rc."""
from __future__ import annotations

import math
import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent

RT = "0x0748"
LEAD = "0.3"
TOOL = '"$HOME/sgxfive-test-t10"'
PROG = '"$S/bins/p1139-green.bin"'
D_OFF = 0x22
W, H = 3072, 2048
STAGES = ("pr3",)
# PR -> thr0 (r8-ldpm's kept counts at 3072x2048: 0x400 0, 0x294 1, 0xc0 4, 0x60 7)
THR0 = {0: 0x400, 1: 0x294, 4: 0xC0, 7: 0x60}
ORDER = (0, 1, 4, 7, 1, 0, 7, 4, 7, 4)       # no row follows its own count
LAMBDA, F_CONST = 0.109, 0.439
CLIP = (0.01, 0.99)
MARGIN = 1.0
SHORT_NS = 1000


def hx(v):
    return f"0x{v:x}"


def pois_interval(mean, tail=0.025):
    """(lo, hi): the smallest k with cdf(k) >= tail and the smallest k with cdf(k) >= 1 - tail."""
    cdf, k, lo, hi = 0.0, 0, None, None
    while hi is None:
        cdf += math.exp(-mean) * mean ** k / math.factorial(k)
        if lo is None and cdf >= tail:
            lo = k
        if cdf >= 1 - tail:
            hi = k
        k += 1
    return lo, hi


TOTAL_PR = sum(c for c in ORDER)
TOTAL_LO, TOTAL_HI = pois_interval(LAMBDA * TOTAL_PR)


def names():
    seen, out = {}, []
    for c in ORDER:
        seen[c] = seen.get(c, 0) + 1
        out.append((f"pr3-c{c}-{seen[c]}", c))
    return out


def reads(*keys):
    return "reads:" + ",".join(keys)


def rows():
    out = []
    for n, c in names():
        thr0 = THR0[c]
        words = [f"dbg:render_pb_pages={hx(thr0 + D_OFF)}", "expect:rc3-overflow"]
        if c == 0:
            words += [reads("clr", "short"), "ctl:short=1"]
        cmd = (f'0 {LEAD} {RT} -- {TOOL} probe --tri pixel --width {W} --height {H} --vertices 1500 {PROG}')
        out.append(dict(name=n, set="control" if c == 0 else "heldout", risk="safe",
                        knobs=" ".join(words), tool="rt", args=cmd, thr0=thr0, pr=c))
    return out


def tables():
    return {"pr3": rows()}


def thr0_of(r):
    k = r["knobs"] if isinstance(r["knobs"], list) else r["knobs"].split()
    return int(next(x for x in k if x.startswith("dbg:")).split("=")[1], 16) - D_OFF


def pr_of(r):
    return {v: k for k, v in THR0.items()}[thr0_of(r)]


def predictions(st, rs):
    P = []
    src = {"control": "r8-ldpm f9/m6 (PR 0 at 0x400), E1032's 'none at 0'; the period from the kept timelines",
           "heldout": "r8-ldpm's kept counts (3072x2048), E1019 and E1032's rates"}
    first = next(r["name"] for r in rs if r["set"] == "heldout")
    for r in rs:
        n, s, c = r["name"], r["set"], r["pr"]
        add = lambda q, v, m: P.append((n, q, v, m, s, src[s]))  # noqa: E731
        add("rc", "0" if c == 0 else "3", "CTL")
        if c == 0:
            add("clr", "0", "CTL")
            add("short", "1", "CTL")
        else:
            add("pulses", f">={c}", "R-PULSE")
            add("pulses_mean", f"{LAMBDA}*{c}", "R-RARE")
        add("p_clear", "0.99" if c else "0.01", "R-PULSE")
        add("p_clear", f"1-exp(-{LAMBDA}*{c})", "R-RARE")
        add("p_clear", f"{F_CONST}", "R-CONST")
        if n == first:
            add("total_pulses", f"{TOTAL_LO}-{TOTAL_HI}", "R-RARE")
    return P


HEAD = ("pr3 (10): one scene (3072x2048, 1500 vertices) at partial-render counts 0, 1, 4, 7 (2, 2, 3, 3 "
        "rows; thr0 0x400, 0x294, 0xc0, 0x60), 0x0748 sampled alone (about 0.46 us a sample against "
        "7.5 us in r13-dpm): clear events against the count; the PR 0 rows are the controls")


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
    print("total PR", TOTAL_PR, "total pulses interval", TOTAL_LO, TOTAL_HI)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
