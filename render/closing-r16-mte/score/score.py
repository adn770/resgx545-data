#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r16-mte's scorer, frozen before the run. Every verdict rule comes from kit/scorekit.py
(gate, tally, headline), the kept files are read through kit/kitscore.py (byte copies of resgx545
b2b5288c82ed, pinned in FROZEN.commits); the frozen forms are gen/model.py, their maps' sha256 in
predictions/rclip.tsv (checked here: a model that drifted from the frozen maps stops the scorer).
Standard library only.

  score.py rclip KEPT_DIR [ROOTS...]   CONTROL, ROW, READING lines, then SUMMARY lines (exit 0)
  score.py gate rclip ROOTS...         exit 0 (no stage is gated by another's controls)
  score.py premise rclip KEPT_DIR      STOP lines and exit 1 when a control has no reading

The image of a row: its `probe P: row N:` lines (raster order, W x H values), or, with none, a
one-valued `probe P: o0 V (N of N)` line of N = W x H (a kept probe without --pixels). Each pixel
is G (0xff00ff00), B (0xff203040), S (0xdeadbeef) or X (any other). A form holds on a row when
every pixel is one its prediction allows (an edge pixel of the default triangle: G or B).

Row states: held (True: the frozen H-TILECLIP + H-BG + H-EN map), FAILED (False), cannot tell
(None: the job did not complete, or no whole image). Controls: g-twin-64 passes when its image is
all G; g-clear-64 (the gate) when its image is all G and equal to g-twin-64's. Both gate every row
(scorekit.headline). READING lines: every combination of form x outside x enable (gen/model.py:
9 x 2 x 3) that every decided row allows, and per dimension the values left; RETIRE says whether
one value of each is left with both controls passing (Q116's retirement rule, R16-6 a; the lead
confirms)."""
import itertools
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import model as M  # noqa: E402
import scorekit as SK  # noqa: E402

FIXED = ("cases.tsv", "void.tsv", "readings.tsv")
REQUIRED = {"rclip": (".txt",) + FIXED}
GATES = {}
ROW = re.compile(r"^probe \S+: row (\d+): ([0-9a-fA-F ]+)$", re.M)
O0 = re.compile(r"^probe \S+: o0 0x([0-9a-f]{8}) \((\d+) of (\d+)\)$", re.M)
COMBOS = tuple(itertools.product(M.FORMS, M.OUTSIDES, M.ENABLES))
CLAIM = ("Q116: the region clip keeps whole 32 x 16 tiles, first to last inclusive, rows from "
         "memory row 0; the background writes the rest; bit 31 clear turns it off (H-TILECLIP + "
         "H-BG + H-EN)")


def producible(row):
    a = row["args"].split()
    return {"pixels", "o0"} if a[:1] == ["probe"] and "--pixels" in a else set()


def word(s):
    return "held" if s is True else "FAILED" if s is False else "cannot tell"


def cword(s):
    return "PASS" if s is True else "FAILED" if s is False else "cannot tell"


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")


def image(text, w, h):
    """the code string of a probe's image, or None"""
    rows = {}
    for m in ROW.finditer(text or ""):
        rows[int(m.group(1))] = [int(t, 16) for t in m.group(2).split()]
    if rows:
        if sorted(rows) != list(range(h)) or any(len(v) != w for v in rows.values()):
            return None
        return M.codes([v for y in range(h) for v in rows[y]])
    m = O0.search(text or "")
    if m and int(m.group(2)) == int(m.group(3)) == w * h:
        return M.codes([int(m.group(1), 16)]) * (w * h)
    return None


def check_frozen(stage):
    """the frozen maps' sha256 against gen/model.py's, every row and rival"""
    preds = K.predictions(KP, stage)
    for n in M.NAMES:
        r = M.row(n)
        for c in (M.FROZEN,) + M.RIVALS:
            want = preds.get(n, {}).get("map", {}).get(M.combo_name(c))
            if want != "sha256:" + M.sha(M.predict(r, c)):
                raise SystemExit("score.py: %s %s is not the frozen map" % (n, M.combo_name(c)))


def observed(d):
    cases = K.rows(d, "cases.tsv")
    out = {}
    for t in K.table(KP, "rclip"):
        n = t["name"]
        r = M.row(n)
        out[n] = image(K.text(d, n + ".txt"), r["w"], r["h"]) if n in cases and \
            K.completed(cases[n]) else None
    return out


def verdicts(stage, d):
    check_frozen(stage)
    obs = observed(d)
    controls, rows, lines = {}, [], []
    twin = obs.get("g-twin-64")
    for t in K.table(KP, stage):
        n = t["name"]
        r = M.row(n)
        o = obs[n]
        f = M.predict(r, M.FROZEN)
        state = None if o is None else M.matches(f, o)
        also = [M.combo_name(c) for c in M.RIVALS if o is not None and M.matches(M.predict(r, c), o)]
        counts = "-" if o is None else " ".join("%s %d" % (k, o.count(k)) for k in "GBSX")
        if t["set"] == "control":
            if n == "g-clear-64" and state:
                state = None if twin is None else (o == twin)
            controls[n] = state
            lines.append("CONTROL %s: %s (%s): %s" % (n, counts, r["why"], cword(state)))
        else:
            rows.append(state)
            lines.append("ROW %s: %s: %s; rivals allowing it: %s" % (
                n, counts, word(state), ", ".join(also) if also else "none"))
    return controls, rows, lines, obs


def survivors(obs):
    """the combinations every decided row allows"""
    left = []
    for c in COMBOS:
        ok = True
        for n, o in obs.items():
            if o is not None and not M.matches(M.predict(M.row(n), c), o):
                ok = False
                break
        left.append(c) if ok else None
    return left


def readings(controls, obs):
    left = survivors(obs)
    out = ["READING rclip: %d of %d combinations allowed by every decided row: %s" % (
        len(left), len(COMBOS), ", ".join(M.combo_name(c) for c in left) or "none")]
    dims = []
    for i, (label, vals) in enumerate((("form", M.FORMS), ("outside", M.OUTSIDES),
                                       ("enable", M.ENABLES))):
        have = [v for v in vals if any(c[i] == v for c in left)]
        dims.append(have)
        out.append("READING rclip %s: %s" % (label, ", ".join(have) or "none"))
    g = SK.gate(controls)
    one = all(len(h) == 1 for h in dims)
    decided = sum(1 for o in obs.values() if o is not None)
    out.append("RETIRE rclip: %s" % (
        "yes: one form (%s), one outside (%s), one enable (%s) on %d decided rows, both controls "
        "PASS" % (dims[0][0], dims[1][0], dims[2][0], decided) if one and g.ok else
        "no: " + ("; ".join(g.problems) if not g.ok else
                  "forms left %s" % "; ".join(",".join(h) or "none" for h in dims))))
    return out


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, rows, lines, obs = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        print("\n".join(readings(controls, obs)))
        print("SUMMARY: " + argv[1] + ": " + SK.headline(CLAIM, controls, rows))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
