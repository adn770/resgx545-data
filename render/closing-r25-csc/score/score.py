#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r25-csc's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 7f214e511d6a, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage is gated)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

What the stage reads (t22's probe and copy output, kept as NAME.txt):
  `probe NAME: poked SPACE:N 0xOLD -> 0xNEW`   the echo: one a poke, in the pokes' order; a poke
      `S:N=V` holds when NEW = V, `S:N^=V` when NEW = OLD ^ V; a row with no poke holds with no
      echo line. A poke row whose echo does not hold is cannot tell in every model (its premise).
  `probe NAME: row Y: ...`                     the 2048 pixels: their sha256 as E568's
  `target: WxH hash 0xH`                       the copy's target hash (E037)

Halves (gen/make.py): per format, zc a b c (zeros copy, then the fills) and bc d e f (BT.601 copy,
then the fills). A fill is decided only when every control of its half before it passed (the
copy's E037 hash, the unpoked fill's frozen pixels): otherwise cannot tell. Headlines per model
and set: fit (b, c: zeros copy then a BT.601 poke) and heldout (e, f: BT.601 copy then a zeros
poke), each with its half's controls only, so a failed BT.601-half control never voids the fit.

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what
verdicts() reads; producible(row) is the set of reading keys a row's job can produce."""
import hashlib
import os
import re
import shlex
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

REQUIRED = {"csc": (".txt", "cases.tsv", "void.tsv", "readings.tsv")}
GATES = {}
BEFORE = {"a": ("zc",), "b": ("zc", "a"), "c": ("zc", "a"),
          "d": ("bc",), "e": ("bc", "d"), "f": ("bc", "d")}
HALF_CONTROLS = {"fit": ("zc", "a"), "heldout": ("bc", "d")}


def producible(row):
    a = row["args"].split()
    if a[:1] == ["copy"]:
        return {"hash"}
    if a[:1] == ["probe"]:
        return {"echo", "o0"}
    return set()


# ---- readers ----------------------------------------------------------------------------------
_POKED = re.compile(r"^probe \S+: poked (\w+):(\d+) 0x([0-9a-f]{8}) -> 0x([0-9a-f]{8})$")
_ROW = re.compile(r"^probe \S+: row (\d+): ([0-9a-f ]+)$")
_HASH = re.compile(r"^target: \d+x\d+ hash (0x[0-9a-f]{16})$")
_SPEC = re.compile(r"^(\w+):(\d+)(\^?)=(0x[0-9a-fA-F]+|\d+)$")


def pokes(args):
    a = shlex.split(args.replace("$S", "/s").replace("$W", "/w"))
    return [a[i + 1] for i, x in enumerate(a) if x == "--poke"]


def echo(text):
    """[(space, index, old, new)] of the echo lines."""
    return [(m[1], int(m[2]), int(m[3], 16), int(m[4], 16))
            for m in map(_POKED.match, text.splitlines()) if m]


def echo_state(args, text):
    """(True, False or None, reading): every poke echoed with the word it sent."""
    want, got = pokes(args), echo(text)
    if not text:
        return None, "no output"
    if len(got) != len(want):
        return False, f"{len(got)} of {len(want)} pokes echoed"
    for spec, (sp, ix, old, new) in zip(want, got):
        m = _SPEC.match(spec)
        if not m or (m[1], int(m[2])) != (sp, ix):
            return False, f"echo {sp}:{ix} for poke {spec}"
        v = int(m[4], 0)
        if new != ((old ^ v) if m[3] else v):
            return False, f"{spec}: 0x{old:08x} -> 0x{new:08x}"
    return True, ",".join(f"{sp}:{ix}=0x{new:08x}" for sp, ix, _, new in got) or "-"


def pixsha(text):
    vals = []
    for m in map(_ROW.match, text.splitlines()):
        if m:
            vals += [v.rjust(8, "0") for v in m[2].split()]
    if len(vals) != 2048:
        return None
    return hashlib.sha256(",".join(vals).encode()).hexdigest()


def copy_hash(text):
    for m in map(_HASH.match, text.splitlines()):
        if m:
            return m[1]
    return None


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


def _models(preds, n, q):
    return dict(preds.get(n, {}).get(q, {}))


def split(n):
    """(format, suffix) of a row name yF-S."""
    f, s = n.split("-", 1)
    return f, s


def verdicts(stage, d):
    """controls {name: state}, per {(model, set): [states]}, lines."""
    r = Run(stage, d)
    controls, per, lines = {}, {}, []
    for row in r.table:
        n, t = row["name"], r.text(row["name"])
        f, s = split(n)
        if s in ("zc", "bc"):
            h = copy_hash(t)
            want = _models(r.preds, n, "hash").get("H-E037")
            controls[n] = None if h is None else h == want
            lines.append(f"CONTROL {n}: hash {h} (frozen {want}): "
                         f"{'PASS' if controls[n] else _st(controls[n])}")
            continue
        ok, why = echo_state(row["args"], t) if t else (None, "not run")
        sha = pixsha(t) if ok else None
        before = [controls.get(f"{f}-{c}") for c in BEFORE[s]]
        premise = ok is True and all(v is True for v in before)
        if row["set"] == "control":
            want = _models(r.preds, n, "pixsha").get("H-STATE")
            v = None if sha is None or not all(v is True for v in before) else sha == want
            controls[n] = v
            lines.append(f"CONTROL {n}: pixels {sha} (frozen {want}); echo {why}; before "
                         f"{', '.join(BEFORE[s])}: {before}: {'PASS' if v else _st(v)}")
            continue
        for m, want in sorted(_models(r.preds, n, "pixsha").items()):
            v = None if sha is None or not premise else sha == want
            per.setdefault((m, row["set"]), []).append(v)
            lines.append(f"ROW {n} {m}: {_st(v)} (pixels {sha}; echo {why}; controls before "
                         f"{', '.join(f'{f}-{c}' for c in BEFORE[s])}: {before})")
    return controls, per, lines


def read_files(stage, d):
    verdicts(stage, d)


def summary(stage, controls, per):
    out = []
    for (m, st), states in sorted(per.items()):
        cs = {n: v for n, v in controls.items() if split(n)[1] in HALF_CONTROLS[st]}
        h = SK.headline(f"{m} ({st})", cs, states)
        out.append(f"SUMMARY: {stage}: " + (h if h.startswith(m) else f"{m} ({st}): {h}"))
    return out


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        g = SK.gate(controls)
        print("SUMMARY: " + argv[1] + ": controls " + ("all passed" if g.ok else
                                                       "; ".join(g.problems)))
        print("\n".join(summary(argv[1], controls, per)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
