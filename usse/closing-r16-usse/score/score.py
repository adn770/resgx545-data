#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r16-usse's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 b2b5288c82ed, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Every row is a fill probe (`probe --temps 32 FILE`) that prints `probe NAME: o0 ...` and one
`probe NAME: scratch +0xOFF 0xVALUE` line for each scratch dword the program changed (at most
32; `scratch N more changed` past them). A model's frozen prediction (predictions/STAGE.tsv) is
the dwords it changes, `OFFSET=VALUE` joined by commas, for one quantity of the row (uadd:
dwords, urpt the same; utest: tests, the packed test bits, and values, the operation's value). A model holds on
a row when every dword it names reads its value (a dword not printed reads its fill, 0xd0000000 |
i) and the program changed no dword outside those the row's models name; it FAILED when one
differs; cannot tell when the job did not complete, printed no o0 line, or printed past 32 dwords.
A control (reads:scratch) PASSES when its kept-table model (H-E521, H-E498, H-E499, H-E529) holds.
One SUMMARY line per quantity, model and set (scorekit.headline over that model's rows), gated by
every control of the stage. Each ROW line also lists the dwords that differ from H-RULE (utest)
or H-ZX (uadd; H-ZX-ADV urpt), so a failed row says where.

REQUIRED: the files each stage's scorer reads (the runner and sessioncheck.py kept check them);
read_files(STAGE, DIR) reads exactly what score() reads; producible(row) is the set of reading
keys a row's job can produce (the freeze refuses a control that reads anything else)."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"uadd": BASE, "utest": BASE, "urpt": BASE}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none, each has its own
CONTROL_MODEL = {"u-ctl-e521": "H-E521", "u-ctl-rpt": "H-E521", "u-ctl-e498": "H-E498", "t-ctl-and-a": "H-E499",
                 "t-ctl-and-o": "H-E529"}
MAIN = {"uadd": "H-ZX", "utest": "H-RULE", "urpt": "H-ZX-ADV"}
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
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for r in K.table(KP, stage):
        if r["name"] in cases:
            K.text(d, r["name"] + ".txt")


def compare(pred, got, named):
    """(state, description) of one model's dwords against a readback (None: no readback)."""
    if got is None:
        return None, "no readback"
    extra = sorted(set(got) - named)
    bad = [k for k in sorted(pred) if got.get(k, fill(k)) != pred[k]]
    if extra:
        return False, "changed outside the model: " + ", ".join("+0x%03x" % k for k in extra)
    return not bad, f"{len(pred) - len(bad)}/{len(pred)} dwords"


def verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    controls, per_model, lines = {}, {}, []
    for r in K.table(KP, stage):
        n = r["name"]
        want = {q: {m: parse_pred(v) for m, v in ms.items()} for q, ms in preds.get(n, {}).items()}
        named = {k for ms in want.values() for p in ms.values() for k in p}
        if n in cases and K.completed(cases[n]):
            got, why = readback(K.text(d, n + ".txt"), n)
        else:
            got, why = None, "the job did not complete" if n in cases else "not run"
        res = {(q, m): compare(p, got, named) for q, ms in want.items() for m, p in ms.items()}
        desc = "; ".join(f"{q} {m} {t}" for (q, m), (_, t) in res.items())
        if got is None:
            desc = why
        else:
            mm = CONTROL_MODEL.get(n, MAIN[stage])
            main = next((ms[mm] for ms in want.values() if mm in ms), None)
            if main:
                off = [k for k in sorted(main) if got.get(k, fill(k)) != main[k]]
                if off:
                    desc += "; read " + ", ".join("+0x%03x=0x%08x" % (k, got.get(k, fill(k)))
                                                  for k in off)
        if r["set"] == "control":
            m = CONTROL_MODEL[n]
            q = next(q for q, ms in want.items() if m in ms)
            st = res[(q, m)][0]
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        held = [f"{m} ({q})" for (q, m), (s, _) in res.items() if s]
        verdict = f"held {', '.join(held)}" if held else (
            "no frozen model exact" if got is not None else "cannot tell")
        lines.append(f"ROW {n} ({r['set']}): {desc}: {verdict}")
        for (q, m), (s, _) in res.items():
            per_model.setdefault(f"{q} {m} ({r['set']})", []).append(s)
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
            h = SK.headline(m, controls, states)
            print("SUMMARY: " + argv[1] + ": " + (h if h.startswith(m) else f"{m}: {h}"))
        if not per_model:
            print("SUMMARY: " + argv[1] + ": " + SK.headline("no model", controls, []))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
