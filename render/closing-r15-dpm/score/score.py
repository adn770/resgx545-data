#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r15-dpm's frozen scorer (stage pr4). Every verdict rule comes from kit/scorekit.py, the
kept files are read through kit/kitscore.py (byte copies of resgx545 158bdc5455b2, pinned in
FROZEN.commits) and one job's output through score/read.py.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW and READING lines, MODEL tallies, SUMMARY
  score.py gate STAGE ROOTS...         exit 0 (one stage, no gate)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A row is scored only when its job completed (kitscore.completed) and its knob proof holds (its rc:
0 at PR 0, 3 at PR > 0, the overflow's; 0x0624 is not sampled in this session); otherwise it is
cannot tell. PR is the row's label (the knob), not a reading.

  controls   the PR 0 rows (thr0 0x400): CLR 0 (0x0748 bit 2 clear lines) and short 1 (the sampling
             period at most 2000 ns). A PR 0 row with CLR > 0 is FAILED: "none at 0" is refuted and
             the gate shuts every verdict; a long period is FAILED: R-PULSE is not tested.
  rows       R-PULSE (PULSES >= PR at every row with PR > 0, the plan's form), R-RARE-TOTAL (the
             total PULSES over the PR > 0 rows lies in the frozen Poisson interval)
  decision   the strict form (R-PULSE held only if all 8 rows hold it) and the ranking by per-job
             log-loss over the 10 rows (p_clear of the predictions): R-RARE is RANKED FIRST when its
             log-loss is the lowest and each rival's is at least MARGIN above, else NO RANKING.

REQUIRED: the files the stage reads; read_files(STAGE, DIR) reads exactly those; producible(row) is
the set of reading keys the row's job can produce (score/read.py's words)."""
import collections
import math
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import read as R  # noqa: E402
import plan as PL  # noqa: E402

STAGES = PL.STAGES
BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {s: BASE for s in STAGES}
GATES = {}
MODELS = ("R-PULSE", "R-RARE-TOTAL")


def producible(row):
    """Every job reads clr, pulses, period and short (score/read.py words)."""
    return {"clr", "pulses", "period", "short"}


def readings(stage, d):
    cases = K.rows(d, "cases.tsv")
    out = {}
    for r in K.table(KP, stage):
        n = r["name"]
        c = cases.get(n)
        if c is None or not K.completed(c):
            out[n] = None
            continue
        rd = R.reading(K.text(d, n + ".txt"))
        want_rc = 0 if PL.pr_of(r) == 0 else 3
        if rd.get("void") or c["rc"] != want_rc:
            out[n] = None
            continue
        out[n] = rd
    return out


def holds(want, got):
    """Whether the reading `got` is the frozen value `want` (an int, or ">=N"); None when unread."""
    if got is None:
        return None
    if want.startswith(">="):
        return got >= int(want[2:])
    return got == int(want)


def frozen_constants(preds):
    """(LAMBDA, F_CONST) as frozen in the predictions' p_clear rows, parsed."""
    by = next(p for p in preds.values() if "p_clear" in p and "R-RARE" in p["p_clear"])["p_clear"]
    lam = float(re.fullmatch(r"1-exp\(-([0-9.]+)\*\d+\)", by["R-RARE"]).group(1))
    return lam, float(by["R-CONST"])


def frozen_total(preds):
    for p in preds.values():
        if "total_pulses" in p:
            lo, hi = p["total_pulses"]["R-RARE"].split("-")
            return int(lo), int(hi)
    return None


def logloss(ps, ys):
    lo, hi = PL.CLIP
    return -sum(math.log(min(hi, max(lo, p)) if y else 1 - min(hi, max(lo, p))) for p, y in zip(ps, ys))


def ranking(rows, rds, preds):
    """({model: log-loss}, verdict) over the rows; None without every row read."""
    lam, f_const = frozen_constants(preds)
    if any(rds[r["name"]] is None for r in rows):
        return None, "cannot tell"
    ys = [rds[r["name"]]["clr"] > 0 for r in rows]
    prs = [PL.pr_of(r) for r in rows]
    ll = {"R-PULSE": logloss([0.99 if p else 0.01 for p in prs], ys),
          "R-RARE": logloss([1 - math.exp(-lam * p) for p in prs], ys),
          "R-CONST": logloss([f_const] * len(rows), ys)}
    best = min(ll, key=ll.get)
    others = [v for k, v in ll.items() if k != "R-RARE"]
    if best == "R-RARE" and all(v - ll["R-RARE"] >= PL.MARGIN for v in others):
        return ll, "R-RARE RANKED FIRST"
    return ll, "NO RANKING"


def verdicts(stage, d):
    rows = K.table(KP, stage)
    preds = K.predictions(KP, stage)
    rds = readings(stage, d)
    controls, lines = {}, []
    for r in rows:
        if r["set"] != "control":
            continue
        n, rd = r["name"], rds[r["name"]]
        want = {q: by["CTL"] for q, by in preds[n].items() if "CTL" in by and q != "rc"}
        st = None if rd is None else all(holds(v, rd[q]) for q, v in want.items())
        controls[n] = st
        lines.append(f"CONTROL {n}: " + ("cannot tell" if rd is None else
                     f"clr {rd['clr']} pulses {rd['pulses']} period {rd['period']} ns short {rd['short']} "
                     f"(frozen clr 0, short 1): " + ("PASS" if st else "FAILED")))
    g = SK.gate(controls)
    tallies = collections.defaultdict(list)
    total, unread = 0, False
    for r in rows:
        n, rd = r["name"], rds[r["name"]]
        if r["set"] == "control":
            continue
        want = preds[n]["pulses"]["R-PULSE"]
        got = None if rd is None else rd["pulses"]
        st = holds(want, got)
        st = st if g.ok else None
        tallies["R-PULSE"].append(st)
        lines.append(f"ROW {n} [R-PULSE, heldout]: "
                     f"{'held' if st else 'FAILED' if st is False else 'cannot tell'}: pulses {got} "
                     f"(frozen {want}; PR {PL.pr_of(r)}, clr {None if rd is None else rd['clr']})")
        unread |= rd is None
        total += 0 if rd is None else rd["pulses"]
    tot = frozen_total(preds)
    if tot:
        st = None if unread or not g.ok else tot[0] <= total <= tot[1]
        tallies["R-RARE-TOTAL"].append(st)
        lines.append(f"ROW all [R-RARE-TOTAL, heldout]: "
                     f"{'held' if st else 'FAILED' if st is False else 'cannot tell'}: total pulses "
                     f"{total} (frozen {tot[0]}-{tot[1]})")
    for r in rows:
        rd = rds[r["name"]]
        if rd is None:
            lines.append(f"READING {r['name']}: none")
            continue
        w = sorted(rd["widths"])
        lines.append(f"READING {r['name']}: PR {PL.pr_of(r)} lines {rd['n']} clr {rd['clr']} pulses "
                     f"{rd['pulses']} period {rd['period']} ns widths(ns) "
                     + (",".join(str(x) for x in w[:8]) if w else "-"))
    ll, rank = ranking(rows, rds, preds) if g.ok else (None, "cannot tell (a control did not pass)")
    return controls, lines, dict(tallies), ll, rank


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, lines, tallies, ll, rank = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        for mdl, states in tallies.items():
            print(f"MODEL {mdl}: {SK.tally(states)}")
        if ll:
            print("MODEL log-loss: " + ", ".join(f"{k} {v:.2f}" for k, v in ll.items()))
        print("SUMMARY: pr4: " + SK.headline("the PR 0 rows read no bit 2 clear and a short sampling period",
                                             controls, [True] if controls else []))
        for mdl in MODELS:
            if mdl in tallies:
                print(f"SUMMARY: pr4: {mdl}: " + SK.headline(f"{mdl} holds", controls, tallies[mdl]))
        strict = tallies.get("R-PULSE", [])
        word = ("R-PULSE HOLDS" if strict and all(st is True for st in strict) else
                "R-PULSE FAILS" if any(st is False for st in strict) else "cannot tell")
        print(f"SUMMARY: pr4: DECISION: {word} (a clear event per partial render at the short period, "
              f"{SK.tally(strict)}); ranking: {rank}")
        return 0
    print(__doc__)
    return 2


def read_files(stage, d):
    """Exactly the files score() reads in the kept directory."""
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.text(d, "readings.tsv")
    for n in cases:
        K.text(d, n + ".txt")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
