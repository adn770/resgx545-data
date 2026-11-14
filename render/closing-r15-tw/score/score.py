#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r15-tw's scorer, frozen before the run. Every verdict rule comes from kit/scorekit.py,
the kept files are read through kit/kitscore.py (byte copies of resgx545 158bdc5455b2, pinned in
FROZEN.commits). Standard library only.

  score.py tw14 KEPT_DIR [ROOTS...]    CONTROL, READING and ROW lines, then SUMMARY lines (exit 0)
  score.py gate tw14 ROOTS...          exit 0 (no stage is gated by another)
  score.py premise tw14 KEPT_DIR       STOP lines and exit 1 when a control has no reading

A kept output's `row N:` lines are the probe's 32 rows of 64 pixels (raster order). A model's
frozen image is predictions/tw14/NAME.MODEL.txt, one token a pixel (gen/make.py):
  XXXXXXXX        the dword read, exactly
  h:XXXX          the low 16 bits of the read (the u16 rows: texel T is the half T & 1 of dword
                  T >> 1)
  t:B0,B1,B2,B3   each byte of the read within TOL (the bilinear rows' blends, r13-tex t3c's)
A model holds on a row when the job ended ok and every pixel matches, FAILED when it ended ok and a
pixel does not or it did not end ok (a fault, a hang: no model predicts one), cannot tell when the
row did not run or printed no image. A control passes when its one model holds. A held-out row is
cannot tell unless tw-zero (E1047's f1-zero, the bit-14 control) and its shape's reference passed
(GATE). One SUMMARY line per model, scorekit.headline over that model's rows with the controls
those rows are gated by. READING lines decode every ok image: how many pixels name a scratch dword
(0xD0000000 | i) and the dwords' range, the pixels each model gives.

REQUIRED: the per-row files every kept row has (the runner and sessioncheck.py kept check them);
read_files(STAGE, DIR) reads exactly what the scorer reads; producible(row) is the set of reading
keys a row's job can produce (the generator refuses a control that reads anything else)."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"tw14": (".txt",) + FIXED}
ROW = re.compile(r"row (\d+): ([0-9a-fA-F ]+)$", re.M)
TOL = 1
ZERO = "tw-zero"
GATE = {"tw16-u0": "tw-ref16", "tw16-u1": "tw-ref16", "tw-bl16": "tw-ref16",
        "tw64-u0": "tw-ref64", "tw64-u2": "tw-ref64", "tw128-u0": "tw-ref128",
        "tw128-u2": "tw-ref128", "tw-u16": "tw-refu16", "tw-bl32": None}
CLAIM = {"H-TWP": "bit 14 point read: s + floor(4096 frac u) in tiles, tile row W + 4096",
         "H-TWP4128": "bit 14 point read: tile row 4128 texels",
         "H-CLAMP1": "bit 14 point read: u clamped to [0, 1]",
         "H-WRAPW": "bit 14 point read: move floor(128 W u) mod 4096",
         "H-TWP4096": "bit 14 point read: tile row 4096 texels",
         "U16-TX": "bit 14 u16: H-TWP in texels, 16 x 16 texel tiles",
         "U16-T32": "bit 14 u16: tiles of 16 x 16 dwords of texel pairs",
         "U16-DW": "bit 14 u16: move and widening in dwords",
         "H-FOOT-TW": "bit 14 bilinear: every tap at its wrapped texel's bit-14 address",
         "H-FOOT-SHIFT": "bit 14 bilinear: the second column unwrapped",
         "H-POINT": "bit 14 bilinear: the filter dropped"}


def producible(row):
    a = row["args"].split()
    return {"pixels"} if a[:1] == ["probe"] and "--pixels" in a else set()


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")


def pixels(text):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if not rows or sorted(rows) != list(range(len(rows))):
        return None
    px = [v for y in sorted(rows) for v in rows[y]]
    return px if len(px) == 2048 else None


def match(tok, v):
    if tok.startswith("h:"):
        return (v & 0xFFFF) == int(tok[2:], 16)
    if tok.startswith("t:"):
        want = [int(b) for b in tok[2:].split(",")]
        return all(abs(want[i] - (v >> 8 * i & 255)) <= TOL for i in range(4))
    return v == int(tok, 16)


def frozen(name, model):
    return open(os.path.join(KP, "predictions", "tw14", f"{name}.{model}.txt")).read().split()


def state(cases, d, name, model):
    """(True / False / None, description) of one model on one kept row."""
    r = cases.get(name)
    if r is None or r["class"] not in ("ok", "fault", "hang"):
        return None, "did not run"
    if r["class"] != "ok":
        return False, f"ended {r['class']}"
    px = pixels(K.text(d, name + ".txt"))
    if px is None:
        return None, "no image"
    toks = frozen(name, model)
    hit = sum(match(t, v) for t, v in zip(toks, px))
    return hit == len(toks), f"{hit}/{len(toks)} pixels"


def decode(name, d, models):
    px = pixels(K.text(d, name + ".txt"))
    if px is None:
        return None
    named = [v & 0x0FFFFFFF for v in px if v >> 28 == 0xD]
    parts = [f"{len(named)} of 2048 pixels name a scratch dword"]
    if named:
        parts.append(f"dwords {min(named)} to {max(named)}")
    for m in models:
        toks = frozen(name, m)
        parts.append(f"{m} {sum(match(t, v) for t, v in zip(toks, px))} of 2048")
    return f"READING {name}: " + "; ".join(parts)


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def score(d):
    preds = K.predictions(KP, "tw14")
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, "tw14")
    models = {r["name"]: sorted({m for mv in preds.get(r["name"], {}).values() for m in mv})
              for r in table}
    controls, lines, per_model, ctl_of_model = {}, [], {}, {}
    for r in table:
        n = r["name"]
        if r["set"] != "control":
            continue
        (m,) = models[n]
        st, desc = state(cases, d, n, m)
        controls[n] = st
        lines.append(f"CONTROL {n}: {m} {desc}: {cword(st)}")
    for r in table:
        n = r["name"]
        if r["set"] == "control":
            continue
        gates = [ZERO] + ([GATE[n]] if GATE[n] else [])
        g = SK.gate({c: controls.get(c) for c in gates})
        rd = decode(n, d, models[n])
        if rd:
            lines.append(rd)
        for m in models[n]:
            st, desc = state(cases, d, n, m)
            st = SK.gated(g, st)
            per_model.setdefault(m, []).append(st)
            ctl_of_model.setdefault(m, set()).update(gates)
            lines.append(f"ROW {n} {m}: {desc}: {word(st)}"
                         + ("" if g.ok else f" (gate: {'; '.join(g.problems)})"))
    for m, rows in sorted(per_model.items()):
        ctl = {c: controls.get(c) for c in sorted(ctl_of_model[m])}
        lines.append(f"SUMMARY: tw14: {m}: " + SK.headline(CLAIM[m], ctl, rows))
    return lines


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        print(f"gate {argv[2]}: open (no stage is gated)")
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] == "tw14":
        print("\n".join(score(argv[2])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
