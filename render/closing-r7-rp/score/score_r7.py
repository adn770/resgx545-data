#!/usr/bin/env python3
"""score_r7.py: the r7-rp scorers' one entry point (the driver run/r7.sh calls it).  Each stage is scored by its area's frozen
scorer; nothing is scored unless run/freeze_r7.sh verify S7 passes (the frozen files, the predictions and the t7 hash).

  score_r7.py STAGE KEPT S7           the stage's detail and one SUMMARY line (exit 0; non-zero only on a scorer error)
  score_r7.py gate STAGE KEPT S7      exit 0 the stage's gate passed (or it has none), 1 failed, 2 cannot tell
  score_r7.py verdict ATT_DIR S7      every question's SUMMARY lines from the attempt's kept stage directories
  score_r7.py missing STAGE KEPT      the files the stage's scorer declares (REQUIRED) that the kept directory lacks

Areas: s0, q287 -> score_q287; q291g, q291 -> score_q291; p7-rdc, p7-rd -> score_rd7; q293, q139 -> score_dump; q086 -> score_q086.
"""
import importlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import scorekit  # noqa: E402

AREA = {"s0": "score_q287", "q287": "score_q287", "q291g": "score_q291", "q291": "score_q291", "p7-rdc": "score_rd7",
        "p7-rd": "score_rd7", "q293": "score_dump", "q139": "score_dump", "q086": "score_q086"}
GATED = ("s0", "q291g", "p7-rdc")


def stages():
    with open(os.path.join(KP, "stages.txt")) as f:
        return [l.strip() for l in f if l.strip()]


def module(stage):
    return importlib.import_module(AREA[stage])


def verified(s7):
    if os.environ.get("R7_NO_VERIFY") == "tests-only":   # the scorer tests on worlds, never the driver
        return True
    p = subprocess.run([os.path.join(KP, "run", "freeze_r7.sh"), "verify", s7], capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stdout + p.stderr)
        print("SUMMARY: refused: the frozen files do not verify (run/freeze_r7.sh verify %s)" % s7)
    return p.returncode == 0


def kept_rows(kept, only_ok=False):
    """cases.tsv's row names (only_ok: the rows of class ok, the ones that owe a dump)."""
    rows = []
    p = os.path.join(kept, "cases.tsv")
    if os.path.exists(p):
        with open(p) as f:
            for l in f.read().splitlines()[1:]:
                c = l.split("\t")
                if l.strip() and (not only_ok or (len(c) > 8 and c[8] == "ok")):
                    rows.append(c[0])
    return rows


def missing(stage, kept):
    """The files the stage's scorer declares (REQUIRED[stage]) that the kept directory lacks: fixed names, `.txt` (and every
    per-row suffix the runner always writes) for every row, any other per-row suffix (a depth or render dump) for every row
    that completed (class ok): a refused or faulted job writes no dump, and its scorer reads it as such."""
    m = module(stage)
    if hasattr(m, "missing"):
        return m.missing(stage, kept)
    req = tuple(getattr(m, "REQUIRED", {}).get(stage, ()))
    always = tuple(f for f in req if not f.startswith(".") or f in (".txt", ".err", ".dmesg"))
    dumps = tuple(f for f in req if f.startswith(".") and f not in (".txt", ".err", ".dmesg"))
    out = scorekit.missing_files(always, kept, kept_rows(kept)) if always else []
    if dumps:
        out += [f for f in scorekit.missing_files(dumps, kept, kept_rows(kept, True)) if f != "(no row)"]
    return out


def main(argv):
    if len(argv) >= 4 and argv[0] == "gate":
        stage, kept, s7 = argv[1], argv[2], argv[3]
        if not verified(s7):
            return 2
        if stage not in GATED:
            print("gate %s: none (the stage's controls void its own verdicts only)" % stage)
            return 0
        g = module(stage).gate(stage, kept)
        print("gate %s: %s" % (stage, {0: "passed", 1: "FAILED", 2: "cannot tell"}.get(g, g)))
        return g
    if len(argv) >= 3 and argv[0] == "verdict":
        att, s7 = argv[1], argv[2]
        if not verified(s7):
            return 1
        done = []
        for st in stages():
            mod = AREA[st]
            if mod in done:
                continue
            done.append(mod)
            for line in importlib.import_module(mod).verdict(att):
                print(line)
        return 0
    if len(argv) >= 3 and argv[0] == "missing":
        m = missing(argv[1], argv[2])
        print(len(m), " ".join(m[:5]))
        return 0
    if len(argv) >= 3 and argv[0] in AREA:
        stage, kept, s7 = argv[0], argv[1], argv[2]
        if not verified(s7):
            return 1
        summary, detail = module(stage).score(stage, kept)
        for line in detail:
            print(line)
        print("SUMMARY: %s" % summary)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
