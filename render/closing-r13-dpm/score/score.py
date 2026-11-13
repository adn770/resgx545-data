#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r13-dpm's frozen scorer (stage pr2). Every verdict rule comes from kit/scorekit.py, the
kept files are read through kit/kitscore.py (byte copies of resgx545 05b7039ee021, pinned in
FROZEN.commits) and one job's output through score/read.py.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW and READING lines, MODEL tallies, SUMMARY
  score.py gate STAGE ROOTS...         exit 0 (one stage, no gate)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A row is scored only when its job completed (kitscore.completed) and its knob proof holds (0x0624
read = the row's thr0); otherwise it is cannot tell.

  controls   the PR 0 rows (thr0 0x400): nparts 0 and CLR 0 (0x0748 bit 2 clear lines). A PR 0 row
             with CLR > 0 is FAILED: R-PR's "none at 0" clause is refuted; it gates every row.
  rows       H-COUNT (each row reads exactly its PR partial renders), H-PR-STRICT (CLR >= PR at every
             row with PR > 0, the plan's form), H0 (0x0710 high half 0 at every line)
  decision   the plan's strict form (H-PR-STRICT at every row with PR > 0) and the ranking, printed
             together; the strict form is reported as held only when all 6 rows hold it
  ranking    E1019's per-job form (c1-q036): p = 1 - exp(-R PR) | 1 - (1 - Q)^N | F, clipped, the
             log-loss over the 8 rows; the constants are the frozen predictions' (p_clear). R-PR is
             RANKED FIRST when its log-loss is the lowest and each rival's is at least MARGIN above;
             else NO RANKING (a small sample). Only with both controls passed.

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
PASS_MODELS = ("CTL",)
MODELS = ("H-COUNT", "H-PR-STRICT", "H0")


def producible(row):
    """Every job reads knob, nparts, clr, pulses and gmax (score/read.py words)."""
    return {"knob", "nparts", "clr", "pulses", "gmax"}


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
        if rd.get("void") or rd.get("knob") != PL.thr0_of(r):
            out[n] = None
            continue
        out[n] = rd
    return out


def holds(q, got, want):
    """Whether the reading `got` of quantity q is the frozen value `want`; None when unread."""
    if got is None:
        return None
    if want.startswith(">="):
        return got >= int(want[2:])
    if q == "knob":
        return got == int(want, 16)
    return got == int(want)


def value(rd, q):
    if rd is None:
        return None
    return {"hi10": rd.get("hi10")}.get(q, rd.get(q))


def frozen_constants(preds):
    """(R_PR, Q_LEN, F_CONST) as frozen in the predictions' p_clear rows, parsed."""
    by = next(p for p in preds.values() if "p_clear" in p)["p_clear"]
    r = float(re.fullmatch(r"1-exp\(-([0-9.]+)\*\d+\)", by["H-R-PR"]).group(1))
    q = float(re.fullmatch(r"1-\(1-([0-9.]+)\)\^N", by["H-R-LEN"]).group(1))
    return r, q, float(by["H-CONST"])


def logloss(ps, ys):
    lo, hi = PL.CLIP
    return -sum(math.log(min(hi, max(lo, p)) if y else 1 - min(hi, max(lo, p))) for p, y in zip(ps, ys))


def ranking(rows, rds, preds):
    """({rival: log-loss}, verdict) over the rows, E1019's per-job form; None without every row read."""
    r_pr, q_len, f_const = frozen_constants(preds)
    if any(rds[r["name"]] is None for r in rows):
        return None, "cannot tell"
    ys = [rds[r["name"]]["clr"] > 0 for r in rows]
    prs = [PL.pr_of(r) for r in rows]
    ns = [rds[r["name"]]["n"] for r in rows]
    ll = {"H-R-PR": logloss([1 - math.exp(-r_pr * p) for p in prs], ys),
          "H-R-LEN": logloss([1 - (1 - q_len) ** n for n in ns], ys),
          "H-CONST": logloss([f_const] * len(rows), ys)}
    best = min(ll, key=ll.get)
    others = [v for k, v in ll.items() if k != "H-R-PR"]
    if best == "H-R-PR" and all(v - ll["H-R-PR"] >= PL.MARGIN for v in others):
        return ll, "R-PR RANKED FIRST"
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
        want = {q: by["CTL"] for q, by in preds[n].items() if "CTL" in by and q != "knob"}
        st = None if rd is None else all(holds(q, rd[q], v) for q, v in want.items())
        controls[n] = st
        lines.append(f"CONTROL {n}: " + ("cannot tell" if rd is None else
                     f"nparts {rd['nparts']} clr {rd['clr']} pulses {rd['pulses']} (frozen 0, 0): "
                     + ("PASS" if st else "FAILED")))
    g = SK.gate(controls)
    tallies = collections.defaultdict(list)
    for r in rows:
        n, rd = r["name"], rds[r["name"]]
        for q, mdl in (("nparts", "H-COUNT"), ("clr", "H-PR-STRICT"), ("hi10", "H0")):
            if mdl not in preds[n].get(q, {}):
                continue
            want = preds[n][q][mdl]
            st = holds(q, value(rd, q), want)
            st = st if g.ok else None
            tallies[mdl].append(st)
            lines.append(f"ROW {n} [{mdl}, {r['set']}]: "
                         f"{'held' if st else 'FAILED' if st is False else 'cannot tell'}: "
                         f"{q} {value(rd, q)} (frozen {want})")
    for r in rows:
        rd = rds[r["name"]]
        if rd is None:
            lines.append(f"READING {r['name']}: none")
            continue
        vs = "; ".join(f"0x{k:04x} " + ",".join(f"0x{x:x}" for x in v[:6]) + ("..." if len(v) > 6 else "")
                       for k, v in rd["vals"].items() if k in (0x700, 0x70C, 0x710, 0x720, 0x728))
        lines.append(f"READING {r['name']}: PR {rd['nparts']} lines {rd['n']} clr {rd['clr']} pulses "
                     f"{rd['pulses']} G {rd['gmax']} hi10 {rd['hi10']}; {vs}")
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
        print("SUMMARY: pr2: " + SK.headline("the PR 0 rows read no partial render and no bit 2 clear",
                                             controls, [True] if controls else []))
        for mdl in ("H-COUNT", "H-PR-STRICT", "H0"):
            if mdl in tallies:
                print(f"SUMMARY: pr2: {mdl}: " + SK.headline(f"{mdl} holds", controls, tallies[mdl]))
        strict = tallies.get("H-PR-STRICT", [])
        word = ("R-PR STRICT HOLDS" if strict and all(st is True for st in strict) else
                "R-PR STRICT FAILS" if any(st is False for st in strict) else "cannot tell")
        print(f"SUMMARY: pr2: DECISION: {word} (the plan's clear per partial render, {SK.tally(strict)}); "
              f"ranking: {rank}")
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
