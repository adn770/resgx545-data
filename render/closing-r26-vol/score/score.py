#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r26-vol's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 95445c7, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when the gate of STAGE is open (GATES)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

What the stages read (t24's probe output, kept as NAME.txt): `probe NAME: row Y: ...`, the 2048
pixels (8 hex digits each, raster order); their sha256 is E567's (comma joined).

vc: each control PASSes when its job completed and its pixel sha256 is its frozen H-E567 value
(c-cube-w5 and c-cube-w15 are frozen on two different values: both passing shows a w that acts).
vb: per bit, the pair vb-B-w0 and vb-B-w15 (and vb-B-w0r for t0b27, t0b30): cannot tell when a
job did not complete or print 2048 pixels, or the repeat differs from the w 0 job; else H-NOVOL
holds when the two images are equal at all 2048 pixels, H-VOL when they differ. Headline
H-NOVOL over the 19 bits, with vc's controls (from a root holding vc) or the gate it passed.

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what
verdicts() reads; producible(row) is the set of reading keys a row's job can produce."""
import hashlib
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

FILES = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"vc": FILES, "vb": FILES}
GATES = {"vb": "vc"}


def producible(row):
    return {"o0", "rows"} if row["args"].split()[:1] == ["probe"] else set()


# ---- readers ----------------------------------------------------------------------------------
def pixels(text):
    """the pixels (8 hex digits each, raster order) of `probe NAME: row Y: ...` lines."""
    vals = []
    for ln in text.splitlines():
        if ln.startswith("probe ") and ": row " in ln:
            vals += [v.rjust(8, "0") for v in ln.split(": ", 2)[2].split()]
    return vals


def image(text):
    v = pixels(text)
    return v if len(v) == 2048 else None


def pixsha(text):
    v = image(text)
    return hashlib.sha256(",".join(v).encode()).hexdigest() if v else None


def equal(a, b):
    return sum(x == y for x, y in zip(a, b))


# ---- the stage's kept files -------------------------------------------------------------------
class Run:
    def __init__(self, stage, d):
        self.stage, self.d = stage, d
        self.cases = K.rows(d, "cases.tsv")
        K.rows(d, "void.tsv")
        self.table = K.table(KP, stage)
        self.preds = K.predictions(KP, stage)

    def text(self, n):
        r = self.cases.get(n)
        if r is None or not K.completed(r):
            return ""
        return K.text(self.d, n + ".txt")


def _st(v):
    return "held" if v is True else "FAILED" if v is False else "cannot tell"


def vc_verdicts(r):
    controls, lines = {}, []
    for row in r.table:
        n = row["name"]
        sha = pixsha(r.text(n))
        want = r.preds.get(n, {}).get("pixsha", {}).get("H-E567")
        controls[n] = None if sha is None else sha == want
        lines.append(f"CONTROL {n}: pixels {sha} (frozen {want}): "
                     f"{'PASS' if controls[n] else _st(controls[n])}")
    return controls, {}, lines


def bits(table):
    """[(bit, [names])] in table order: vb-B-w0, vb-B-w15[, vb-B-w0r]."""
    out = {}
    for row in table:
        b = row["name"].split("-")[1]
        out.setdefault(b, []).append(row["name"])
    return list(out.items())


def vb_verdicts(r):
    per, lines = {"H-NOVOL": []}, []
    acts = []
    for b, names in bits(r.table):
        img = {n.rsplit("-", 1)[1]: image(r.text(n)) for n in names}
        w0, w15, rep = img.get("w0"), img.get("w15"), img.get("w0r", "none")
        why = ""
        if w0 is None or w15 is None:
            v, why = None, "a job of the pair did not complete or print 2048 pixels"
        elif rep is None:
            v, why = None, "the repeat did not complete or print 2048 pixels"
        elif rep != "none" and rep != w0:
            v, why = None, f"the repeat differs from w 0 at {2048 - equal(rep, w0)} pixels"
        else:
            v = w0 == w15
            why = f"{equal(w0, w15)} of 2048 pixels equal"
        per["H-NOVOL"].append(v)
        if v is False:
            acts.append(b)
        vol = None if v is None else not v
        lines.append(f"ROW vb-{b} H-NOVOL: {_st(v)}; H-VOL: {_st(vol)} ({why})")
    lines.append("BITS where w acts (H-VOL): " + (", ".join(acts) if acts else "none"))
    return {}, per, lines


def verdicts(stage, d):
    """controls {name: state}, per {model: [states]}, lines."""
    r = Run(stage, d)
    return vc_verdicts(r) if stage == "vc" else vb_verdicts(r)


def read_files(stage, d):
    verdicts(stage, d)


def gate_controls(stage, roots):
    dep = GATES.get(stage)
    for root in roots:
        d = os.path.join(root, dep) if dep else None
        if d and os.path.isdir(d):
            return verdicts(dep, d)[0]
    return None


def summary(stage, controls, per):
    out = []
    for m, states in sorted(per.items()):
        h = SK.headline(m, controls or {"(gate)": True}, states)
        out.append(f"SUMMARY: {stage}: " + (h if h.startswith(m) else f"{m}: {h}"))
    return out


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        c = gate_controls(argv[2], argv[3:])
        if c is None:
            print(f"gate {argv[2]}: {dep} has not run")
            return 1
        g = SK.gate(c)
        print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
        return 0 if g.ok else 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        if controls:
            g = SK.gate(controls)
            print("SUMMARY: " + argv[1] + ": controls " + ("all passed" if g.ok else
                                                           "; ".join(g.problems)))
        else:
            controls = gate_controls(argv[1], argv[3:])
        print("\n".join(summary(argv[1], controls, per)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
