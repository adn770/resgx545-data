#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r13-tex's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 05b7039ee021, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A kept output's `row N:` lines are its pixels (raster order): 32 rows of 64 for a probe fill
(srgb3, addr4, t3c), 64 of 64 for sb12's `probe --tri`. A model's frozen prediction is
predictions/STAGE/NAME.MODEL.txt, one token a pixel:
  XXXXXXXX     the dword read, exactly
  h:XXXX       the low 16 bits of the read (addr4's 16-bit row)
  t:B0,B1,B2,B3  each byte of the read within TOL (t3c's blends of a level above 0, its bilinear
               bit-14 rows)
  -            no prediction (a region another model of the row speaks for)
A model holds on a row when every predicted pixel matches, FAILED when one does not, cannot tell
when the job did not complete or printed no image. sb12's `inset` (the pixels whose word is one
of E383's words of the row's mode, predictions/sb12/words-mN.txt) is frozen per model as `>=N` or
`<N`. t3c: a held-out row NAME is cannot tell unless NAME-ref held H-BILIN. One SUMMARY line per
model and set (scorekit.headline over that model's rows of the set), gated by every control of the
stage.

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
REQUIRED = {"srgb3": BASE, "addr4": BASE, "t3c": BASE, "sb12": BASE}
GATES = {}          # {stage: the earlier stage whose controls gate it}: none, each has its own
ROW = re.compile(r"row (\d+): ([0-9a-fA-Fx ]+)$", re.M)
TOL = 1             # bytes: t3c's blends (texmodel's bilinear, E720's two stages within 1)
PAGE12 = 12 * 1024  # addr4's texture base, dwords


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
    return px if len(px) in (2048, 4096) else None


def done(cases, n):
    return n in cases and K.completed(cases[n])


def pred_tokens(stage, name, model):
    with open(os.path.join(KP, "predictions", stage, f"{name}.{model}.txt")) as f:
        return f.read().split()


def words(mode):
    with open(os.path.join(KP, "predictions", "sb12", f"words-m{mode}.txt")) as f:
        return {int(t, 16) for t in f.read().split()}


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for r in K.table(KP, stage):
        if r["name"] in cases:
            K.text(d, r["name"] + ".txt")


# ---- one model on one row ---------------------------------------------------------------------
def within(tok, v):
    want = [int(b) for b in tok[2:].split(",")]
    return all(abs(want[i] - (v >> 8 * i & 255)) <= TOL for i in range(4))


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
        elif t.startswith("t:"):
            hit += within(t, v)
        else:
            hit += v == int(t, 16)
    return hit == det, f"{hit}/{det} pixels"


def quantity(rule, got):
    if got is None:
        return None
    if rule.startswith(">="):
        return got >= int(rule[2:])
    if rule.startswith("<"):
        return got < int(rule[1:])
    return got == int(rule)


def mode_of(name):
    m = re.match(r"sb12-(?:rep-|mv-)?m(\d)", name)
    return int(m.group(1)) if m else None


def inset(name, px):
    if px is None:
        return None
    w = words(mode_of(name))
    return sum(v in w for v in px)


def addr_reading(name, px):
    """addr4 sweep rows: the most common values of the dword read less the u mode 0 (REPEAT)
    reading's, the offset the rivals name."""
    if px is None or not name.startswith("addr4-") or name.endswith(("uv5", "h16", "ctl", "bduv5")):
        return ""
    sys.path.insert(0, os.path.join(KP, "gen"))
    import addr as A
    job = [j for j in A.JOBS if j[0] == name][0]
    c = collections.Counter()
    for p, v in enumerate(px):
        c[(v & 0x0FFFFFFF) - PAGE12 - A.predict(job, "REPEAT", p % 64, p // 64)] += 1
    return "; read less REPEAT " + ", ".join(f"{k:+d} x{n}" for k, n in c.most_common(4))


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
        if "inset" in want:
            got = inset(n, px)
            for m, rule in want["inset"].items():
                prev = res.get(m)
                st = quantity(rule, got)
                desc = f"inset {got} (frozen {rule})"
                if prev is not None:
                    st = None if prev[0] is None or st is None else prev[0] and st
                    desc = prev[1] + ", " + desc
                res[m] = (st, desc)
        states[n] = res
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items())
        if stage == "addr4":
            desc += addr_reading(n, px)
        if stage == "sb12" and px is not None:
            desc += f"; {len(set(px))} distinct words"
        if r["set"] == "control":
            st = None if not res or any(s is None for s, _ in res.values()) else all(
                s for s, _ in res.values())
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        held = [m for m, (s, _) in res.items() if s]
        verdict = f"held {', '.join(held)}" if held else (
            "no frozen model exact" if px is not None else "cannot tell")
        lines.append(f"ROW {n} ({r['set']}): {desc}: {verdict}")
    for r in table:
        n = r["name"]
        if r["set"] == "control":
            continue
        res = dict(states[n])
        ref = states.get(n + "-ref")
        if ref is not None and ref.get("H-BILIN", (None,))[0] is not True:
            lines.append(f"GATED {n}: its reference {n}-ref did not hold H-BILIN: cannot tell")
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
