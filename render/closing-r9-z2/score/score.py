#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r9-z2's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 02ae0a0ec5e6, pinned in FROZEN.commits).

  score.py z2 KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate z2 ROOTS...         exit 0 (no stage gates z2)
  score.py premise z2 KEPT_DIR      STOP lines and exit 1 when a control has no reading

A held-out row is scored per frozen model over every dword of the target (format 1: one a pixel;
format 2: one a pair of rows, E490's layout), the model's values computed from the format-0
reference of the same ramp (gen/z2.py): held when all match, FAILED otherwise, cannot tell when the
row or its reference did not complete or kept no dump. One SUMMARY per model (scorekit.headline),
gated by both format-0 controls.

REQUIRED: the files the scorer reads; read_files(STAGE, DIR) reads exactly what verdicts() reads;
producible(row) is the set of reading keys a row's job can produce."""
import os
import re
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

REQUIRED = {"z2": (".txt", "cases.tsv", "void.tsv", "readings.tsv", ".depth.1.bin")}
GATES = {}


def producible(row):
    a = row["args"].split()
    keys = {"job", "drawn"} if a[:1] == ["tri"] else set()
    if "--pixels" in a:
        keys.add("pixels")
    if "--depth" in a:
        keys.add("depth_changed")
    return keys


def changed(text):
    m = re.search(r"^depth #1: (\d+) dwords, (\d+) changed", text or "", re.M)
    return int(m.group(2)) if m else None


def dwords(d, name):
    b = K._read(os.path.join(d, name))
    return None if b is None or len(b) % 4 else list(struct.unpack("<%dI" % (len(b) // 4), b))


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for r in K.table(KP, stage):
        if r["name"] in cases:
            K.text(d, r["name"] + ".txt")
            dwords(d, r["name"] + ".depth.1.bin")


def verdicts(stage, d):
    import z2 as Z
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    done = lambda n: n in cases and K.completed(cases[n])
    controls, per_model, lines = {}, {}, []
    for r in K.table(KP, stage):
        n = r["name"]
        want = preds.get(n, {})
        if r["set"] == "control":
            got = changed(K.text(d, n + ".txt")) if done(n) else None
            frozen = int(want["depth_changed"]["H-E831"])
            st = None if got is None else got == frozen
            controls[n] = st
            lines.append(f"CONTROL {n}: depth_changed {got} (frozen {frozen}): "
                          f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        ref = n.split("-f")[0] + "-f0"
        fmt, b19 = int(n.split("-f")[1][0]), n.endswith("-b19")
        z0 = dwords(d, ref + ".depth.1.bin") if done(ref) else None
        dump = dwords(d, n + ".depth.1.bin") if done(n) else None
        res = {}
        for m in want.get("dwords", {}):
            if z0 is None or dump is None:
                res[m] = (None, "no dump")
                continue
            pred = Z.predict(z0, fmt, b19, m)
            same = sum(i < len(dump) and dump[i] == v for i, v in pred.items())
            res[m] = (same == len(pred), f"{same}/{len(pred)} dwords")
        for m, (s, _) in res.items():
            per_model.setdefault(m, []).append(s)
        held = [m for m, (s, _) in res.items() if s]
        lines.append(f"ROW {n}: " + "; ".join(f"{m} {t}" for m, (_, t) in res.items()) + ": "
                     + (f"held {', '.join(held)}" if held else
                        "no frozen model" if dump is not None and z0 is not None else "cannot tell"))
    return controls, per_model, lines


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        for m, states in sorted(per_model.items()):
            print("SUMMARY: " + argv[1] + ": " + SK.headline(m, controls, states))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
