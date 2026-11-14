#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r19-flag's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 6809cddd24ce, pinned in FROZEN.commits).

  score.py fl KEPT_DIR [ROOTS...]   CONTROL, ROW and SUMMARY lines (exit 0)
  score.py gate fl ROOTS...         open (the stage is not gated: its control row is its first job)
  score.py premise fl KEPT_DIR      STOP lines and exit 1 when a control has no reading

Stage fl (Q045, E1086). The control fl-ctl is read from the runner's premise reading (readings.tsv:
job, ovf, thr, lists) against its frozen values. Each junk row is a vector of two readings: its end
(ok, fault or hang: the kept class) and `same`, 1 when the last `target:` hash of its output equals
fl-ctl's (0 when it differs); a model holds on a row when every quantity it freezes reads as frozen
(an end that is none of ok, fault or hang, or a missing hash on an ok row, cannot tell). A model
holds on the stage when it holds on both junk rows (fl-junk-a, the fit label, and fl-junk-b, its
held-out replicate). The headline names the one model that holds on both, or says why none does.

REQUIRED: the files the scorer reads (the runner and sessioncheck.py kept check them: ".suffix"
for each row that ended ok, "any:.suffix" for each row whatever its end, a plain name once);
read_files(STAGE, DIR) reads exactly what verdicts() reads; producible(row) is the set of reading
keys a row's job can produce (the freeze refuses a control that reads anything else)."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

STAGE = "fl"
CONTROL = "fl-ctl"
JUNK = ("fl-junk-a", "fl-junk-b")
REQUIRED = {STAGE: ("any:.txt", "any:.dmesg", "cases.tsv", "void.tsv", "readings.tsv")}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none, fl is gated by its control
HASH = re.compile(r"^target: \d+x\d+ hash (0x[0-9a-f]+)", re.M)
FAULT = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)")
CLAIMS = {
    "H-NOLOAD": "no task reads the state page's lists: the junk changes nothing (image of the unfilled twin)",
    "H-LOAD-FAULT": "a load task reads the junk lists and the walk faults",
    "H-LOAD-HANG": "a load task reads the junk lists and the job hangs (recovered)",
    "H-LOAD-CORRUPT": "a load task reads the junk lists and the final render's image differs",
}


def producible(row):
    return {"job", "ovf", "thr", "lists"} if row["args"].split()[:1] == ["tri"] else set()


def last_hash(text):
    h = HASH.findall(text)
    return h[-1] if h else None


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")
        K.text(d, n + ".dmesg")


def control_state(d, cases, preds):
    """PASS True / FAILED False / cannot tell None, and its CONTROL line."""
    c = cases.get(CONTROL)
    if c is None or not K.completed(c):
        return None, f"CONTROL {CONTROL}: did not complete ({c['class'] if c else 'not run'}): cannot tell"
    want = {q: mv["H-REF"] for q, mv in preds.get(CONTROL, {}).items()}
    got = K.readings(d).get(CONTROL, {})
    if any(k not in got for k in want):
        return None, f"CONTROL {CONTROL}: reading {got} lacks a frozen key: cannot tell"
    bad = [f"{k} {got[k]} (frozen {v})" for k, v in want.items() if got[k] != v]
    state = not bad
    return state, f"CONTROL {CONTROL}: {got} {'PASS' if state else 'FAILED: ' + '; '.join(bad)}"


def junk_reading(cases, d, n, ctl_hash):
    """{quantity: value} of a kept junk row ({} when it did not run or ended otherwise)."""
    r = cases.get(n)
    if r is None or r["class"] not in ("ok", "fault", "hang"):
        return {}
    out = {"end": r["class"]}
    text = K.text(d, n + ".txt")
    if r["class"] == "ok":
        h = last_hash(text)
        if h and ctl_hash:
            out["same"] = "1" if h == ctl_hash else "0"
    else:
        f = FAULT.findall(K.text(d, n + ".dmesg"))
        if f:
            out["fstat"], out["faddr"] = f[0]
    return out


def model_state(pred, rd):
    if not rd:
        return None
    if rd.get("end") != pred.get("end"):
        return False
    states = [None if rd.get(q) is None else rd[q] == v for q, v in pred.items() if q != "end"]
    if any(s is False for s in states):
        return False
    return None if any(s is None for s in states) else True


def verdicts(stage, d):
    """(controls, {model: [state of fl-junk-a, state of fl-junk-b]}, lines)."""
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    ctl, line = control_state(d, cases, preds)
    lines = [line]
    ctl_text = K.text(d, CONTROL + ".txt") if ctl is not None else ""
    ctl_hash = last_hash(ctl_text)
    models = {}
    for n in JUNK:
        rd = junk_reading(cases, d, n, ctl_hash)
        lines.append(f"READING {n}: {rd if rd else 'did not end ok, fault or hang'}")
        for m in sorted({m for qm in preds.get(n, {}).values() for m in qm}):
            pred = {q: mv[m] for q, mv in preds[n].items() if m in mv}
            s = model_state(pred, rd)
            models.setdefault(m, []).append(s)
            lines.append(f"ROW {n} {m}: " + ("held" if s else "FAILED" if s is False else "cannot tell"))
    return {CONTROL: ctl}, models, lines


def summary(controls, models):
    held = [m for m, ss in sorted(models.items()) if ss and all(s is True for s in ss)]
    if len(held) == 1:
        m = held[0]
        return SK.headline(f"{m}: {CLAIMS[m]}", controls, models[m])
    if not held:
        return SK.headline("no model", controls, []) if not SK.gate(controls).ok else \
            "no frozen model holds on both junk rows (a mixed or unseen outcome)"
    return "cannot tell: models " + ", ".join(held) + " all hold on both junk rows"


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        print(f"gate {argv[2]}: open (not gated; its control row is its first job)")
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, models, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        print("SUMMARY: " + argv[1] + ": " + summary(controls, models))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
