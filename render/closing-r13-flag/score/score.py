#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r13-flag's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 0493e36a4691, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Readings of a row (all from the kept files; a row the runner did not run reads nothing):
  end     the runner's class in cases.tsv: ok, fault, hang (fail: no reading)
  image   f1: the sha256 of the 2048 `row Y:` tokens ("%08x", raster order) of an ok probe
  inset   f2: the pixels (of 4096) whose word is one of E383's bit-12 mode 0 words
  fstat, fpage, faddr   f1, f2: the last kernel `BIF fault S at A` line of the row's slice: S, A's
          page, A; f1's fpage is given from the probe's `scratch at` address (+0x...)
A model's row is held when every quantity it predicts for the row equals the reading, FAILED when
one differs, cannot tell when a reading is missing or the row's gate (its controls) is not open.

REQUIRED: the files each stage's scorer reads (the runner and sessioncheck.py kept check them);
read_files(STAGE, DIR) reads exactly what score() reads; producible(row) is the set of reading
keys a row's job can produce (the generator refuses a control that reads anything else)."""
import hashlib
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FILES = (".txt", ".dmesg", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"f1": FILES, "f2": FILES, "f3": FILES}
# the gate of f2 and f3 (session.toml gate = true): closed when an earlier flagged stage's kept
# files show a failed recovery (the plan's stop at the first failed recovery: hook_fault stops that
# stage with rc 24, after which the driver would go on to the next stage; the gate skips it)
EARLIER = {"f2": ("f1",), "f3": ("f1", "f2")}
RECOVERY = "SGX recovery failed"
ROW = re.compile(r"row (\d+): ([0-9a-fA-F ]+)$", re.M)
FAULT = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)")
SCRATCH = re.compile(r"scratch at (0x[0-9a-f]+)")
# the rows each control gates (f1: its pair; f2, f3: every row)
F1_PAIR = {"f1-tw32": "f1-ref-a", "f1-small": "f1-ref-b"}
CLAIMS = {
    "f1": "{m}: T3 bit 14 on a twiddled 32 x 32 texture",
    "f2": "{m}: sideband bit 11 in pack modes 0, 4, 8",
    "f3": "{m}: VDM_STATE1 bits 11:9 counter (Q163)",
}


def recovery_failed(stage, roots):
    """The first kept file of an earlier stage, in any attempt root, with a failed recovery."""
    import glob
    import gzip
    for root in roots:
        for st in EARLIER.get(stage, ()):
            for f in sorted(glob.glob(os.path.join(root, st, "*"))):
                b = gzip.open(f).read() if f.endswith(".gz") else open(f, "rb").read()
                if RECOVERY.encode() in b:
                    return f"{os.path.relpath(f, root)} has '{RECOVERY}'"
    return None


def producible(row):
    a = row["args"].split()
    if a[:1] == ["probe"]:
        return {"pixels", "job"} if "--tri" in a else {"pixels"}
    if a[:1] == ["tri"]:
        return {"job"}
    return set()


def pixels(text, n):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = m.group(2).split()
    if sorted(rows) != list(range(len(rows))):
        return None
    px = [t.lower().zfill(8) for y in sorted(rows) for t in rows[y]]
    return px if len(px) == n else None


def fault_line(dmesg):
    f = FAULT.findall(dmesg or "")
    return f[-1] if f else None


def words_m0():
    return set(open(os.path.join(KP, "predictions/f2/words-m0.txt")).read().split())


def reading(stage, name, cases, d):
    """{quantity: value} of a kept row, or {} when the row did not run (or failed)."""
    r = cases.get(name)
    if r is None or r["class"] not in ("ok", "fault", "hang"):
        return {}
    out = {"end": r["class"]}
    text, dm = K.text(d, name + ".txt"), K.text(d, name + ".dmesg")
    if stage == "f1" and r["class"] == "ok":
        px = pixels(text, 2048)
        if px is not None:
            out["image"] = hashlib.sha256(" ".join(px).encode()).hexdigest()
    if stage == "f2" and r["class"] == "ok":
        px = pixels(text, 4096)
        if px is not None:
            w = words_m0()
            out["inset"] = sum(1 for t in px if t in w)
    if stage in ("f1", "f2") and r["class"] == "fault":
        fl = fault_line(dm)
        if fl:
            a = int(fl[1], 16)
            out.update(fstat=fl[0], faddr=fl[1], fpage=f"{a & ~0xFFF:#x}")
            m = SCRATCH.search(text)
            if stage == "f1" and m:
                out["fpage"] = f"+{(a & ~0xFFF) - int(m.group(1), 16):#x}"
    return out


def match(quantity, want, got):
    if got is None:
        return None
    if quantity == "inset":
        n = int(want[2:]) if want.startswith(">=") else int(want[1:])
        return got >= n if want.startswith(">=") else got < n
    return str(got) == want


def model_state(pred, rd):
    """held (True), FAILED (False) or cannot tell (None) of one model's predictions for a row."""
    if not rd:
        return None
    if pred.get("end") is not None and rd.get("end") != pred["end"]:
        return False
    states = [match(q, v, rd.get(q)) for q, v in pred.items() if q != "end"]
    if any(s is False for s in states):
        return False
    if any(s is None for s in states):
        return None
    return True


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")
        K.text(d, n + ".dmesg")


def verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, stage)
    controls, lines, per_model = {}, [], {}
    reads = {r["name"]: reading(stage, r["name"], cases, d) for r in table}
    for r in table:
        n = r["name"]
        if r["set"] != "control":
            continue
        p = {q: next(iter(mv.values())) for q, mv in preds.get(n, {}).items()}
        st = model_state(p, reads[n])
        controls[n] = st
        lines.append(f"CONTROL {n}: {reads[n] or 'no reading'} (frozen {p}): "
                     f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
    for r in table:
        n = r["name"]
        if r["set"] in ("control", "prime", "between") and n not in preds:
            continue
        if r["set"] == "control":
            continue
        rd = reads[n]
        gate = SK.gate({F1_PAIR[n]: controls.get(F1_PAIR[n])} if stage == "f1" else controls)
        models = {}
        for q, mv in preds.get(n, {}).items():
            for m, v in mv.items():
                models.setdefault(m, {})[q] = v
        extra = ""
        if stage == "f2":
            c = cases.get(n, {})
            extra = (f" sideband {r['args'].split('--sideband ')[1].split()[0]}"
                     f" fault_int {c.get('fault_int', '-')} fault_word {c.get('fault_word', '-')}")
        if r["set"] in ("prime", "between"):
            st = model_state(models.get("M1", {}), rd)
            lines.append(f"OPEN {n}: {rd or 'no reading'} (M1 {models.get('M1')}): "
                         f"{'as frozen' if st else 'NOT as frozen' if st is False else 'cannot tell'}")
            continue
        for m, p in sorted(models.items()):
            st = SK.gated(gate, model_state(p, rd))
            per_model.setdefault(m, []).append(st)
            lines.append(f"ROW {n} {m}: {rd or 'no reading'}{extra} (frozen {p}): "
                         f"{'held' if st else 'FAILED' if st is False else 'cannot tell'}")
    return controls, per_model, lines


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        why = recovery_failed(argv[2], argv[3:])
        print(f"gate {argv[2]}: " + (f"closed: {why}" if why else "open (no failed recovery in "
                                     + ", ".join(EARLIER.get(argv[2], ())) + ")"))
        return 1 if why else 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        stage = argv[1]
        controls, per_model, lines = verdicts(stage, argv[2])
        print("\n".join(lines))
        for m, rows in sorted(per_model.items()):
            print("SUMMARY: " + stage + ": " + SK.headline(CLAIMS[stage].format(m=m), controls, rows))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
