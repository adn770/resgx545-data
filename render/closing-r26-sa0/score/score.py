#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r26-sa0's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 95445c7de9fd, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Every row is a `probe --coords` fill (t24) that prints `probe NAME: o0 ...` and one `probe NAME:
scratch +0xOFF 0xVALUE` line for each scratch dword it changed (at most 32). Dword k (+4k) is the
value stored for pair k. A model's frozen prediction (predictions/STAGE.tsv):
  dwords  H-E521 / H-ZX / H-SX: the eight dwords `OFFSET=VALUE`. A model holds on a row when every
          dword reads its value and no dword outside the eight changed; FAILED otherwise.
  mix     H-MIX (E1061's sa0 reading): the eight values of H-ZX as a set. Holds when every one of
          the eight dwords reads a value of the set, at least one is not its own pair's (that
          row would be H-ZX) and no dword outside the eight changed.
A row with no o0 line, a failed job or more than 32 changed dwords is cannot tell. Controls: c-e521
passes on H-E521, c-one-r10 on H-ZX (8 of 8). Retirement rule (R26-3 a): H-ZX holds on all six
held-out rows of stage us (its SUMMARY line); each ROW line says which dwords differ from H-ZX.

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what
verdicts() reads; producible(row) is the set of reading keys a row's job can produce."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"uc": BASE, "us": BASE}
GATES = {"us": "uc"}
CONTROL_MODEL = {"c-e521": "H-E521", "c-one-r10": "H-ZX"}
SCR = re.compile(r"^probe (\S+): scratch \+0x([0-9a-f]+) 0x([0-9a-f]{8})$", re.M)


def producible(row):
    a = row["args"].split()
    return {"scratch"} if a[:1] == ["probe"] and "--tri" not in a else set()


def fill(off):
    return 0xD0000000 | off // 4


def parse_pred(v):
    return {int(k, 16): int(x, 16) for k, x in (p.split("=") for p in v.split(","))}


def readback(text, name):
    """(dwords {offset: value}, problem): the scratch dwords a probe printed, or None and why."""
    text = text or ""
    if re.search(rf"^probe {re.escape(name)}: failed", text, re.M):
        return None, "the job failed"
    if not re.search(rf"^probe {re.escape(name)}: o0 ", text, re.M):
        return None, "no o0 line"
    if re.search(rf"^probe {re.escape(name)}: scratch \d+ more changed", text, re.M):
        return None, "more than 32 dwords changed"
    return {int(m.group(2), 16): int(m.group(3), 16) for m in SCR.finditer(text)
            if m.group(1) == name}, ""


def read_files(stage, d):
    verdicts(stage, d)


def exact(pred, got, named):
    extra = sorted(set(got) - named)
    bad = [k for k in sorted(pred) if got.get(k, fill(k)) != pred[k]]
    if extra:
        return False, "changed outside the eight: " + ", ".join("+0x%03x" % k for k in extra)
    return not bad, f"{len(pred) - len(bad)}/{len(pred)} dwords"


def mixed(values, zxp, got, named):
    """H-MIX: every dword of the eight a value of the set, one not its own pair's."""
    extra = sorted(set(got) - named)
    vals = {k: got.get(k, fill(k)) for k in named}
    inset = [k for k in sorted(vals) if vals[k] in values]
    own = [k for k in sorted(vals) if vals[k] == zxp.get(k)]
    if extra:
        return False, "changed outside the eight: " + ", ".join("+0x%03x" % k for k in extra)
    ok = len(inset) == len(vals) and len(own) < len(vals)
    return ok, f"{len(inset)}/{len(vals)} dwords a pair's value, {len(vals) - len(own)} not their own"


def verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    controls, per_model, lines = {}, {}, []
    for r in K.table(KP, stage):
        n = r["name"]
        p = preds.get(n, {})
        dw = {m: parse_pred(v) for m, v in p.get("dwords", {}).items()}
        zxp = dw.get("H-ZX", {})
        named = {k for v in dw.values() for k in v}
        if n in cases and K.completed(cases[n]):
            got, why = readback(K.text(d, n + ".txt"), n)
        else:
            got, why = None, "the job did not complete" if n in cases else "not run"
        res = {}
        if got is None:
            res = {m: (None, why) for m in list(dw) + list(p.get("mix", {}))}
            desc = why
        else:
            for m, v in dw.items():
                res[m] = exact(v, got, named)
            for m, v in p.get("mix", {}).items():
                res[m] = mixed({int(x, 16) for x in v.split(",")}, zxp, got, named)
            desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items())
            off = [k for k in sorted(zxp) if got.get(k, fill(k)) != zxp[k]]
            if off:
                desc += "; read " + ", ".join("+0x%03x=0x%08x" % (k, got.get(k, fill(k)))
                                              for k in off)
        if r["set"] == "control":
            st = res[CONTROL_MODEL[n]][0]
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        held = [m for m, (s, _) in res.items() if s]
        verdict = f"held {', '.join(held)}" if held else (
            "no frozen model exact" if got is not None else "cannot tell")
        lines.append(f"ROW {n} ({r['set']}): {desc}: {verdict}")
        for m, (s, _) in res.items():
            per_model.setdefault(f"dwords {m} ({r['set']})", []).append(s)
    return controls, per_model, lines


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        for root in argv[3:]:
            dd = os.path.join(root, dep)
            if os.path.isdir(dd):
                g = SK.gate(verdicts(dep, dd)[0])
                print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
                return 0 if g.ok else 1
        print(f"gate {argv[2]}: {dep} has not run")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        for m, states in sorted(per_model.items()):
            h = SK.headline(m, controls or {"(gate)": True}, states)
            print("SUMMARY: " + argv[1] + ": " + (h if h.startswith(m) else f"{m}: {h}"))
        if not per_model:
            print("SUMMARY: " + argv[1] + ": " + SK.headline("no model", controls, []))
        elif not controls:
            print("SUMMARY: " + argv[1] + ": controls are stage uc's (the gate)")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
