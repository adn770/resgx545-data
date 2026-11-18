#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r35-pk's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 eea6d2ab8f45, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading
  score.py narrow ATTEMPT_DIR          Q302's frozen narrow rule (README.md "Narrow rule") over
                                       the stages ATTEMPT_DIR holds: each clause decided or not

A kept output's 64 `row N:` lines are its 4096 dwords (raster order), its `scratch +0xOFF 0xV`
lines the scratch dwords the job changed. Quantities (frozen in predictions/STAGE.tsv, gen/pk.py;
every expected image is computed here from THIS stage's mode 0 reference STAGE-m00-ref, never from
a frozen reading):
  pixels  a control's image, dword for dword, against predictions/STAGE/NAME.MODEL.txt
  thr     s0's mode 4 ramp control: "MAXCLEAR,MINSET" of the alpha bit over the ramp's alphas
  match   the model's image (gen/pk.py predict: a packer per rounding rule, or the reference
          itself for H-AS0) against the row: "all" or "N/4096"; "notall" holds on any "N/4096"
  whole   every dword written, and every scratch dword, one of the reference's values: "all"
          or "notall"
  rel     stage r3: H-1136's image from the stage's 0x80 reference of the mode and its mode 0
          reference (gen/pk.py rel1136): "all" or "N/4096"; "notall" holds on any "N/4096"
D1: a row of a decoder form whose known-value control (FORM) did not PASS is "cannot tell: form
control". One SUMMARY line per model (the rounding rules and H-WHOLE per mode) and set
(scorekit.headline), gated by the stage's controls; GATES: every stage on s0.

REQUIRED: the files each stage's scorer reads (the runner and sessioncheck.py kept check them);
read_files(STAGE, DIR) reads exactly what score() reads; producible(row) is the set of reading
keys a row's job can produce (the freeze refuses a control that reads anything else)."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import pk as Q  # noqa: E402
import scorekit as SK  # noqa: E402

BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
STAGES = ("s0", "r1", "r2", "r3", "pw")
REQUIRED = {s: BASE for s in STAGES}
GATES = {"r1": "s0", "r2": "s0", "r3": "s0", "pw": "s0"}
ROW = re.compile(r"^probe \S+: row (\d+): ([0-9a-fA-F ]+)$", re.M)
SCR = re.compile(r"^probe \S+: scratch \+0x([0-9a-fA-F]+) 0x([0-9a-fA-F]+)$", re.M)
NOTALLY = ("ref",)
PER_MODE = set(Q.RULES) | {"H-WHOLE", "H-NARROW", "H-1136", "H-LOWDEP"}
# D1: the known-value controls of each decoder form: (stage, row) that must PASS
RAMP_CTL = (("s0", "s0-m00-ref"),)
FORM = {3: (("s0", "s0-m03-col"),), 4: (("s0", "s0-m04-col"), ("s0", "s0-m04-ramp")),
        5: (("s0", "s0-m05-col"),), 6: (("s0", "s0-m06-col"),), 9: (("s0", "s0-m09-col"),),
        10: (("s0", "s0-m10-col"),), 12: (("pw", "pw-m12-col"),), 13: (("pw", "pw-m13-col"),)}


def producible(row):
    a = row["args"].split()
    return {"pixels"} if a[:3] == ["probe", "--temps", "32"] and "--pixels" in a else set()


# ---- reading the kept files -------------------------------------------------------------------
def pixels(text):
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if sorted(rows) != list(range(64)) or any(len(v) != 64 for v in rows.values()):
        return None
    return [v for y in range(64) for v in rows[y]]


def scratch(text):
    return {int(o, 16): int(v, 16) for o, v in SCR.findall(text or "")}


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for r in K.table(KP, stage):
        if r["name"] in cases:
            K.text(d, r["name"] + ".txt")


def tokens(stage, name, model):
    with open(os.path.join(KP, "predictions", stage, f"{name}.{model}.txt")) as f:
        return [int(t, 16) for t in f.read().split()]


def name_parts(name):
    """(stage, mode, rest) of a row name STAGE-mMM[-...]."""
    m = re.match(r"^(s0|r1|r2|r3|pw)-m(\d\d)(?:-(.+))?$", name)
    return (m.group(1), int(m.group(2)), m.group(3) or "") if m else (None, None, None)


def holds(rule, got):
    if got is None:
        return None
    if rule == "notall":
        return got != "all"
    return got == rule


# ---- the readings -----------------------------------------------------------------------------
def load(stage, d):
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, stage)
    imgs, scr = {}, {}
    for r in table:
        n = r["name"]
        ok = n in cases and K.completed(cases[n])
        t = K.text(d, n + ".txt") if ok else None
        imgs[n] = pixels(t) if ok else None
        scr[n] = scratch(t) if ok else {}
    return table, imgs, scr


def analyse(stage, d):
    """{name: dict(row, img, got {(quantity, model): reading}, extra)} of the stage's rows."""
    table, imgs, scr = load(stage, d)
    preds = K.predictions(KP, stage)
    ref0 = imgs.get(f"{stage}-m00-ref")
    alpha = [v >> 24 for v in tokens("s0", "s0-m00-ref", "H-RAMP")] if stage == "s0" else None
    out = {}
    for r in table:
        n = r["name"]
        _, mode, rest = name_parts(n)
        img = imgs[n]
        got, extra = {}, ""
        for q, ms in preds.get(n, {}).items():
            for m in ms:
                if q == "thr":
                    got[(q, m)] = Q.thr_of(alpha, img)
                elif q == "match":
                    want = None if ref0 is None else Q.predict(ref0, mode, "H-AS0" if m in (
                        "H-AS0", "H-AS0-PART") else m, r1_low(r))
                    got[(q, m)] = Q.match(want, img)
                elif q == "whole":
                    w, (nw, nin, npx) = Q.whole(ref0, img, scr[n].values())
                    got[(q, m)] = w
                    extra = (f"; {nw} dwords written ({len(scr[n])} past the target), {nin} of "
                             f"the reference's values, {npx} pixels named")
                elif q == "rel":
                    refm = imgs.get(f"{stage}-m{mode:02d}-ref")
                    want = None if refm is None or ref0 is None else Q.rel1136(
                        refm, ref0, mode, r1_word(r))
                    got[(q, m)] = Q.match(want, img)
        if mode in Q.NARROW and rest and stage == "r1":
            fits = Q.channel_fits(ref0, mode, img)
            if fits is not None:
                extra = "; channels fit: " + ", ".join(
                    f"{c} {'/'.join(x[2:] for x in v) or 'none'}" for c, v in fits.items())
        out[n] = dict(row=r, img=img, got=got, extra=extra, mode=mode)
    return out


def r1_word(r):
    a = r["args"].split()
    return int(a[a.index("--cmd") + 1].split("=")[1], 16)


def r1_low(r):
    return r1_word(r) & 0xFF


# ---- verdicts ---------------------------------------------------------------------------------
def control_states(stage, d):
    """{control: True/False/None} of a stage's controls (no form check: controls have none)."""
    return verdicts(stage, d, forms=False)[0]


def form_problem(stage, d, mode, cache):
    """The first form control of a ramp row of `mode` that did not PASS, or None."""
    root = os.path.dirname(os.path.abspath(d))
    for st, name in RAMP_CTL + FORM.get(mode, ()):
        if st not in cache:
            sd = os.path.join(root, st)
            cache[st] = control_states(st, sd) if os.path.isdir(sd) else {}
        if cache[st].get(name) is not True:
            return name
    return None


def verdicts(stage, d, forms=True):
    preds = K.predictions(KP, stage)
    an = analyse(stage, d)
    controls, per_model, lines, cache = {}, {}, [], {}
    for n, a in an.items():
        r, img = a["row"], a["img"]
        if r["set"] != "control":
            continue
        res = {}
        for q, ms in preds.get(n, {}).items():
            for m, v in ms.items():
                if q == "pixels":
                    if img is None:
                        res[m] = (None, "no image")
                    else:
                        want = tokens(stage, n, m)
                        hit = sum(x == y for x, y in zip(want, img))
                        res[m] = (hit == len(want) == len(img), f"{hit}/{len(want)} dwords")
                else:
                    got = a["got"].get((q, m))
                    res[m] = (holds(v, got), f"{q} {got} (frozen {v})")
        st = None if not res or any(s is None for s, _ in res.values()) else all(
            s for s, _ in res.values())
        controls[n] = st
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items()) + (
            "; no image" if img is None else "")
        lines.append(f"CONTROL {n}: {desc}: "
                     f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
    if not forms:
        return controls, per_model, lines
    if stage == "pw":
        cache["pw"] = controls
    for n, a in an.items():
        r, img, mode = a["row"], a["img"], a["mode"]
        if r["set"] == "control":
            continue
        bad = form_problem(stage, d, mode, cache) if r["set"] not in NOTALLY else None
        res = {}
        for q, ms in preds.get(n, {}).items():
            for m, v in ms.items():
                got = a["got"].get((q, m))
                res[m] = (None if bad else holds(v, got), f"{q} {got} (frozen {v})")
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items()) or "read (no model)"
        desc += a["extra"] + ("; no image" if img is None else "")
        held = [m for m, (s, _) in res.items() if s]
        verdict = (f"cannot tell: form control {bad}" if bad and res else
                   f"held {', '.join(held)}" if held else "no frozen model exact"
                   if res and any(s is False for s, _ in res.values()) else
                   "cannot tell" if res else "read (no model)")
        lines.append(f"ROW {n} ({r['set']}): {desc}: {verdict}")
        if r["set"] in NOTALLY:
            continue
        for m, (s, _) in res.items():
            k = f"{m} m{mode:02d} ({r['set']})" if m in PER_MODE else f"{m} ({r['set']})"
            per_model.setdefault(k, []).append(s)
    return controls, per_model, lines


def gate_of(stage, roots):
    dep = GATES.get(stage)
    if dep is None:
        return True, f"gate {stage}: none"
    for root in roots:
        dd = os.path.join(root, dep)
        if os.path.isdir(dd):
            g = SK.gate(control_states(dep, dd))
            return g.ok, f"gate {stage} on {dep}: {'open' if g.ok else '; '.join(g.problems)}"
    return False, f"gate {stage}: {dep} has not run"


# ---- the narrow rule (frozen; README.md "Narrow rule") ----------------------------------------
def decided(per_model, prefix_models, key):
    """The one model of prefix_models every row of `key` holds (all decided), else None, with the
    count of rows."""
    held = []
    for m in prefix_models:
        st = per_model.get(f"{m}{key}", [])
        if st and all(s is True for s in st):
            held.append((m, len(st)))
    return held[0] if len(held) == 1 else None


def narrow(att):
    """(verdict, [clause lines], [why not]) of Q302's narrow rule over an attempt directory."""
    why, clauses, per = [], [], {}
    for s in STAGES:
        d = os.path.join(att, s)
        if not os.path.isdir(d):
            why.append(f"{s} did not run")
            continue
        c, pm, _ = verdicts(s, d)
        g = SK.gate(c)
        if not g.ok:
            why.append(f"{s} controls: {'; '.join(g.problems)}")
            continue
        for k, v in pm.items():
            per.setdefault(k, []).extend(v)
    rules = tuple(Q.RULES)
    for m, clause in ((3, "(d) RGB565"), (4, "(a) mode 4"), (5, "(a) mode 5"), (6, "(a) mode 6")):
        h = decided(per, rules, f" m{m:02d} (heldout)")
        clauses.append(f"{clause}: " + (f"{h[0]} on every pixel of {h[1]} rows" if h else
                                        "not decided"))
    st = per.get("H-AS0 (heldout)", [])
    n11 = sum(1 for x in st if x is True)
    clauses.append("(a) ARGB8888-like: " + (
        f"H-AS0 on {len(st)} of {len(st)} rows" if st and all(x is True for x in st) else
        f"not decided ({n11} of {len(st)} rows H-AS0)"))
    for m in Q.WHOLE:
        h = decided(per, ("H-WHOLE", "H-NARROW"), f" m{m:02d} (heldout)")
        clauses.append(f"(a) mode {m}: " + (f"{h[0]} on {h[1]} rows" if h else "not decided"))
    ok = []
    for m in Q.R3_MODES:
        h = decided(per, ("H-1136", "H-LOWDEP"), f" m{m:02d} (heldout)")
        ok.append(h[0] if h else None)
    clauses.append("(e) bit 25 with low bytes 0x40, 0xc0: " + (
        f"{ok[0]} in modes 0, 4, 5, 6" if len(set(ok)) == 1 and ok[0] else
        "not decided (" + ", ".join(f"{m}: {h}" for m, h in zip(Q.R3_MODES, ok)) + ")"))
    clauses.append("(b) past the target (12, 13): readings only, no frozen form")
    clauses.append("(c) mode 14: not run (E031: it faults; R35-4 (a))")
    return "NARROW", clauses, why


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        ok, msg = gate_of(argv[2], argv[3:])
        print(msg)
        return 0 if ok else 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "narrow":
        v, clauses, why = narrow(argv[2])
        print(f"NARROW-RULE: {v} (Q302 stays open on (b) and (c))")
        for c in clauses:
            print(f"  clause: {c}")
        for w in why:
            print(f"  because: {w}")
        return 0
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
