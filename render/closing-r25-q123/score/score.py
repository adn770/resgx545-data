#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r25-q123's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 7f214e511d6a, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage is gated: GATES is empty)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

What each stage reads (t22's probe output, kept as NAME.txt):
  `probe NAME: o0 0xV (2048 of 2048)`          a uniform o0; `o0 mixed` is no single value
  `probe NAME: placed words read back: K of N`  the placed program as built (premise: a row whose
      placed words are not N of N is cannot tell in every model)

Models (predictions/STAGE.tsv): q123s H-STEP80000 against H-STEP20000, H-STEP40000,
H-STEP100000 and H-NOSTEP (o0 = the link (X mod step) / 8 + 2, 18 bits, read and jump alike; the
controls at 0x300008 frozen H-STEP80000 only); q123w H-INDEX (o0 = 0xb0000000 | the target word)
against H-WRAP256 (0xc0de0000 | target & 0xff), the control H-INDEX only.

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what
verdicts() reads; producible(row) is the set of reading keys a row's job can produce."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {s: (".txt",) + FIXED for s in ("q123s", "q123w")}
GATES = {}
CONTROL_MODEL = {"q123s": "H-STEP80000", "q123w": "H-INDEX"}


def producible(row):
    a = row["args"].split()
    if a[:1] == ["probe"]:
        return {"o0"} | ({"placed"} if "--place" in a else set())
    return set()


_O0 = re.compile(r"^probe \S+: o0 0x([0-9a-f]{8}) \((\d+) of (\d+)\)$")
_PLACED = re.compile(r"^probe \S+: placed words read back: (\d+) of (\d+) as built")


def o0(text):
    for m in map(_O0.match, text.splitlines()):
        if m and m[2] == m[3]:
            return int(m[1], 16)
    return None


def placed(text):
    for m in map(_PLACED.match, text.splitlines()):
        if m:
            return f"{m[1]}/{m[2]}"
    return None


def _st(v):
    return "held" if v is True else "FAILED" if v is False else "cannot tell"


def verdicts(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    preds = K.predictions(KP, stage)
    controls, per_model, lines = {}, {}, []
    for row in K.table(KP, stage):
        n = row["name"]
        r = cases.get(n)
        t = K.text(d, n + ".txt") if r is not None and K.completed(r) else ""
        v, pl = (o0(t), placed(t)) if t else (None, None)
        models = dict(preds.get(n, {}).get("o0", {}))
        want_pl = preds.get(n, {}).get("placed", {}).get("H-PLACED")
        ok_pl = pl is not None and pl == want_pl
        shown = "None" if v is None else f"0x{v:08x}"
        if row["set"] == "control":
            want = models[CONTROL_MODEL[stage]]
            controls[n] = None if v is None or pl is None else (ok_pl and f"0x{v:08x}" == want)
            lines.append(f"CONTROL {n}: o0 {shown} (frozen {want}), placed {pl}: "
                         f"{'PASS' if controls[n] else _st(controls[n])}")
            continue
        for m, want in sorted(models.items()):
            s = None if v is None or not ok_pl else f"0x{v:08x}" == want
            per_model.setdefault(m, []).append(s)
            lines.append(f"ROW {n} {m}: {_st(s)} (o0 {shown}, frozen {want}, placed {pl})")
    return controls, per_model, lines


def read_files(stage, d):
    verdicts(stage, d)


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        if GATES.get(argv[2]) is None:
            return 0
        print(f"gate {argv[2]}: not gated")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        g = SK.gate(controls)
        print("SUMMARY: " + argv[1] + ": controls " +
              ("all passed" if g.ok else "; ".join(g.problems)))
        for m, states in sorted(per_model.items()):
            h = SK.headline(m, controls, states)
            print("SUMMARY: " + argv[1] + ": " + (h if h.startswith(m) else f"{m}: {h}"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
