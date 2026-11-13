#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r10-tex's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 9849dab7540c, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

Every stage is a probe stage: a kept output's 32 `row N:` lines are its 2048 pixels (raster
order). A model's frozen prediction is predictions/STAGE/NAME.MODEL.txt, one token a pixel:
  XXXXXXXX     the dword read, exactly
  h:XXXX       the low 16 bits of the read (t3b's 16-bit rows)
  aN           cube3: a two-axis tie pixel reads a face of axis N ((index // 256) // 2)
  i:B0,B1,B2,B3 / o:...   cube3 edges: an in / out pixel's bytes, each within TOL of the read
  -            no prediction (a texel tie, a three-axis tie, a pixel neither in nor out)
A model holds on a row when every predicted pixel matches, FAILED when one does not, cannot tell
when the job did not complete or printed no image. Edge rows: the in pixels are the gate (at
least 90% within TOL, else cannot tell), then every out pixel decides. cube3's `lower` quantity
(the tie pixels that read a face other than the higher tied axis) is frozen per model (a number,
or `>0`). t3b: a held-out row is cannot tell unless its `-ref` row held H-TEXMODEL.
One SUMMARY line per model and set (scorekit.headline over that model's rows of the set), gated by
every control of the stage.

REQUIRED: the files each stage's scorer reads (the runner and sessioncheck.py kept check them);
read_files(STAGE, DIR) reads exactly what score() reads; producible(row) is the set of reading
keys a row's job can produce (the freeze refuses a control that reads anything else)."""
import collections
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"addr3": BASE, "cube3": BASE, "t3b": BASE, "srgb2": BASE}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none, each has its own
ROW = re.compile(r"row (\d+): ([0-9a-fA-Fx ]+)$", re.M)
TOL = 1             # bytes, cube3 edges (E931: the in pixels read the exact blend within 0.5)
IN_GATE = 0.9
N_FACE = 16         # cube3's faces: 16 x 16


def producible(row):
    a = row["args"].split()
    return {"pixels"} if a[:1] == ["probe"] and "--pixels" in a else set()


# ---- reading the kept files -------------------------------------------------------------------
def pixels(text, n=2048):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if not rows or sorted(rows) != list(range(len(rows))):
        return None
    px = [v for y in sorted(rows) for v in rows[y]]
    return px if len(px) == n else None


def done(cases, n):
    return n in cases and K.completed(cases[n])


def pred_tokens(stage, name, model):
    with open(os.path.join(KP, "predictions", stage, f"{name}.{model}.txt")) as f:
        return f.read().split()


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for r in K.table(KP, stage):
        if r["name"] in cases:
            K.text(d, r["name"] + ".txt")


# ---- one model on one row ---------------------------------------------------------------------
def axis_of(v):
    return (v & 0x0FFFFFFF) // (N_FACE * N_FACE) // 2


def within(tok, v):
    want = [float(b) for b in tok[2:].split(",")]
    return all(abs(want[i] - (v >> 8 * i & 255)) <= TOL for i in range(4))


def compare(tokens, px):
    """(state, description) of one model's tokens against a kept image (None: no image)."""
    if px is None:
        return None, "no image"
    if any(t[:2] in ("i:", "o:") for t in tokens):
        ins = [within(t, v) for t, v in zip(tokens, px) if t.startswith("i:")]
        outs = [within(t, v) for t, v in zip(tokens, px) if t.startswith("o:")]
        desc = f"in {sum(ins)}/{len(ins)}, out {sum(outs)}/{len(outs)} within {TOL}"
        if not ins or sum(ins) < IN_GATE * len(ins) or not outs:
            return None, desc + " (in gate shut)"
        return all(outs), desc
    hit = det = 0
    for t, v in zip(tokens, px):
        if t == "-":
            continue
        det += 1
        if t.startswith("h:"):
            hit += (v & 0xFFFF) == int(t[2:], 16)
        elif t.startswith("a"):
            hit += axis_of(v) == int(t[1:])
        else:
            hit += v == int(t, 16)
    desc = f"{hit}/{det} pixels"
    if all(t.startswith("h:") for t in tokens):
        desc += " (low 16 bits)"
    return hit == det, desc


def lower_reads(stage, name, px):
    """cube3: the two-axis tie pixels that read a face other than the higher tied axis."""
    if px is None:
        return None
    toks = pred_tokens(stage, name, "H-HIGHAXIS")
    return sum(1 for t, v in zip(toks, px) if t[:1] == "a" and axis_of(v) != int(t[1:]))


def addr_reading(name, px):
    """addr3: the most common values of the index read less H-MASK-V's (E957's offsets)."""
    if px is None:
        return ""
    sys.path.insert(0, os.path.join(KP, "gen"))
    import addr as A
    job = [j for j in A.JOBS if j[0] == name][0]
    _, _, w, h, um, vm, _ = job
    c = collections.Counter()
    for p, v in enumerate(px):
        c[(v & 0x0FFFFFFF) - A.BASE - A.predict(w, h, um, vm, "REPEAT", p % 64, p // 64)] += 1
    return "; read less H-MASK-V " + ", ".join(f"{k:+d} x{n}" for k, n in c.most_common(4))


# ---- verdicts ---------------------------------------------------------------------------------
def verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, stage)
    imgs = {r["name"]: (pixels(K.text(d, r["name"] + ".txt")) if done(cases, r["name"]) else None)
            for r in table}
    controls, per_model, lines, states = {}, {}, [], {}
    for r in table:
        n, px = r["name"], imgs[r["name"]]
        want = preds.get(n, {})
        res = {}
        for m in want.get("pixels", {}):
            res[m] = compare(pred_tokens(stage, n, m), px)
        if "lower" in want:
            lo = lower_reads(stage, n, px)
            for m, v in want["lower"].items():
                ok = None if lo is None else (lo > 0 if v == ">0" else lo == int(v))
                prev = res.get(m, (True, ""))
                st = None if prev[0] is None or ok is None else prev[0] and ok
                res[m] = (st, (prev[1] + ", " if prev[1] else "") + f"lower {lo} (frozen {v})")
        states[n] = res
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items())
        if stage == "addr3":
            desc += addr_reading(n, px)
        if r["set"] == "control":
            st = None if any(s is None for s, _ in res.values()) else all(s for s, _ in res.values())
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        held = [m for m, (s, _) in res.items() if s]
        verdict = f"held {', '.join(held)}" if held else (
            "no frozen model exact" if px is not None else "cannot tell")
        lines.append(f"ROW {n} ({r['set']}): {desc}: {verdict}")
    # t3b: a held-out row counts only when its reference held its texmodel image
    for r in table:
        n = r["name"]
        if r["set"] == "control":
            continue
        res = dict(states[n])
        ref = states.get(n + "-ref")
        if ref is not None and ref.get("H-TEXMODEL", (None,))[0] is not True:
            lines.append(f"GATED {n}: its reference {n}-ref did not hold H-TEXMODEL: cannot tell")
            res = {m: (None, t) for m, (s, t) in res.items()}
        for m, (s, _) in res.items():
            per_model.setdefault(f"{m} ({r['set']})", []).append(s)
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
