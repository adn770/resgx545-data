#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r17-tw's scorer, frozen before the run. Every verdict rule comes from kit/scorekit.py,
the kept files are read through kit/kitscore.py (byte copies of resgx545 c2180e64ecda, pinned in
FROZEN.commits). Standard library only.

  score.py tw17 KEPT_DIR [ROOTS...]    CONTROL, READING, ROW, LEFTWRAP and RIGHTWRAP lines, then
                                       SUMMARY lines (exit 0)
  score.py gate tw17 ROOTS...          exit 0 (no stage is gated by another)
  score.py premise tw17 KEPT_DIR       STOP lines and exit 1 when a control has no reading

A kept output's `row N:` lines are the probe's 32 rows of 64 pixels (raster order). A model's
frozen image is predictions/tw17/NAME.MODEL.txt, one token a pixel (gen/make.py):
  XXXXXXXX        the dword read, exactly (point rows, references)
  t:B0,B1,B2,B3   the blend; a model holds when each byte is within TOL (bilinear rows, and
                  bl64leftr, E1058's kept bl64left image)
A model holds on a row when the job ended ok and every pixel matches, FAILED when it ended ok and a
pixel does not or it did not end ok (a fault, a hang: no model predicts one), cannot tell when the
row did not run or printed no image. A control passes when its one model holds. A held-out row is
cannot tell unless bl64leftr (E1058's bl64left rerun, the bit-14 control) and its width's
reference (ref256, ref512h16, ref2048h16) passed (GATE, gen/tw17.py's). One SUMMARY line per
model, scorekit.headline over that model's rows with the controls those rows are gated by.

The LEFT-WRAP rule (decision R17-3 a, pre-declared): H-WIDE (column -1 reads W' - 1) and H-WIDE-G
(it reads W - 1) name dwords 65536 apart, so their blends differ by at most one in byte 2 and part
by exact bytes only. Over every held-out bilinear row that ended ok with its gate open, at the
pixels where the two frozen images differ: the winner is byte-exact on at least 90 % and the loser
on at most 10 %, with at least MIN_LEFT such pixels; anything else is cannot tell. The kept fit set
gave 124 of 128 against 0 of 128 (gen/derive.py). The right wrap (H-WIDE: column W' reads 0;
H-WIDE-NEXT: the next tile row) parts by names and is the two models' own ROW and SUMMARY lines;
RIGHTWRAP lines count its pixels.

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
REQUIRED = {"tw17": (".txt",) + FIXED}
ROW = re.compile(r"row (\d+): ([0-9a-fA-F ]+)$", re.M)
TOL = 1
ZERO = "bl64leftr"
MIN_LEFT = 64
LEFT_WIN, LEFT_LOSE = 0.9, 0.1
GATE = {"bl16left": None, "bl64grid": None, "bl128off3": None, "pt128off": None,
        "pt256off": "ref256", "pt512off": "ref512h16", "bl256edge": "ref256",
        "bl512edge": "ref512h16", "bl256corner": "ref256", "bl2048edge": "ref2048h16"}
CLAIM = {"H-WIDE": "bit 14 bilinear: the sample over W + 4096 texels at frac u, columns mod W'",
         "H-WIDE-G": "bit 14 bilinear: H-WIDE with column -1 at W - 1 (within 1)",
         "H-WIDE-NEXT": "bit 14 bilinear: H-WIDE with column W' the next tile row",
         "UNWRAP-G": "bit 14 bilinear: columns X + m, X + 1 + m, -1 at W - 1",
         "F-FRAC": "bit 14 bilinear: taps X mod W, X + 1 plus m",
         "H-POINT": "bit 14 bilinear: the filter dropped",
         "H-WIDE-PT": "bit 14 point read: column floor((W + 4096) frac u)",
         "H-TWP": "bit 14 point read: column floor(W frac u) + floor(4096 frac u)"}


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


def match(tok, v, tol=TOL):
    if tok.startswith("t:"):
        want = [int(b) for b in tok[2:].split(",")]
        return all(abs(want[i] - (v >> 8 * i & 255)) <= tol for i in range(4))
    return v == int(tok, 16)


def frozen(name, model):
    return open(os.path.join(KP, "predictions", "tw17", f"{name}.{model}.txt")).read().split()


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
    preds = K.predictions(KP, "tw17")
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, "tw17")
    models = {r["name"]: sorted({m for mv in preds.get(r["name"], {}).values() for m in mv})
              for r in table}
    controls, lines, per_model, ctl_of_model = {}, [], {}, {}
    left = [0, 0, 0]
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
        if "H-WIDE" in models[n]:
            lw = leftwrap(cases, d, n) if g.ok else None
            if lw:
                lines.append(f"LEFTWRAP {n}: {lw[0]} parting pixels; H-WIDE exact {lw[1]}; "
                             f"H-WIDE-G exact {lw[2]}")
                left = [a + b for a, b in zip(left, lw)]
            rw = rightwrap(cases, d, n) if g.ok else None
            if rw:
                lines.append(f"RIGHTWRAP {n}: {rw[0]} parting pixels; H-WIDE {rw[1]}; "
                             f"H-WIDE-NEXT {rw[2]} (within {TOL})")
    for m, rows in sorted(per_model.items()):
        ctl = {c: controls.get(c) for c in sorted(ctl_of_model[m])}
        lines.append(f"SUMMARY: tw17: {m}: " + SK.headline(CLAIM[m], ctl, rows))
    lines.append("SUMMARY: tw17: LEFT-WRAP: " + left_verdict(left, controls.get(ZERO)))
    return lines


def parting(name, a, b):
    """The pixels where two models' frozen images differ (exactly)."""
    return [i for i, (x, y) in enumerate(zip(frozen(name, a), frozen(name, b))) if x != y]


def leftwrap(cases, d, name):
    """(parting pixels, H-WIDE exact, H-WIDE-G exact) on one ok row, else None."""
    r = cases.get(name)
    if r is None or r["class"] != "ok":
        return None
    px = pixels(K.text(d, name + ".txt"))
    if px is None:
        return None
    ix = parting(name, "H-WIDE", "H-WIDE-G")
    a, b = frozen(name, "H-WIDE"), frozen(name, "H-WIDE-G")
    return [len(ix), sum(match(a[i], px[i], 0) for i in ix), sum(match(b[i], px[i], 0) for i in ix)]


def rightwrap(cases, d, name):
    """(parting pixels, H-WIDE within TOL, H-WIDE-NEXT within TOL) on one ok row, else None."""
    r = cases.get(name)
    if r is None or r["class"] != "ok":
        return None
    px = pixels(K.text(d, name + ".txt"))
    if px is None:
        return None
    ix = parting(name, "H-WIDE", "H-WIDE-NEXT")
    if not ix:
        return None
    a, b = frozen(name, "H-WIDE"), frozen(name, "H-WIDE-NEXT")
    return [len(ix), sum(match(a[i], px[i]) for i in ix), sum(match(b[i], px[i]) for i in ix)]


def left_verdict(left, zero):
    """The LEFT-WRAP rule over the summed (n, H-WIDE exact, H-WIDE-G exact)."""
    n, a, b = left
    head = f"{n} parting pixels, H-WIDE exact {a}, H-WIDE-G exact {b}: "
    if zero is not True:
        return head + f"cannot tell (control {ZERO}: {cword(zero)})"
    if n < MIN_LEFT:
        return head + f"cannot tell (fewer than {MIN_LEFT} pixels)"
    if a >= LEFT_WIN * n and b <= LEFT_LOSE * n:
        return head + "column -1 reads W' - 1 (H-WIDE)"
    if b >= LEFT_WIN * n and a <= LEFT_LOSE * n:
        return head + "column -1 reads W - 1 (H-WIDE-G)"
    return head + "cannot tell (neither rule met)"


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        print(f"gate {argv[2]}: open (no stage is gated)")
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] == "tw17":
        print("\n".join(score(argv[2])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
