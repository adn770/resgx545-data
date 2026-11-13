#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r10-dpm's frozen scorer (r9-ldpm's, cut to one stage). Every verdict rule comes from
kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of resgx545 9849dab,
pinned in FROZEN.commits) and one job's output through score/read.py (r9-ldpm's reader).

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL and ROW lines, TARGET lines, MODEL tallies, SUMMARY
  score.py gate STAGE ROOTS...         exit 0 (one stage, no gate)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A row is scored only when its job completed (kitscore.completed: rc 0, or the rc 3 overflow of an
`expect:rc3-overflow` row) and its knob proof holds (0x0624 read = the row's thr0); otherwise it
is cannot tell.

  controls   a0-cal-2048 and a0-cal-2048f (r9-ldpm's a0 pair, E935): every CTL value and the replay's
             steps (H-STEPMODEL) inside the bracket the job read. A control off stops the stage on
             the laptop (rc 24) and gates every verdict here.
  rows       the 15 replicates: S6 (the single value E962 quoted, max(pp, p - 1), `rd["S"][6]`; the
             control's `s6` is the bracket) against H-BIAS (R + 1 .. R + 2), H-BIAS-SAME (the kept
             read), H-REPLAY6 (R); the need and nparts against H-REPLAY (tally)
  targets    the frozen rivals, per target over its 3 replicates (S6_range of the predictions):
             NOISE  R in [min, max] and max - min <= 2; BIAS  every replicate in R + 1 .. R + 2;
             otherwise NEITHER; a missing S6 makes the target cannot tell
  decision   at least 4 of 5 targets NOISE and at most 1 BIAS: NOISE decided; at least 4 BIAS and
             at most 1 NOISE: BIAS decided; else MIXED; only with both controls passed

REQUIRED: the files the stage reads; read_files(STAGE, DIR) reads exactly those; producible(row) is
the set of reading keys the row's job can produce (score/read.py's words)."""
import collections
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
PASS_MODELS = ("CTL", "H-STEPMODEL")
ROW_MODELS = ("H-BIAS", "H-BIAS-SAME", "H-REPLAY6", "H-REPLAY")
NEED_DECIDED = 4                                   # targets of 5 the decision needs
NEED_OTHER = 1                                     # targets of the rival class it allows


def producible(row):
    """The reading keys of the row's job: every job reads knob, nparts, gmax and runpeaks; a probe
    job its steps below min(thr0, U) and mono; a completed job (thr0 >= U) its need; one with a
    partial render gps_abort, gps_left and gps_next."""
    keys = {"knob", "nparts", "gmax", "runpeaks"}
    w, h = PL.target(dict(args=row["args"]))
    thr0 = PL.thr0_of(row)
    S, A, U, _ = PL.model(w, h)
    keys |= {f"s{k}" for k, v in S.items() if v < min(thr0, U)} | {"mono"}
    keys |= {"need"} if thr0 >= U else {"gps_abort", "gps_left", "gps_next"}
    return keys


# ---- reading ------------------------------------------------------------------------------------
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


def value(rd, q):
    if rd is None:
        return None
    if q == "S6":
        return rd["S"].get(6)
    if q.startswith("s") and q[1:].isdigit():
        return rd["iv"].get(int(q[1:]))             # the step bracket
    v = rd.get(q)
    if v is None:
        return None
    return str(int(v)) if isinstance(v, bool) else v


def parse_range(want):
    if ".." in want:
        a, b = want.split("..")
        return int(a, 16), int(b, 16)
    return int(want, 16), int(want, 16)


def holds(got, want):
    if got is None:
        return None
    if isinstance(got, tuple):                      # a step bracket (a, max(a, b - 1))
        return got[0] <= int(want, 16) <= got[1]
    if isinstance(got, int):
        lo, hi = parse_range(want) if want.startswith("0x") else (int(want), int(want))
        return lo <= got <= hi
    return str(got) == want


def shown(got):
    return ("[0x%x, 0x%x]" % got if isinstance(got, tuple) else
            f"0x{got:x}" if isinstance(got, int) else got)


# ---- the frozen rivals, per target ------------------------------------------------------------
def classify(vals, Rv, span=PL.SPAN, bias=PL.BIAS):
    """(class, noise state, bias state) of one target's replicates' S_6 reads against the replay Rv.
    A missing read (None) makes both states cannot tell (None)."""
    if not vals or any(v is None for v in vals):
        return "cannot tell", None, None
    noise = min(vals) <= Rv <= max(vals) and max(vals) - min(vals) <= span
    biased = all(Rv + bias[0] <= v <= Rv + bias[1] for v in vals)
    return ("NOISE" if noise else "BIAS" if biased else "NEITHER"), noise, biased


def decision(classes):
    """The frozen rule over the targets' classes."""
    n, b = classes.count("NOISE"), classes.count("BIAS")
    if len(classes) != len(PL.TARGETS) or "cannot tell" in classes:
        return "cannot tell"
    if n >= NEED_DECIDED and b <= NEED_OTHER:
        return "NOISE decided"
    if b >= NEED_DECIDED and n <= NEED_OTHER:
        return "BIAS decided"
    return "MIXED"


def frozen_target(preds, w, h):
    """The frozen H-NOISE and H-BIAS target forms of the predictions (the first replicate's rows),
    parsed, so that the scorer judges by what was frozen."""
    p = preds[f"s6r-{PL.tag(w, h)}-1"]["S6_range"]
    m = re.fullmatch(r"contains=(0x[0-9a-f]+);span<=(\d+)", p["H-NOISE"])
    Rv, span = int(m.group(1), 16), int(m.group(2))
    lo, hi = parse_range(re.fullmatch(r"all=(.*)", p["H-BIAS"]).group(1))
    return Rv, span, (lo - Rv, hi - Rv)


# ---- controls ---------------------------------------------------------------------------------
def control_states(rds, preds, rows):
    out, lines = {}, []
    for r in rows:
        if r["set"] != "control":
            continue
        n, rd = r["name"], rds[r["name"]]
        st, why = True, []
        for q, by in preds.get(n, {}).items():
            for mdl, v in by.items():
                if mdl not in PASS_MODELS:
                    continue
                h = holds(value(rd, q), v)
                if h is not True:
                    why.append(f"{q} {shown(value(rd, q))} (frozen {v})")
                    st = None if h is None and st is not False else False if h is False else st
        if rd is None:
            st = None
        out[n] = st
        lines.append(f"CONTROL {n}: {'PASS' if st else 'FAILED' if st is False else 'cannot tell'}"
                     + (": " + "; ".join(why) if why else ""))
    return out, lines


def verdicts(stage, d):
    rows = K.table(KP, stage)
    preds = K.predictions(KP, stage)
    rds = readings(stage, d)
    controls, lines = control_states(rds, preds, rows)
    g = SK.gate(controls)
    res = collections.defaultdict(list)
    for r in rows:
        if r["set"] != "heldout":
            continue
        for q, by in preds.get(r["name"], {}).items():
            for mdl, v in by.items():
                if mdl not in ROW_MODELS:
                    continue
                got = value(rds[r["name"]], q)
                st = holds(got, v) if q in ("S6", "nparts", "need") else None
                if q == "need":
                    st = None if got is None else got == int(v, 16)
                res[mdl].append((r, st if g.ok else None, f"{q} {shown(got)} (frozen {v})"))
    tallies = {}
    for mdl, items in sorted(res.items()):
        for r, st, det in items:
            lines.append(f"ROW {r['name']} [{mdl}, heldout]: "
                         f"{'held' if st else 'FAILED' if st is False else 'cannot tell'}: {det}")
        tallies[mdl] = [st for _, st, _ in items]
    # the targets: the frozen rivals over the three replicates
    classes, noise, bias = [], [], []
    for w, h in PL.TARGETS:
        Rv, span, bs = frozen_target(preds, w, h)
        vals = [value(rds[f"s6r-{PL.tag(w, h)}-{k}"], "S6") for k in range(1, PL.REPS + 1)]
        cls, nz, bi = classify(vals, Rv, span, bs)
        if not g.ok:
            nz = bi = None
        classes.append(cls)
        noise.append(nz)
        bias.append(bi)
        shown_vals = ",".join("-" if v is None else f"0x{v:x}" for v in vals)
        lines.append(f"TARGET {w}x{h} (replay S_6 0x{Rv:x}, kept 0x{PL.KEPT[(w, h)]:x}): replicates "
                     f"{shown_vals}: {cls}")
    tallies["H-NOISE"], tallies["H-BIAS"] = noise, bias
    return controls, lines, tallies, classes


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, lines, tallies, classes = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        for mdl, states in tallies.items():
            print(f"MODEL {mdl}: {SK.tally(states)}")
        print("SUMMARY: s6rep: " + SK.headline("the premise held (the a0 pair repeats E935 on B60AB0B4)",
                                               controls, [True] if controls else []))
        for mdl in ("H-NOISE", "H-BIAS"):
            print(f"SUMMARY: s6rep: {mdl}: " + SK.headline(f"{mdl} holds at the target", controls, tallies[mdl]))
        dec = decision(classes) if SK.gate(controls).ok else "cannot tell (a control did not pass)"
        print(f"SUMMARY: s6rep: DECISION: {dec}; classes " + ", ".join(
            f"{w}x{h} {c}" for (w, h), c in zip(PL.TARGETS, classes)))
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
