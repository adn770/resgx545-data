#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r34-q044's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 5745c8dc1a8d, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading
  score.py retire ATTEMPT_DIR          Q044's frozen retire rule (README.md "Retire rule") over
                                       the stages ATTEMPT_DIR holds: RETIRE or NARROW, and why

A kept output's 64 `row N:` lines are its 4096 dwords (raster order). Quantities (frozen in
predictions/STAGE.tsv, gen/q044.py):
  pixels  the image, dword for dword, against predictions/STAGE/NAME.MODEL.txt (sha256 frozen)
  xor     the one value every dword the stage's reference row of the mode (STAGE-mMM-ref) wrote
          differs by in this row (its sentinel dwords unchanged), over the dwords STAGE-mMM-ref2
          repeats when the table has one; "mixed" for several; a frozen "nonzero" holds on any
          reading but 0x00000000
  same    the dwords of a second reference equal to the first
  thr     (mode-4 ramp rows) "MAXCLEAR,MINSET" of the stored alpha bit over the ramp alphas of
          predictions/p2/alpha.txt; "mixed" when the two overlap
A row whose reference did not complete or printed no image is cannot tell. One SUMMARY line per
model and set (scorekit.headline), gated by the stage's controls; GATES: every stage on s0.

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
STAGES = ("s0", "p1", "p2", "pw")
REQUIRED = {s: BASE for s in STAGES}
GATES = {"p1": "s0", "p2": "s0", "pw": "s0"}
ROW = re.compile(r"^probe \S+: row (\d+): ([0-9a-fA-F ]+)$", re.M)
SENT = 0xDEADBEEF
NOTALLY = ("ref", "q012")
Q012 = (22, 34)


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


def alpha_map():
    with open(os.path.join(KP, "predictions", "p2", "alpha.txt")) as f:
        return [None if t == "-" else int(t, 16) for t in f.read().split()]


# ---- the readings (gen/q044.py's, the same rules) ---------------------------------------------
def xor_of(ref, img, ref2=None):
    if ref is None or img is None:
        return None, 0
    xs, n = set(), 0
    for i, (r, v) in enumerate(zip(ref, img)):
        if ref2 is not None and ref2[i] != r:
            continue
        if r == SENT:
            if v != SENT:
                return "mixed", n
            continue
        n += 1
        xs.add(r ^ v)
    if len(xs) != 1:
        return ("mixed" if xs else None), n
    return f"0x{xs.pop():08x}", n


def thr_of(alpha, img):
    if img is None:
        return None
    halves = [h for v in img for h in (v & 0xFFFF, v >> 16)]
    clear = [a for a, h in zip(alpha, halves) if a is not None and not h >> 15]
    sets = [a for a, h in zip(alpha, halves) if a is not None and h >> 15]
    mc, ms = (max(clear) if clear else None), (min(sets) if sets else None)
    if mc is not None and ms is not None and mc >= ms:
        return "mixed"
    return f"{'-' if mc is None else mc},{'-' if ms is None else ms}"


def name_parts(name):
    m = re.match(r"^(s0|p1|p2|pw)-m(\d\d)r?-(\w+)$", name)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (None, None, None)


def holds(rule, got):
    if got is None:
        return None
    if rule == "nonzero":
        return got != "0x00000000"
    return got == rule


# ---- verdicts ---------------------------------------------------------------------------------
def analyse(stage, d):
    """{name: dict(img, reading per quantity, extra)} of the stage's rows."""
    cases = K.rows(d, "cases.tsv")
    table = K.table(KP, stage)
    names = {r["name"] for r in table}
    imgs = {r["name"]: (pixels(K.text(d, r["name"] + ".txt"))
                        if r["name"] in cases and K.completed(cases[r["name"]]) else None)
            for r in table}
    alpha = alpha_map() if stage == "p2" else None
    out = {}
    for r in table:
        n = r["name"]
        st, mode, what = name_parts(n)
        got, extra = {}, ""
        ref = f"{stage}-m{mode:02d}-ref" if mode is not None else None
        ref2 = f"{stage}-m{mode:02d}-ref2" if mode is not None else None
        if what not in (None, "ref", "ref2") and ref in names and not n.startswith("s0-"):
            if stage == "p2" and mode == 4 and what.startswith("e"):
                got["thr"] = thr_of(alpha, imgs[n])
            else:
                r2 = imgs.get(ref2) if ref2 in names else None
                if ref2 in names and r2 is None:
                    x, k = None, 0                   # its repeat is unknown: cannot tell
                else:
                    x, k = xor_of(imgs.get(ref), imgs[n], r2)
                got["xor"] = x
                extra = f"; {k} dwords compared" + (" (where the two references agree)"
                                                     if ref2 in names else "")
        if what == "ref2":
            a, b = imgs.get(ref), imgs[n]
            got["same"] = None if a is None or b is None else str(sum(
                x == y for x, y in zip(a, b)))
        out[n] = dict(row=r, img=imgs[n], got=got, extra=extra)
    return out


def verdicts(stage, d):
    preds = K.predictions(KP, stage)
    an = analyse(stage, d)
    controls, per_model, lines = {}, {}, []
    for n, a in an.items():
        r, img = a["row"], a["img"]
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
                    got = a["got"].get(q)
                    res[m] = (holds(v, got), f"{q} {got} (frozen {v})")
        desc = "; ".join(f"{m} {t}" for m, (_, t) in res.items())
        if not res and a["got"]:
            desc = "; ".join(f"{q} {v}" for q, v in a["got"].items())
        desc += a["extra"]
        if img is None:
            desc += "; no image"
        if r["set"] == "control":
            st = None if not res or any(s is None for s, _ in res.values()) else all(
                s for s, _ in res.values())
            controls[n] = st
            lines.append(f"CONTROL {n}: {desc}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            continue
        held = [m for m, (s, _) in res.items() if s]
        verdict = (f"held {', '.join(held)}" if held else "no frozen model exact"
                   if res and any(s is False for s, _ in res.values()) else
                   "cannot tell" if res else "read (no model)")
        lines.append(f"ROW {n} ({r['set']}): {desc}: {verdict}")
        if r["set"] in NOTALLY:
            continue
        for m, (s, _) in res.items():
            per_model.setdefault(f"{m} ({r['set']})", []).append(s)
    return controls, per_model, lines


def gate_of(stage, roots):
    dep = GATES.get(stage)
    if dep is None:
        return True, f"gate {stage}: none"
    for root in roots:
        dd = os.path.join(root, dep)
        if os.path.isdir(dd):
            g = SK.gate(verdicts(dep, dd)[0])
            return g.ok, f"gate {stage} on {dep}: {'open' if g.ok else '; '.join(g.problems)}"
    return False, f"gate {stage}: {dep} has not run"


# ---- the retire rule (frozen; README.md "Retire rule") ----------------------------------------
def retire(att):
    """(verdict, [reasons]) of Q044's retire rule over the stages an attempt directory holds."""
    sys.path.insert(0, os.path.join(KP, "gen"))
    why, notes = [], []
    st = {}
    for s in STAGES:
        d = os.path.join(att, s)
        if not os.path.isdir(d):
            why.append(f"{s} did not run")
            continue
        c, _, _ = verdicts(s, d)
        g = SK.gate(c)
        if not g.ok:
            why.append(f"{s} controls: {'; '.join(g.problems)}")
        st[s] = (analyse(s, d), K.predictions(KP, s))
    # (b) bit 25: every run mode but 22 and 34 reads its H-INV25 mask or 0 (decided)
    inv, none_ = [], []
    for s in ("p1", "pw"):
        if s not in st:
            continue
        an, pr = st[s]
        for n, a in an.items():
            _, mode, what = name_parts(n)
            if what != "b25" or mode in Q012:
                continue
            got = a["got"].get("xor")
            mask = pr[n]["xor"]["H-INV25"]
            if got is None:
                why.append(f"{n}: cannot tell")
            elif got == mask:
                inv.append(mode)
            elif got == "0x00000000":
                none_.append(mode)
            else:
                why.append(f"{n}: xor {got}, neither H-INV25 ({mask}) nor 0")
    notes.append(f"bit 25: H-INV25 in {len(inv)} modes; reads 0 against a non-zero H-INV25 "
                 f"mask in {sorted(m for m in none_ if m not in INV0)}")
    # 22 and 34: read on the repeating dwords, split to Q012 (R34-4 (a)); 14 named from E031
    if "p1" in st:
        an, _ = st["p1"]
        for m in Q012:
            a = an.get(f"p1-m{m:02d}-b25")
            notes.append(f"mode {m}: xor {a['got'].get('xor') if a else None}{a['extra'] if a else ''}"
                         f" -> Q012")
    notes.append("mode 14: not run (E031: faults in both runs, nothing stored)")
    # (a) the low byte: mode 4 one of H-GE / H-GT on every equality row, nothing elsewhere
    if "p2" in st:
        an, pr = st["p2"]
        ge = gt = 0
        for n, a in an.items():
            _, mode, what = name_parts(n)
            if mode == 4 and what.startswith("e"):
                got = a["got"].get("thr")
                g1, g2 = pr[n]["thr"]["H-GE"], pr[n]["thr"]["H-GT"]
                if got == g1 and got != g2:
                    ge += 1
                elif got == g2 and got != g1:
                    gt += 1
                else:
                    why.append(f"{n}: thr {got}, neither H-GE ({g1}) nor H-GT ({g2})")
            elif what and what.startswith("w"):
                got = a["got"].get("xor")
                if got != "0x00000000":
                    why.append(f"{n}: xor {got} (H-THR1 / H-NULL: 0)")
        if ge and gt:
            why.append(f"mode 4: H-GE on {ge} rows, H-GT on {gt}")
        notes.append(f"low byte: H-GE {ge}, H-GT {gt} rows of {len(Q_EQ)}")
        if ge + gt != len(Q_EQ):
            why.append("mode 4: not every equality row decided")
    return ("RETIRE" if not why else "NARROW"), why, notes


INV0 = set()      # modes whose H-INV25 mask is 0 (filled from gen/q044.py at import of retire)
Q_EQ = ()


def _load_gen():
    global INV0, Q_EQ
    sys.path.insert(0, os.path.join(KP, "gen"))
    import q044
    INV0 = {m for m, v in q044.INV25.items() if v == 0}
    Q_EQ = q044.EQ


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        ok, msg = gate_of(argv[2], argv[3:])
        print(msg)
        return 0 if ok else 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) == 3 and argv[1] == "retire":
        _load_gen()
        v, why, notes = retire(argv[2])
        print(f"RETIRE-RULE: {v}")
        for w in why:
            print(f"  because: {w}")
        for n in notes:
            print(f"  note: {n}")
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
