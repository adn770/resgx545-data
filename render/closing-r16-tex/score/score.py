#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r16-tex's scorer (r14-tex's, resgx545-data render/closing-r14-tex/score/score.py,
with the form quantity added and addr5's readings replaced by chain's and ty's). Every verdict rule
comes from kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of
resgx545 b2b5288c82ed, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A kept output's `row N:` lines are its pixels (raster order, 32 rows of 64 for a probe fill). A
model's frozen prediction is predictions/STAGE/NAME.MODEL.txt, one token a pixel:
  XXXXXXXX     the dword read, exactly
  h:XXXX       the low 16 bits of the read (chain's u16 rows: the half read)
  u:XXXX       the high 16 bits of the read
  -            no prediction
or a `rel` line of predictions/STAGE.tsv, value REF+K (ty's 32 x 32 mode 4 rows): every pixel of
the row reads REF's pixel of this run plus K, where REF's pixel is a name (0xDxxxxxxx; REF without
an image, or with no name, is cannot tell), or a `form` line (ty), value
  half<L       every pixel is a name n < L with each byte halved, rounded up ((b + 1) >> 1), and
               the 32 rows are alike (E1039's post hoc form)
  lin1:map:W<L half<L, and the names are c + U with one c for the row, U = W + (x mod W) (the
               unwrapped column of a `map` u of log2 W bits)
  flat<L       every pixel is one and the same value, a name n < L halved (modes 5 to 7: E1055's
               one value a row)
  whole<L      every pixel is a name n < L (0xD0000000 | n) A model holds on a row when every predicted pixel
matches, FAILED when one does not, cannot tell when the job did not complete or printed no image.
One SUMMARY line per model and set (scorekit.headline over that model's rows of the set), gated
by every control of the stage.

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
REQUIRED = {"ty": BASE}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none, each has its own
ROW = re.compile(r"row (\d+): ([0-9a-fA-Fx ]+)$", re.M)


def producible(row):
    a = row["args"].split()
    return {"pixels"} if a[:1] == ["probe"] and "--pixels" in a else set()


# ---- reading the kept files -------------------------------------------------------------------
def pixels(text):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if not rows or sorted(rows) != list(range(len(rows))):
        return None
    px = [v for y in sorted(rows) for v in rows[y]]
    return px if len(px) == 2048 else None


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
def compare(tokens, px):
    """(state, description) of one model's tokens against a kept image (None: no image)."""
    if px is None:
        return None, "no image"
    if len(tokens) != len(px):
        return None, f"{len(px)} pixels, {len(tokens)} predicted"
    hit = det = 0
    for t, v in zip(tokens, px):
        if t == "-":
            continue
        det += 1
        if t.startswith("h:"):
            hit += (v & 0xFFFF) == int(t[2:], 16)
        elif t.startswith("u:"):
            hit += (v >> 16) == int(t[2:], 16)
        else:
            hit += v == int(t, 16)
    return hit == det, f"{hit}/{det} pixels"


def relative(rule, px, imgs):
    """(state, description) of a `rel` rule REF+K against a kept image."""
    ref, _, k = rule.rpartition("+")
    rp = imgs.get(ref)
    if px is None:
        return None, "no image"
    if rp is None:
        return None, f"{ref} has no image"
    named = [(v, r) for v, r in zip(px, rp) if r >> 28 == 0xD]
    if not named:
        return None, f"{ref} reads no name"
    hit = sum(v == r + int(k) for v, r in named)
    return hit == len(named), f"{hit}/{len(named)} pixels as {ref} + {k}"


def half(d):
    return sum(((d >> 8 * i & 255) + 1) >> 1 << 8 * i for i in range(4))


def unhalf(v, limit):
    """The names n < limit whose bytes halved, rounded up, give v (a byte h from 2h - 1 or 2h)."""
    out = [0]
    for i in range(3):
        h = v >> 8 * i & 255
        if h > 128:
            return []
        bs = [0] if h == 0 else [b for b in (2 * h - 1, 2 * h) if b < 256]
        out = [n | b << 8 * i for n in out for b in bs]
    if v >> 24 != 0x68:
        return []
    return sorted(n for n in out if half(0xD0000000 | n) == v and n < limit)


def form(rule, px):
    """(state, description) of a `form` rule against a kept image."""
    if px is None:
        return None, "no image"
    kind, _, limit = rule.partition("<")
    limit = int(limit)
    if kind == "flat":
        hit = sum(bool(unhalf(v, limit)) for v in px)
        return hit == len(px) and len(set(px)) == 1, f"{hit}/{len(px)} halved names, {len(set(px))} distinct"
    if kind == "whole":
        hit = sum(v >> 28 == 0xD and (v & 0x0FFFFFFF) < limit for v in px)
        return hit == len(px), f"{hit}/{len(px)} pixels names"
    cands = [unhalf(v, limit) for v in px]
    hit = sum(bool(c) for c in cands)
    alike = all(px[64 * y:64 * y + 64] == px[:64] for y in range(32))
    desc = f"{hit}/{len(px)} pixels halved names, rows {'alike' if alike else 'differ'}"
    if kind == "half":
        return hit == len(px) and alike, desc
    _, _, w = kind.split(":")
    w = int(w)
    cs = None
    for x in range(64):
        c = {n - (w + x % w) for n in cands[x]}
        cs = c if cs is None else cs & c
    ok = hit == len(px) and alike and bool(cs)
    return ok, desc + (f"; c + U with c in {sorted(cs)[:4]}" if cs else "; no c + U")


def ty_reading(name, px):
    """ty: the lowest name of each halved pixel of row 0 (the fold's map), or the distinct
    values."""
    if px is None or not name.startswith("ty-"):
        return ""
    names = [unhalf(v, 1 << 24) for v in px[:64]]
    if all(names):
        lo = [n[0] for n in names]
        return f"; row 0 lowest names {lo[0]} to {max(lo)}, first 4 {lo[:4]}"
    return f"; {len(set(px))} distinct values, first {px[0]:08x}"


# ---- verdicts ---------------------------------------------------------------------------------
def verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, stage)
    imgs = {r["name"]: (pixels(K.text(d, r["name"] + ".txt")) if done(cases, r["name"]) else None)
            for r in table}
    controls, per_model, lines = {}, {}, []
    for r in table:
        n, px = r["name"], imgs[r["name"]]
        want = preds.get(n, {})
        res = {}
        for m in want.get("pixels", {}):
            res[m] = compare(pred_tokens(stage, n, m), px)
        for m, rule in want.get("rel", {}).items():
            res[m] = relative(rule, px, imgs)
        for m, rule in want.get("form", {}).items():
            res[m] = form(rule, px)
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items())
        if stage == "ty":
            desc += ty_reading(n, px)
        if r["set"] == "control":
            st = None if not res or any(s is None for s, _ in res.values()) else all(
                s for s, _ in res.values())
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        held = [m for m, (s, _) in res.items() if s]
        verdict = f"held {', '.join(held)}" if held else (
            "no frozen model exact" if px is not None and any(
                s is not None for s, _ in res.values()) else "cannot tell")
        lines.append(f"ROW {n} ({r['set']}): {desc}: {verdict}")
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
