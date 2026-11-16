#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r34-q010's scorer, frozen before the run. Every verdict rule comes from kit/scorekit.py,
the kept files are read through kit/kitscore.py (byte copies of resgx545 5745c8dc1a8d, pinned in
FROZEN.commits). Standard library only.

  score.py c KEPT_DIR [ROOTS...]   CONTROL, READING, ROW lines, SUMMARY lines, the Q010 RULE (exit 0)
  score.py q010 ROOT               Q010's retire rule alone over the attempt ROOT (ROOT/c)
  score.py gate STAGE ROOTS...     exit 0 (one stage, not gated)
  score.py premise STAGE KEPT_DIR  STOP lines and exit 1 when a control has no reading

Reading of a row: hash, an ok copy's `target: 64x32 hash H` (from its kept text; for a control
also its `job` word, from readings.tsv as the runner's hook_reading wrote it). A row that did not
run, or failed, reads nothing.

Controls (predictions/c.tsv, model H-REF, every key must equal its reading): z0-ld and z0-rd
(a zeros load, then the copy without the load: black 0xd3522437a14b6325), every triple's L
(`*-ld`: a BT.601 load, E037's 0xb6067a95fa98de2d) and T0's R rows t0a-rd and t0b-rd (the copy
without the load after a load and a debugfs reset keeps it: E1097, E1103, E1112's q010-pre). The
in-session references (z0-ld, z0-rd, t0a-rd, t0b-rd) gate every row; each R row is also gated by
its own triple's L. A gated row reads cannot tell.

Hypotheses (frozen, every R row held out): H-FILL, H-TRI, H-BOTH, H-NONE predict all 9 held-out R
rows (CLEARED where their job runs, KEPT elsewhere); H-IDLE (t4-rd, t5-rd CLEARED) and H-COPYNL
(t3a-rd, t3b-rd CLEARED) predict their own rows only; their rivals are the full patterns, which
say KEPT there. A row is held when its hash equals the frozen one, FAILED when it is another of
KEPT and CLEARED, cannot tell for any other hash or no reading.

Q010 RULE (against the question line: "which job clears colour-space set 0 between jobs, given
(a) a copy without the load keeps the set across a debugfs reset, (b) reads zeros after the kit's
health fill and triangle, with no fault or hang and after a recovered hang followed by them, (c)
the first job of a session after hung jobs reads zeros (E271)?"): RETIRE-CAPABLE iff every control
passed, all 9 held-out R rows are decided (KEPT or CLEARED, so the replicates of T1, T2, T3 are
both decided) and exactly one of H-FILL, H-TRI, H-BOTH holds on all 9 (so T3, T4, T5 read KEPT:
H-COPYNL and H-IDLE fail, and every replicate pair agrees). Then the line's question is answered
by held-out rows; (a) is re-read held out on this module (t0a-rd, t0b-rd) and (b)'s health pair
without a fault (t6-rd); (b)'s recovered hangs and (c) are E1112's and E271's readings, which the
answer explains [infer] (each ran the health pair or a recovery before its copy) and which a safe
session cannot re-run: the rule names them for the lead. Any other outcome: narrow only, with the
reason."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGE = "c"
FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {STAGE: (".txt",) + FIXED}
GATES = {}
KEPT_HASH = "0xb6067a95fa98de2d"
CLEARED_HASH = "0xd3522437a14b6325"
WORD = {KEPT_HASH: "KEPT", CLEARED_HASH: "CLEARED"}
REFS = ("z0-ld", "z0-rd", "t0a-rd", "t0b-rd")      # the in-session references: gate every row
FULL = ("H-FILL", "H-TRI", "H-BOTH", "H-NONE")
JOBS = ("H-FILL", "H-TRI", "H-BOTH")               # the hypotheses that name a job
SIDE = ("H-IDLE", "H-COPYNL")
CLAIMS = {
    "H-FILL": "the t10 fill clears colour-space set 0 (T1, T6 CLEARED; T0, T2-T5 KEPT)",
    "H-TRI": "the t10 triangle clears colour-space set 0 (T2, T6 CLEARED; T0, T1, T3-T5 KEPT)",
    "H-BOTH": "the t10 fill and the t10 triangle each clear colour-space set 0 (T1, T2, T6 CLEARED)",
    "H-NONE": "no job of the session clears colour-space set 0 (every R KEPT)",
    "H-IDLE": "a 60 or 120 s idle before the copy clears colour-space set 0 (T4, T5 CLEARED)",
    "H-COPYNL": "a plain copy (no YUV, no load) clears colour-space set 0 (T3 CLEARED)",
}
ANSWER = {
    "H-FILL": "the kit's health fill (t10 `fill`, a library transfer fill) clears set 0; the health "
              "triangle, a plain copy, a debugfs reset and 120 s idle do not",
    "H-TRI": "the kit's health triangle (t10 `tri`, a 3D render) clears set 0; the health fill, a "
             "plain copy, a debugfs reset and 120 s idle do not",
    "H-BOTH": "the kit's health fill and health triangle each clear set 0 alone; a plain copy, a "
              "debugfs reset and 120 s idle do not",
}


def producible(row):
    return {"job", "hash"} if row["args"].split()[:1] == ["copy"] else set()


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")


def hash_of(cases, d, n):
    """An ok row's copy hash, or None (did not run, failed, or no target line)."""
    r = cases.get(n)
    if r is None or not K.completed(r):
        return None
    h = re.search(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", K.text(d, n + ".txt"), re.M)
    return h.group(1) if h else None


def controls(d):
    """{control: True PASS / False FAILED / None cannot tell}, and the CONTROL lines."""
    preds = K.predictions(KP, STAGE)
    cases, rds = K.rows(d, "cases.tsv"), K.readings(d)
    out, lines = {}, []
    for r in K.table(KP, STAGE):
        n = r["name"]
        if r["set"] != "control":
            continue
        want = {q: mv["H-REF"] for q, mv in preds[n].items()}
        c = cases.get(n)
        if c is None or not K.completed(c):
            out[n] = None
            lines.append(f"CONTROL {n}: did not complete ({c['class'] if c else 'not run'}): cannot tell")
            continue
        got = rds.get(n, {})
        bad = {q: got.get(q) for q, v in want.items() if got.get(q) != v}
        out[n] = not bad
        lines.append(f"CONTROL {n}: " + (f"job {got.get('job')}, hash {got.get('hash')} "
                                         f"({WORD.get(got.get('hash'), 'other')})" if not bad else
                                         "differs: " + ", ".join(f"{q} {v} (frozen {want[q]})" for q, v in sorted(bad.items())))
                     + f": {cword(out[n])}")
    return out, lines


def models():
    """{model: {row: frozen hash}} of the held-out rows."""
    out = {}
    for n, qs in K.predictions(KP, STAGE).items():
        for m, v in qs.get("hash", {}).items():
            if m != "H-REF":
                out.setdefault(m, {})[n] = v
    return out


def row_state(frozen, got):
    if got not in WORD:
        return None
    return got == frozen


def score(d):
    """(lines, per-model row states {model: {row: state}}, controls)."""
    ctl, lines = controls(d)
    cases = K.rows(d, "cases.tsv")
    ms = models()
    per = {m: {} for m in ms}
    for r in K.table(KP, STAGE):
        n = r["name"]
        if r["set"] != "heldout":
            continue
        got = hash_of(cases, d, n)
        lines.append(f"READING {n}: hash {got} ({WORD.get(got, 'no reading' if got is None else 'other: cannot tell')})")
        g = SK.gate({k: ctl.get(k) for k in REFS + (n[:-3] + "-ld",)})
        for m in sorted(ms):
            if n not in ms[m]:
                continue
            st = SK.gated(g, row_state(ms[m][n], got))
            per[m][n] = st
            lines.append(f"ROW {n} {m}: (frozen {ms[m][n]} {WORD[ms[m][n]]}): {word(st)}")
    for m in sorted(per):
        lines.append(f"SUMMARY: {STAGE}: {m}: " + SK.headline(CLAIMS[m], ctl, list(per[m].values())))
    return lines, per, ctl


def rule(per, ctl):
    """Q010 RULE (the docstring): RETIRE-CAPABLE with the job, or narrow only with why."""
    npass = sum(1 for v in ctl.values() if v is True)
    head = f"Q010 RULE: controls {npass} of {len(ctl)} passed"
    rows = sorted(per["H-NONE"])
    decided = [n for n in rows if per["H-NONE"][n] is not None]
    head += f"; held-out R rows decided {len(decided)} of {len(rows)}"
    holds = [m for m in FULL if per[m] and all(v is True for v in per[m].values())]
    head += "; full patterns holding on every row: " + (", ".join(holds) or "none")
    for m in SIDE:
        t = SK.tally(per[m].values())
        head += f"; {m} {t}"
    if not all(v is True for v in ctl.values()):
        return [head + ": a control did not pass: narrow only"]
    if len(decided) != len(rows):
        return [head + ": a held-out row is not decided: narrow only"]
    one = [m for m in holds if m in JOBS]
    if len(one) == 1 and len(holds) == 1:
        return [head + f": one job hypothesis, {one[0]}: RETIRE-CAPABLE",
                f"Q010 ANSWER [HW]: {ANSWER[one[0]]} (9 of 9 held-out rows, both replicates, every control)",
                "Q010 GIVENS: (a) re-read held out here (t0a-rd, t0b-rd KEPT after a load and a debugfs "
                "reset); (b)'s pair without a fault re-read (t6-rd CLEARED); (b)'s recovered hangs (E1112) "
                "and (c) (E271) are not re-run (flagged class): explained by the answer [infer], the lead "
                "confirms; the body extras (a recovery without a health job, the power-on state, set 1, "
                "the luma-key words) are not the line's question"]
    if holds == ["H-NONE"]:
        return [head + ": no job, no plain copy and no 120 s idle clears the set within one stage: "
                "narrow only (the stage boundary itself, or a longer idle [infer])"]
    return [head + ": no single job hypothesis holds on every row: narrow only"]


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        print(f"gate {argv[2]}: open (not gated)")
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "q010":
        _, per, ctl = score(os.path.join(argv[2], STAGE))
        print("\n".join(rule(per, ctl)))
        return 0
    if len(argv) >= 3 and argv[1] == STAGE:
        lines, per, ctl = score(argv[2])
        print("\n".join(lines + rule(per, ctl)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
